from math import cos, radians, sin

class Engrave():
    def __init__(self, cfg):
        self.cfg = cfg
        self.m = cfg.mill
        self.d = cfg.draw
        self.letterHeight = 0.0
        self.angle = 0.0
        self.ticks = 0
        self.startAngle = 0
        self.radius = 0

    def setup(self):
        cmds = \
        (
            ('letterheight', self.setLetterHeight),
            ('angle', self.setAngle),
            ('ticks', self.setTicks),
            ('startangle', self.setStartAngle),
            ('radius', self.setRadius),
        )
        cfg = self.cfg
        for (cmd, action) in cmds:
            cfg.cmdAction[cmd] = action

    def setLetterHeight(self, args):
        self.letterHeight = abs(self.cfg.evalFloatArg(args[1]))

    def setAngle(self, args):
        self.angle = self.cfg.evalFloatArg(args[1])

    def setTicks(self, args):
        self.ticks = self.cfg.evalIntArg(args[1])

    def setStartAngle(self, args):
        self.startAngle = self.cfg.evalFloatArg(args[1])

    def setRadius(self, args):
        self.radius = self.cfg.evalFloatArg(args[1])

    def engrave(self):
        cfg = self.cfg
        x0 = cfg.x
        y0 = cfg.y

        tick10 = self.letterHeight
        tick5 = .75 * tick10
        tick2 = .50 * tick10
        tick1 = .25 * tick10
        letterX = 1.15 * self.letterHeight

        tickAngle = self.angle / self.ticks

        tickLen = (tick10, tick1, tick2, tick2, tick1, \
                   tick5,  tick1, tick2, tick2, tick1)

        if cfg.probe:
            cfg.probeInit()

        if cfg.level:
            inp = open(cfg.probeData, 'r')
            zRef = inp.readline()[2]
            levelData = []
            for l in inp:
                (xPrb, yPrb, zPrb) = l[:3]
                levelData.append((xPrb, yPrb, zPrb - zRef))
            levelIndex = 0
            
        m = self.m
        cfg.font.setHeight(self.letterHeight)
        m.safeZ()
        m.move((x0, y0))
        if cfg.probe:
            prb = cfg.prb
            prb.write("g0 z%7.4f\n" % (cfg.retract))
            prb.blankLine()
            prb.write("g38.2 z%6.4f (reference probe)\n" % (cfg.probeDepth))
            prb.write("g0 z%6.4f\n" % (cfg.retract))
            prb.blankLine()

        min_dist = cfg.min_dist
        for i in range(0, self.ticks+1):
            rem = i % 10
            length = tickLen[rem]
            angle = i * tickAngle + self.startAngle
            theta = radians(angle)
            if cfg.probe or cfg.levle:
                r0 = self.radius + tick10
                x0 = r0 * cos(theta)
                y0 = r0 * sin(theta)
            if cfg.probe:
                prb.write("g0 x%7.4f y%7.4f\n" % (x0, y0))
                prb.write("g38.2 z%6.4f\n" % (cfg.probeDepth))
                prb.write("g0 z%6.4f\n" % (cfg.retract))
                prb.blankLine()
            if cfg.level:
                zOffset = 0.0
                if i < len(levelData):
                    (xPrb, yPrb, zOffset) = levelData[i]
                if  abs(x0 - xPrb) < min_dist and abs(y0 - yPrb) < min_dist:
                    levelIndex += 1
                else:
                    for levelIndex, (xPrb, yPrb, zOffset) \
                        in enumerate(levelData):
                        if  abs(x0 - xPrb) < min_dist and \
                            abs(y0 - yPrb) < min_dist:
                            levelIndex += 1
                            break
                m.setzOffset(zOffset)

            r0 = self.radius
            x0 = r0 * cos(theta)
            y0 = r0 * sin(theta)
            m.retract()
            m.move((x0, y0))
            r0 += length
            x0 = r0 * cos(theta)
            y0 = r0 * sin(theta)
            m.zDepth()
            m.cut((x0, y0))

            if rem == 0:
                if angle <= 90.0:
                    tmp = angle
                else:
                    tmp = 180.0 - angle
                string = "%d" % ((int(tmp)))
                r0 = self.radius + letterX
                x0 = r0 * cos(theta)
                y0 = r0 * sin(theta)
                cfg.font.millOnArc((x0, y0), angle - 90, string, True)
            

