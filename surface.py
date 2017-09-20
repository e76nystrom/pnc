from __future__ import print_function
from dbgprt import dprtSet, dprt, dflush
from geometry import Arc, Line, tangent, LINE, CCW, CW, MIN_DIST
from math import atan2, ceil, cos, degrees, radians, sin, sqrt

class Surface():
    def __init__(self, cfg):
        self.cfg = cfg
        self.stepOver = 0.85
        self.edge = 0.020
        self.cmds = \
        ( \
          ('surface', self.surface), \
          ('surfstepover', self.setStepOver), \
          ('surfedge', self.setEdge), \
          # ('', self.), \
        )
        dprtSet(True)

    def setStepOver(self, args):
        self.stepOver = float(args[1]) / 100.0

    def setEdge(self, args):
        self.edge = float(args[1])

    def surface(self, args):
        layer = args[1]
        cfg = self.cfg
        cfg.ncInit()
        segments = cfg.dxfInput.getPath(layer)
        for seg in segments:
            if len(seg) != 4:
                ePrint("rectPocket wrong number if sides")
                continue
            vert = []
            horiz = []
            for l in seg:
                if l.type == LINE:
                    if abs(l.p0[0] - l.p1[0]) < MIN_DIST:
                        vert.append(l)
                    elif abs(l.p0[1] - l.p1[1]) < MIN_DIST:
                        horiz.append(l)
                    else:
                        ePrint("rectPocket line not horizontal or vertical")
                        continue
                else:
                    ePrint("rectPocket segment not a line")
                    contiue
            if len(vert) != 2 or len(horiz) != 2:
                ePrint("rectPocket incorrect number of sides")
                continue
            hl0 = horiz[0]
            vl0 = vert[0]
            edge = self.edge
            endMillSize = cfg.endMillSize
            w = abs(hl0.p0[0] - hl0.p1[0]) # width
            h = abs(vl0.p0[1] - vl0.p1[1]) # height
            x = min(hl0.p0[0], hl0.p1[0])
            y = min(vl0.p0[1], vl0.p1[1])
            dprt("x %7.4f y %7.4f w %7.4f h %7.4f" % (x, y, w, h))
            self.drawRect(x, y, w, h)
            self.drawRect(x-edge, y-edge, w + 2*edge, h + 2*edge)
            stepOver = self.stepOver * endMillSize
            self.path = []
            self.index = 0
            prev = None
            w += endMillSize + 2*edge
            h += 2*edge
            # dist = h - endMillSize
            dist = h
            passes = int(ceil(dist / stepOver))
            stepOver = dist / passes
            # passes += 1
            dprt("passes %2d stepOver %7.4f dist %7.4f w %7.4f h %7.4f" % \
                 (passes, stepOver, dist, w, h))
            x0 = x - (endMillSize / 2.0 + edge)
            # y0 = y + (endMillSize / 2.0 - edge)
            y0 = y + (stepOver - endMillSize / 2.0 - edge)
            dprt("x0 %7.4f y0 %7.4f w %7.4f h %7.4f" % (x0, y0, w, h))
            sign = 1
            x1 = x0 + w
            for i in range(passes):
                dprt("pass %2d x0 %7.4f y0 %7.4f w %7.4f h %7.4f" % \
                     (i, x0, y0, w, h))
                if sign > 0:
                    p0 = (x0, y0)
                    p1 = (x1, y0)
                else:
                    p0 = (x1, y0)
                    p1 = (x0, y0)
                sign = - sign
                if prev != None:
                    self.addSeg(prev, p0)
                self.addSeg(p0, p1)
                self.drawMill(p0)
                self.drawMill(p1)
                prev = p1
                y0 += stepOver
            self.millPath()

    def addSeg(self, p0, p1):
        self.path.append(Line(p0, p1, self.index))
        self.index += 1

    def millPath(self):
        for l in self.path:
            l.prt()
        cfg = self.cfg
        mp = cfg.getMillPath()
        if len(self.path) != 0:
            cfg.mill.last = self.path[0].p0 # start at beginning
            mp.millPath(self.path, closed=False)

    def drawRect(self, x, y, w, h):
        draw = self.cfg.draw
        if draw != None:
            x1 = x + w
            y1 = y + h
            p0 = (x, y)
            p1 = (x1, y)
            p2 = (x1, y1)
            p3 = (x, y1)
            draw.move(p0)
            draw.line(p1)
            draw.line(p2)
            draw.line(p3)
            draw.line(p0)

    def drawMill(self, p):
        draw = self.cfg.draw
        if draw != None:
            draw.circle(p, self.cfg.endMillSize / 2.0)
