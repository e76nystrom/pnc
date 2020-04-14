from __future__ import print_function

from math import ceil, sqrt

from dbgprt import dprt, ePrint
from geometry import ARC, CCW, CW, LINE, MAX_VALUE, MIN_DIST, \
    Arc, Line, Point, newPoint, prtSeg, reverseSeg, xyDist
from math import asin, atan2, degrees, pi, sqrt

HORIZONTAL = 0
VERTICAL = 1

class RectPocket():
    def __init__(self, cfg):
        self.cfg = cfg
        dprt("Rect loaded")
        self.stepOver = 0.85
        self.stepOverPercent = True
        self.spiral = True
        self.cmds = \
        ( \
          ('rectpocket', self.rectPocket, True), \
          ('rectstepover', self.setStepOver), \
          ('rectspiral', self.setSpiral), \
          ('roundedpocket', self.roundedPocket), \
          ('rectslot', self.rectSlot,), \
          ('openSlot', self.openSlot,), \
          # ('', self.), \
        )

    def setStepOver(self, args):
        tmp = args[1].strip()
        self.stepOverPercent = tmp.endswith('%')
        if self.stepOverPercent:
            tmp = tmp[:-1]
            self.stepOver = self.cfg.evalFloatArg(tmp) / 100.0
        else:
            self.stepOver = self.cfg.evalFloatArg(tmp)

    def getStepOver(self):
        return self.stepOver * self.cfg.endMillSize if self.stepOverPercent \
            else self.stepOver

    def setSpiral(self, args):
        self.spiral = self.cfg.evalBoolArg(args[1])

    def rectPocket(self, args):
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
                    continue
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
            stepOver = self.getStepOver()
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
                dist = h - 4 * offset + (1 - self.getStepOver())
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
                        if prev is not None:
                            self.addLineSeg(prev, p0)
                        self.addLineSeg(p0, p1)
                        self.drawMill(p0)
                        self.drawMill(p1)
                        prev = p1
                        y0 += stepOver
                self.millPath()

    def millRect(self, prev, x0, y0, w, h, direction=CW) :
        x1 = x0 + w
        y1 = y0 + h
        p0 = (x0, y0)
        p1 = (x1, y0)
        p2 = (x1, y1)
        p3 = (x0, y1)
        if prev is not None:
            self.addLineSeg(prev, p0)
        if w > 0 and h > 0:
            if direction == CW:
                self.addLineSeg(p0, p1)
                self.addLineSeg(p1, p2)
                self.addLineSeg(p2, p3)
                self.addLineSeg(p3, p0)
            else:
                self.addLineSeg(p0, p3)
                self.addLineSeg(p3, p2)
                self.addLineSeg(p2, p1)
                self.addLineSeg(p1, p0)
            prev = p0
        elif h <= 0:
            self.addLineSeg(p0, p1)
            prev = p1
        elif w <= 0:
            self.addLineSeg(p0, p3)
            prev = p3
        self.drawMill(p0)
        self.drawMill(p1)
        self.drawMill(p2)
        self.drawMill(p3)
        return(prev)

    def addLineSeg(self, p0, p1):
        self.path.append(Line(p0, p1, self.index))
        self.index += 1

    def addArcSeg(self, c, r, a0, a1):
        self.path.append(Arc(c, r, a0, a1, self.index))
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
        if draw is not None:
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
        if draw is not None:
            draw.circle(p, self.cfg.endMillSize / 2.0)

    def roundedPocket(self, args):
        cfg = self.cfg
        cfg.ncInit()
        x = cfg.x
        y = cfg.y
        if len(args) >= 2:
            w = float(cfg.evalFloatArg(args[1]))
        if len(args) >= 3:
            h = float(cfg.evalFloatArg(args[2]))
        self.path = []
        self.index = 0
        if h < w:
            r = h / 2.0
            w0 = w / 2.0 - r
            c0 = (x - w0, y)
            c1 = (x + w0, y)
            r0 = r - cfg.endMillSize / 2.0 + cfg.finishAllowance
            p0 = (x - w0, y - r0)
            p1 = (x + w0, y - r0)
            p2 = (x + w0, y + r0)
            p3 = (x - w0, y + r0)
            self.addArcSeg(c0, r0, 90, 270)
            self.addLineSeg(p0, p1)
            self.addArcSeg(c1, r0, 270, 90)
            self.addLineSeg(p2, p3)
            draw = cfg.draw
            if draw is not None:
                p0 = (x - w0, y - r)
                p1 = (x + w0, y - r)
                p2 = (x + w0, y + r)
                p3 = (x - w0, y + r)
                draw.move(p3)
                draw.arc(p0, c0)
                draw.line(p1)
                draw.arc(p2, c1)
                draw.line(p3)
        else:
            r = w / 2.0
            h0 = h / 2.0 - r
            c0 = (x, y - h0)
            c1 = (x, y + h0)
            r0 = r - cfg.endMillSize / 2.0 + cfg.finishAllowance
            p0 = (x + r, y - h0)
            p1 = (x + r, y + h0)
            p2 = (x - r, y + h0)
            p3 = (x - r, y - h0)
            self.addArcSeg(c0, r, 180, 0)
            self.addLineSeg(p0, p1)
            self.addArcSeg(c1, r, 0, 180)
            self.addLineSeg(p2, p3)
            draw = cfg.draw
            if draw is not None:
                p0 = (x + r, y - h0)
                p1 = (x + r, y + h0)
                p2 = (x - r, y + h0)
                p3 = (x - r, y - h0)
                draw.move(p3)
                draw.arc(p0, c0)
                draw.line(p1)
                draw.arc(p2, c1)
                draw.line(p3)
        self.millPath()

    def rectSlot(self, args):
        layer = args[1]
        cfg = self.cfg
        cfg.ncInit()
        segments = cfg.dxfInput.getPath(layer)
        millSeg = []
        for seg in segments:
            if len(seg) != 4:
                ePrint("rectPocket wrong number of sides")
                continue
            vert = []
            horiz = []
            arc = []
            for l in seg:
                if l.type == LINE:
                    if abs(l.p0[0] - l.p1[0]) < MIN_DIST:
                        vert.append(l)
                    elif abs(l.p0[1] - l.p1[1]) < MIN_DIST:
                        horiz.append(l)
                elif l.type == ARC:
                    arc.append(l)
            if (len(arc) == 2 and \
                abs(arc[0].r - cfg.endMillSize / 2.0) < MIN_DIST):
                path = []
                path.append(Line(arc[0].c, arc[1].c))
                millSeg.append(path)
                
        last = cfg.mill.last
        mp = cfg.getMillPath()
        while len(millSeg):
            minDist = MAX_VALUE
            index = None
            for i, path in enumerate(millSeg):
                dist0 = xyDist(last, path[0].p0)
                dist1 = xyDist(last, path[-1].p1)
                if dist0 < dist1:
                    dist = dist0
                    swap = False
                else:
                    dist = dist1
                    swap = True
                if dist < minDist:
                    minDist = dist
                    minSwap = swap
                    index = i

            path = millSeg.pop(index)
            if swap:
                path = reverseSeg(path, False)
            mp.millPath(path, closed=False)

    def openSlot(self, args):
        layer = args[1]
        cfg = self.cfg
        cfg.ncInit()
        segments = cfg.dxfInput.getPath(layer)
        for seg in segments:
            vert = []
            horiz = []
            for l in seg:
                if l.type == LINE:
                    if abs(l.p0.x - l.p1.x) < MIN_DIST:
                        vert.append(l)
                    elif abs(l.p0.y - l.p1.y) < MIN_DIST:
                        horiz.append(l)
                    else:
                        pass
                else:
                    pass
            if (len(horiz) == 2) and (len(vert) == 2):
                dxf = cfg.dxfInput
                xMin = dxf.xMin
                xMax = dxf.xMax
                direction = None
                match = 0
                ySum = 0.0
                for l in horiz:
                    p0 = l.p0
                    p1 = l.p1
                    ySum += p0.y
                    if p0.x > p1.x:
                        (p0, p1) = (p1, p0)
                    if abs(p0.x - xMin) < MIN_DIST and \
                       abs(p1.x - xMax) < MIN_DIST:
                        match += 1
                if match == 2:
                    direction = HORIZONTAL
                    l = horiz[0]
                    slotLen = abs(l.p1.x - l.p0.x)
                    slotWidth = abs(horiz[1].p0.y - l.p0.y)
                    offset = (xMin, ySum / 2)
                    rotateAngle = 0
                else:
                    yMin = dxf.yMin
                    yMax = dxf.yMax
                    xSum = 0.0
                    for l in vert:
                        p0 = l.p0
                        p1 = l.p1
                        xSum += p0.x
                        if p0.y > p1.y:
                            (p0, p1) = (p1.y, p0.y)
                        if abs(p0.y - yMin) < MIN_DIST and \
                           abs(p1.y - yMax) < MIN_DIST:
                            match += 1
                    if match == 2:
                        direction = VERTICAL
                        l = vert[0]
                        slotLen = abs(l.p1.x - l.p0.x)
                        slotWidth = abs(vert[1].p0.y - l.p0.y)
                        offset = (xSum / 2, yMin)
                        rotateAngle = pi / 2.0
                    else:
                        continue
            else:
                continue

            r = cfg.endMillSize / 2.0
            h = slotWidth / 2.0 - r - cfg.finishAllowance
            stepOver = self.getStepOver()
            millDist = slotLen + r
            passes = int(ceil(millDist / stepOver))
            stepOver = millDist / passes

            path = self.path2(r, h, stepOver, passes, CCW)

            for l in path:
                if rotateAngle != 0:
                    l.rotate(Point(0, 0), rotateAngle)
                l.offset(offset)
            cfg.mill.last = path[0].p0 # start at beginning
            mp = cfg.getMillPath()
            mp.millPath(path, closed=False)

    def path0(self, r, h, stepOver, passes, direction=None):
        x = -r
        y = h
        path = []
        for i in range(passes):
            if (i & 1) == 0:
                c = Point(x, y - stepOver)
                l = Arc(c, stepOver, 0, 90, direction=CW)
                path.append(l)
                p1 = l.p1
                x = p1.x
                y = -h
                l = Line(p1, Point(x, y))
                path.append(l)
            else:
                c = Point(x, y + stepOver)
                l = Arc(c, stepOver, 270, 0, direction=CCW)
                path.append(l)
                p1 = l.p1
                x = p1.x
                y = h
                l = Line(p1, Point(x, y))
                path.append(l)
        return path

    def path1(self, r, h, stepOver, passes, direction=CW):
        r0 = stepOver       # milling arc radius
        r1 = r0 / 3         # return radius
        a = degrees(pi / 2 + 2 * atan2(r0 - r1, r0))
        x = -r
        y = 0
        c0 = Point(x, y)
        path = []
        if direction == CW:
            arc0 = Arc(c0, r0, 270, 90, direction=CW)
            for i in range(passes):
                path.append(arc0)
                c1 = Point(x, arc0.p1.y + r1)
                arc1 = Arc(c1, r1, a, 270, direction=CW)
                path.append(arc1)
                x += r0
                c0 = Point(x, y)
                arc0 = Arc(c0, r0, 270, a, direction=CW)
                l = Line(arc1.p1, arc0.p0)
                path.append(l)
        else:
            a = 360 - a
            arc0 = Arc(c0, r0, 270, 90, direction=CCW)
            for i in range(passes):
                path.append(arc0)
                c1 = Point(x, arc0.p1.y - r1)
                arc1 = Arc(c1, r1, 90, a, direction=CCW)
                path.append(arc1)
                x += r0
                c0 = Point(x, y)
                arc0 = Arc(c0, r0, a, 90, direction=CCW)
                l = Line(arc1.p1, arc0.p0)
                path.append(l)         
        return path

    def path2(self, r, h, stepOver, passes, direction=CW):
        r0 = stepOver       # milling arc radius
        r1 = r0 / 3         # return radius
        centerVDist = 2 * h - (r0 + r1)
        centerDist = sqrt(centerVDist * centerVDist + r0 * r0)
        a0 = atan2(centerVDist, r0)
        a1 = asin((r0 - r1) / centerDist)
        a = degrees(pi / 2 + a0 + a1)
        h0 = h - r0
        path = []
        x = -r
        y = 0
        if direction == CW:
            c0 = Point(x, h0)
            arc0 = Arc(c0, r0, 0, 90, direction=CW)
            for i in range(passes):
                path.append(arc0)
                p0 = arc0.p1
                l = Line(p0, Point(p0.x, -h0))
                path.append(l)
                c1 = Point(x, -h0)
                l = Arc(c1, r0, 270, 0, direction=CW)
                path.append(l)
                c2 = Point(x, -h0 - r0 + r1)
                arc1 = Arc(c2, r1, a, 270, direction=CW)
                path.append(arc1)
                x += r0
                c0 = Point(x, h0)
                arc0 = Arc(c0, r0, 0, a, direction=CW)
                l = Line(arc1.p1, arc0.p0)
                path.append(l)
        else:
            a = 360 - a
            c0 = Point(x, -h0)
            arc0 = Arc(c0, r0, 270, 0, direction=CCW)
            for i in range(passes):
                path.append(arc0)
                p0 = arc0.p1
                l = Line(p0, Point(p0.x, h0))
                path.append(l)
                c1 = Point(x, h0)
                l = Arc(c1, r0, 0, 90, direction=CCW)
                path.append(l)
                c2 = Point(x, h0 + r0 - r1)
                arc1 = Arc(c2, r1, 90, a, direction=CCW)
                path.append(arc1)
                x += r0
                c0 = Point(x, -h0)
                arc0 = Arc(c0, r0, a, 0, direction=CCW)
                l = Line(arc1.p1, arc0.p0)
                path.append(l)
        return path
                     
            
            
            
