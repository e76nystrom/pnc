from dbgprt import dprt
from pnc import Draw, Drill, O_UPPER_LEFT, O_LOWER_LEFT
from geometry import MIN_DIST

class DrillHolder():
    def __init__(self, cfg):
        self.cfg = cfg
        self.m = cfg.mill
        self.d = cfg.draw
        self.letterHeight = 0.1
        self.mountRetract = None
        self.retract = None
        self.cmds = \
        ( \
          ('dhdrillholes', self.millHoles),
          ('dhlabelholes', self.labelHoles),
          ('dhletterheight', self.setLetterHeight),
          ('dhdxf', self.dxfHolder),
          ('dhscad', self.scadHolderBase),
          ('dhmountretract', self.setMountRetract),
          ('dhretract', self.setRetract),
          ('dhgrid', self.setGrid),
          ('dhoffset', self.setOffset),
          ('dhspacing', self.setSpacing),
          ('dhtextoffset', self.setTestOfset),
          ('dhmountsize', self.setMontSize),
          ('dhxmount', self.setXMount),
          ('dhymount', self.setYMount),
          # ('', self.),
        )
        self.holes = \
            ( \
              (0.086, "44"), \
              (0.089, "43"), \
              (0.140, "4-40"), \
              (0.104, "37"), \
              (0.107, "36"), \
              (0.140, "6-32"), \
              (0.125, "1/8"), \

              (0.128, "30"), \
              (0.136, "29"), \
              (0.167, "8-32"), \
              (0.140, "28"), \
              (0.150, "25"), \
              (0.152, "24"), \
              (0.194, "10-24"), \
              
              (0.154, "23"), \
              (0.157, "22"), \
              (0.159, "21"), \
              (0.194, "10-32"), \
              (0.161, "20"), \
              (0.166, "19"), \
              (0.169, "18"), \

              (0.173, "17"), \
              (0.188, "3/16"), \
              (0.191, "11"), \
              (0.194, "10"), \
              (0.196, "9"), \
              (0.199, "8"), \
              (0.201, "7"), \

              (0.204, "6"), \
              (0.255, "1/4-20"), \
              (0.205, "5"), \
              (0.209, "4"), \
              (0.213, "3"), \
              (0.219, "7/32"), \
              (0.255, "1/4-28"), \

              (0.250, "1/4"), \
              (0.261, "G"), \
              (0.318, "5/16-18"), \
              (0.277, "J"), \
              (0.318, "5/16-24"), \
              (0.313, "5/16"), \
              (0.375, ""), \
            )

        self.grid = (7, 6)
        self.offset = (0.5, 0.5)
        self.spacing = (0.5, 0.5)
        self.textOffset = -0.25
        self.top = False

        self.mountSize = 0.125
        self.xMount = (0.1875, 2)
        self.yMount = (0.25, 3)

        self.clearance = 0.001

        self.setup()

    def setup(self):
        (xGrid, yGrid) = self.grid
        (xOffset, yOffset) = self.offset
        (xSpace, ySpace) = self.spacing

        self.xSize = 2 * xOffset + (xGrid - 1) * xSpace
        self.ySize = 2 * yOffset + (yGrid - 1) * ySpace

        orientation = self.cfg.orientation
        if orientation == O_UPPER_LEFT:
            if self.top:
                y = -yOffset
                ySpace = -ySpace
            else:
                y = -ySize + yOffset
        elif orientation == O_LOWER_LEFT:
            if self.top:
                y = self.ySize - yOffset
                ySpace = -ySpace
            else:
                y = yOffset
        else:
            ePrint("drillHolder invalid orientation")

        index = 0
        self.holeInfo = []
        for i in range(yGrid):
            x = xOffset
            for j in range(xGrid):
                (size, label) = self.holes[index]
                self.holeInfo.append((x, y, size, label))
                x += xSpace
                index += 1
            y += ySpace

        (xMountOffset, xMountGrid) = self.xMount
        (yMountOffset, yMountGrid) = self.yMount
        xMountSpace = (self.xSize - 2 * xMountOffset) / (xMountGrid - 1)
        yMountSpace = (self.ySize - 2 * yMountOffset) / (yMountGrid - 1)

        self.mountInfo = []
        y = yMountOffset
        for i in range(yMountGrid):
            x = xMountOffset
            for j in range(xMountGrid):
                self.mountInfo.append((x, y))
                x += xMountSpace
            y += yMountSpace

    def setLetterHeight(self, args):
        self.letterHeight = abs(float(args[1]))

    def setMountRetract(self, args):
        self.mountRetract = float(args[1])

    def setRetract(self, args):
        self.retract = float(args[1])

    def setGrid(self, args):
        self.grid = (int(args[1]), int(args[2]))

    def setOffset(self, args):
        self.offset = (float(args[1]), float(args[2]))

    def setSpacing(self, args):
        self.spacing = (float(args[1]), float(args[2]))

    def setTextOffset(self, args):
        self.textOffset = float(args[1])

    def setMountSize(self, args):
        self.mountSize float(args[1])

    def setXMount(self, args):
        self.xMount = (float(args[1]), int(args[2]))

    def setYMount(self, args):
        self.yMount = (float(args[1]), int(args[2]))

    def millHoles(self, args):
        holes = []
        d = Drill(self.mountSize)
        for p in self.mountInfo:
            d.addLoc(p)
        holes.append(d)
        cfg = self.cfg
        retract = cfg.retract   # save retract value
        if self.mountRetract is not None:
            cfg.retract = self.mountRetract
        else:
            cfg.retract = cfg.safeZ
        cfg.dxfMillHole(None, holes)
        
        holes = []
        i = 0
        for (x, y, size, text) in self.holeInfo:
            dprt("%2d (%7.4f, %7.4f) size %7.4f %5s" % \
                 (i, x, y, size, text))
            i += 1
            size += self.clearance
            add = True
            for h in holes:
                if abs(size - h.size) < MIN_DIST:
                    dprt("add %7.4f to %7.4f" % (size, h.size))
                    h.addLoc((x, y))
                    add = False
                    break
            if add:
                dprt("new %7.4f" % (size))
                d = Drill(size)
                d.addLoc((x, y))
                holes.append(d)

        if self.retract is not None:
            cfg.retract = self.retract
        else:                   # if retract not specified
            cfg.retract = retract # restore retract value
        cfg.dxfMillHole(None, holes)
        cfg.draw.material(self.xSize, self.ySize)

    def labelHoles(self, args):
        cfg = self.cfg

        if cfg.probe:
            cfg.probeInit()
            prb = cfg.prb
            (x, y) = self.holeInfo[0][0:2]
            prb.write("g0 x %7.4f y %7.4f\n" % (x, y + self.textOffset))
            prb.write("g38.2 z%6.4f (reference probe)\n" % (cfg.probeDepth))
            prb.write("g0 z%6.4f\n\n" % (cfg.retract))

        if cfg.level:
            zRef = inp.readline()[2]
            levelData = []
            for probeData in inp:
                (x, y, z) = probeData[0:3]
                levelData.append((x, y, z - zRef))
            levelIndex = 0
            inp.close()
            
        font = cfg.font
        font.setHeight(self.letterHeight)
        offset = self.textOffset
        if offset < 0:
            offset -= self.letterHeight / 2
        else:
            offset += self.letterHeight / 2
        m = self.cfg.mill
        m.safeZ()
        for (x, y, size, text) in self.holeInfo:
            if len(text) != 0:
                if cfg.probe:
                    prb.write("g0 x %7.4f y %7.4f\n" % \
                              (x, y + self.textOffset))
                    prb.write("g38.2 z%6.4f (reference probe)\n" % \
                              (cfg.probeDepth))
                    prb.write("g0 z%6.4f\n\n" % (cfg.retract))

                if cfg.level:
                    found = False
                    (xProbe, yProbe, zOffset) = levelData[levelIndex]
                    if abs(x - xProbe) < MIN_DIST and \
                       abs(y - yProbe) < MIN_DIST:
                        found = True
                        levelIndex += 1
                    else:
                        for levelIndex, (xProbe, yProbe, zOffset) in \
                            enumerate(levelData):
                            if abs(x - xProbe) < MIN_DIST and \
                               abs(y - yProbe) < MIN_DIST:
                                found = True
                                levelIndex += 1
                    if found:
                        font.setZOffset(zOffset)
                    else:
                        ePrint("level data not found")

                y += offset
                font.mill((x, y), text, center=True)

    def dxfHolder(self, args):
        file = args[1]
        d = Draw()
        d.open(file, True, False)
        d.material(self.xSize, self.ySize)
        r = self.mountSize / 2.0
        for p in self.mountInfo:
            d.circle(p, r)
        for (x, y, size, text) in self.holeInfo:
            d.circle((x, y), size / 2.0)
        d.close()

    def scadHolderBase(self, args):
        file = args[1]
        print(file)
        f = open(file, "w")
        m = 25.4
        self.baseThickness = 0.0625
        self.mountHole = 0.125
        self.mountSpacer = 0.375
        self.mountHeight = 0.875
        self.mountRecess = 0.250
        self.mountRecessHeight = 0.125

        self.wall = 0.8
        self.wallHeight = 0.25
        self.printClearance = 0.005

        f.write("//base x %7.4f y %7.4f\n" % (self.xSize, self.ySize))
        f.write("$fs = 0.05;	// minimum segment length\n")
        f.write("difference()\n{\n")
        f.write(" union()\n {\n")
        f.write("  linear_extrude(%7.4f)\n" % (self.baseThickness * m))
        f.write("   square([%7.4f, %7.4f]);\n" % \
                (self.xSize * m, self.ySize * m))

        for (x, y) in self.mountInfo:
            f.write("  linear_extrude(%7.4f)\n" % (self.mountHeight * m))
            f.write("   translate([%7.4f, %7.4f, 0.0])\n" % \
                    (x * m, y * m))
            f.write("    circle(%7.4f);\n" % (self.mountSpacer * m / 2.0))
        f.write(" }\n")
        f.write(" union()\n {\n")
        for (x, y) in self.mountInfo:
            f.write("  linear_extrude(%7.4f)\n" % (self.mountHeight * m))
            f.write("   translate([%7.4f, %7.4f, 0.0])\n" % \
                    (x * m, y * m))
            f.write("    circle(%7.4f);\n" % (self.mountHole * m / 2.0))
        f.write(" }\n")
        f.write(" union()\n {\n")
        for (x, y) in self.mountInfo:
            f.write("  linear_extrude(%7.4f)\n" % (self.mountRecessHeight * m))
            f.write("   translate([%7.4f, %7.4f, 0.0])\n" % \
                    (x * m, y * m))
            f.write("    circle(%7.4f);\n" % (self.mountRecess * m / 2.0))
        f.write(" }\n")
        f.write("}\n")

        for (x, y, size, text) in self.holeInfo:
            f.write("//drill x %7.4f y %7.4f size %7.4f %s\n" % \
                    (x, y, size, text))
            f.write("linear_extrude(%7.4f)\n" % (self.wallHeight * m))
            f.write("translate([%7.4f, %7.4f, 0.0])\n" % \
                    (x * m, y * m))
            f.write("difference()\n");
            size = (size + self.printClearance) * m / 2.0
            f.write("{circle(%7.4f); circle(%7.4f);}\n" % \
                    (size + self.wall, size))
            f.write("\n")
            
        f.close()

        
