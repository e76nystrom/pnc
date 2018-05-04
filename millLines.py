################################################################################

from dxfwrite import DXFEngine as dxf
from dbgprt import dprt
from math import atan2, ceil, cos, degrees, hypot, pi, radians, sin, sqrt, tan

MIN_DIST = .0001

def xyDist(p0, p1):
    return(hypot(p0[0] - p1[0], p0[1] - p1[1]))

def linePoint(p0, p1, dist):
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    if abs(dy) < MIN_DIST:      # horizontal
        x = dist
        y = 0
    elif abs(dx) < MIN_DIST:    # vertical
        x = 0
        y = dist
    else:                       # oblique
        m = abs(dy / dx)
        x = sqrt(dist * dist / (m * m + 1))
        y = m * x
    # dprt("linePoint")
    # dprt("p0 (%7.3f, %7.3f) p1 (%7.3f, %7.3f)" % \
    #         (p0[0], p0[1], p1[0], p1[1]))
    # dprt("x %7.3f y %7.3f" % (x, y))
    if p1[0] < p0[0]:
        x = -x
    if p1[1] < p0[1]:
        y = -y
    # dprt("x %7.3f y %7.3f" % (x, y))
    return((p0[0] + x, p0[1] + y))

def point90(p0, p1, dist):
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    if abs(dy) < MIN_DIST:      # horizontal
        x = 0
        y = dist
    elif abs(dx) < MIN_DIST:    # vertical
        x = dist
        y = 0
    else:                       # oblique
        m = -dx / dy
        x = sqrt(dist * dist / (m * m + 1))
        y = m * x
    # print "point90"
    # dprt("p0 (%7.3f, %7.3f) p1 (%7.3f, %7.3f)" % \
    #        (p0[0], p0[1], p1[0], p1[1]))
    # print "x %7.3f y %7.3f" % (x, y)
    return((x, y))

