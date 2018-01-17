
from pnc import Drill, O_UPPER_LEFT, O_LOWER_LEFT

from geometry import MIN_DIST

class DrillHolder():
    def __init__(self, cfg):
        self.cfg = cfg
        self.m = cfg.mill
        self.d = cfg.draw
        self.letterHeight = 0.1
        self.cmds = \
        ( \
          ('dhdrillholes', self.millHoles),
          ('dhlabelholes', self.labelHoles),
          ('dhletterheight', self.setLetterHeight)
          # ('', self.),
        )
        self.holes = \
            ( \
              (0.086, "44"), \
              (0.089, "43"), \
              (0.140, "4-40"), \
              (0.106, "36"), \
              (0.110, "35"), \
              (0.140, "6-32"), \
              (0.125, "1/8"), \

              (0.128, "30"), \
              (0.136, "29"), \
              (0.167, "8-32"), \
              (0.140, "28"), \
              (0.1495, "25"), \
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
              (0.1875, "3/16"), \
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
              (0.3125, "5/16"), \
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

        self.setup()

    def setup(self):
        (xGrid, yGrid) = self.grid
        (xOffset, yOffset) = self.offset
        (xSpace, ySpace) = self.spacing

        xSize = 2 * xOffset + xGrid * xSpace
        ySize = 2 * yOffset + yGrid * ySpace
        if self.cfg.orientation == O_UPPER_LEFT:
            if self.top:
                y = -yOffset
                ySpace = -ySpace
            else:
                y = -ySize + yOffset
        elif self.cfg.orientation == O_LOWER_LEFT:
            if self.top:
                y = ySize - yOffset
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
                self.holeInfo.append((x, y) + self.holes[index])
                x += xSpace
                index += 1
            y += ySpace

        (xMountOffset, xMountGrid) = self.xMount
        (yMountOffset, yMountGrid) = self.yMount
        xMountSpace = (xSize - 2 * xMountOffset) / (xMountGrid - 1)
        yMountSpace = (ySize - 2 * yMountOffset) / (yMountGrid - 1)

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

    def millHoles(self, args):
        holes = []
        d = Drill(self.mountSize)
        for p in self.mountInfo:
            d.addLoc(p)
        holes.append(d)
        
        for (x, y, size, text) in self.holeInfo:
            for h in holes:
                if abs(size - h.size) < MIN_DIST:
                    h.addLoc((x, y))
                    break
                else:
                    d = Drill(size)
                    holes.append(d)
                    d.addLoc((x, y))
                    break

        self.cfg.dxfMillHole(None, holes)

    def labelHoles(self, args):
        font = self.cfg.font;
        font.setHeight(self.letterHeight)
        for (x, y, size, text) in self.holeInfo:
            if len(text) != 0:
                w = font.width(text)
                y = y + self.textOffset
                font.mill((x, y), text, center=True)
