from math import degrees

from dxfwrite import CENTER, MIDDLE
from dxfwrite import DXFEngine as dxf
from enum import Enum
from svgwrite import Drawing
from svgwrite.path import Path
from svgwrite.shapes import Circle, Rect

from dbgprt import dprt, ePrint
from geometry import MIN_DIST, calcAngle, labelP, offset, xyDist
from orientation import (O_CENTER, O_LOWER_LEFT, O_LOWER_RIGHT, O_POINT,
                         O_UPPER_LEFT, O_UPPER_RIGHT)

BORDER = 'BORDER'
PATH = 'PATH'
HOLE = 'HOLE'
TEXT = 'TEXT'
DEBUG = 'DEBUG'

class Color(Enum):
    RED = 1
    YELLOW = 2
    GREEN = 3
    CYAN = 4
    BLUE = 5
    MAGENTA = 6
    WHITE = 7

class Draw():
    def __init__(self, cfg, d=None, svg=None):
        self.cfg = cfg
        self.d = d
        self.svg = svg
        self.path = None
        self.materialPath = None
        self.enable = True
        self.reverse = False
        self.last = (0.0, 0.0)
        self.offset = 0.0
        self.pScale = 25.4 * 2
        self.xOffset = 50
        self.yOffset = 350
        self.layerIndex = 0
        self.lBorder = BORDER
        self.lPath = PATH
        self.lHole = HOLE
        self.lText = TEXT
        self.lDebug = DEBUG
        self.lCount = 0
        self.definedLayers = {}
        self.color = Color.WHITE.value

    def open(self, inFile, drawDxf=True, drawSvg=True):
        if drawSvg and self.svg is None:
            svgFile = inFile + ".svg"
            try:
                self.svg = Drawing(svgFile, profile='full', fill='black')
                self.path = Path(stroke_width=.5, stroke='black', fill='none')
            except IOError:
                self.svg = None
                self.path = None
                ePrint("svg file open error %s" % (svgFile))

        if drawDxf and self.d is None:
            dxfFile = inFile + "_ngc.dxf"
            try:
                self.d = dxf.drawing(dxfFile)
                self.layerIndex = 0
                self.d.add_layer('0', color=self.color, lineweight=0)
                self.setupLayers()
            except IOError:
                self.d = None
                ePrint("dxf file open error %s" % (dxfFile))

    def nextLayer(self):
        self.layerIndex += 1
        self.setupLayers()

    def setupLayers(self):
        i = str(self.layerIndex)
        self.layers = [['lBorder', i + BORDER], \
                       ['lPath', i + PATH], \
                       ['lHole', i + HOLE], \
                       ['lText', i + TEXT], \
                       ['lDebug', i + DEBUG]]
        for (var, l) in self.layers:
            self.definedLayers[l] = True
            self.d.add_layer(l, color=self.color, lineweight=0)
            exec("self." + var + "='" + l + "'")

    def close(self):
        if self.d is not None:
            dprt("save drawing file")
            self.d.save()
            self.d = None

        if self.svg is not None:
            self.svg.add(self.lPath)
            if self.materialPath is not None:
                self.svg.add(self.materialPath)
                self.svg.save()
                self.svg = None

    def scaleOffset(self, point):
        if self.offset == 0.0:
            point = ((self.xOffset + point[0]) * self.pScale, \
                     (self.yOffset - point[1]) * self.pScale)
        else:
            point = ((self.xOffset + point[0]) * self.pScale, \
                     (self.yOffset - point[1]) * self.pScale)
        return point

    def scale(self, point):
        point = (point[0] * self.pScale, point[1] * self.pScale)
        return point

    def material(self, xSize, ySize):
        if self.svg is not None:
            self.offset = 0.0
            path = self.materialPath
            if path is None:
                self.materialPath = Path(stroke_width=.5, stroke='red', \
                                      fill='none')
                path = self.materialPath
            path.push('M', (self.scaleOffset((0, 0))))
            path.push('L', (self.scaleOffset((xSize, 0))))
            path.push('L', (self.scaleOffset((xSize, ySize))))
            path.push('L', (self.scaleOffset((0, ySize))))
            path.push('L', (self.scaleOffset((0, 0))))

            self.path.push('M', (self.scaleOffset((0, 0))))

            # dwg = svgwrite.Drawing(name, (svg_size_width, svg_size_height), \
            # debug=True)

        cfg = self.cfg
        if self.d is not None:
            orientation = cfg.orientation
            if orientation == O_UPPER_LEFT:
                p0 = (0.0, 0.0)
                p1 = (xSize, 0.0)
                p2 = (xSize, -ySize)
                p3 = (0.0, -ySize)
            elif orientation == O_LOWER_LEFT:
                p0 = (0.0, 0.0)
                p1 = (xSize, 0.0)
                p2 = (xSize, ySize)
                p3 = (0.0, ySize)
            elif orientation == O_UPPER_RIGHT:
                p0 = (0.0, 0.0)
                p1 = (-xSize, 0.0)
                p2 = (-xSize, -ySize)
                p3 = (0.0, -ySize)
            elif orientation == O_LOWER_RIGHT:
                p0 = (0.0, 0.0)
                p1 = (-xSize, 0.0)
                p2 = (-xSize, ySize)
                p3 = (0.0, ySize)
            elif orientation == O_CENTER:
                p0 = (-xSize/2, -ySize/2)
                p1 = (xSize/2, -ySize/2)
                p2 = (xSize/2, ySize/2)
                p3 = (-xSize/2, ySize/2)
            elif orientation == O_POINT:
                dxfInput = cfg.dxfInput
                p0 = (dxfInput.xMin, dxfInput.yMin)
                p1 = (dxfInput.xMin, dxfInput.yMax)
                p2 = (dxfInput.xMax, dxfInput.yMax)
                p3 = (dxfInput.xMax, dxfInput.yMin)
            else:
                ePrint("invalid orientation")
            self.d.add(dxf.line(p0, p1, layer=self.lBorder))
            self.d.add(dxf.line(p1, p2, layer=self.lBorder))
            self.d.add(dxf.line(p2, p3, layer=self.lBorder))
            self.d.add(dxf.line(p3, p0, layer=self.lBorder))

    def materialOutline(self, lines, layer=None):
        cfg = self.cfg
        if self.svg is not None:
            self.xOffset = 0.0
            self.yOffset = cfg.dxfInput.ySize
            self.svg.add(Rect((0, 0), (cfg.dxfInput.xSize * self.pScale, \
                                       cfg.dxfInput.ySize * self.pScale), \
                              fill='rgb(255, 255, 255)'))
            path = self.materialPath
            if path is None:
                self.materialPath = Path(stroke_width=.5, stroke='red', \
                                         fill='none')
                path = self.materialPath
            for l in lines:
                (start, end) = l
                path.push('M', (self.scaleOffset(start)))
                path.push('L', (self.scaleOffset(end)))

        if self.d is not None:
            if layer is None:
                layer = self.lBorder
            for l in lines:
                (start, end) = l
                self.d.add(dxf.line(cfg.dxfInput.fix(start), \
                                    cfg.dxfInput.fix(end), layer=layer))

    def move(self, end):
        if self.enable:
            if self.svg is not None:
                self.path.push('M', self.scaleOffset(end))
                # dprt("svg move %7.4f %7.4f" % self.scaleOffset(end))
            # dprt("   move %7.4f %7.4f" % end)
            self.last = end

    def line(self, end, layer=None):
        if self.enable:
            if self.svg is not None:
                self.path.push('L', self.scaleOffset(end))
                # dprt("svg line %7.4f %7.4f" % self.scaleOffset(end))
            if self.d is not None:
                if layer is None:
                    layer = self.lPath
                else:
                    if not layer in self.definedLayers:
                        self.definedLayers[layer] = True
                        self.d.add_layer(layer, color=self.color, lineweight=0)
                self.d.add(dxf.line(self.last, end, layer=layer))
            # dprt("   line %7.4f %7.4f" % end)
            self.last = end

    def arc(self, end, center, layer=None):
        if self.enable:
            r = xyDist(end, center)
            if self.svg is not None:
                self.path.push_arc(self.scaleOffset(end), 0, r, \
                                    large_arc=True, angle_dir='+', \
                                    absolute=True)
            if self.d is not None:
                if layer is None:
                    layer = self.lPath
                else:
                    if not layer in self.definedLayers:
                        self.definedLayers[layer] = True
                        self.d.add_layer(layer, color=self.color, lineweight=0)
                p0 = self.last
                p1 = end
                if xyDist(p0, p1) < MIN_DIST:
                    self.d.add(dxf.circle(r, center, layer=layer))
                else:
                    # dprt("p0 (%7.4f, %7.4f) p1 (%7.4f, %7.4f)" % \
                    #      (p0[0], p0[1], p1[0], p1[1]))
                    # if orientation(p0, center, p1) == CCW:
                    #     (p0, p1) = (p1, p0)
                    a0 = degrees(calcAngle(center, p0))
                    a1 = degrees(calcAngle(center, p1))
                    if a1 == 0.0:
                        a1 = 360.0
                    # dprt("a0 %5.1f a1 %5.1f" % (a0, a1))
                    self.d.add(dxf.arc(r, center, a0, a1, layer=layer))
                self.last = end

    def circle(self, end, r, layer=None):
        if self.enable:
            if self.d is not None:
                if layer is None:
                    layer = self.lHole
                else:
                    if not layer in self.definedLayers:
                        self.definedLayers[layer] = True
                        self.d.add_layer(layer, color=self.color, lineweight=0)
                self.d.add(dxf.circle(r, end, layer=layer))
        self.last = end

    def hole(self, end, drillSize):
        if self.enable:
            if self.svg is not None:
                self.path.push('L', self.scaleOffset(end))
                # dprt("svg line %7.4f %7.4f" % self.scaleOffset(end))
                self.svg.add(Circle(self.scaleOffset(end), \
                                    (drillSize / 2) * self.pScale, \
                                    stroke='black', stroke_width=.5, \
                                    fill="none"))
            if self.d is not None:
                self.d.add(dxf.line(self.last, end, layer=self.lPath))
                self.d.add(dxf.circle(drillSize / 2, end, layer=self.lHole))
        self.last = end

    def text(self, txt, p0, height, layer=None):
        if self.enable:
            if self.d is not None:
                if layer is None:
                    layer = self.lText
                else:
                    if not layer in self.definedLayers:
                        self.definedLayers[layer] = True
                        self.d.add_layer(layer, color=self.color, lineweight=0)
                self.d.add(dxf.text(txt, p0, height, layer=layer))

    def add(self, entity):
        if self.enable:
            if self.d is not None:
                self.d.add(entity)

    def drawCross(self, p, layer=None):
        if layer is None:
            layer = self.lDebug
        else:
            if not layer in self.definedLayers:
                self.definedLayers[layer] = True
                self.d.add_layer(layer, color=self.color, lineweight=0)
        (x, y) = p
        dprt("cross %2d %7.4f, %7.4f" % (self.lCount, x, y))
        labelP(p, "%d" % (self.lCount))
        last = self.last
        self.move((x - 0.02, y))
        self.line((x + 0.02, y), layer)
        self.move((x, y - 0.02))
        self.line((x, y + 0.02), layer)
        self.lCount += 1
        self.move(last)

    def drawX(self, p, txt=None, swap=False, layer=None, h=0.010):
        if layer is None:
            layer = self.lDebug
        else:
            if not layer in self.definedLayers:
                self.definedLayers[layer] = True
                self.d.add_layer(layer, color=self.color, lineweight=0)
        (x, y) = p
        xOfs = 0.020
        yOfs = 0.010
        if swap:
            (xOfs, yOfs) = (yOfs, xOfs)
        last = self.last
        self.move((x - xOfs, y - yOfs))
        self.line((x + xOfs, y + yOfs), layer)
        self.move((x - xOfs, y + yOfs))
        self.line((x + xOfs, y - yOfs), layer)
        self.move(p)
        if txt is not None:
            self.text('%s' % (txt), (x + xOfs, y - yOfs), h, layer)
        self.move(last)

    def drawCircle(self, p, d=0.010, layer=None, txt=None):
        if layer is None:
            layer = self.lDebug
        else:
            if not layer in self.definedLayers:
                self.definedLayers[layer] = True
                if self.d is not None:
                    self.d.add_layer(layer, color=self.color, lineweight=0)
        last = self.last
        self.circle(p, d / 2.0, layer)
        if txt is not None:
            self.add(dxf.text(txt, p, 0.010, \
                              alignpoint=p, halign=CENTER, valign=MIDDLE, \
                              layer=layer))
        self.move(last)

    def drawLine(self, p, m, b, x):
        self.move(self.offset((0, b), p))
        self.move(self.offset((x, m * x + b), p))

    def drawLineCircle(self, m, b, r, index):
        p = (index * 1, 3)
        self.drawLine(p, m, b, 2 * r)
        self.hole(offset((0, 0), p), 2 * r)

    def drawStart(self, l):
        if l.type == ARC:
            (x0, y0) = l.p0
            if not l.swapped:
                a0 = l.a0
            else:
                a0 = l.a1
