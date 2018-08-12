from __future__ import print_function
import sys
from dbgprt import dprtSet, dprt, dflush
from geometry import Arc, Line
from geometry import calcAngle, createPath, degAtan2, fix, inside, \
    orientation, oStr, pathDir, quadrant, reverseSeg, splitArcs, xyDist
from geometry import ARC, INDEX_MARKER, LINE, CCW, CW, MIN_DIST, \
    MIN_VALUE, MAX_VALUE
from math import acos, atan2, ceil, cos, degrees, pi, radians, sin, sqrt

XPLUS_YPLUS   = 0
XMINUS_YPLUS  = 1
XMINUS_YMINUS = 2
XPLUS_YMINUS  = 3
XPLUS  = 4
YPLUS  = 5
XMINUS = 6
YMINUS = 7

SIMPLE_BOX = False

class corner():
    def __init__(self, cfg):
        self.cfg = cfg
        print("corner loaded")
        self.dbg = False
        self.quadrant = None
        self.leadRadius = 0.025
        self.passOffset = 0.027
        self.maxPasses = 0
        self.quadrantValues = \
        ( \
          ('xplus_yplus',   XPLUS_YPLUS), \
          ('xminus_yplus',  XMINUS_YPLUS), \
          ('xminus_yminus', XMINUS_YMINUS), \
          ('xplus_yminus',  XPLUS_YMINUS), \
          ('xplus',  XPLUS), \
          ('yplus',  YPLUS), \
          ('xminus', XMINUS), \
          ('yminus', YMINUS), \
        )
        self.cmds = \
        ( \
          ('corner', self.corner), \
          ('quadrant', self.setQuadrant), \
          ('corpasscut', self.setPassCut), \
          ('corleadradius' , self.setLead), \
          ('corpasses' , self.setPasses), \
          # ('', self.), \
        )
        dprtSet(True)

    def setQuadrant(self, args):
        val = args[1].lower()
        for (x, i) in self.quadrantValues:
            if val == x:
                self.quadrant = i
                break

    def setPassCut(self, args):
        self.offset = float(args[1])

    def setLead(self, args):
        self.leadRadius = float(args[1])

    def setPasses(self, args):
        self.maxPasses = int(args[1])
          
    def corner(self, args, dbg=True):
        cfg = self.cfg
        dir = CCW
        if cfg.dir is not None and cfg.dir == 'CW':
            dir = CW
        cfg.ncInit()

        dxf = cfg.dxfInput
        xMin = dxf.xMin
        xMax = dxf.xMax
        yMin = dxf.yMin
        yMax = dxf.yMax

        if SIMPLE_BOX:
            q = self.quadrant
            if q == XPLUS_YPLUS:
                xMin = (xMax + xMin) / 2
                yMin = (yMax + yMin) / 2
            elif q == XMINUS_YPLUS:
                xMax = (xMax + xMin) / 2
                yMin = (yMax + yMin) / 2
            elif q == XMINUS_YMINUS:
                xMax = (xMax + xMin) / 2
                yMax = (yMax + yMin) / 2
            elif q == XPLUS_YMINUS:
                xMin = (xMax + xMin) / 2
                yMax = (yMax + yMin) / 2

            p0 = (xMin, yMax)
            p1 = (xMax, yMax)
            p2 = (xMax, yMin)
            p3 = (xMin, yMin)
            box = []
            box.append(Line(p0, p1))
            box.append(Line(p1, p2))
            box.append(Line(p2, p3))
            box.append(Line(p3, p0))

            dprt("\nsimple box")
            for l in box:
                l.prt()
                # l.draw()
            dprt()

        layer = args[1]
        segments = cfg.dxfInput.getPath(layer)

        # for seg in segments:
        #     for l in seg:
        #         l.prt()
        #         l.draw()
        #     dprt()

        mp = cfg.getMillPath()
        for seg in segments:
            splitSeg = splitArcs(seg)

            # for l in splitSeg:
            #     l.draw()

            if not SIMPLE_BOX:
                box = self.createBox(splitSeg)
                if box is None:
                    continue
                dprt("\ngeneral box")
                for l in box:
                    l.prt()
                    l.draw()
                dprt()
                
            seg1 = []
            for l in splitSeg:
                (x0, y0) = l.p0
                (x1, y1) = l.p1
                if l.type == ARC:
                    p = ((x0 + x1) / 2, (y0 + y1) / 2)
                    if (inside(p, box) & 1) == 0:
                        continue
                elif l.type == LINE:
                    if (inside(l.p0, box) & 1) == 0 and \
                       (inside(l.p1, box) & 1) == 0:
                        continue
                seg1.append(l)

            dprt("seg len %d" % (len(seg1)))
            if len(seg1) == 0:
                continue

            # for l in seg1:
            #     l.prt()
            #     l.draw()

            self.closePath(seg1)

            for l in seg1:
                l.prt()
                l.draw()

            if self.quadrant <= XPLUS_YMINUS:
                self.setTrim()

            offset = cfg.endMillSize / 2.0 + cfg.finishAllowance

            passes = self.maxPasses
            passOffset = self.passOffset
            if passes == 0:
                dprt("\nfind max dist")
                maxD = MIN_VALUE
                for l in seg1:
                    if l.index <= INDEX_MARKER:
                        continue
                    d = l.pointDistance((self.trimX, self.trimY))
                    if d is not None:
                        l.prt()
                        dprt("d %7.4f" % (d))
                    maxD = max(maxD, d)

                total = maxD - offset
                passes = int(round(total / self.passOffset))
                passOffset = total / passes
                dprt("maxD %7.4f total %7.4f passes %d passOffset %7.4f" % \
                     (maxD, total, passes, self.passOffset))

            path = []
            for i in range(passes):
                dprt("\npass %2d offset %7.4f\n" % (i, offset))
                seg2 = createPath(seg1, offset, outside=True, keepIndex=True,
                                  split=False, dbg=False)[0]


                if self.quadrant <= XPLUS_YMINUS:
                    dprt()
                    seg3 = self.trim(seg2)
                else:
                    seg3 = []
                    for l in seg2:
                        if l.index <= INDEX_MARKER:
                            continue
                        seg3.append(l)

                print("seg3Len %d" % (len(seg3)))
                if len(seg3) == 0:
                    break

                path.append(seg3)

                # dprt()
                # for l in seg3:
                #     l.prt()
                #     l.draw()

                offset += self.passOffset

            finalPath = []
            lastPoint = None
            for (i, seg) in enumerate(path):
                if (i & 1) != 0:
                    seg = reverseSeg(seg)
                if lastPoint is not None:
                    finalPath.append(Line(lastPoint, seg[0].p0))
                finalPath += seg
                lastPoint = finalPath[-1].p1
            finalPath = reverseSeg(finalPath, makeCopy=False)

            if self.quadrant <= XPLUS_YMINUS:
                self.addEntry(finalPath)
                self.addExit(finalPath)
            else:
                self.addEntry1(finalPath)
                self.addExit1(finalPath)

            dprt()
            for l in finalPath:
                l.prt()
                l.draw()

            mp.millPath(finalPath, closed=False, minDist=False)

    def addEntry(self, path):
        l = path[0]
        (x, y) = l.p0
        dx = x - l.p1[0]
        dy = y - l.p1[1]
        r = self.leadRadius
        if abs(x - self.trimX) < MIN_DIST:
            if self.xPlus:
                x += r
                if dy > 0:
                    a0 = 90;  a1 = 180; dir = CCW; en = 0
                else:
                    a0 = 180; a1 = 270; dir = CW;  en = 1
            else:
                x -= r
                if dy < 0:
                    a0 = 270; a1 = 360; dir = CCW; en = 2
                else:
                    a0 = 0;   a1 = 90;  dir = CW;  en = 3
        elif abs(y - self.trimY) < MIN_DIST:
            if self.yPlus:
                y += r
                if dx < 0:
                    a0 = 180; a1 = 270; dir = CCW; en = 4
                else:
                    a0 = 270; a1 = 360; dir = CW;  en = 5
            else:
                y -= r
                if dx > 0:
                    a0 = 0;   a1 = 90;  dir = CCW; en = 6
                else:
                    a0 = 90;  a1 = 180; dir = CW;  en = 7
        dprt("entry %d dir %s" % (en, oStr(self.cfg.dir)))
        l = Arc((x, y), r, a0, a1, dir=dir)
        path.insert(0, l)

    def addEntry1(self, path):
        q = self.quadrant
        (x, y) = path[0].p0
        (xEnd, yEnd) = path[-1].p1
        r = self.leadRadius
        if q == XPLUS:
            if y > yEnd:
                y += r
                a0 = 180; a1 = 270; dir = CCW; en = 0
            else:
                y -= r
                a0 = 90;  a1 = 180; dir = CW;  en = 1
        elif q == YPLUS:
            pass
        elif q == XMINUS:
            pass
        elif q == YMINUS:
            pass
        dprt("entry %d dir %s" % (en, oStr(self.cfg.dir)))
        l = Arc((x, y), r, a0, a1, dir=dir)
        path.insert(0, l)

    def addExit(self, path):
        l = path[-1]
        (x, y) = l.p1
        dx = x - l.p0[0]
        dy = y - l.p0[1]
        r = self.leadRadius
        if abs(x - self.trimX) < MIN_DIST:
            if self.xPlus:
                x += r
                if dy > 0:
                    a0 = 90;  a1 = 180; dir = CW;  ex = 0
                else:
                    a0 = 180; a1 = 270; dir = CCW; ex = 1
            else:
                x -= r
                if dy < 0:
                    a0 = 270; a1 = 360; dir = CW;  ex = 2
                else:
                    a0 = 0;   a1 = 90;  dir = CCW; ex = 3
        elif abs(y - self.trimY) < MIN_DIST:
            if self.yPlus:
                y += r
                if dx < 0:
                    a0 = 180; a1 = 270; dir = CW;  ex = 4
                else:
                    a0 = 270; a1 = 360; dir = CCW; ex = 5
            else:
                y -= r
                if dx > 0:
                    a0 = 0;   a1 = 90;  dir = CW;  ex = 6
                else:
                    a0 = 90;  a1 = 180; dir = CCW; ex = 7
        dprt("exit %d dir %s" % (ex, oStr(self.cfg.dir)))
        l = Arc((x, y), r, a0, a1, dir=dir)
        path.append(l)

    def addExit1(self, path):
        q = self.quadrant
        (x, y) = path[-1].p1
        (xStr, yStr) = path[0].p0
        r = self.leadRadius
        if q == XPLUS:
            if y > yStr:
                y += r
                a0 = 180; a1 = 270; dir = CW; ex = 0
            else:
                y -= r
                a0 = 90;  a1 = 180; dir = CCW;  ex = 1
        elif q == YPLUS:
            pass
        elif q == XMINUS:
            pass
        elif q == YMINUS:
            pass
        dprt("exit %d dir %s" % (ex, oStr(self.cfg.dir)))
        l = Arc((x, y), r, a0, a1, dir=dir)
        path.append(l)

    def trim(self, path):
        dprt("trim start")
        rtnPath = []
        for l in path:
            if l.index == INDEX_MARKER:
                continue
            if l.type == ARC:
                if xyDist((self.trimX, self.trimY), l.c) < l.r:
                    continue
            # elif l.type == LINE:
            #     rtnPath.append(l)
            #     continue
            dprt()
            l.prt()
            dprt("horz trim")
            l1 = l.horizontalTrim(self.trimY, self.yPlus)
            if l1 != None:
                l1.prt()
                dprt("vert trim")
                l1 = l.verticalTrim(self.trimX, self.xPlus)
                if l1 != None:
                    l1.prt()
                    rtnPath.append(l1)
                else:
                    dprt("vert returned None")
            else:
                dprt("horz returned None")
        dprt("\ntrim done")
        return(rtnPath)

    def createBox(self, path):
            dxf = self.cfg.dxfInput
            xMin = dxf.xMin
            xMax = dxf.xMax
            yMin = dxf.yMin
            yMax = dxf.yMax
            q = self.quadrant
            if q <= XPLUS_YMINUS:
                p = self.findQuadrantPoints(path)
                if p is None:
                    return(None)
                if q == XPLUS_YPLUS:
                    (xMin, yMin) = p
                elif q == XMINUS_YPLUS:
                    (xMax, yMin) = p
                elif q == XMINUS_YMINUS:
                    (xMax, yMax) = p
                elif q == XPLUS_YMINUS:
                    (xMin, yMax) = p
                p0 = (xMin, yMax)
                p1 = (xMax, yMax)
                p2 = (xMax, yMin)
                p3 = (xMin, yMin)
            else:
                p0 = (xMin, yMax)
                p1 = (xMax, yMax)
                p2 = (xMax, yMin)
                p3 = (xMin, yMin)
                (xStr, yStr) = path[0].p0
                (xEnd, yEnd) = path[-1].p1
                if q == XPLUS:
                    if abs(xStr - xEnd) > MIN_DIST:
                        if xEnd < xStr:
                            xStr = xEnd
                    p0 = (xStr, yMax)
                    p3 = (xStr, yMin)
                elif q == YPLUS:
                    pass
                elif q == XMINUS:
                    pass
                elif q == YMINUS:
                    pass

            box = []
            box.append(Line(p0, p1))
            box.append(Line(p1, p2))
            box.append(Line(p2, p3))
            box.append(Line(p3, p0))
            return(box)

    def findQuadrantPoints(self, path):
        if not self.pathInQuadrant(path):
            return(None)
        q = self.quadrant
        if q == XPLUS_YPLUS:
            pX = self.getPtForMaxX(path)
            pY = self.getPtForMaxY(path)
        elif q == XMINUS_YPLUS:
            pX = self.getPtForMinX(path)
            pY = self.getPtForMaxY(path)
        elif q == XMINUS_YMINUS:
            pX = self.getPtForMinX(path)
            pY = self.getPtForMinY(path)
        elif q == XPLUS_YMINUS:
            pX = self.getPtForMaxX(path)
            pY = self.getPtForMinY(path)
        elif q == XPLUS:
            pass
        elif q == YPLUS:
            pass
        elif q == XMINUS:
            pass
        elif q == YMINUS:
            pass
        (x, y) = (pY[0], pX[1])
        return((x, y))

    def pathInQuadrant(self, path):
        xMax = yMax = MIN_VALUE
        xMin = yMin = MAX_VALUE
        for l in path:
            l.prt()
            for (x, y) in (l.p0, l.p1):
                if x > xMax:    # check x
                    xMax = x
                if x < xMin:
                    xMin = x
                if y > yMax:    # check y
                    yMax = y
                if y < yMin:
                    yMin = y
        dxf = self.cfg.dxfInput
        q = self.quadrant
        if q == XPLUS_YPLUS:
            result = abs(xMax - dxf.xMax) < MIN_DIST and \
                     abs(yMax - dxf.yMax) < MIN_DIST
        elif q == XMINUS_YPLUS:
            result = abs(xMin - dxf.xMin) < MIN_DIST and \
                     abs(yMax - dxf.yMax) < MIN_DIST
        elif q == XMINUS_YMINUS:
            result = abs(xMin - dxf.xMin) < MIN_DIST and \
                     abs(yMin - dxf.yMin) < MIN_DIST
        elif q == XPLUS_YMINUS:
            result = abs(xMax - dxf.xMax) < MIN_DIST and \
                     abs(yMin - dxf.yMin) < MIN_DIST
        elif q == XPLUS:
            result = abs(xMax - dxf.xMax) < MIN_DIST
        elif q == YPLUS:
            result = abs(yMax - dxf.yMax) < MIN_DIST
        elif q == XMINUS:
            result = abs(xMin - dxf.xMin) < MIN_DIST
        elif q == YMINUS:
            result = abs(yMin - dxf.yMin) < MIN_DIST
        return(result)

    def getPtForMinX(self, path):
        minX = MAX_VALUE
        for l in path:
            if l.p0[0] < minX:
                p = l.p0
                minX = l.p0[0]
            if l.p1[0] < minX:
                p = l.p1
                minX = l.p1[0]
        return(p)

    def getPtForMaxX(self, path):
        maxX = MIN_VALUE
        for l in path:
            if l.p0[0] > maxX:
                p = l.p0
                maxX = l.p0[0]
            if l.p1[0] > maxX:
                p = l.p1
                maxX = l.p1[0]
        return(p)

    def getPtForMinY(self, path):
        minY = MAX_VALUE
        for l in path:
            if l.p0[1] < minY:
                p = l.p0
                minY = l.p0[1]
            if l.p1[1] < minY:
                p = l.p1
                minY = l.p1[1]
        return(p)
                
    def getPtForMaxY(self, path):
        maxY = MIN_VALUE
        for l in path:
            if l.p0[1] > maxY:
                p = l.p0
                maxY = l.p0[1]
            if l.p1[1] > maxY:
                p = l.p1
                maxY = l.p1[1]
        return(p)

    def setTrim(self):
        cfg = self.cfg
        dxf = cfg.dxfInput
        draw = cfg.draw
        offset = self.cfg.endMillSize / 2.0
        dprt("xMin %7.4f xMax %7.4f ymin %7.4f yMax %7.4f" % \
             (dxf.xMin, dxf.xMax, dxf.yMin, dxf.yMax))
        q = self.quadrant
        if q == XPLUS_YPLUS:
            self.xPlus = True
            self.yPlus = True
            self.trimX = dxf.xMax + offset
            self.trimY = dxf.yMax + offset
            self.refY = self.minY
            draw.move((dxf.xMin, self.trimY))
            draw.line((self.trimX, self.trimY))
            draw.line((self.trimX, self.refY))
        elif q == XMINUS_YPLUS:
            self.xPlus = False
            self.yPlus = True
            self.trimX = dxf.xMin - offset
            self.trimY = dxf.yMax + offset
            self.refY = self.minY
            draw.move((dxf.xMax, self.trimY))
            draw.line((self.trimX, self.trimY))
            draw.line((self.trimX, self.refY))
        elif q == XMINUS_YMINUS:
            self.xPlus = False
            self.yPlus = False
            self.trimX = dxf.xMin - offset
            self.trimY = dxf.yMin - offset
            self.refY = self.maxY
            draw.move((dxf.xMax, self.trimY))
            draw.line((self.trimX, self.trimY))
            draw.line((self.trimX, self.refY))
        elif q == XPLUS_YMINUS:
            self.xPlus = True
            self.yPlus = False
            self.trimX = dxf.xMax + offset
            self.trimY = dxf.yMin - offset
            self.refY = self.maxY
            draw.move((dxf.xMin, self.trimY))
            draw.line((self.trimX, self.trimY))
            draw.line((self.trimX, self.refY))
        elif q == XPLUS:
            pass
        elif q == YPLUS:
            pass
        elif q == XMINUS:
            pass
        elif q == YMINUS:
            pass

    def closePath(self, path):
        q = self.quadrant
        if q <= XPLUS_YMINUS:
            if q == XPLUS_YPLUS:
                p = (self.setMinX(path), self.setMinY(path))
            elif q == XMINUS_YPLUS:
                p = (self.setMaxX(path), self.setMinY(path))
            elif q == XMINUS_YMINUS:
                p = (self.setMaxX(path), self.setMaxY(path))
            elif q == XPLUS_YMINUS:
                p = (self.setMinX(path), self.setMaxY(path))
            pStr = path[0].p0
            pEnd = path[-1].p1
            path.append(Line(pEnd, p, i=INDEX_MARKER))
            path.append(Line(p, pStr, i=INDEX_MARKER))
        else:
            path[0].prt()
            path[-1].prt()
            (xStr, yStr) = pStr = path[0].p0
            (xEnd, yEnd) = pEnd = path[-1].p1
            dprt("xStr %7.4f yStr %7.4f xEnd %7.4f yEnd %7.4f" %
                 (xStr, yStr, xEnd, yEnd))
            if q == XPLUS:
                if abs(xStr - xEnd) < MIN_DIST:
                    path.append(Line(pEnd, pStr, i=INDEX_MARKER))
                else:
                    if xStr < xEnd:
                        l0Vertical = True
                        p = (xStr, yEnd)
                    else:
                        l0Vertical = False
                        p = (xEnd, yStr)
                    dprt("x %7.4f y %7.4f" % p)
                    l0 = Line(pEnd, p, i=INDEX_MARKER)
                    l1 = Line(p, pStr, i=INDEX_MARKER)
                    if l0Vertical:
                        l0.index -= 1
                    else:
                        l1.index -= 1
                    path.append(l0)
                    path.append(l1)
            elif q == YPLUS:
                pass
            elif q == XMINUS:
                pass
            elif q == YMINUS:
                pass
            dprt()

    def setMinX(self, path):
        minX = MAX_VALUE
        for l in path:
            x0 = l.p0[0]
            x1 = l.p1[0]
            minX = min(minX, x0, x1)
        self.minX = minX
        return(minX)

    def setMaxX(self, path):
        maxX = MIN_VALUE
        for l in path:
            x0 = l.p0[0]
            x1 = l.p1[0]
            maxX = max(maxX, x0, x1)
        self.maxX = maxX
        return(maxX)

    def setMinY(self, path):
        minY = MAX_VALUE
        for l in path:
            y0 = l.p0[1]
            y1 = l.p1[1]
            minY = min(minY, y0, y1)
        self.minY = minY
        return(minY)

    def setMaxY(self, path):
        maxY = MIN_VALUE
        for l in path:
            y0 = l.p0[1]
            y1 = l.p1[1]
            maxY = max(maxY, y0, y1)
        self.maxY = maxY
        return(maxY)
