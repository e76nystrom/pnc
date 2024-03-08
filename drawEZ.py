from math import degrees
from enum import Enum

import ezdxf
# from ezdxf.gfxattribs import GfxAttribs
from ezdxf.enums import TextEntityAlignment

from svgwrite import Drawing
from svgwrite.path import Path
from svgwrite.shapes import Circle, Rect

from dbgprt import dprt, ePrint
from geometry import ARC, MIN_DIST, calcAngle, labelP, offset, xyDist
from orientation import (O_CENTER, O_LOWER_LEFT, O_LOWER_RIGHT, O_POINT,
                         O_UPPER_LEFT, O_UPPER_RIGHT)

from math import radians, sin, cos, atan2

DRAWING = 'DRAWING'
BORDER  = 'BORDER'
PATH    = 'PATH'
HOLE    = 'HOLE'
TEXT    = 'TEXT'
DEBUG   = 'DEBUG'

class Color(Enum):
    RED     = 1
    YELLOW  = 2
    GREEN   = 3
    CYAN    = 4
    BLUE    = 5
    MAGENTA = 6
    WHITE   = 7

class Draw():
    def __init__(self, cfg):
        self.cfg = cfg
        # self.d = d
        self.dxfFile = ""
        self.doc = None
        self.msp = None

        self.svg = None
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
        self.lDrawing = DRAWING
        self.lBorder =  BORDER
        self.lPath =    PATH
        self.lHole =    HOLE
        self.lText =    TEXT
        self.lDebug =   DEBUG
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

        if drawDxf and self.msp is None:
            self.dxfFile = inFile + "_ngc.dxf"
            self.doc = ezdxf.new(setup=True)
            self.msp = self.doc.modelspace()
            self.layerIndex = 1
            self.doc.layers.add(str(self.layerIndex), color=self.color,
                                linetype='CONTINUOUS', lineweight=0)
            self.setupLayers()

    def close(self):
        if self.doc is not None:
            dprt("save drawing file %s" % (self.dxfFile))
            self.doc.saveas(self.dxfFile)
            self.doc = None
            self.msp = None

        if self.svg is not None:
            self.svg.add(self.lPath)
            if self.materialPath is not None:
                self.svg.add(self.materialPath)
                self.svg.save()
                self.svg = None

    def nextLayer(self):
        self.layerIndex += 1
        self.setupLayers()

    def setupLayers(self):
        i = str(self.layerIndex)
        self.layers = [['lBorder', i + BORDER],
                       ['lPath',   i + PATH],
                       ['lHole',   i + HOLE],
                       ['lText',   i + TEXT],
                       ['lDebug',  i + DEBUG]]
        for (var, l) in self.layers:
            self.definedLayers[l] = True
            self.doc.layers.add(name=var, linetype="CONTINUOUS")
            exec("self." + var + "='" + l + "'")

    def getLayer(self, layer, dLayer):
        if layer is None:
            layer = dLayer
        else:
            if not layer in self.definedLayers:
                self.definedLayers[layer] = True
                self.doc.layers.add(name=layer, color= self.color,
                                    linetype="CONTINUOUS",
                                    lineweight=0)
        return layer

    def scaleOffset(self, point):
        if self.offset == 0.0:
            point = ((self.xOffset + point[0]) * self.pScale,
                     (self.yOffset - point[1]) * self.pScale)
        else:
            point = ((self.xOffset + point[0]) * self.pScale,
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
                self.materialPath = Path(stroke_width=.5, stroke='red',
                                      fill='none')
                path = self.materialPath
            path.push('M', (self.scaleOffset((0, 0))))
            path.push('L', (self.scaleOffset((xSize, 0))))
            path.push('L', (self.scaleOffset((xSize, ySize))))
            path.push('L', (self.scaleOffset((0, ySize))))
            path.push('L', (self.scaleOffset((0, 0))))

            self.path.push('M', (self.scaleOffset((0, 0))))

            # dwg = svgwrite.Drawing(name, (svg_size_width, svg_size_height),
            # debug=True)

        cfg = self.cfg
        if self.msp is not None:
            p0 = p1 = p2 = p3 = (0.0, 0.0)
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

            line = self.msp.add_line
            line(p0, p1, dxfattribs={"layer": self.lBorder})
            line(p1, p2, dxfattribs={"layer": self.lBorder})
            line(p2, p3, dxfattribs={"layer": self.lBorder})
            line(p3, p0, dxfattribs={"layer": self.lBorder})


    def materialOutline(self, lines, layer=None):
        cfg = self.cfg
        if self.svg is not None:
            self.xOffset = 0.0
            self.yOffset = cfg.dxfInput.ySize
            self.svg.add(Rect((0, 0), (cfg.dxfInput.xSize * self.pScale,
                                       cfg.dxfInput.ySize * self.pScale),
                              fill='rgb(255, 255, 255)'))
            path = self.materialPath
            if path is None:
                self.materialPath = Path(stroke_width=.5, stroke='red',
                                         fill='none')
                path = self.materialPath
            for l in lines:
                (start, end) = l
                path.push('M', (self.scaleOffset(start)))
                path.push('L', (self.scaleOffset(end)))

        if self.msp is not None:
            if layer is None:
                layer = self.lBorder
            for l in lines:
                (start, end) = l
                self.msp.add_line(cfg.dxfInput.fix(start),
                                  cfg.dxfInput.fix(end),
                                  dxfattribs={"layer": layer})

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
                
            if self.msp is not None:
                layer = self.getLayer(layer, self.lPath)
                self.msp.add_line(self.last, end,
                                  dxfattribs={"layer": layer})

            # dprt("   line %7.4f %7.4f" % end)
            self.last = end

    def lineDxf(self, start, end, layer=None):
        if self.msp is not None:
            layer = self.getLayer(layer, self.lPath)
            self.msp.add_line(start, end, dxfattribs={"layer": layer})

    def arc(self, end, center, layer=None):
        if self.enable:

            r = xyDist(end, center)
            if self.svg is not None:
                self.path.push_arc(self.scaleOffset(end), 0, r,
                                    large_arc=True, angle_dir='+',
                                    absolute=True)
                
            if self.msp is not None:
                layer = self.getLayer(layer, self.lPath)
                # if (layer == "1PATH" and
                #     xyDist(center, (5.7874, 10.4331)) < MIN_DIST):
                #     print("found")
                p0 = self.last
                p1 = end
                if xyDist(p0, p1) < MIN_DIST:
                    # self.d.add(dxf.circle(r, center, layer=layer))
                    self.msp.add_circle(center, radius=r,
                                        dxfattribs={"layer": layer})
                else:
                    # dprt("p0 (%7.4f, %7.4f) p1 (%7.4f, %7.4f)" %
                    #      (p0[0], p0[1], p1[0], p1[1]))
                    # if orientation(p0, center, p1) == CCW:
                    #     (p0, p1) = (p1, p0)
                    a0 = degrees(calcAngle(center, p0))
                    a1 = degrees(calcAngle(center, p1))
                    if a1 == 0.0:
                        a1 = 360.0
                    # dprt("a0 %5.1f a1 %5.1f" % (a0, a1))
                    self.msp.add_arc(center, radius=r, start_angle=a0,
                                     end_angle=a1,
                                     dxfattribs={"layer": layer})
                self.last = end

    def arcDxf(self, center, r, start, end, layer=None):
        if self.msp is not None:
            layer = self.getLayer(layer, self.lPath)
            self.msp.add_arc(center, radius=r, start_angle=start,
                             end_angle=end, dxfattribs={"layer": layer})

    def circle(self, end, r, layer=None):
        if self.enable:
            if self.msp is not None:
                layer = self.getLayer(layer, self.lHole)
                self.msp.add_circle(end, radius=r,
                                    dxfattribs={"layer": layer})
        self.last = end

    def circleDxf(self, center, r, layer=None):
        if self.msp is not None:
            layer = self.getLayer(layer, self.lHole)
            self.msp.add_circle(center, radius=r, dxfattribs={"layer": layer})
        

    def hole(self, end, drillSize):
        if self.enable:
            if self.svg is not None:
                self.path.push('L', self.scaleOffset(end))
                # dprt("svg line %7.4f %7.4f" % self.scaleOffset(end))
                self.svg.add(Circle(self.scaleOffset(end),
                                    (drillSize / 2) * self.pScale,
                                    stroke='black', stroke_width=.5,
                                    fill="none"))

            if self.msp is not None:
                self.msp.add_line(self.last, end,
                                  dxfattribs={"layer": self.lPath})
                self.msp.add_circle(end, radius=drillSize / 2,
                                    dxfattribs={"layer": self.lPath})
        self.last = end

    def text(self, txt, p0, height, layer=None, align=None):
        if self.enable and self.msp is not None:
            layer = self.getLayer(layer, self.lText)
            # self.d.add(dxf.text(txt, p0, height, layer=layer))
            attrib = {"layer": layer,
                      "style": "LiberationMono"}
            txt = self.msp.add_text(txt, height=height, dxfattribs=attrib)
            if align is None:
                txt.set_placement(p0)
            else:
                txt.set_placement(p0, align=align)

    # def add(self, entity):
    #     if self.enable:
    #         if self.d is not None:
    #             self.d.add(entity)

    def drawCross(self, p, layer=None):
        if self.enable and self.msp is not None:
            layer = self.getLayer(layer, self.lDebug)

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
        if self.enable and self.msp is not None:
            layer = self.getLayer(layer, self.lDebug)

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
        if self.enable and self.msp is not None:
            layer = self.getLayer(layer, self.lDebug)

            last = self.last
            self.circle(p, d / 2.0, layer)
            if txt is not None:
                align = TextEntityAlignment.MIDDLE_CENTER
                txt = self.msp.add_text(txt, height=0.010,
                                        dxfattribs={"layer": layer})
                txt.set_placement(p, align= align)
            self.move(last)

    def drawLine(self, p, m, b, x):
        self.move(offset((0, b), p))
        self.line(offset((x, m * x + b), p))

    def drawLineCircle(self, m, b, r, index):
        p = (index * 1, 3)
        self.drawLine(p, m, b, 2 * r)
        self.hole(offset((0, 0), p), 2 * r)

    def drawStart(self, l): #, cfg):
        r = .05
        (sx, sy) = l.p0

        if l.lType == ARC:
            (cx, cy) = l.c
            a = atan2(sy - cy, sx - cx)
            if not l.swapped:
                a += radians(90)
            else:
                a -= radians(90)
            print("center angle %3.0f" % (degrees(a)))
        else:
            a = l.fwdAngle()
            print("fwdAngle %3.0f" % (degrees(a)))

        ax = radians(150)
        a0 = a - ax
        a1 = a + ax
        x0 = r * cos(a0) + sx
        y0 = r * sin(a0) + sy
        x1 = r * cos(a1) + sx
        y1 = r * sin(a1) + sy

        line = self.msp.add_line
        layer = self.lDebug
        line((x0, y0), l.p0, dxfattribs={"layer": layer})
        line((x1, y1), l.p0, dxfattribs={"layer": layer})
        
    def rectangle(self, xMin, yMin, xMax, yMax):
        p0 = (xMin, yMin)
        p1 = (xMin, yMax)
        p2 = (xMax, yMax)
        p3 = (xMax, yMin)

        line = self.msp.add_line
        layer = self.lDebug
        line(p0, p1, dxfattribs={"layer": layer})
        line(p1, p2, dxfattribs={"layer": layer})
        line(p2, p3, dxfattribs={"layer": layer})
        line(p3, p0, dxfattribs={"layer": layer})
