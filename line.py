from math import ceil, hypot

from dbgprt import dprt, dprtSet
from geometry import LINE, MIN_DIST, Line


class Engrave():
    def __init__(self, cfg):
        self.cfg = cfg
        self.m = cfg.mill
        self.d = cfg.draw
        self.p0 = (0.0, 0.0)
        self.p1 = (0.0, 0.0)
        self.offset = 0
        self.probeDist = 0.5
        self.cmds = \
        ( \
            ('linestart', self.setLineStart), \
            ('lineend', self.setLineEnd), \
            ('offset', self.setOffset), \
            ('probedist', self.setProbeDist), \
            ('scribelines', self.scribeLines, True), \
            ('scribe', self.scribe, True), \
        )
        dprtSet(True)

    def setLineStart(self, args):
        self.p0 = (self.cfg.evalFloatArg(args[1]), \
                   self.cfg.evalFloatArg(args[2]))

    def setLineEnd(self, args):
        self.p1 = (self.cfg.evalFloatArg(args[1]), \
                   self.cfg.evalFloatArg(args[2]))

    def setOffset(self, args):
        self.offset = self.cfg.evalFloatArg(args[1])

    def setProbeDist(self, args):
        self.probDist = self.cfg.evalFloatArg(args[1])

    def scribeLines(self, args):
        layer = args[1]
        segments = self.cfg.dxfInput.getPath(layer)
        for seg in segments:
            if len(seg) != 1:
                continue
            line = seg[0]
            if line.lType != LINE:
                continue
            self.scribeLine(line)

    def scribe(self):
        l = Line(self.p0, self.p1)
        if l.length != 0:
            self.scribeLine(l)

    def scribeLine(self, line):
        cfg = self.cfg
        cfg.ncInit()
        p0 = line.linePoint(self.offset)
        p1 = line.linePoint(line.length - self.offset)
        line = Line(p0, p1)
        segments = int(ceil(line.length / self.probeDist))
        segLen = line.length / segments
        segments += 1
            
        if cfg.level:
            inp = cfg.probeOpen()
            if inp is None:
                return
            l = inp.readline().strip()
            l = l.split()
            zRef = float(l[2])
            dprt("zRef %7.4f\n" % (zRef))
            
            levelData = []
            for prbData in inp:
                prbData.strip()
                (x, y, z) = prbData.split()[:3]
                x = float(x)
                y = float(y)
                z = float(z)
                dprt("x %7.4f y %7.4f z %7.4f zOffset %7.4f" % \
                     (x, y, z, z - zRef))
                levelData.append((x, y, z - zRef))
            levelIndex = 0
            inp.close()
            dprt()
        else:
            if cfg.probe:
                prb = cfg.probeInit()
                prb.safeZ()
                prb.move(line.p0)
                prb.retract()
                prb.probe(line.p0, comment="reference probe")

        m = cfg.mill
        m.safeZ()
        m.move(line.p0)
        m.retract()
        if cfg.level:
            m.probeSetZ()
        m.zDepth()

        zOffset = 0.0
        for i in range(segments):
            dist = i * segLen
            (x0, y0) = line.linePoint(dist)

            if cfg.level:
                zOffset = 0.0
                if i < len(levelData):
                    (prbX, prbY, zOffset) = levelData[i]
                dist = hypot(x0 - prbX, y0 - prbY)
                dprt("levelIndex %2d x0 %7.4f prbX %7.4f y0 %7.4f "\
                     "prbY %7.4f dist %7.4f" % \
                          (levelIndex, x0, prbX, y0, prbY, dist))
                if dist < MIN_DIST:
                    levelIndex += 1
                else:
                    for levelIndex, (prbX, prbY, zOffset) \
                        in enumerate(levelData):
                        dist = hypot(x0 - prbX, y0 - prbY)
                        if dist < MIN_DIST:
                            levelIndex += 1
                            break
                    dprt("x %7.4f y %7.4f zOffset %7.4f" % \
                         (x0, y0, zOffset))
            else:
                if cfg.probe:
                    prb.probe((x0, y0), comment="point %d" % i)

            m.cut((x0, y0), zOffset, "zOffset %7.4f" % zOffset)
