from math import radians

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
        self.letterHeight = abs(float(args[1]))

    def setAngle(self, args):
        self.angle = float(args[1])

    def setTicks(self, args):
        self.ticks = int(args[1])

    def setStartAngle(self, args):
        self.startAngle = float(args[1])

    def setDiameter(self, args):
        self.diameter = float(args[1])

    def setXDir(self, args):
        self.xDir = int(args[1]) != 0

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

        if cfg.probe:
            cfg.probeInit()

        if cfg.level:
            inp = open(cfg.probeData, 'r')
            (zRef, prbAngle) = inp.readline()[2:4]
            levelData = []
            for (z, prbAngle) in inp:
                levelData.append((prbAngle, z - zRef))
            levelIndex = 0
            inp.close()
            
        cfg.font.setHeight(self.letterHeight)
        m = self.m
        d = self.d
        xDir = self.xDir
        m.safeZ()
        m.move((x0, y0))
        if cfg.probe:
            prb = cfg.prb
            prb.write("g0 a%7.4f\n" % (self.startAngle))
            if xDir:
                prb.write("g0 x%7.4f y%7.4f\n" % (x0, y0 + tick10))
            else:
                prb.write("g0 x%7.4f y%7.4f\n" % (x0 + tick10, y0))
            prb.write("g0 z%7.4f\n\n" % (cfg.retract))

            prb.write("g0 a%7.4f\n" % (self.startAngle))
            prb.write("g38.2 z%6.4f (reference probe)\n" % (cfg.probeDepth))
            prb.write("g0 z%6.4f\n\n" % (cfg.retract))

        min_dist = cfg.min_dist
        for i in range(0, self.ticks+1):
            rem = i % 10
            length = tickLen[rem]
            angle = -i * tickAngle + self.startAngle
            if cfg.probe:
                prb.write("g0 a%7.4f\n" % (angle))
                prb.write("g38.2 z%6.4f\n" % (cfg.probeDepth))
                prb.write("g0 z%6.4f\n\n" % (cfg.retract))
            if cfg.level:
                probeAngle = None
                zOffset = 0.0
                if i < len(levelData):
                    (probeAngle, zOffset) = levelData[i]
                if probeAngle != None and abs(probeAngle - angle) < min_dist:
                    levelIndex += 1
                else:
                    for levelIndex, (probAngle, zOffset) \
                        in enumerate(levelData):
                        if abs(probeAngle - angle) < MIN_DIST:
                            levelIndex += 1
                            break
                m.setzOffset(zOffset)
                
            if xDir:
                m.out.write("g0 x%7.4f a%7.4f (%d)\n" % (x0, angle, i))
                m.zDepth()
                m.cut((x0, y0 + length), draw=False)
                x = x0 + radians(angle) * radius
                d.move((x, y0))
                d.line((x, y0 + length))
            else:
                m.out.write("g0 y%7.4f a%7.4f (%d)\n" % (y0, angle, i))
                m.zDepth()
                m.cut((x0 + length, y0), draw=False)
                y = y0 + radians(angle) * radius
                d.move((x0, y))
                d.line((x0 + length, y))

            if rem == 0:
                str = "%d" % (int(abs(angle)))
                if xDir:
                    pt = (x0, y0 + letterX)
                else:
                    pt = (x0 + letterX, y0)
                cfg.font.millOnCylinder(pt, angle, radius, \
                                        str, xDir, True)
