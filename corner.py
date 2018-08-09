from __future__ import print_function
import sys
from dbgprt import dprtSet, dprt, dflush
from geometry import Arc, Line
from geometry import calcAngle, createPath, degAtan2, fix, inside, \
    orientation, oStr, pathDir, quadrant, reverseSeg, splitArcs, xyDist
from geometry import ARC, INDEX_MARKER, LINE, CCW, CW, MIN_DIST, \
    MIN_VALUE, MAX_VALUE
from math import acos, atan2, ceil, cos, degrees, pi, radians, sin, sqrt

NO_SYMMETRY = 0
UPPER = 1
LOWER = 2
RIGHT = 3
LEFT = 4

XPLUS_YPLUS = 0
XMINUS_YPLUS = 1
XMINUS_YMINUS = 2
XPLUS_YMINUS = 3

class corner():
    def __init__(self, cfg):
        self.cfg = cfg
        print("corner loaded")
        self.dbg = False
        self.symmetry = NO_SYMMETRY
        self.quadrant = None
        self.leadRadius = 0.025
        self.passOffset = 0.027
        self.maxPasses = 20
        self.symmetryValues = \
        ( \
          ('none', NO_SYMMETRY), \
          ('upper', UPPER), \
          ('lower', LOWER), \
          ('right', RIGHT), \
          ('left', LEFT), \
        )
        self.quadrantValues = \
        ( \
          ('xplus_yplus', XPLUS_YPLUS), \
          ('xminus_yplus', XMINUS_YPLUS), \
          ('xminus_yminus', XMINUS_YMINUS), \
          ('xplus_yminus', XPLUS_YMINUS), \
        )
        self.cmds = \
        ( \
          ('corner', self.corner), \
          ('symmetry', self.setSymmetry), \
          ('quadrant', self.setQuadrant), \
          ('corpasscut', self.setPassCut), \
          ('corleadradius' , self.setLead), \
          ('corpasses' , self.setPasses), \
          # ('', self.), \
        )
        dprtSet(True)

    def setSymmetry(self, args):
        val = args[1].lower()
        for (x, i) in self.symmetryValues:
            if val == x:
                self.symmetry = i
                break

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
        s = self.symmetry
        if s == NO_SYMMETRY:
            pass
        elif s == UPPER:
            yMin = (yMax + yMin) / 2
        elif s == LOWER:
            yMax = (yMax + yMin) / 2
        elif s == RIGHT:
            xMax = (xMax + xMin) / 2
        elif s == LEFT:
            xMin = (xMax + xMin) / 2
        else:
            pass

        p0 = (xMin, yMax)
        p1 = (xMax, yMax)
        p2 = (xMax, yMin)
        p3 = (xMin, yMin)
        box = []
        box.append(Line(p0, p1))
        box.append(Line(p1, p2))
        box.append(Line(p2, p3))
        box.append(Line(p3, p0))
        layer = args[1]
        segments = cfg.dxfInput.getPath(layer)

        # dprt("\nbox")
        # for s in box:
        #     s.prt()
        #     s.draw()
        # dprt()

        seg = segments[0]

        seg0 = splitArcs(seg)
        seg1 = []
        for l in seg0:
            (x0, y0) = l.p0
            (x1, y1) = l.p1
            if l.type == ARC:
                p = ((x0 + x1) / 2, (y0 + y1) / 2)
                if inside(p, box) == 1:
                    seg1.append(l)
            elif l.type == LINE:
                if (x0 < xMin) or (x0 > xMax) or (y0 < yMin) or (y0 > yMax):
                    continue
                seg1.append(l)

        self.closePath(seg1)
        for s in seg1:
            s.prt()
            s.draw()

        self.setTrim()

        offset = cfg.endMillSize / 2.0 + cfg.finishAllowance

        dprt("\nfind max dist")
        maxD = MIN_VALUE
        for l in seg1:
            if l.index == INDEX_MARKER:
                continue
            d = l.pointDistance((self.trimX, self.trimY))
            if d is not None:
                l.prt()
                dprt("d %7.4f" % (d))
                maxD = max(maxD, d)
        dprt("maxD %7.4f" % (maxD))

        path = []
        for i in range(self.maxPasses):
            dprt("\npass %2d offset %7.4f\n" % (i, offset))
            seg2 = createPath(seg1, offset, outside=True, keepIndex=True,
                              split=False, dbg=False)[0]

            dprt()
            seg3 = self.trim(seg2)

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

        self.addEntry(finalPath)
        self.addExit(finalPath)

        dprt()
        for l in finalPath:
            l.prt()
            l.draw()

        mp = cfg.getMillPath()
        mp.millPath(finalPath, closed=False, minDist=False)

    def addEntry(self, seg):
        l = seg[0]
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
        seg.insert(0, l)

    def addExit(self, seg):
        l = seg[-1]
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
        seg.append(l)

    def trim(self, seg):
        dprt("trim start")
        rtnSeg = []
        for l in seg:
            if l.index == INDEX_MARKER:
                continue
            if l.type == ARC:
                if xyDist((self.trimX, self.trimY), l.c) < l.r:
                    continue
            # elif l.type == LINE:
            #     rtnSeg.append(l)
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
                    rtnSeg.append(l1)
                else:
                    dprt("vert returned None")
            else:
                dprt("horz returned None")
        dprt("\ntrim done")
        return(rtnSeg)

    def setTrim(self):
        cfg = self.cfg
        dxf = cfg.dxfInput
        draw = cfg.draw
        offset = self.cfg.endMillSize / 2.0
        q = self.quadrant
        dprt("xMin %7.4f xMax %7.4f ymin %7.4f yMax %7.4f" % \
             (dxf.xMin, dxf.xMax, dxf.yMin, dxf.yMax))
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

    def closePath(self, seg):
        q = self.quadrant
        if q == XPLUS_YPLUS:
            p = (self.setMinX(seg), self.setMinY(seg))
        elif q == XMINUS_YPLUS:
            p = (self.setMaxX(seg), self.setMinY(seg))
        elif q == XMINUS_YMINUS:
            p = (self.setMaxX(seg), self.setMaxY(seg))
        elif q == XPLUS_YMINUS:
            p = (self.setMinX(seg), self.setMaxY(seg))
        pStr = seg[0].p0
        pEnd = seg[-1].p1
        seg.append(Line(pEnd, p, i=INDEX_MARKER))
        seg.append(Line(p, pStr, i=INDEX_MARKER))

    def setMinX(self, seg):
        minX = MAX_VALUE
        for l in seg:
            x0 = l.p0[0]
            x1 = l.p1[0]
            minX = min(minX, x0, x1)
        self.minX = minX
        return(minX)

    def setMaxX(self, seg):
        maxX = MIN_VALUE
        for l in seg:
            x0 = l.p0[0]
            x1 = l.p1[0]
            maxX = max(maxX, x0, x1)
        self.maxX = maxX
        return(maxX)

    def setMinY(self, seg):
        minY = MAX_VALUE
        for l in seg:
            y0 = l.p0[1]
            y1 = l.p1[1]
            minY = min(minY, y0, y1)
        self.minY = minY
        return(minY)

    def setMaxY(self, seg):
        maxY = MIN_VALUE
        for l in seg:
            y0 = l.p0[1]
            y1 = l.p1[1]
            maxY = max(maxY, y0, y1)
        self.maxY = maxY
        return(maxY)
            
