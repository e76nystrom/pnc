from __future__ import print_function
from dbgprt import dprtSet, dprt, dflush
from geometry import Arc, Line, tangent, LINE, CCW, CW, MIN_DIST
from math import atan2, ceil, cos, degrees, radians, sin, sqrt

class RectPocket():
    def __init__(self, cfg):
        self.cfg = cfg
        print("test loaded")
        self.stepOver = 0.85
        self.spiral = True
        self.cmds = \
        ( \
          ('rectpocket', self.pocket), \
          ('rectstepover', self.setStepOver), \
          ('rectspiral', self.setSpiral), \
          # ('', self.), \
        )
        dprtSet(True)

    def setStepOver(self, args):
        self.stepOver = float(args[1]) / 100.0

    def setSpiral(self, args):
        self.spiral = int(args[1]) != 0

    def pocket(self, args):
        layer = args[1]
        cfg = self.cfg
        dir = CCW
        if cfg.dir != None and cfg.dir == 'CW':
            dir = CW
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
            w = abs(hl0.p0[0] - hl0.p1[0]) # width
            h = abs(vl0.p0[1] - vl0.p1[1]) # height
            x = min(hl0.p0[0], hl0.p1[0])
            y = min(vl0.p0[1], vl0.p1[1])
            self.drawRect(x, y, w, h)
            stepOver = self.stepOver * cfg.endMillSize
            self.path = []
            self.index = 0
            prev = None
            offset = cfg.endMillSize / 2.0 + cfg.finishAllowance
            if self.spiral:
                dist = min(h, w) / 2.0 - offset
                if dist < 0:
                    ePrint("rectPocket rectangle too small for end mill")
                    continue
                passes = int(ceil(dist / stepOver))
                stepOver = dist / passes
                dprt("x %7.4f y %7.4f w %7.4f h %7.4f" % (x, y, w, h))
                dprt("passes %2d stepOver %7.4f dist %7.4f" % \
                     (passes, stepOver, dist))
                x0 = x + offset
                y0 = y + offset
                w -= 2.0 * offset
                h -= 2.0 * offset
                for i in range(passes + 1):
                    dprt("pass %2d x0 %7.4f y0 %7.4f w %7.4f h %7.4f" % \
                         (i, x0, y0, w, h))
                    prev = self.millRect(prev, x0, y0, w, h, cfg.dir)
                    x0 += stepOver
                    y0 += stepOver
                    w -= 2 * stepOver
                    h -= 2 * stepOver
                self.millPath()
            else:
                if min(h, w) < cfg.endMillSize + cfg.finishAllowance * 2.0:
                    ePrint("rectPocket rectangle too small for end mill")
                    continue
                dist = h - 4 * offset + (1 - self.stepOver) * cfg.endMillSize
                passes = int(ceil(dist / stepOver))
                stepOver = dist / passes
                r = cfg.endMillSize / 2.0
                s = stepOver / 2.0
                d = sqrt(r*r - s*s)
                
                dprt("x %7.4f y %7.4f w %7.4f h %7.4f" % (x, y, w, h))
                dprt("passes %2d offset %7.4f dist %7.4f stepOver %7.4f" \
                     "d %7.4f" % \
                     (passes, offset, dist, stepOver, d))

                x0 = x + offset
                y0 = y + offset
                w -= 2.0 * offset
                h -= 2.0 * offset
                prev = self.millRect(None, x0, y0, w, h, cfg.dir)
                self.drawRect(x0 + offset, y0 + offset, \
                              w - 2*offset, h - 2*offset)

                x0 += offset + d
                y0 += stepOver
                w -= (offset + d) * 2
                h -= offset * 2
                if h > 0 and  w > 0:
                    sign = 1
                    for i in range(passes):
                        dprt("pass %2d x0 %7.4f y0 %7.4f w %7.4f h %7.4f" % \
                             (i, x0, y0, w, h))
                        x1 = x0 + w
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

    def millRect(self, prev, x0, y0, w, h, dir=CCW):
        x1 = x0 + w
        y1 = y0 + h
        p0 = (x0, y0)
        p1 = (x1, y0)
        p2 = (x1, y1)
        p3 = (x0, y1)
        if prev != None:
            self.addSeg(prev, p0)
        if w > 0 and h > 0:
            if dir == CW:
                self.addSeg(p0, p1)
                self.addSeg(p1, p2)
                self.addSeg(p2, p3)
                self.addSeg(p3, p0)
            else:
                self.addSeg(p0, p3)
                self.addSeg(p3, p2)
                self.addSeg(p2, p1)
                self.addSeg(p1, p0)
            prev = p0
        elif h <= 0:
            self.addSeg(p0, p1)
            prev = p1
        elif w <= 0:
            self.addSeg(p0, p3)
            prev = p3
        self.drawMill(p0)
        self.drawMill(p1)
        self.drawMill(p2)
        self.drawMill(p3)
        return(prev)

    def addSeg(self, p0, p1):
        self.path.append(Line(p0, p1, self.index))
        self.index += 1

    def millPath(self):
        for l in self.path:
            l.prt()
        cfg = self.cfg
        mp = cfg.getMillPath()
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