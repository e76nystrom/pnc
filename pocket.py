from __future__ import print_function
import pyclipper
from dbgprt import dprtSet, dprt, dflush
from geometry import Arc, Line
from geometry import calcAngle, xyDist
from geometry import ARC, LINE, CCW, CW, MIN_DIST, MAX_VALUE
from math import acos, ceil, cos, degrees, radians, sin, sqrt

SCALE = 10000.0

class pocket():
    def __init__(self, cfg):
        self.cfg = cfg
        print("test loaded")
        self.stepOver = 0.85
        self.cmds = \
        ( \
          ('pocket', self.pocket), \
          ('stepover', self.setStepOver), \
          # ('', self.), \
        )
        dprtSet(True)

    def setStepOver(self, args):
        self.stepOver = float(args[1]) / 100.0

    def pocket(self, args):
        layer = args[1]
        cfg = self.cfg
        dir = CCW
        if cfg.dir is not None and cfg.dir == 'CW':
            dir = CW
        stepOver = cfg.endMillSize * self.stepOver
        cfg.ncInit()
        segments = cfg.dxfInput.getPath(layer)
        pco = pyclipper.PyclipperOffset()
        mp = cfg.getMillPath()
        self.last = cfg.mill.last
        for seg in segments:
            pco.Clear()
            mainPath = []
            for (i, l) in enumerate(seg):
                l.draw()
                l.prt()
                if l.type == LINE:
                    (x, y) = l.p0
                    # dprt("%2d (%7.4f %7.4f)" % (i, x, y))
                    mainPath.append((int(SCALE * x), int(SCALE * y)))
                elif l.type == ARC:
                    self.arcLines(mainPath, l)
            dprt()
            for (i, (x, y)) in enumerate(mainPath):
                dprt("%3d (%7.4f %7.4f)" % (i, float(x) / SCALE, float(y) / SCALE))
            dprt()
            
            pco.AddPath(mainPath, pyclipper.JT_ROUND, \
                        pyclipper.ET_CLOSEDPOLYGON)
            offset = cfg.endMillSize / 2.0 + cfg.finishAllowance
            step = 0
            offsetPaths = []
            while True:
                result = pco.Execute(-int(offset * SCALE))
                dprt("%2d offset %7.4f results %d" % (step, offset, len(result)))
                if len(result) == 0:
                    break
                rData = []
                for (rNum, r) in enumerate(result):

                    # convert from list of points to lines

                    (x, y) = r[-1]
                    pLast = (float(x) / SCALE, float(y) / SCALE)
                    path = []
                    for (i, (x, y)) in enumerate(r):
                        x = float(x) / SCALE
                        y = float(y) / SCALE
                        dprt("%3d (%7.4f %7.4f)" % (i, x, y))
                        p = (x, y)
                        l = Line(pLast, p, i)
                        txt = "s %d r %d i %d" % (step, rNum, i)
                        l.label(txt)
                        path.append(l)
                        pLast = p

                    result[rNum] = path
                        
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

                if len(result) > 1:
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
                            dprt("step %d rNum %d Onum %d index %3d dist %7.4f" % \
                                 (step, rNum, oNum, i, dist))
                            if not oConnect[oNum] and dist < minDist:
                                minDist = dist
                                index = i
                                rIndex = rNum
                                oIndex = oNum
                                
                    if rPath is None:
                        break
                    if index is not None: # connect path
                        dprt("connect rIndex %d index %3d to "\
                             "oIndex %d dist %7.4f" % \
                             (rIndex, index, oIndex, minDist))
                        path = result[rIndex]
                        rData[rIndex] = None
                        oConnect[oIndex] = True
                        oPath = offsetPaths[oIndex]
                        oPath.append(Line(oPath[-1].p1, path[index].p0))
                        oPath += path[index:] + path[:index]
                    else:       # add new path
                        dprt("add rPath %d oNum %d" % (rPath, len(offsetPaths)))
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

    def arcLines(self, mainPath, l, err=0.001):
        r = l.r
        adjacent = r - err
        # halfCord = sqrt(r*r - adjacent*adjacent)
        angle = 2 * degrees(acos(adjacent / r))
        a0 = degrees(calcAngle(l.c, l.p0))
        a1 = degrees(calcAngle(l.c, l.p1))
        (x, y) = l.c
        if not l.swapped:   # clockwise
            if a1 < a0:
                a1 += 360.0
            # dprt("a0 %5.1f a1 %5.1f total %5.1f cw" % \
            #       (fix(a0), fix(a1), a1 - a0))
            arcAngle = a1 - a0
            segments = int(ceil((arcAngle) / angle))
            aInc = arcAngle / segments
            aRad = radians(aInc)
        else:               # counter clockwise
            if a0 < a1:
                a0 += 360.0
            # dprt("a0 %5.1f a1 %5.1f total %5.1f ccw" % \
            #       (fix(a0), fix(a1), a0 - a1))
            arcAngle = a0 - a1
            segments = int(ceil((arcAngle) / angle))
            aInc = -arcAngle / segments

        # mainPath.append((int(l.p0[0] * SCALE), int(l.p0[1] * SCALE)))
        aRad = radians(aInc)
        a = radians(a0)
        for i in range(1, segments-1):
            p = (int((r * cos(a) + x) * SCALE), int((r * sin(a) + y) * SCALE))
            mainPath.append(p)
            a += aRad
        mainPath.append((int(l.p1[0] * SCALE), int(l.p1[1] * SCALE)))