class MillLine():
    def __init__(self, cfg, mill, draw):
        self.cfg = cfg
        self.mill = mill
        self.draw = draw
        self.rampDist = 0.0
        self.last = (0.0, 0.0)
        self.debug = True

    def setLoc(self, loc):
        self.mill.safeZ()
        self.mill.move(loc)
        self.last = loc

    def millLines(self, layer):
        cfg = self.cfg
        lines = cfg.dxfInput.getLines(layer)
        self.draw1 = None
        for l in lines:
            (start, end) = l

            if abs(start[0] - end[0]) < MIN_DIST: # y slot
                slot = "y"
            elif abs(start[1] - end[1]) < MIN_DIST: # x slot
                slot = "x"
            else:                   # oblique slot
                slot = "oblique"

            cfg.out.write("(millLines %s slot start %6.4f, %6.4f "\
                          "end %6.4f, %6.4f)\n" % \
                          (slot, start[0], start[1], end[0], end[1]))

            self.mill.safeZ()
            self.mill.move(start)
            self.mill.moveZ(cfg.pauseHeight)
            if cfg.pause:
                self.mill.pause()
            if cfg.test:
                self.mill.move(end)
                if cfg.pause:
                    self.mill.pause()
                continue
            self.mill.plungeZ(0.0)
            self.mill.setFeed(cfg.feed)
            self.passes = int(ceil(abs(cfg.depth / cfg.depthPass)))

            dist = xyDist(start, end)
            if cfg.rampAngle != 0.0:
                self.rampDist = cfg.depthPass / tan(cfg.rampAngle)
                # print "rampDist %0.4f" % (self.rampDist)

            if cfg.width != 0.0:
                self.widthPasses = 0
                self.widthPerPass = 0.0
                if cfg.vBit == 0.0 and cfg.widthPerPass != 0.0:
                    self.widthPasses = ceil(cfg.width / cfg.widthPerPass)
                    self.widthPerPass = cfg.width / self.widthPasses

            if start[0] == end[0]:   # y slot
                self.ySlot(start, end)
            elif start[1] == end[1]: # x slot
                self.xSlot(start, end)
            else:                   # oblique slot
                self.obliqueSlot(start, end)

    def calcWidthPasses(self, currentDepth, lastDepth):
        cfg = self.cfg
        if cfg.width != 0.0 and cfg.vBit != 0.0:
            halfWidth = cfg.width / 2
            halfAngle = cfg.vBit / 2
            maxDepth = halfWidth / tan(halfAngle)
            if cfg.depth > maxDepth:
                cfg.depth = maxDepth

            height = maxDepth - abs(lastDepth)
            currentHalfWidth = height * tan(halfAngle)

            cutDepth = abs(currentDepth) - abs(lastDepth)
            self.cutHalfWidth = cutHalfWidth =  cutDepth * tan(halfAngle)
            widthPasses = int(ceil(currentHalfWidth / cutHalfWidth))
            while True:
                widthPerPass = ((currentHalfWidth - cutHalfWidth) /
                                widthPasses)
                if widthPasses == 1 or widthPerPass > .0025:
                    break
                widthPasses -= 1
            self.widthPasses = widthPasses
            self.widthPerPass = widthPerPass

            if self.debug:
                dprt("halfWidth %0.4f halfAngle %0.1f maxDepth %0.4f" % \
                      (halfWidth, halfAngle, maxDepth))
                dprt("height %0.4f currentHalfWidth %0.4f" % \
                      (height, currentHalfWidth))
                dprt("currentDepth %0.4f cutHalfWidth %0.4f "\
                      "widthPasses %d widthPerPass %0.4f\n" % \
                      (currentDepth, cutHalfWidth,
                       widthPasses, widthPerPass))

            if self.debug and self.draw1 is None:
                self.draw1 = draw = Draw()
                draw.open("slot", dxfFile=True, svg=False)
                d = draw.d
                if d is not None:
                    x0 = 0
                    d0 = (x0 - halfWidth, 0)
                    d1 = (x0 + halfWidth, 0)
                    d2 = (x0, -maxDepth)
                    l = draw.lBorder
                    d.add(dxf.line(d0, d1, layer=l))
                    d.add(dxf.line(d1, d2, layer=l))
                    d.add(dxf.line(d2, d0, layer=l))

            if self.debug and self.draw1 is not None:
                d = self.draw1.d
                x0 = 0
                d0 = (x0 - halfWidth, currentDepth)
                d1 = (x0 + halfWidth, currentDepth)
                d.add(dxf.line(d0, d1, layer=draw.lBorder))

                d0 = (x0 - cutHalfWidth, lastDepth)
                d1 = (x0 + cutHalfWidth, lastDepth)
                d2 = (x0, currentDepth)
                l = draw.lPath
                d.add(dxf.line(d0, d1, layer=l))
                d.add(dxf.line(d1, d2, layer=l))
                d.add(dxf.line(d2, d0, layer=l))


    def ySlot(self, start, end):
        cfg = self.cfg
        currentDepth = 0.0
        lastDepth = 0.0
        absDepth = abs(cfg.depth)
        for passNum in range(0, self.passes):
            if passNum & 1 == 0:
                p0 = start
                p1 = end
            else:
                p1 = start
                p0 = end

            if abs(currentDepth - cfg.depthPass) < absDepth:
                currentDepth -= cfg.depthPass
            else:
                currentDepth = cfg.depth
            cfg.out.write("(pass %d depth %6.4f)\n" % (passNum, currentDepth))

            if cfg.rampAngle != 0.0:
                passDepth = currentDepth - lastDepth
                (x0, y0) = p0
                d0 = self.rampDist / 2.0
                if p1[1] < p0[1]:
                    d0 = -d0
                self.mill.cut((x0, y0 + d0), lastDepth + passDepth / 2.0)
                self.mill.cut(p0, currentDepth)
            else:
                self.mill.plungeZ(currentDepth)

            self.mill.cut(p1)

            self.calcWidthPasses(currentDepth, lastDepth)

            if self.widthPasses != 0:
                w = 0.0
                for widthPass in range(self.widthPasses):
                    w += self.widthPerPass
                    cfg.out.write("(width pass %d width %6.4f)\n" % \
                                  (widthPass, w))
                    (x0, y0) = p1
                    (x1, y1) = p0
                    self.mill.cut((x0 + w, y0))
                    self.mill.cut((x0 + w, y1))
                    self.mill.cut((x0 - w, y1))
                    self.mill.cut((x0 - w, y0))
                    self.mill.cut(p1)

                    if self.debug and self.draw1 is not None:
                        d = self.draw1.d
                        cutHalfWidth = self.cutHalfWidth
                        # x = 0 + w
                        d0 = (w - cutHalfWidth, lastDepth)
                        d1 = (w + cutHalfWidth, lastDepth)
                        d2 = (w, currentDepth)
                        l = self.draw1.lPath
                        d.add(dxf.line(d0, d1, layer=l))
                        d.add(dxf.line(d1, d2, layer=l))
                        d.add(dxf.line(d2, d0, layer=l))
                        # x = 0 - w
                        d0 = (-w - cutHalfWidth, lastDepth)
                        d1 = (-w + cutHalfWidth, lastDepth)
                        d2 = (-w, currentDepth)
                        d.add(dxf.line(d0, d1, layer=l))
                        d.add(dxf.line(d1, d2, layer=l))
                        d.add(dxf.line(d2, d0, layer=l))
            lastDepth = currentDepth
        if self.debug and self.draw1 is not None:
            self.debug = False
            self.draw1.close()
            self.draw1 = None

    def xSlot(self, start, end):
        cfg = self.cfg
        currentDepth = 0.0
        lastDepth = 0.0
        absDepth = abs(cfg.depth)
        for passNum in range(0, self.passes):
            if passNum & 1 == 0:
                p0 = start
                p1 = end
            else:
                p1 = start
                p0 = end

            if abs(currentDepth - cfg.depthPass) < absDepth:
                currentDepth -= cfg.depthPass
            else:
                currentDepth = cfg.depth
            cfg.out.write("(pass %d depth %6.4f)\n" % (passNum, currentDepth))

            if cfg.rampAngle != 0.0:
                passDepth = currentDepth - lastDepth
                (x0, y0) = p0
                d0 = self.rampDist / 2.0
                if p1[0] < p0[0]:
                    d0 = -d0
                self.mill.cut((x0 + d0, y0), lastDepth + passDepth / 2.0)
                self.mill.cut(p0, currentDepth)
            else:
                self.mill.plungeZ(currentDepth)

            self.mill.cut(p1)

            self.calcWidthPasses(currentDepth, lastDepth)

            if self.widthPasses != 0:
                w = 0.0
                for widthPass in range(self.widthPasses):
                    w += self.widthPerPass
                    cfg.out.write("(width pass %d width %6.4f)\n" % \
                                  (widthPass, w))
                    (x0, y0) = p1
                    (x1, y1) = p0
                    self.mill.cut((x0, y0 + w))
                    self.mill.cut((x0, y1 + w))
                    self.mill.cut((x0, y1 - w))
                    self.mill.cut((x0, y0 - w))
                    self.mill.cut(p1)
            lastDepth = currentDepth

    def obliqueSlot(self, start, end):
        cfg = self.cfg
        currentDepth = 0.0
        lastDepth = 0.0
        absDepth = abs(cfg.depth)
        for passNum in range(0, self.passes):
            if passNum & 1 == 0:
                p0 = start
                p1 = end
            else:
                p1 = start
                p0 = end

            if abs(currentDepth - cfg.depthPass) < absDepth:
                currentDepth -= cfg.depthPass
            else:
                currentDepth = cfg.depth

            cfg.out.write("(pass %d depth %6.4f)\n" % (passNum, currentDepth))

            # dprt("currentDepth %0.3f absDepth %0.3f" % \
            #        (currentDepth, absDepth))

            if cfg.rampAngle != 0.0:
                passDepth = currentDepth - lastDepth
                rampPoint = linePoint(p0, p1, self.rampDist / 2)
                self.mill.cut(rampPoint, lastDepth + passDepth / 2.0)
                self.mill.cut(p0, currentDepth)
            else:
                self.mill.plungeZ(currentDepth)

            self.mill.cut(p1)

            self.calcWidthPasses(currentDepth, lastDepth)

            if self.widthPasses != 0:
                w = 0.0
                for widthPass in range(self.widthPasses):
                    w += self.widthPerPass
                    (dx, dy) = point90(p0, p1, w)
                    cfg.out.write("(width pass %d width %6.4f)\n" % \
                                  (widthPass, w))
                    # print "pass %d" % (widthPass)
                    # dprt("p0 (%7.3f, %7.3f) p1 (%7.3f, %7.3f)" % \
                    #        (p0[0], p0[1], p1[0], p1[1]))
                    # print "w %6.4f dx %7.4f dy %7.4f" % (w, dx, dy)
                    (x0, y0) = p1
                    (x1, y1) = p0
                    self.mill.cut((x0 + dx, y0 + dy))
                    self.mill.cut((x1 + dx, y1 + dy))
                    self.mill.cut((x1 - dx, y1 - dy))
                    self.mill.cut((x0 - dx, y0 - dy))
                    self.mill.cut(p1)
            lastDepth = currentDepth

