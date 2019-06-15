from math import radians

from geometry import MIN_DIST


class Engrave():
    def __init__(self, cfg):
        self.cfg = cfg
        self.m = cfg.mill
        self.d = cfg.draw
        self.letterHeight = 0.0
        self.angle = 0.0
        self.ticks = 0
        self.startAngle = 0
        self.diameter = 0
        self.xDir = True

    def setup(self):
        cmds = \
        ( \
            ('letterheight', self.setLetterHeight),
            ('angle', self.setAngle),
            ('ticks', self.setTicks),
            ('startangle', self.setStartAngle),
            ('xdir', self.setXDir),
            ('diameter', self.setDiameter),
        )
        cfg = self.cfg
        cfg.addCommands(cmds)

    def setLetterHeight(self, args):
        self.letterHeight = abs(self.cfg.evalFloatArg(args[1]))

    def setAngle(self, args):
        self.angle = self.cfg.evalFloatArg(args[1])

    def setTicks(self, args):
        self.ticks = self.cfg.evalIntArg(args[1])

    def setStartAngle(self, args):
        self.startAngle = self.cfg.evalFloatArg(args[1])

    def setDiameter(self, args):
        self.diameter = self.cfg.evalFloatArg(args[1])

    def setXDir(self, args):
        self.xDir = self.cfg.evalBoolArg(args[1])

    def engrave(self):
        cfg = self.cfg
        x0 = cfg.x
        y0 = cfg.y
        radius = self.diameter / 2.0
        tickAngle = self.angle / self.ticks

        tick10 = self.letterHeight
        tick5 = .75 * tick10
        tick2 = .50 * tick10
        tick1 = .25 * tick10
        letterX = 1.15 * self.letterHeight

        tickLen = (tick10, tick1, tick2, tick2, tick1, \
                   tick5,  tick1, tick2, tick2, tick1)

        xDir = self.xDir
        if cfg.probe:
            cfg.probeInit()
            prb = cfg.prb
            prb.write("g0 a%7.4f\n" % (self.startAngle))
            if xDir:
                prb.write("g0 x%7.4f y%7.4f\n" % (x0, y0 + tick10))
            else:
                prb.write("g0 x%7.4f y%7.4f\n" % (x0 + tick10, y0))
            prb.write("g0 z%7.4f\n" % (cfg.retract))
            prb.blankLine()

            prb.write("g0 a%7.4f\n" % (self.startAngle))
            prb.write("g38.2 z%6.4f (reference probe)\n" % (cfg.probeDepth))
            prb.write("g0 z%6.4f\n" % (cfg.retract))
            prb.blankLine()

        if cfg.level:
            inp = open(cfg.probeData, 'r')
            (zRef, prbAngle) = inp.readline()[2:4]
            levelData = []
            for (z, prbAngle) in inp:
                levelData.append((prbAngle, z - zRef))
            levelIndex = 0
            inp.close()
            
        font = cfg.font
        font.setHeight(self.letterHeight)
        m = self.m
        d = self.d
        m.safeZ()
        m.move((x0, y0))
        for i in range(0, self.ticks+1):
            rem = i % 10
            length = tickLen[rem]
            angle = -i * tickAngle + self.startAngle

            if cfg.probe:
                prb.write("g0 a%7.4f\n" % (angle))
                prb.write("g38.2 z%6.4f\n" % (cfg.probeDepth))
                prb.write("g0 z%6.4f\n" % (cfg.retract))
                prb.blankLine()

            if cfg.level:
                probeAngle = None
                zOffset = 0.0
                if i < len(levelData):
                    (probeAngle, zOffset) = levelData[i]
                if probeAngle is not None and \
                   abs(probeAngle - angle) < MIN_DIST:
                    levelIndex += 1
                else:
                    for levelIndex, (_, zOffset) \
                        in enumerate(levelData):
                        if abs(probeAngle - angle) < MIN_DIST:
                            levelIndex += 1
                            break
                font.setZOffset(zOffset)
                
            if xDir:
                m.write("g0 x%7.4f a%7.4f (%d)\n" % (x0, angle, i))
                m.zDepth()
                m.cut((x0, y0 + length), draw=False)
                x = x0 + radians(angle) * radius
                d.move((x, y0))
                d.line((x, y0 + length))
            else:
                m.write("g0 y%7.4f a%7.4f (%d)\n" % (y0, angle, i))
                m.zDepth()
                m.cut((x0 + length, y0), draw=False)
                y = y0 + radians(angle) * radius
                d.move((x0, y))
                d.line((x0 + length, y))

            if rem == 0:
                string = "%d" % (int(abs(angle)))
                if xDir:
                    pt = (x0, y0 + letterX)
                else:
                    pt = (x0 + letterX, y0)
                font.millOnCylinder(pt, angle, radius, \
                                    string, xDir, True)
