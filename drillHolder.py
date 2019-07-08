import os

from dbgprt import dprt, ePrint
from draw import Draw
from geometry import MIN_DIST
from orientation import O_LOWER_LEFT, O_UPPER_LEFT

class Drill():
    def __init__(self, size):
        self.size = size
        self.loc = []

    def addLoc(self, p):
        self.loc.append(p)

class DrillHolder():
    def __init__(self, cfg):
        self.cfg = cfg
        self.m = cfg.mill
        self.d = cfg.draw

        self.letterHeight = 0.1

        self.mountRetract = None
        self.retract = None

        self.grid = (7, 6)
        self.offset = (0.5, 0.5)
        self.spacing = (0.5, 0.5)
        self.textOffset = -0.25
        self.top = False

        self.mountSize = 0.125
        self.xMount = (0.1875, 2)
        self.yMount = (0.25, 3)

        self.clearance = 0.001

        self.cmds = \
        ( \
          ('dhdrillholes', self.millHoles, True),
          ('dhlabelholes', self.labelHoles, True),
          ('dhletterheight', self.setLetterHeight),
          ('dhdxf', self.dxfHolder),
          ('dhscad', self.scadHolderBase, True),
          ('dhmountretract', self.setMountRetract),
          ('dhretract', self.setRetract),
          ('dhgrid', self.setGrid),
          ('dhoffset', self.setOffset),
          ('dhspacing', self.setSpacing),
          ('dhtextoffset', self.setTextOffset),
          ('dhtop', self.setTop),
          ('dhmountsize', self.setMountSize),
          ('dhxmount', self.setXMount),
          ('dhymount', self.setYMount),
          ('dhclearance', self.setClearance),
          # ('', self.),
        )
        self.holes = \
            ( \
              (0.086, "44"), \
              (0.089, "43"), \
              (0.141, "4-40"), \
              (0.104, "37"), \
              (0.107, "36"), \
              (0.141, "6-32"), \
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
              (0.319, "5/16-18"), \
              (0.277, "J"), \
              (0.319, "5/16-24"), \
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
        self.yMount = (0.1875, 3)

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
                y = -self.ySize + yOffset
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
        for _ in range(yGrid):
            x = xOffset
            for _ in range(xGrid):
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
        for _ in range(yMountGrid):
            x = xMountOffset
            for _ in range(xMountGrid):
                self.mountInfo.append((x, y))
                x += xMountSpace
            y += yMountSpace

    def setLetterHeight(self, args):
        self.letterHeight = abs(self.cfg.evalFloatArg(args[1]))

    def setMountRetract(self, args):
        self.mountRetract = self.cfg.evalFloatArg(args[1])

    def setRetract(self, args):
        self.retract = self.cfg.evalFloatArg(args[1])

    def setGrid(self, args):
        self.grid = (int(args[1]), int(args[2]))

    def setOffset(self, args):
        self.offset = (self.cfg.evalFloatArg(args[1]), self.cfg.evalFloatArg(args[2]))

    def setSpacing(self, args):
        self.spacing = (self.cfg.evalFloatArg(args[1]), self.cfg.evalFloatArg(args[2]))

    def setTextOffset(self, args):
        self.textOffset = self.cfg.evalFloatArg(args[1])

    def setTop(self, args):
        self.top = self.cfg.evalBoolArg(args[1])

    def setMountSize(self, args):
        self.mountSize = self.cfg.evalFloatArg(args[1])

    def setXMount(self, args):
        self.xMount = (self.cfg.evalFloatArg(args[1]), int(args[2]))

    def setYMount(self, args):
        self.yMount = (self.cfg.evalFloatArg(args[1]), int(args[2]))

    def setClearance(self, args):
        self.clearance = self.cfg.evalFloatArg(args[1])

    def millHoles(self, _):
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

    def labelHoles(self, _):
        cfg = self.cfg

        if cfg.probe:
            cfg.probeInit()
            prb = cfg.prb
            (x, y) = self.holeInfo[0][0:2]
            prb.write("g0 x %7.4f y %7.4f\n" % (x, y + self.textOffset))
            prb.write("g1 z%6.4f\n" % (cfg.retract))
            prb.blankLine()
            prb.write("g38.2 z%6.4f f%3.1f(reference probe)\n" %
                      (cfg.probeDepth, cfg.probeFeed))
            prb.write("g10 L20 P0 z0.000 (zero z)\n")
            prb.write("g0 z%6.4f\n" % (cfg.retract))
            prb.blankLine()

        if cfg.level:
            try:
                inp = open(cfg.probeData, "r")
            except IOError:
                ePrint("unable to open level data %s" % (cfg.probeData))
                cfg.level = False
                return
            (x0, y0, zRef) = inp.readline().split(" ")[:3]
            #zRef = float(zRef)
            x0 = float(x0)
            y0 = float(y0)
            zRef = 0.0
            levelData = []
            for probeData in inp:
                (x, y, z) = probeData.split(" ")[:3]
                levelData.append((float(x), float(y), float(z) - zRef))
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
        zOffset = 0.0

        if cfg.level:
            m.write("\nm5	(stop spindle to probe)\n")
            m.write("g4 p3\n")
            m.write("g0 x %7.4f y %7.4f\n" % (x0, y0))
            m.retract()
            m.write("g38.2 z%6.4f f%3.1f (probe reference point)\n" %
                      (cfg.probeDepth, cfg.probeFeed))
            m.write("g10 L20 P0 z0.000 (zero z)\n")
            m.retract()
            m.write("m3	(start spindle)\n")
            m.write("g4 p3\n")
            
        for (x, y, _, text) in self.holeInfo:
            if len(text) != 0:
                y += offset
                if cfg.probe:
                    prb.write("g0 x %7.4f y %7.4f\n" % (x, y))
                    prb.write("g38.2 z%6.4f f%3.1f(reference probe)\n" %
                              (cfg.probeDepth, cfg.probeFeed))
                    prb.write("g0 z%6.4f\n" % (cfg.retract))
                    prb.blankLine()

                if cfg.level:
                    found = False
                    if levelIndex < len(levelData):
                        (xProbe, yProbe, zOffset) = levelData[levelIndex]
                        if abs(x - xProbe) < MIN_DIST and \
                           abs(y - yProbe) < MIN_DIST:
                            found = True
                            levelIndex += 1
                    if not found:
                        for levelIndex, (xProbe, yProbe, zOffset) in \
                            enumerate(levelData):
                            if abs(x - xProbe) < MIN_DIST and \
                               abs(y - yProbe) < MIN_DIST:
                                found = True
                                levelIndex += 1
                    if not found:
                        zOffset = 0.0
                        ePrint("level data not found")
                    font.setZOffset(zOffset)

                m.write("\n(x %7.4f y %7.4f zOffset %6.4f %s)\n" % \
                            (x, y, zOffset, text))
                font.mill((x, y), text, center=True)

    def dxfHolder(self, args):
        dFile = args[1]
        if len(os.path.dirname(dFile)) == 0:
            dFile = os.path.join(self.cfg.dirPath, dFile)
        d = Draw(self.cfg)
        d.open(dFile, True, False)
        d.material(self.xSize, self.ySize)
        r = self.mountSize / 2.0
        for p in self.mountInfo:
            d.circle(p, r)
        for (x, y, size, _) in self.holeInfo:
            d.circle((x, y), size / 2.0)
        d.close()

    def scadHolderBase(self, args):
        sFile = args[1]
        if len(os.path.dirname(sFile)) == 0:
            sFile = os.path.join(self.cfg.dirPath, sFile)
        print(sFile)
        f = open(sFile, "w")
        m = 25.4
        self.baseThickness = 0.0625
        self.mountHole = 0.125
        self.mountSpacer = 0.3125
        self.mountHeight = 0.4375
        self.mountRecess = 0.250
        self.mountRecessHeight = 0.125

        self.wall = 0.8
        self.wallHeight = 0.25
        self.printClearance = 0.005

        self.xChamfer = 0.4
        self.zChamfer = 0.4

        f.write("//base x %7.4f y %7.4f\n" % (self.xSize, self.ySize))
        f.write("$fs = 0.05;	// minimum segment length\n")
        f.write("difference()\n{\n")
        f.write(" union()\n {\n")
        f.write("  linear_extrude(%7.4f)\n" % (self.baseThickness * m))

        # f.write("   square([%7.4f, %7.4f]);\n" % \
        #         (self.xSize * m, self.ySize * m))

        r = (self.mountSpacer / 2.0) * m
        xSize = self.xSize * m
        ySize = self.ySize * m
        f.write("  hull()\n  {\n")
        locations = ((r, r), \
                     (r, ySize - r), \
                     (xSize - r, ySize - r), \
                     (xSize - r, r), \
                     )
        for (x, y) in locations:
            f.write("   translate([%7.3f, %7.3f, 0])\n" % (x, y))
            f.write("    circle(%7.4f);\n" % (r))
        f.write("  }\n")

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
            f.write("difference()\n{\n")
            
            f.write(" linear_extrude(%7.4f)\n" % (self.wallHeight * m))
            f.write("  translate([%7.4f, %7.4f, 0.0])\n" % \
                    (x * m, y * m))
            f.write("   difference()\n")
            size = (size + self.printClearance) * m / 2.0
            f.write("   {\n    circle(%7.4f);\n    circle(%7.4f);\n  }\n" % \
                    (size + self.wall, size))

            f.write(" translate([%7.4f, %7.4f, %7.4f])\n" % \
                    (x * m, y * m, self.wallHeight * m - self.zChamfer))
            f.write("  cylinder(h = %7.4f, r1 = %7.4f, r2 = %7.4f);\n" % \
                    (self.zChamfer, size, size  + self.xChamfer))
            f.write("}\n")
            f.write("\n")
                     
            
        f.close()
