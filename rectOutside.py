from dbgprt import dprtSet
from geometry import Line, createPath


class RectOutside():
    def __init__(self, cfg):
        self.cfg = cfg
        print("test loaded")
        self.xOffset = 0.0
        self.yOffset = 0.0
        self.cmds = \
        ( \
          ('rectOffset', self.rectOffset), \
          ('rectOutside', self.rectOutside), \
          # ('', self.), \
        )
        dprtSet(True)

    def rectOffset(self, args):
        self.xOffset = self.cfg.evalFloatArg(args[1])
        self.yOffset = self.cfg.evalFloatArg(args[2])

    def rectOutside(self, args):
        w = self.cfg.evalFloatArg(args[1])
        h = self.cfg.evalFloatArg(args[2])
        seg = []
        p0 = (self.xOffset, self.yOffset)
        p1 = (self.xOffset + w, self.yOffset)
        p2 = (self.xOffset + w, self.yOffset + h)
        p3 = (self.xOffset, self.yOffset + h)
        seg.append(Line(p0, p1))
        seg.append(Line(p1, p2))
        seg.append(Line(p2, p3))
        seg.append(Line(p3, p0))
        cfg = self.cfg
        cfg.ncInit()
        mp = cfg.getMillPath()
        dist = cfg.endMillSize / 2 + cfg.finishAllowance
        (path, tabPoints) = createPath(seg, dist, True, None, \
                                       addArcs = cfg.addArcs)
        mp.millPath(path, tabPoints)
