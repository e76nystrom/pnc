from __future__ import print_function
import sys
from dbgprt import dprtSet, dprt, dflush
from geometry import Arc, Line
from geometry import calcAngle, createPath, degAtan2, fix, inside, \
    orientation, oStr, pathDir, quadrant, splitArcs, xyDist
from geometry import ARC, INDEX_MARKER, LINE, CCW, CW, MIN_DIST, MAX_VALUE
from math import acos, atan2, ceil, cos, degrees, pi, radians, sin, sqrt

NO_SYMMETRY = 0
UPPER = 1
LOWER = 2
RIGHT = 3
LEFT = 4

XPLUS_YPLUS = 0
XMINUS_YPLUS = 1
XMINUS_YMINUS = 2
XPLUS_YMINUS = 2

class corner():
    def __init__(self, cfg):
        self.cfg = cfg
        print("corner loaded")
        self.dbg = False
        self.symmetry = NO_SYMMETRY
        self.quadrant = None
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
                if (x0 < xMin) or (x0 > xMax) or (y0 < yMin) or (yMin > yMax):
                    continue
                seg1.append(l)

        self.closePath(seg1)
        for s in seg1:
            s.prt()
            s.draw()

        self.setTrim()

        offset = cfg.endMillSize / 2.0 + cfg.finishAllowance
        for i in range(15):
            dprt("\npass %2d\n" % (i))
            seg2 = createPath(seg1, offset, outside=True, keepIndex=True,
                              split=False, dbg=False)[0]
            if len(seg2) == 0:
                break

            dprt()
            seg3 = self.trim(seg2)

            dprt()
            for s in seg3:
                s.prt()
                s.draw()

            offset += 0.025

    def trim(self, seg):
        rtnSeg = []
        for l in seg:
            if l.index == INDEX_MARKER:
                continue
            l1 = l.horizontalTrim(self.trimY, self.yPlus)
            if l1 != None:
                l1 = l.verticalTrim(self.trimX, self.xPlus)
                if l1 != None:
                    l1.prt()
                    rtnSeg.append(l1)
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
            draw.move((dxf.xMin, self.trimY))
            draw.line((self.trimX, self.trimY))
            draw.line((self.trimX, dxf.yMin))
        elif q == XMINUS_YPLUS:
            self.xPlus = False
            self.yPlus = True
            self.trimX = dxf.xMin - offset
            self.trimY = dxf.yMax + offset
        elif q == XMINUS_YMINUS:
            self.xPlus = False
            self.yPlus = False
            self.trimX = dxf.xMin - offset
            self.trimY = dxf.yMin - offset
        elif q == XPLUS_YMINUS:
            self.xPlus = True
            self.yPlus = False
            self.trimX = dxf.xMax + offset
            self.trimY = dxf.yMin - offset

    def closePath(self, seg):
        q = self.quadrant
        if q == XPLUS_YPLUS:
            p = (self.setMinX(seg), self.setMinY(seg))
        elif q == xMINUS_YPLUS:
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
        return(minX)

    def setMaxX(self, seg):
        maxX = MIN_VALUE
        for l in seg:
            x0 = l.p0[0]
            x1 = l.p1[0]
            maxX = max(maxX, x0, x1)
        return(maxX)

    def setMinY(self, seg):
        minY = MAX_VALUE
        for l in seg:
            y0 = l.p0[1]
            y1 = l.p1[1]
            minY = min(minY, y0, y1)
        return(minY)

    def setMaxY(self, seg):
        maxY = MIN_VALUE
        for l in seg:
            y0 = l.p0[1]
            y1 = l.p1[1]
            maxY = max(maxY, y0, y1)
        return(maxY)
            
