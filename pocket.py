import sys
from math import acos, ceil, cos, degrees, pi, radians, sin

import pyclipper
from pyclipper import PyclipperOffset
from dbgprt import dprt, dprtSet
from geometry import (ARC, LINE, MAX_VALUE, Arc, Line, calcAngle, degAtan2,
                      fix, orientation, oStr, pathDir, xyDist)

SCALE = 1000000.0

NO_SYMMETRY = 0
UPPER = 1
LOWER = 2
RIGHT = 3
LEFT = 4

def floatScale(p):
    return(float(p[0]) / SCALE, float(p[1]) / SCALE)

def intScale(p):
    return(int(p[0] * SCALE), int(p[1] * SCALE))

class pocket():
    def __init__(self, cfg):
        self.cfg = cfg
        print("test loaded")
        self.stepOver = 0.85
        self.arcs = False
        self.dbg = False
        self.symmetry = NO_SYMMETRY
        self.symmetryValues = \
        ( \
          ('none', NO_SYMMETRY), \
          ('upper', UPPER), \
          ('lower', LOWER), \
          ('right', RIGHT), \
          ('left', LEFT), \
        )
        self.cmds = \
        ( \
          ('pocket', self.pocket, True), \
          ('stepover', self.setStepOver), \
          ('pocketarcs', self.pocketArcs), \
          ('pocketdbg', self.pocketDbg), \

          ('outside', self.outside), \
          ('symmetry', self.setSymmetry), \
          # ('', self.), \
        )
        dprtSet(True)

    def setStepOver(self, args):
        self.stepOver = self.cfg.evalFloatArg(args[1]) / 100.0

    def pocketArcs(self, args):
        self.arcs = self.cfg.evalBoolArg(args[1])

    def pocketDbg(self, args):
        self.dbg = self.cfg.evalBoolArg(args[1])

    def setSymmetry(self, args):
        val = args[1].lower()
        for (x, i) in self.symmetryValues:
            if val == x:
                self.symmetry = i
                break

    def pocket(self, args, dbg=None):
        if dbg is None:
            dbg = self.dbg
        layer = args[1]
        cfg = self.cfg
        # dir = CCW
        # if cfg.dir is not None and cfg.dir == 'CW':
        #     dir = CW
        stepOver = cfg.endMillSize * self.stepOver
        cfg.ncInit()
        segments = cfg.dxfInput.getPath(layer)
        pco = PyclipperOffset()
        mp = cfg.getMillPath()
        self.last = cfg.mill.last
        for seg in segments:
            self.pDir = pathDir(seg)
            pco.Clear()
            mainPath = []
            for (i, l) in enumerate(seg):
                l.draw()
                if dbg:
                    l.prt()
                if l.type == LINE:
                    mainPath.append(intScale(l.p0))
                elif l.type == ARC:
                    self.arcLines(mainPath, l, dbg=dbg)
            if dbg:
                dprt()
                for (i, p) in enumerate(mainPath):
                    (x, y) = floatScale(p)
                    dprt("%3d (%7.4f %7.4f)" % (i, x, y))
                dprt()
            
            pco.AddPath(mainPath, pyclipper.JT_ROUND, \
                        pyclipper.ET_CLOSEDPOLYGON)
            offset = cfg.endMillSize / 2.0 + cfg.finishAllowance
            step = 0
            offsetPaths = []
            while True:
                result = pco.Execute(-int(offset * SCALE))
                if dbg:
                    dprt("%2d offset %7.4f results %d" % \
                         (step, offset, len(result)))
                if len(result) == 0:
                    break
                rData = []
                for (rNum, r) in enumerate(result):

                    # convert from list of points to lines

                    if self.arcs:
                        pLast = floatScale(r[-1])
                        index = 0
                        maxDist = -1
                        for (i, p) in enumerate(r):
                            p = floatScale(p)
                            dist = xyDist(p, pLast)
                            if dbg:
                                dprt("%3d (%7.4f %7.4f) dist %9.6f" % \
                                     (i, p[0], p[1], dist))
                            if dist > maxDist:
                                maxDist = dist
                                index = i
                            r[i] = p
                            pLast = p
                        r = r[index:] + r[:index]
                        if dbg:
                            dprt("index %d maxDist %7.4f" % (index, maxDist))
                            pLast = r[-1]
                            dprt("pLast (%7.4f %7.4f)" % (pLast[0], pLast[1]))
                            for (i, p) in enumerate(r):
                                dprt("%3d (%7.4f %7.4f) dist %9.6f" % \
                                     (i, p[0], p[1], xyDist(p, pLast)))
                                pLast = p
                                dprt()
                        path = self.makePath(r, step, rNum, dbg)
                    else:
                        pLast = floatScale(r[-1])
                        path = []
                        for (i, p) in enumerate(r):
                            p = floatScale(p)
                            if dbg:
                                dprt("%3d (%7.4f %7.4f)" % (i, p[0], p[1]))
                            l = Line(pLast, p, i)
                            txt = "s %d r %d i %d" % (step, rNum, i)
                            l.label(txt)
                            path.append(l)
                            pLast = p

                    result[rNum] = path
                        
                    if dbg:
                        dprt()
                        for l in path:
                            l.prt()
                        dprt()

                    # find shortest distance to each path

                    oData = []
                    for (oNum, oPath) in enumerate(offsetPaths):
                        lEnd = oPath[-1]
                        pEnd = lEnd.p1
                        minDist = MAX_VALUE
                        index = None
                        for (i, l) in enumerate(path):
                            dist = xyDist(pEnd, l.p0)
                            if dist < minDist:
                                minDist = dist
                                index = i
                        oData.append((index, minDist))
                    rData.append(oData)
                
                # connect to nearest path

                if dbg and len(result) > 1:
                    dprt("multiple results")
                oConnect = [False] * len(offsetPaths)
                while True:
                    minDist = MAX_VALUE
                    index = None
                    rPath = None
                    for (rNum, oData) in enumerate(rData):
                        if oData == None:
                            continue
                        rPath = rNum
                        for (oNum, (i, dist)) in enumerate(oData):
                            if dbg:
                                dprt("step %d rNum %d Onum %d index %3d "\
                                     "dist %9.6f" % \
                                     (step, rNum, oNum, i, dist))
                            if not oConnect[oNum] and dist < minDist:
                                minDist = dist
                                index = i
                                rIndex = rNum
                                oIndex = oNum
                                
                    if rPath is None:
                        break
                    if index is not None: # connect path
                        if dbg:
                            dprt("connect rIndex %d index %3d to "\
                                 "oIndex %d dist %9.6f" % \
                                 (rIndex, index, oIndex, minDist))
                        path = result[rIndex]
                        rData[rIndex] = None
                        oConnect[oIndex] = True
                        oPath = offsetPaths[oIndex]
                        oPath.append(Line(oPath[-1].p1, path[index].p0))
                        oPath += path[index:] + path[:index]
                    else:       # add new path
                        if dbg:
                            dprt("add rPath %d oNum %d" % \
                                 (rPath, len(offsetPaths)))
                        rData[rPath] = None
                        path = result[rPath]
                        path = self.closest(path)
                        offsetPaths.append(path)

                offset += stepOver
                step += 1
                if step > 99:
                    break
            for path in offsetPaths:
                mp.millPath(path, closed=False, minDist=False)

    def outside(self, args, dbg=True):
        layer = args[1]
        cfg = self.cfg
        # dir = CCW
        # if cfg.dir is not None and cfg.dir == 'CW':
        #     dir = CW
        # stepOver = cfg.endMillSize * self.stepOver
        cfg.ncInit()
        segments = cfg.dxfInput.getPath(layer)
        dxf = cfg.dxfInput
        s = self.symmetry
        if s == NO_SYMMETRY:
            pass
        elif s == UPPER:
            yMin = (dxf.yMax + dxf.yMin) / 2
            p0 = (dxf.xMin, dxf.yMax)
            p1 = (dxf.xMax, dxf.yMax)
            p2 = (dxf.xMax, yMin)
            p3 = (dxf.xMin, yMin)
        elif s == LOWER:
            pass
        elif s == RIGHT:
            pass
        elif s == LEFT:
            pass
        else:
            pass
        p0 = intScale(p0)
        p1 = intScale(p1)
        p2 = intScale(p2)
        p3 = intScale(p3)
        pco = pyclipper.PyclipperOffset()
        pc = pyclipper.Pyclipper()
        clip = (p0, p1, p2, p3)
        # mp = cfg.getMillPath()
        self.last = cfg.mill.last
        for seg in segments:
            self.pDir = pathDir(seg)
            mainPath = []
            for (i, l) in enumerate(seg):
                l.draw()
                if dbg:
                    l.prt()
                if l.type == LINE:
                    mainPath.append(intScale(l.p0))
                elif l.type == ARC:
                    self.arcLines(mainPath, l, dbg=dbg)

            if dbg:
                dprt("\nclip")
                for (i, p) in enumerate(clip):
                    (x, y) = floatScale(p)
                    dprt("%3d (%7.4f %7.4f)" % (i, x, y))

                dprt("\nmainPath")
                for (i, p) in enumerate(mainPath):
                    (x, y) = floatScale(p)
                    dprt("%3d (%7.4f %7.4f)" % (i, x, y))

            pco.Clear()
            pco.AddPath(mainPath, pyclipper.JT_ROUND, False)
            offset = int((cfg.endMillSize / 2.0) * SCALE)
            offsetResult = pco.Execute(offset)

            if dbg:
                dprt("\noffsetResult len %d" % (len(offsetResult)))
                for r in offsetResult:
                    dprt("r len %d" % (len(r)))
                    for (i, p) in enumerate(r):
                        (x, y) = floatScale(p)
                        dprt("%3d (%7.4f %7.4f)" % (i, x, y))
                    dprt()

            pc.Clear()
            pc.AddPath(clip, pyclipper.PT_CLIP, True)
            pc.AddPath(mainPath, pyclipper.PT_SUBJECT, False)
            result = pc.Execute(pyclipper.CT_INTERSECTION,
                                pyclipper.PFT_EVENODD,
                                pyclipper.PFT_EVENODD)

            if dbg:
                for r in result:
                    dprt("\nresult")
                    for (i, p) in enumerate(r):
                        (x, y) = floatScale(p)
                        dprt("%3d (%7.4f %7.4f)" % (i, x, y))
                    dprt()

    def closest(self, path):
        p0 = self.last
        minD = MAX_VALUE
        for (i, l) in enumerate(path):
            dist = xyDist(p0, l.p0)
            if dist < minD:
                minD = dist
                index = i
        path = path[index:] + path[:index]
        self.last = path[0].p0
        return(path)

    def arcLines(self, mainPath, l, err=0.001, dbg=False):
        r = l.r
        adjacent = r - err
        angle = 2 * degrees(acos(adjacent / r))
        a0 = degrees(calcAngle(l.c, l.p0))
        a1 = degrees(calcAngle(l.c, l.p1))
        if not l.swapped:   # clockwise
            if a1 < a0:
                a1 += 360.0
            if dbg:
                dprt("a0 %5.1f a1 %5.1f total %5.1f cw" % \
                     (fix(a0), fix(a1), a1 - a0))
            arcAngle = a1 - a0
            segments = int(ceil((arcAngle) / angle))
            aInc = arcAngle / segments
            # aRad = radians(aInc)
        else:               # counter clockwise
            if a0 < a1:
                a0 += 360.0
            if dbg:
                dprt("a0 %5.1f a1 %5.1f total %5.1f ccw" % \
                     (fix(a0), fix(a1), a0 - a1))
            arcAngle = a0 - a1
            segments = int(ceil((arcAngle) / angle))
            aInc = -arcAngle / segments

        if dbg:
            dprt("segments %d arcAngle %7.2f aInc %7.2f" % \
                 (segments, arcAngle, aInc))
        mainPath.append(intScale(l.p0))
        (x, y) = l.c
        aRad = radians(aInc)
        a = radians(a0) + aRad
        for i in range(1, segments):
            p = (r * cos(a) + x, r * sin(a) + y)
            if dbg:
                dprt("%2d a %7.2f (%7.2f %7.2f)" % \
                     (i, degrees(a), p[0], p[1]))
            mainPath.append(intScale(p))
            a += aRad

    def pointsArc(self, p0, p1, p2, dbg=False):
        if dbg:
            dprt("p0 (%7.4f %7.4f) p1 (%7.4f %7.4f) "\
                 "p2 (%7.4f %7.4f) %7.4f %7.4f" % \
                 (p0[0], p0[1], p1[0], p1[1], p2[0], p2[1], \
                  xyDist(p0, p1), xyDist(p1, p2)))
        (eqType0, m0, b0) = self.lineMid90(p0, p1, dbg)
        (eqType1, m1, b1) = self.lineMid90(p1, p2, dbg)
        if dbg:
            dprt("eqType0 %5s m0 %7.4f b0 %7.4f "\
                 "eqType1 %5s m1 %7.4f b1 %7.4f" % \
                 (eqType0, m0, b0, eqType1, m1, b1))
        if eqType0:
            if eqType1:
                # y = m0*x + b0
                # y = m1*x + b1
                # m0*x + b0 = m1*x + b1
                # x*(m0 - m1) = b1 - b0
                x = (b1 - b0) / (m0 - m1)
                y = m0 * x + b0
            else:
                # y = m0*x + b0
                # x = m1*y + b1
                # y = m0 * (m1*y + b1) + b0
                # y = m0*m1*y + m0*b1 + b0
                # y - m0*m1*y = m0*b1 + b0
                # y * (1 - m0*m1) = m0*b1 + b0
                # y = (m0*b1 + b0) / (1 - m0*m1)
                y = (m0*b1 + b0) / (1 - m0*m1)
                x = m1 * y + b1
        else:
            if eqType1:
                x = (m0*b1 + b0) / (1 - m0*m1)
                y = m1 * x + b1
            else:
                y = (b1 - b0) / (m0 - m1)
                x = m0 * y + b0
        c = (x, y)
        r0 = xyDist(c, p0)
        if dbg:
            r1 = xyDist(c, p1)
            r2 = xyDist(c, p2)
            dprt("c (%7.4f %7.4f) r0 %7.4f r1 %7.4f r2 %7.4f" % \
                 (c[0], c[1], r0, r1, r2))
        return((c, r0))

    def lineMid90(self, p0, p1, dbg=False):
        (x0, y0) = p0
        (x1, y1) = p1
        xM = (x0 + x1) / 2
        yM = (y0 + y1) / 2
        dx = x1 - x0
        dy = y1 - y0
        eqType = abs(dx) > abs(dy)
        if dbg:
            dprt("eqType %5s dx %10.6f dy %10.6f" % (eqType, abs(dx), abs(dy)))
        # eqType = False
        if eqType:              # if dx > dy line y = mx + b per x = -m*y + b
            m = -dy / dx        # negate slope
            # y = mx + b
            # b = y - mx
            b = xM - m * yM     # swap positions of x and y
        else:                   # if dy > dx x = my + b
            m = -dx / dy
            b = yM - m * xM
        return((not eqType, m, b))

    def makePath(self, points, step, rNum, dbg=False):
        if False:
            r = 1
            for i in range(4):
                a0 = float(i) * pi / 2 + pi / 4
                a = a0
                p0 = (r * cos(a), r * sin(a))
                for j in range(2):
                    tmp = (pi, -pi)[j]
                    a = a0 + tmp / 2
                    p1 = (r * cos(a), r * sin(a))
                    a = a0 + tmp / 1
                    p2 = (r * cos(a), r * sin(a))
                    self.pointsArc(p0, p1, p2)
            dprt()
            sys.exit()

        numPoints = len(points)
        pLast = points[-1]
        i = 0
        path = []
        # points.append(points[0])
        o0 = orientation(pLast, points[0], points[1])
        if dbg:
            dprt("path orientation %s" % oStr(o0))
        while i < numPoints:
            p0 = points[i]
            if dbg:
                dprt("i %3d (%7.4f %7.4f)" % (i, p0[0], p0[1]))
            d0 = xyDist(p0, pLast)
            j = i + 1
            pa = p0
            while j < numPoints - 1:
                pj = points[j]
                dist = xyDist(pa, pj)
                if abs(dist - d0) > 0.001:
                    if dbg:
                        dprt("dist %9.6f d0 %9.6f" % (dist, d0))
                    break
                j += 1
                pa = pj
            delta = j - i
            if delta < 4:
                l = Line(pLast, p0, i)
                txt = "s %d r %d i %d" % (step, rNum, i)
                l.label(txt)
                i += 1
                pLast = p0
            else:
                p1 = points[i + delta / 2]
                (c, r) = self.pointsArc(pLast, p1, pa)
                o = orientation(pLast, p1, pa)
                if o != o0:
                    (pLast, pa) = (pa, pLast)
                a0 = degAtan2(pLast[1] - c[1], pLast[0] - c[0])
                a1 = degAtan2(pa[1] - c[1], pa[0] - c[0])
                l = Arc(c, r, a0, a1, direction=o)
                if dbg:
                    dprt("arc %s %2d i %d (%7.4f %7.4f) %8.3f "\
                         " %d (%7.4f %7.4f) %8.3f" % \
                         (oStr(o), delta, i, pLast[0], pLast[1], a0, \
                          j, pa[0], pa[1], a1))
                i = j
                pLast = pa
            if dbg:
                l.prt()
            path.append(l)
        return(path)

        # while i < numPoints:
        #     p0 = points[i]
        #     dprt("i %3d (%7.4f %7.4f)" % (i, p0[0], p0[1]))
        #     if i < numPoints - 3:
        #         j = i + 1
        #         p1 = points[j]
        #         j += 1
        #         p2 = points[j]
        #         j += 1
        #         (c, r) = self.pointsArc(p0, p1, p2)
        #         arc = False
        #         while j < numPoints - 1:
        #             pj = points[j + 1]
        #             dist = abs(xyDist(c, pj) - r)
        #             dprt("%3d (%7.4f %7.4f) dist %10.6f" % \
        #                  (j, pj[0], pj[1], dist))
        #             if dist > 0.001:
        #                 break
        #             j += 1
        #             arc = True
        #     if arc:
        #         a0 = degAtan2(p0[1] - c[1], p0[0] - c[0])
        #         a1 = degAtan2(pj[1] - c[1], pj[0] - c[0])
        #         dprt("arc i %d (%7.4f %7.4f) %8.3f j %d (%7.4f %7.4f) %8.3f" % \
        #              (i, p0[0], p0[1], a0, j, pj[0], pj[1], a1))
        #         i = j
        #     else:
        #         dprt("%3d (%7.4f %7.4f)" % (i, p0[0], p0[1]))
        #         l = Line(pLast, p0, i)
        #         l.prt()
        #         txt = "s %d r %d i %d" % (step, rNum, i)
        #         l.label(txt)
        #         i += 1
        #     if l is not None:
        #         path.append(l)
        #     l = None
        #     pLast = p0
        # return(path)
