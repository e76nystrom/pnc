
class DrillHolder():
    def __init__(self, cfg):
        self.cfg = cfg
        self.m = cfg.mill
        self.d = cfg.draw
        self.holes = \
            ( \
              (0.086, "44"), \
              (0.089, "43"), \
              (0.106, "36"), \
              (0.110, "35"), \
              (0.125, ""), \
              (0.128, "30"), \
              (0.136, "29"), \

              (0.140, "28"), \
              (0.152, "24"), \
              (0.154, "23"), \
              (0.157, "22"), \
              (0.159, "21"), \
              (0.161, "20"), \
              (0.166, "19"), \

              (0.169, "18"), \
              (0.173, "17"), \
              (0.1875, ""), \
              (0.191, "11"), \
              (0.194, "10"), \
              (0.196, "9"), \
              (0.199, "8"), \

              (0.201, "7"), \
              (0.204, "6"), \
              (0.205, "5"), \
              (0.209, "4"), \
              (0.213, "3"), \
              (0.250, ""), \
              (0.277, "J"), \

              (0.3125, ""), \
              (0.140, ""), \
              (0.140, ""), \
              (0.167, ""), \
              (0.194, ""), \
              (0.194, ""), \
              (0.255, ""), \

              (0.255, ""), \
              (0.318, ""), \
              (0.318, ""), \
              (0.375, ""), \
              (0.375, ""), \
              (0.375, ""), \
              (0.375, ""), \
            )

        self.grid = (7, 6)
        self.offset = (0.5, 0.5)
        self.spacing = (0.5, 0.5)
        self.textOffset = 0.25
        self.top = False

        self.mountSize = 0.125
        self.xMount = (0.1875, 2)
        self.yMount = (0.25, 3)

    def setup(self):
        self.cmds = \
        ( \
          ('dhdrillholes', self.millHoles),
          ('dhlabelholes', self.labelHoles),
          # ('', self.),
        )
        (xGrid, yGrid) = self.grid
        (xOffset, yOffset) = self.offset
        (xSpace, ySpace) = self.spacing

        xSize = 2 * xOffset + xGrid * xSpace
        ySize = 2 * yOffset + yGrid * ySpace
        if self.top:
            y = yOffset
        else:
            y = ySize - yOffset
            ySpace = -ySpace

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

    def millHoles(self):
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
                    d = Drill(drillSize)
                    holes.append(d)
                    d.addLoc((x, y))

        cfg.dxfMillHole(None, d)


    def labelHoles(self):
        for (x, y, size, text) in self.holeInfo:
            pass
