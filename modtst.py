from __future__ import print_function

from dbgprt import dflush, dprt, dprtSet
from geometry import CCW, CW, Arc, Line, tangent


class ModTest():
    def __init__(self, cfg):
        self.cfg = cfg
        print("test loaded")
        self.cmds = \
        ( \
            ('modrun', self.modRun), \
            ('tantest', self.tanTest), \
        )
        dprtSet(True)

    def modRun(self, args):
        dprt("modRun")
        cfg = self.cfg
        cfg.ncInit()

        xOffset = 0
        yOffset = 0
        if True:
            p0 = (xOffset + (-1), yOffset + 1)
            p1 = (xOffset + 0, yOffset + 0)
            p2 = (xOffset + 1, yOffset + 1)
        else:
            p0 = (1, 1)
            p1 = (0, 0)
            p2 = (1, -1)
        l0 = Line(p0, p1)
        l1 = Line(p1, p2)
        (x, y) = l0.bisect(l1, 1)
        dprt("%7.4f %7.4f" % (x, y))
        dflush()


    def tanTest(self, args):
        xOffset = 1
        yOffset = 1.5
        arc = Arc((xOffset, yOffset), 1, 0, 360)
        # p = (xOffset + 2.598, yOffset + -1.5)
        # p = (xOffset + 1.5, yOffset + 2.598)
        p = (xOffset + 2.121, yOffset + 2.121)
        pt = tangent(p, arc, CCW)
        dprt("x %7.4f y %7.4f" % (pt[0] - xOffset, pt[1] - yOffset))
