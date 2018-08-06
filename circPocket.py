from __future__ import print_function
from dbgprt import dprtSet, dprt, dflush
from geometry import Arc, Line, tangent, xyDist, CCW, CW, MIN_DIST
from math import atan2, ceil, cos, degrees, radians, sin, sqrt

class CircularPocket():
    def __init__(self, cfg):
        self.cfg = cfg
        print("test loaded")
        self.stepOver = 0.85
        self.strAngle = 0.0
        self.endAngle = self.strAngle + 360.0
        self.spiral = True
        self.distPass = 0.020
        self.leadRadius = 0.025
        self.cmds = \
        ( \
          ('circpocket', self.pocket), \
          ('circstepover', self.setStepOver), \
          ('circspiral', self.setSpiral), \
          ('circenlarge', self.enlargeHole), \
          ('circfinish', self.finishHole), \
          ('circstepdist', self.setStepDist), \
          ('circleadradius', self.setCircLeadRadius), \
          # ('', self.), \
        )
        dprtSet(True)

    def setStepOver(self, args):
        self.stepOver = float(args[1]) / 100.0

    def setSpiral(self, args):
        self.spiral = int(args[1]) != 0

    def setStepDist(self, args):
        self.distPass = float(args[1])

    def setCircLeadRadius(self, args):
        self.leadRadius = 0.025

    def pocket(self, args):
        layer = args[1]
        cfg = self.cfg
        dir = CCW
        if cfg.dir is not None and cfg.dir == 'CW':
            dir = CW
        cfg.ncInit()
        endAngle = self.endAngle
        swapped = False
        holes = cfg.dxfInput.getHoles(layer)
        for hole in holes:
            diameter = hole.size
            stepOver = self.stepOver * cfg.endMillSize
            radius = diameter / 2.0 - cfg.finishAllowance - \
                     cfg.endMillSize / 2.0
            if self.spiral:
                rDist = diameter / 2.0 - cfg.finishAllowance - cfg.endMillSize
                passes = int(ceil(rDist / stepOver))
                stepOver = rDist / passes
                dprt("diameter %7.4f stepOver %7.4f rDist %7.4f passes %d " \
                     "radius %7.4f" % \
                     (diameter, stepOver, rDist, passes, radius))
                strAngle = self.strAngle
                for (x, y) in hole.loc:
                    dprt("center %7.4f %7.4f" % (x, y))
                    draw = cfg.draw
                    if draw is not None:
                        draw.circle((x, y), diameter / 2)
                    self.path = []
                    self.index = 0
                    r = radius
                    self.addSeg(Arc((x, y), r, strAngle, endAngle, \
                                    self.index, dir=dir))
                    for i in range(passes):
                        rPrev = r
                        a = radians(endAngle)
                        p0 = (rPrev * cos(a) + x, rPrev * sin(a) + y)
                        r -= stepOver
                        arc = Arc((x, y), r, 0.0, 360)
                        p1 = tangent(p0, arc, dir)
                        strAngle = degrees(atan2(p0[0] - x, p0[1] - y))
                        self.addSeg(Line(p0, p1, self.index))
                        self.addSeg(Arc((x, y), r, strAngle, endAngle, \
                                        self.index, dir=dir))
                        self.drawMill(p0)
                        self.drawMill(p1)
                        dprt("pass %d rPrev %7.4f (%7.4f, %7.4f) " \
                             "r %7.4f (%7.4f, %7.4f)" % \
                             (i, rPrev, p0[0], p0[1], r, p1[0], p0[1]))
                    self.drawMill(self.path[-1].p1)
                    self.millPath()
            else:
                dist = diameter - 2 * cfg.finishAllowance - cfg.endMillSize
                passes = int(ceil(dist / stepOver))
                stepOver = dist / passes
                radius = diameter / 2.0 - cfg.finishAllowance - \
                         cfg.endMillSize / 2.0
                dprt("diameter %7.4f stepOver %7.4f dist %7.4f passes %d " \
                     "radius %7.4f" % \
                     (diameter, stepOver, dist, passes, radius))
                strAngle = 90.0
                endAngle = strAngle + 360
                for (x, y) in hole.loc:
                    dprt("center %7.4f %7.4f" % (x, y))
                    self.path = []
                    self.index = 0
                    self.addSeg(Arc((x, y), radius, strAngle, endAngle, \
                                    self.index, dir=dir))
                    r1 = radius - cfg.endMillSize / 2.0
                    a = radians(endAngle)
                    p0 = (-radius * cos(a) + x, radius * sin(a) + y)
                    r = radius - stepOver
                    draw = cfg.draw
                    if draw is not None:
                        draw.circle((x, y), diameter / 2)
                        draw.circle((x, y), radius)
                        draw.circle((x, y), r1)
                        draw.circle((x, y), r)
                    sign = -1
                    for i in range(passes):
                        dprt("pass %2d r %7.4f" % (i, r))
                        # if i == 0:
                        y1 = r + y
                        x1 = sqrt(r1*r1 - r*r) + x
                        r -= stepOver
                        p1 = (sign * x1 + x, y1)
                        self.drawMill(p0)
                        self.drawMill(p1)
                        self.addSeg(Line(p0, p1, self.index))
                        sign = -sign
                        p0 = (sign * x1 + x, y1)
                        self.addSeg(Line(p1, p0, self.index))
                        if r1 - abs(r) < MIN_DIST:
                            break
                    self.drawMill(p0)
                    self.millPath()

    def addSeg(self, seg):
        self.path.append(seg)
        self.index += 1

    def millPath(self):
        for l in self.path:
            l.prt()
        cfg = self.cfg
        mp = cfg.getMillPath()
        cfg.mill.last = self.path[0].p0 # start at beginning
        mp.millPath(self.path, closed=False)

    def drawMill(self, p):
        draw = self.cfg.draw
        if draw is not None:
            draw.circle(p, self.cfg.endMillSize / 2.0)

    def enlargeHole(self, args):
        outerLayer = args[1]
        innerLayer = args[2]
        cfg = self.cfg
        dir = CCW
        if cfg.dir is not None and cfg.dir == 'CW':
            dir = CW
        cfg.ncInit()
        endAngle = self.endAngle
        swapped = False
        outer = cfg.dxfInput.getCircles(outerLayer)
        inner = cfg.dxfInput.getCircles(innerLayer)
        for (c, outerD) in outer:
            found = False
            for (c0, innerD) in inner:
                if xyDist(c, c0) < MIN_DIST:
                    found = True
                    break
            if not found:
                continue
            draw = cfg.draw
            if draw is not None:
                draw.circle(c, innerD / 2.0)
                draw.circle(c, outerD / 2.0)
            outerD -= 2 * cfg.finishAllowance
            totalDist = (outerD - innerD) / 2
            passes = int(round(totalDist / self.distPass))
            distPass = totalDist / passes
            endMillRadius = cfg.endMillSize / 2.0
            (xC, yC) = c

            self.path = []
            self.index = 0
            r0 = innerD / 2.0 - endMillRadius
            if self.leadRadius != 0:
                leadCenter = (r0 - self.leadRadius + xC, yC)
                if dir == CCW:
                    self.addSeg(Arc(leadCenter, self.leadRadius,
                                    270, 0, dir=CCW))
                else:
                    self.addSeg(Arc(leadCenter, self.leadRadius,
                                    0, 90, dir=CW))

            for passCount in range(passes):
                r1 = r0 + distPass
                y1 = sqrt(r1*r1 - r0*r0)
                p0 = (xC + r0, yC)

                if dir == CCW:
                    p1 = (xC + r0, yC + y1)
                else:
                    p1 = (xC + r0, yC - y1)

                self.addSeg(Line(p0, p1))

                a0 = degrees(atan2(y1, r0))
                if dir == CCW:
                    self.addSeg(Arc(c, r1, a0, 0, dir=CCW))
                else:
                    self.addSeg(Arc(c, r1, 0, a0, dir=CW))
                r0 = r1
            self.addSeg(Arc(c, r1, 0, a0, dir=dir))

            if self.leadRadius != 0:
                r2 = r1 - self.leadRadius
                a0R = radians(a0)
                leadCenter = (r2 * cos(a0R) + xC, r2 * sin(a0R) + yC)
                if dir == CCW:
                    self.addSeg(Arc(leadCenter, self.leadRadius,
                                    a0, a0+90, dir=CCW))
                else:
                    self.addSeg(Arc(leadCenter, self.leadRadius,
                                    a0-90, a0, dir=CW))
            self.millPath()

    def finishHole(self, args):
        layer = args[1]
        cfg = self.cfg
        dir = CCW
        if cfg.dir is not None and cfg.dir == 'CW':
            dir = CW
        cfg.ncInit()
        endAngle = self.endAngle
        swapped = False
        holes = cfg.dxfInput.getCircles(layer)
        for (c, diam) in holes:
            draw = self.cfg.draw
            if draw is not None:
                draw.circle(c, diam / 2.0)
            diam -= 2 * cfg.finishAllowance
            endMillRadius = cfg.endMillSize / 2.0
            (xC, yC) = c

            self.path = []
            self.index = 0
            r0 = diam / 2.0 - endMillRadius
            if self.leadRadius != 0:
                leadCenter = (r0 - self.leadRadius + xC, yC)
                if dir == CCW:
                    self.addSeg(Arc(leadCenter, self.leadRadius,
                                    270, 0, dir=CCW))
                else:
                    self.addSeg(Arc(leadCenter, self.leadRadius,
                                    0, 90, dir=CW))

            self.addSeg(Arc(c, r0, 0, 360, dir=dir))

            if self.leadRadius != 0:
                leadCenter = (r0 - self.leadRadius + xC, yC)
                if dir == CCW:
                    self.addSeg(Arc(leadCenter, self.leadRadius,
                                    0, 90, dir=CCW))
                else:
                    self.addSeg(Arc(leadCenter, self.leadRadius,
                                    270, 0, dir=CW))
            self.millPath()

