from __future__ import print_function

from math import ceil

from dbgprt import dprt, dprtSet
from geometry import MIN_DIST


class Broach():
    def __init__(self, cfg):
        self.cfg = cfg
        self.depth = 0.0
        self.start = 0.0
        self.end = 0.0
        self.xStart = 0.0
        self.yStart = 0.0
        self.xEnd = 0.0
        self.yEnd = 0.0
        self.step = 0.0
        self.cmds = \
        ( \
          ('broach', self.broach), \
          ('broachdepth', self.setDepth), \
          ('broachtop', self.setTop), \
          ('broachstart', self.setStart), \
          ('broachend', self.setEnd), \
          ('broachfeed', self.setFeed), \
          ('broachstep', self.setStep), \
          #('', self.), \
          # ('', self.), \
        )
        dprtSet(True)

    def setDepth(self, args):
        self.depth = float(args[1])

    def setTop(self, args):
        self.cfg.retract = float(args[1])

    def setStart(self, args):
        (self.xStart, self.yStart) = self.cfg.getLocation(args)[:2]

    def setEnd(self, args):
        (self.xEnd, self.yEnd) = self.cfg.getLocation(args)[:2]

    def setFeed(self, args):
        self.cfg.zFeed = float(args[1])

    def setStep(self, args):
        self.step = float(args[1])

    def broach(self, _):
        cfg = self.cfg
        cfg.ncInit()
        mill = cfg.mill
        if abs(self.yEnd - self.yStart) < MIN_DIST:
            xFeed = True
            dist = self.xEnd - self.xStart
            loc = self.xStart
        elif abs(self.xEnd - self.xStart) < MIN_DIST:
            xFeed = False
            dist = self.yEnd - self.yStart
            loc = self.yStart

        passes = int(ceil(abs(dist / self.step)))
        step = abs(dist / passes)
        dprt("dist %7.4f passes %d step %6.4f" % (dist, passes, step))
        if dist < 0:
            step = -step

        mill.safeZ()
        mill.move((self.xStart, self.yStart))
        mill.retract()
        for i in range(passes):
            loc += step
            comment = "pass %d/%d" % (i + 1, passes)
            if xFeed:
                mill.move((loc, self.yStart), comment=comment)
            else:
                mill.move((self.xStart, loc), comment=comment)
            mill.plungeZ(self.depth)
            mill.retract()
            mill.blankLine()
        mill.safeZ()
