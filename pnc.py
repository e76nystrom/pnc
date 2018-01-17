#!/cygdrive/c/Python27/Python.exe
#!/cygdrive/c/DevSoftware/Python/Python36-32/Python.exe
#!/usr/local/bin/python2.7
################################################################################

from __future__ import print_function
import sys
import os
import wx
import wx.lib.colourdb
import traceback
import re
import geometry
import inspect
from dbgprt import dprt, dflush, dclose, dprtSet, ePrint
from geometry import Arc, Line
from geometry import oStr, xyDist,  offset
from geometry import inside, rotateMinDist, \
    pathLength, combineArcs, pathDir, \
    labelP, reverseSeg, createPath, \
    calcAngle
from geometry import CW, CCW, MAX_VALUE, MIN_DIST, MIN_VALUE
from mill import Mill
from millLines import MillLine
from sys import stdout
from dxfwrite import DXFEngine as dxf
from dxfwrite import CENTER, MIDDLE
from svgwrite import Drawing
from svgwrite.path import Path
from svgwrite.shapes import Rect, Circle
from math import ceil, cos, degrees, floor, radians, sin, tan
from ezdxf import readfile as ReadFile
from hershey import Font
from os import getcwd
from imp import load_source

O_UPPER_LEFT = 0
O_LOWER_LEFT = 1
O_CENTER = 2
O_POINT = 3
O_MAX = 4

# dxf arcs are always counter clockwise.

dprt("version %s" % (sys.version))

class Config():
    def __init__(self):
        geometry.cfg = self     # set config for geometry module
        self.gui = False        # start in gui
        self.error = False      # initialize error flag
        self.mill = None        # Mill class
        self.printGCode = False # print gcode
        self.draw = None        # Draw class
        self.drawDxf = False    # create dxf drawing
        self.drawSvg = False    # create svg drawing
        self.slot = None        # Slot class
        self.move = None        # Move class
        self.mp = None          # millPath class
        self.line = None        # millLine class
        self.layers = []        # layers to use in dxf file
        self.materialLayer = 'Material' # material layer
        self.dxfInput = None    # dxf input class
        self.init = False       # ncinit has been called
        self.output = True      # produce output in millPath
        self.dxfFile = None     # dxf file from args
        self.fileName = None    # base output file name
        self.d = None           # output debug dxf file
        self.svg = None         # output debug svg file
        self.path = None        # svg path
        self.lineNum = 0        # input line number
        self.slotNum = 0        # slot number
        self.test = False       # test flag
        self.orientation = None # default orientation
        self.orientationLayer = None # layer for orientation point
          
        self.dbg = False        # debugging output
        self.dbgFile = ""       # debug file

        self.climb = False      # climb milling
        self.dir = None         # milling direction
        self.endMillSize = 0.0  # end mill size
        self.finishAllowance = 0.0 # finish allowance
        self.alternate = False  # alternate directions on open path
        self.addArcs = False    # add arcs between line segments

        self.holeMin = 0.0      # hole milling >= size
        self.holeMax = MAX_VALUE # hole milling < size

        self.xSize = 0.0        # material x size
        self.ySize = 0.0        # material y size
        self.zSize = 0.0

        self.xPark = 0.0        # x park location
        self.yPark = 0.0        # y park location
        self.zPark = 1.5        # z park location

        self.xOffset = 0.0      # drill x approach offset
        self.yOffset = 0.0      # drill y approach offset
        self.x = 0.0            # drill x location
        self.y = 0.0            # dirll y location
        self.drillSize = 0.1    # current drill size
        self.peckDepth = 0.0    # peck depth

        self.pause = False       # enable pause
        self.pauseCenter = False # pause at center of hole
        self.pauseHeight = 0.025 # height to pause at

        self.delay = 3.0        # spindle start delay
        self.speed = 1800       # spindle speed
        self.coordinate = 54    # coordinate system

        self.rampAngle = 0.0    # ramp angle
        self.shortRamp = False  # reverse to make ramps short

        self.variables = False  # use variables in ngc file
        self.linuxCNC = False   # generate linux cnc type vars
        self.safeZ = 0.0        # safe z
        self.retract = 0.0      # retract z
        self.top = 0.0          # top
        self.depth = 0.0        # depth
        self.feed = 0.0         # x and y feed rate
        self.zFeed = 0.0        # z feed rate
        self.curFeed = 0.0      # current feed rate

        self.depthPass = 0.0    # depth per pass

        self.widthPasses = 0
        self.widthPerPass = 0
        self.width = 0.0
        self.vBit = 0.0

        self.lastX = 0.0        # last drill x location
        self.lastY = 0.0        # last drill y location
        self.count = 0          # drill hole count
        self.holeCount = None   # total hole count

        self.font = None

        self.min_dist = MIN_DIST
        self.prb = None         # probe output file
        self.probe = False      # generate probe file
        self.probeDepth = 0.0   # probe depth
        self.level = False      # probe input file
        self.probeData = None   # output from probing

        self.runPath = os.path.dirname(sys.argv[0])

        self.tabInit()

        self.cmdAction = {}
        self.cmds = \
        ( \
            ('xpark', self.xPark), \
            ('ypark', self.yPark), \
            ('zpark', self.zPark), \

            ('size', self.setSize), \
            ('drillsize', self.setDrillSize), \
            ('peckdepth', self.setPeckDepth), \

            ('coordinate', self.setCoord), \
            ('variables', self.setVariables), \

            ('safez', self.setSafeZ), \
            ('retract', self.setRetract), \
            ('top', self.setTop), \
            ('depth', self.setDepth), \
            ('depthpass', self.setDepthPass), \

            ('feed', self.setFeed), \
            ('zfeed', self.setZFeed), \

            ('speed', self.setSpeed), \
            ('delay', self.setDelay), \

            ('x', self.setLocX), \
            ('y', self.setLocY), \
            ('loc', self.setLoc), \
            ('xoffset', self.setXOffset), \
            ('yoffset', self.setYOffset), \
            ('drill', self.drill), \

            ('pause', self.setPause), \
            ('pausecenter', self.setPauseCenter), \
            ('pauseheight', self.setPauseHeight), \

            ('rampangle', self.setRampAngle), \
            ('shortramp', self.setShortRamp), \

            ('widthpasses', self.setWidthPasses), \
            ('widthperpass', self.setWidthPerPass), \
            ('width', self.setWidth), \
            ('vbit', self.setVBit), \

            ('xslot', self.xSlot), \
            ('yslot', self.ySlot), \

            ('test', self.setTest), \

            ('endmill', self.setEndMillSize), \
            ('finish', self.setFinish), \
            ('finishallowance', self.setFinish), \

            ('holemin', self.setHoleMin), \
            ('holemax', self.setHoleMax), \

            ('tabs', self.setTabs), \
            ('tabwidth', self.setTabWidth), \
            ('tabdepth', self.setTabDepth), \

            ('direction', self.setDirection), \
            ('output', self.setOutput), \
            ('alternate', self.setAlternate), \
            ('addarcs', self.setAddArcs), \

            ('dxf', self.readDxf), \
            ('setlayers', self.setLayers), \
            ('clrlayers', self.clrLayers), \
            ('materiallayer', self.setMaterialLayer), \
            ('orientation', self.setOrientation), \

            ('dxflines', self.dxfLine), \
            ('dxfgetpath', self.dxfPath), \
            ('dxftab', self.dxfTab), \
            ('dxfpoint', self.dxfPoint), \
            ('dxfoutside', self.dxfOutside), \
            ('dxfinside', self.dxfInside), \
            ('dxfopen', self.dxfOpen), \
            ('dxfdrill', self.dxfDrill), \
            ('dxfmillhole', self.dxfMillHole), \
            ('dxftap', self.dxfTap), \

            ('outputfile', self.outputFile), \

            ('setfont', self.setFont), \
            ('engrave', self.engrave), \
            ('probe', self.setProbe), \
            ('probedepth', self.setProbeDepth), \
            ('level', self.setLevel), \

            ('drawdxf', self.setDrawDxf), \
            ('drawsvg', self.setDrawSvg), \

            ('dbg', self.setDbg), \
            ('dbgfile', self.setDbgFile), \

            ('load', self.load), \
        )
        self.addCommands(self.cmds)

    def addCommands(self, cmds):
        for (cmd, action) in cmds:
            self.cmdAction[cmd.lower()] = action

    def removeCommands(self, cmds):
        for (cmd, action) in cmds:
            del self.cmdAction[cmd.lower()]

    def tabInit(self):
        self.tabPoints = []   # tab points
        self.tabs = 0         # number of tabs
        self.tabWidth = 0.0   # width of tabs
        self.tabDepth = 0.0   # tab thickness

    def setupVars(self):
        if self.linuxCNC:
            self.depthVar = "<_depth>"
            self.retractVar = "<_retract>"
            self.safeZVar = "<_safeZ>"
            self.parkZVar = "<_parkZ>"
            self.topVar = "<_top>"
        else:
            self.topVar = "1"
            self.depthVar = "2"
            self.retractVar = "3"
            self.safeZVar = "4"
            self.parkZVar = "5"

    def parseCmdLine(self):
        n = 1
        self.inFile = None
        while True:
            if n >= len(sys.argv):
                break
            val = sys.argv[n]
            if val.startswith('--'):
                if len(val) >= 3:
                    tmp = val[2:]
                    if tmp == 'probe':
                        self.probe = True
                    elif tmp == 'level':
                        n += 1
                        if n < len(sys.argv):
                            self.level = True
                            self.probeData = sys.argv[n]
                    elif tmp == 'dxf':
                        n += 1
                        if n < len(sys.argv):
                            self.dxfFile = sys.argv[n]
                    elif tmp == 'dbg':
                        n += 1
                        if n < len(sys.argv):
                            self.dbgFile = sys.argv[n]
                            self.dbg = True
                    elif tmp == 'help':
                        self.help()
            elif val.startswith('-'):
                if len(val) >= 2:
                    tmp = val[1]
                    if tmp == "d":
                        self.dbg = True
                    elif tmp == "l":
                        self.linuxCNC = True
                    elif tmp == "g":
                        cfg.gui = True
                    elif tmp == 's':
                        self.drawSvg = True
                    elif tmp == 'x':
                        self.drawDxf = True
                    elif tmp == 'h':
                        self.help()
            elif val.startswith('?'):
                self.help();
            else:
                if self.inFile is None:
                    self.inFile = val
                    if not re.search('\.[a-zA-Z0-9]*$', self.inFile):
                        self.inFile += ".pnc"
                    dprt(self.inFile)
                    dflush()
                else:
                    self.dxfFile = val
            n += 1

    def help(self):
        print("Usage: pnc [options] pncFile [dxfInput]")
        print(" ?            help\n" \
              " -d           debug\n" \
              " -h           help\n" \
              " -s           output svf file\n" \
              " -x           output dxf file\n" \
              " --dbg file   debug output file\n" \
              " --dxf file   dxf input file\n" \
              " --level file level input file\n" \
              " --probe      generate probe data" \
        )
        sys.exit()
        
    def open(self):
        self.setupVars()
        inp = open(self.inFile, 'r')
        self.dirPath = os.path.dirname(self.inFile)
        self.fileName = os.path.basename(self.inFile).replace(".pnc", "")
        if len(self.dirPath) != 0:
            self.baseName = os.path.join(self.dirPath, self.fileName)
        else:
            self.baseName = self.fileName

        dprtSet(self.dbg, os.path.join(self.dirPath, self.dbgFile) \
                if len(self.dbgFile) != 0 else "")

        for l in inp:
            l = l.strip()
            line = re.sub("\s*#.*$", "", l)
            self.lineNum += 1
            dprt("%2d %s" % (self.lineNum, l))
            dflush()
            if len(line) == 0:
                continue
            if line.startswith('#'):
                continue
            arg = line.split(' ')
            if len(arg) >= 1:
                cmd = arg[0].lower()
                arg[0] = line
                if cmd in self.cmdAction:
                    action = self.cmdAction[cmd]
                    try:
                        action(arg)
                        if self.error:
                            break
                    # except ValueError:
                    #     ePrint("Invalid argument line %d %s" % \
                    #           (self.lineNum, line))
                    # except IndexError:
                    #     ePrint("Missing argument line %d %s" % \
                    #           (self.lineNum, line))
                    except:
                        traceback.print_exc()
                        exit()
                else:
                    ePrint("%2d %s" % (self.lineNum, l))
                    ePrint("invalid cmd %s" % cmd)

        try:
            self.draw.close()   # close drawing files
        except:
            pass
        inp.close()             # close input file
        dclose()                # close debug file
        self.end()              # close nc files

    def end(self):
        self.init = False
        if self.mill is not None:
            self.mill.close()
        self.lastX = 0.0
        self.lastY = 0.0
        if self.probe:
            if self.prb is not None:
                self.prb.out.write("(PROBECLOSE)\n")
                self.prb.close()
                self.prb = None
            self.probe = False

    def ncInit(self):
        if self.init:
            return
        self.init = True

        draw = self.draw
        if draw is None:
            self.draw = draw = Draw()
            geometry.draw = draw

        draw.open(self.outFileName, self.drawDxf, self.drawSvg)

        dxfInput = self.dxfInput
        if dxfInput is not None:
            if len(dxfInput.material) != 0:
                self.draw.materialOutline(dxfInput.material)
            else:
                self.draw.material(dxfInput.xSize, dxfInput.ySize)

        draw.move((0.0, 0.0))

        outFile = self.outFileName + ".ngc"
        if self.mill is None:
            self.mill = Mill(self, outFile)
        else:
            self.mill.init(outFile)
        self.mill.setSpeed(self.speed)
        self.openOutput = False

        if self.probe:
            self.probeInit()

    def probeInit(self):
        probeFile = self.outFileName + "-prb.ngc"
        self.prb = prb = Mill(self, probeFile, False)
        prb.out.write("(PROBEOPEN %s.prb)\n" % (probeFile))
        return(prb)

    def probeOpen(self):
        probeData = self.probeData
        if not os.path.isfile(probeData):
            fileDir = os.path.dirname(probeData)
            if len(fileDir) == 0:
                probeData = os.path.join(cfg.dirPath, probeData)
        try:
            inp = open(probeData, 'r')
            return(inp)
        except IOError:
            ePrint("probe data file %s not found" % (self.probeData))
        return(None)
        
    def xPark(self, args):
        self.xPark = float(args[1])

    def yPark(self, args):
        self.yPark = float(args[1])

    def zPark(self, args):
        self.zPark = float(args[1])
        
    def setSize(self, args):
        self.xSize = float(args[1])
        self.ySize = float(args[2])
        if len(args) >= 4:
            self.zSize = float(args[3])

        out = self.mill.out
        out.write("(material size x %0.3f y %0.3f" % \
                            (self.xSize, self.ySize))
        if self.zSize != 0:
            out.write(" z %0.3f" % (self.zSize))
        out.write(")\n")
        self.draw.material(self.xSize, self.ySize)

    def setDrillSize(self, args):
        self.drillSize = float(args[1])

    def setPeckDepth(self, args):
        self.peckDepth = float(args[1])

    def setCoord(self, args):
        self.coordinate = int(args[1])

    def setVariables(self, args):
        self.variables = int(args[1]) != 0

    def setSafeZ(self, args):
        self.safeZ = float(args[1])

    def setRetract(self, args):
        self.retract = float(args[1])

    def setTop(self, args):
        self.top = float(args[1])

    def setDepth(self, args):
        self.depth = float(args[1])

    def setFeed(self, args):
        self.feed = float(args[1])

    def setZFeed(self, args):
        self.zFeed = float(args[1])

    def setSpeed(self, args):
        self.speed = float(args[1])
        if self.mill is not None:
            self.mill.setSpeed(self.speed)

    def setDelay(self, args):
        self.delay = float(args[1])

    def setLoc(self, args):
        self.x = float(args[1])
        self.y = float(args[2])

    def setLocX(self, args):
        self.x = float(args[1])

    def setLocY(self, args):
        self.y = float(args[1])

    def setXOffset(self, args):
        self.xOffset = float(args[1])

    def setYOffset(self, args):
        self.yOffset = float(args[1])

    def setRampAngle(self, args):
        self.rampAngle = radians(float(args[1]))

    def setEndMillSize(self, args):
        self.endMillSize = float(args[1])

    def setHoleMin(self, args):
        if len(args) >= 2:
            self.holeMin = float(args[1])
        else:
            self.holeMin = 0.0

    def setHoleMax(self, args):
        if len(args) >= 2:
            self.holeMax = float(args[1])
        else:
            self.holeMax = MAX_VALUE
            
    def setDepthPass(self, args):
        self.depthPass = abs(float(args[1]))

    def setWidth(self, args):
        self.width = abs(float(args[1]))

    def setVBit(self, args):
        self.vBit = radians(abs(float(args[1])))

    def setWidthPasses(self, args):
        self.widthPasses = int(args[1])

    def setWidthPerPass(self, args):
        self.widthPerPass = float(args[1]) / 2

    def setPause(self, args):
        self.pause = int(args[1]) != 0

    def setTest(self, args):
        self.test = int(args[1]) != 0

    def setDirection(self, args):
        dir = args[1].lower()
        if dir == 'climb':
            self.climb = True
            self.dir = None
        elif dir == 'normal':
            self.climb = False
            self.dir = None
        elif dir == 'cw':
            self.dir = CW
            self.climb = None
        elif dir == 'ccw':
            self.dir = CCW
            self.climb = None
        else:
            ePrint("invalid direction %s" % dir)

    def setFinish(self, args):
        self.finishAllowance = float(args[1])

    def setTabs(self, args):
        self.tabs = int(args[1])

    def setTabWidth(self, args):
        self.tabWidth = float(args[1])

    def setTabDepth(self, args):
        self.tabDepth = float(args[1])

    def setOutput(self, args):
        self.output = int(args[1]) != 0

    def setAlternate(self, args):
        self.alternate = int(args[1]) != 0

    def setAddArcs(self, args):
        self.addArcs = int(args[1]) != 0

    def setShortRamp(self, args):
        self.shortRamp = int(args[1]) != 0

    def setPauseCenter(self, args):
        self.pauseCenter = int(args[1]) != 0

    def setPauseHeight(self, args):
        self.pauseHeight = float(args[1])
        
    def setDrawDxf(self, args):
        self.drawDxf = int(args[1]) != 0

    def setDrawSvg(self, args):
        self.drawSvg = int(args[1]) != 0

    def setDbg(self, args):
        self.dbg = int(args[1]) != 0
        dprtSet(dbgFlag=self.dbg)

    def setDbgFile(self, args):
        self.dbgFile = os.path.join(self.dirPath, args[1])
        self.dbg = True
        dprtSet(self.dbg, dFile=self.dbgFile)

    def drill(self, args=None, tap=False):
        self.ncInit()
        if args is not None:
            if len(args) >= 2:
                self.x = float(args[1])
            if len(args) >= 3:
                self.y = float(args[2])
        self.count += 1
        mill = self.mill
        out = mill.out
        gMove = "0"
        if abs(self.lastY - self.y) < MIN_DIST:
            if self.xOffset != 0:
                out.write("g0 x%7.4f\n" % (self.x - self.xOffset))
                gMove = "1"
                mill.setFeed(self.feed)
            out.write("g%s x%7.4f\n" % (gMove, self.x))
        elif abs(self.lastX - self.x) < MIN_DIST:
            if self.yOffset != 0:
                out.write("g0 y%7.4f\n" % (self.y - self.yOffset))
                gMove = "1"
                mill.setFeed(self.feed)
            out.write("g%s y%7.4f\n" % (gMove, self.y))
        else:
            if self.lastX != self.x and self.lastY != self.y:
                if self.xOffset != 0 or self.yOffset != 0:
                    out.write("g0 x%7.4f y%7.4f\n" % \
                              (self.x - self.xOffset, self.y - self.yOffset))
                    gMove = "1"
                    mill.setFeed(self.feed)
                out.write("g%s x%7.4f y%7.4f\n" % (gMove, self.x, self.y))
        self.draw.hole((self.x, self.y), self.drillSize)
        holeCount = "/%d" % (self.holeCount) if self.holeCount is not None \
                    else ""
        comment = "hole %d%s x%7.4f y%7.4f" % \
                  (self.count, holeCount, self.x, self.y)
        if not tap:
            if self.pause:
                mill.moveZ(self.pauseHeight)
                out.write("m0 (pause)\n")
            mill.zTop()
            if self.peckDepth == 0:
                mill.zDepth(comment=comment)
            else:
                d = self.peckDepth
                while True:
                    mill.plungeZ(d, comment)
                    if d <= self.depth:
                        break
                    mill.zTop()
                    mill.moveZ(d)
                    d += self.peckDepth
                    if d < self.depth:
                        d = self.depth
            mill.retract()
        else:
            out.write("m0 (pause insert tap)\n");
            if cfg.variables:
                z = "[#%s + #%s]" % (self.topVar, self.depthVar)
            else:
                z = "%0.4f" % (cfg.top + cfg.depth)
            out.write("g0 z %s\t(%s)\n" % (z, comment))
            out.write("m0 (pause tap hole)\n")
            mill.retract()
            out.write("m0 (pause remove tap)\n")
        out.write("\n")
        self.lastX = self.x
        self.lastY = self.y

    def getMillPath(self):
        if self.mp is None:
            self.mp = MillPath(self)
        self.mp.config(self)
        return(self.mp)

    def millSlot(self, p, width, length, str):
        self.slotNum + 1
        self.mill.out.write("(%s %2d width %0.3f length %0.3f "\
                            "at x %0.3f y %0.3f)\n" % \
                            (str, self.slotNum, width, length, self.x, self.y))
        self.mill.out.write("(endMill %0.3f depth %0.3f depthPass %0.3f)\n" % \
                            (self.endMillSize, self.depth, self.depthPass))
        seg = []
        seg.append(Line(p[0], p[1]))
        closed = len(p) > 2
        if closed:
            seg.append(Line(p[1], p[2]))
            seg.append(Line(p[2], p[3]))
            seg.append(Line(p[3], p[0]))
            dist = self.endMillSize / 2 + self.finishAllowance
            path = createPath(seg, dist, False, addArcs=False)[0]
        else:
            path = seg
        self.ncInit()
        mp = self.getMillPath()
        mp.millPath(path, None)

    def xSlot(self, args):
        width = float(args[1])
        length = float(args[2])
        # self.slotNum += 1
        # self.out.write("(xSlot %2d width %0.3f length %0.3f "\
        #               "at x %0.3f y %0.3f)\n" % \
        #               (slotNum, width, length, self.x, self.y))
        # self.out.write("(endMill %0.3f depth %0.3f depthPass %0.3f)\n" % \
        #           (self.endMillSize, self.depth, self.depthPass))
        if abs(width - self.endMillSize) < MIN_DIST:
            points = ( \
                       (self.x, self.y), \
                       (self.x + length, self.y))
        else:
            points = ( \
                       (self.x, self.y), \
                       (self.x + length, self.y), \
                       (self.x + length, self.y + width), \
                       (self.x, self.y + width))
        self.millSlot(points, width, length, 'xSlot')
        # ncInit()
        # if slot is None:
        #     slot = Slot(self.mill, self.draw)
        # slot.xSlot(width, length)

    def ySlot(self, args):
        width = float(args[1])
        length = float(args[2])
        # self.slotNum += 1
        # self.out.write("(ySlot %2d width %0.3f length %0.3f "\
        #               "at x %0.3f y %0.3f)\n" % \
        #               (self.slotNum, width, length, self.x, self.y))
        if abs(width - self.endMillSize) < MIN_DIST:
            points = ( \
                       (self.x, self.y), \
                       (self.x, self.y + length))
        else:
            points = ( \
                       (self.x, self.y), \
                       (self.x, self.y + length), \
                       (self.x + width, self.y + length), \
                       (self.x + width, self.y))
        self.millSlot(points, width, length, 'ySlot')
        # self.out.write("(endMill %0.3f depth %0.3f depthPass %0.3f)\n" % \
        #           (self.endMillSize, self.depth, self.depthPass))
        # ncInit()
        # if self.slot is None:
        #     self.slot = Slot(self.mill, self.draw)
        # self.slot.ySlot(width, length)

    def setLayers(self, args):
        for l in args[1:]:
            self.layers.append(l)

    def clrLayers(self, args):
        self.layers = []

    def setMaterialLayer(self, args):
        self.materialLayer = args[1]

    def setOrientation(self, args):
        o = ((O_UPPER_LEFT, "upperleft"), \
             (O_LOWER_LEFT, "lowerleft"), \
             (O_CENTER, "center"), \
             (O_POINT, "point"), \
        )
        val = args[1].lower()
        for (i, x) in o:
            if val == x:
                self.orientation = i
                val = None
                break
        if val is not None:
            self.orientation = int(args[1])
            if self.orientation >= 0 or \
               self.orientation < O_MAX:
                ePrint("invalid orientation %d", self.orientation)
                self.orientation = None
        layer = None
        if self.orientation == O_POINT:
            self.orientationLayer = layer = args[2]
        if self.dxfInput is not None:
            self.dxfInput.setOrientation(self.orientation, layer)

    def readDxf(self, args):
        if self.orientation is None:
            self.error = True
            dprt("orientation not set")
            dflush()
        l = args[0]
        fileName = l.split(' ', 1)[-1]
        if fileName == "*":
            if self.dxfFile is not None:
                if re.search("\.dxf$", self.dxfFile):
                    fileName = self.dxfFile
                    self.baseName = fileName.replace(".dxf", "")
                else:
                    self.baseName = self.dxfFile
                    fileName = self.dxfFile + ".dxf"
            else:
                fileName = self.fileName + ".dxf"
                self.baseName = fileName
        else:
            self.baseName = fileName.split('.')[0]

        fileDir = os.path.dirname(fileName)
        if len(fileDir) == 0 and len(self.dirPath) != 0:
            fileName = os.path.join(self.dirPath, fileName)

        baseDir = os.path.dirname(self.baseName)
        if len(baseDir) == 0 and len(self.dirPath) != 0:
            self.baseName = os.path.join(self.dirPath, self.baseName)

        dprt("fileName %s" % fileName)
        dprt("baseName %s" % self.baseName)

        self.dxfInput = Dxf(self.mill, self.draw)
        self.dxfInput.open(fileName, self.layers, self.materialLayer)
        self.dxfInput.setOrientation(self.orientation, self.orientationLayer)

    def dxfLine(self, args):
        self.ncInit()
        if self.line is None:
            self.line = MillLine(self, self.mill, self.draw)
        self.line.millLines(args[1])

    def dxfPath(self, args):
        layer = args[1]
        self.segments = self.dxfInput.getPath(layer)

    def dxfPoint(self, args):
        x = float(args[1])
        y = float(args[2])
        inside((x, y), self.segments[0])

    def dxfTab(self, args):
        layer = args[1]
        self.tabPoints = self.dxfInput.getPoints(layer)
        self.tabs = len(self.tabPoints)
        for (i, p) in enumerate(self.tabPoints):
            dprt("%2d p %7.4f, %7.4f" % (i, p[0], p[1]))
            # cfg.draw.drawX(p, "t%d" % (i))
        
    def dxfOutside(self, args):
        layer = args[1]
        dist = self.endMillSize / 2 + self.finishAllowance
        self.segments = self.dxfInput.getPath(layer, True)
        self.ncInit()
        mp = self.getMillPath()
        for (i, seg) in enumerate(self.segments):
            dprt("seg %d" % (i))
            if xyDist(seg[0].p0, seg[-1].p1) > MIN_DIST:
                ePrint("dxfOutside - segment not closed skipping")
                continue
            (path, tabPoints) = createPath(seg, dist, True, self.tabPoints, \
                                           addArcs=self.addArcs)
            mp.millPath(path, tabPoints)
        self.tabPoints = []

    def dxfInside(self, args):
        layer = args[1]
        dist = self.endMillSize / 2 + self.finishAllowance
        self.segments = self.dxfInput.getPath(layer, True)
        self.ncInit()
        mp = self.getMillPath()
        for (i, seg) in enumerate(self.segments):
            dprt("seg %d" % (i))
            if xyDist(seg[0].p0, seg[-1].p1) > MIN_DIST:
                ePrint("dxfInside - segment not closed skipping")
                continue
            (path, tabPoints) = createPath(seg, dist, False, self.tabPoints, \
                                           addArcs=self.addArcs)
            mp.millPath(path, tabPoints)
        self.tabPoints = []

    def dxfOpen(self, args):
        layer = args[1]
        dist = self.endMillSize / 2.0 + self.finishAllowance
        d = self.endMillSize / 2.0 + 0.020
        self.segments = self.dxfInput.getPath(layer)
        self.points = self.dxfInput.getPoints(layer)
        if len(self.segments) == 0:
            return
        self.ncInit()
        mp = self.getMillPath()
        for (i, seg) in enumerate(self.segments):
            dprt("seg %d" % (i))
            for l in seg:
                l.prt()
            if xyDist(seg[0].p0, seg[-1].p1) < MIN_DIST:
                ePrint("dxfOpen - segment is closed skipping")
                continue
            l = seg[0].extend(d, True)
            seg.insert(0, l)
            l = seg[-1].extend(d, False)
            seg.append(l)
            if len(self.points) > 0:
                (path, tabPoints) \
                    = createPath(seg, dist, False, self.tabPoints, False, \
                                 self.points[0], addArcs=self.addArcs)
            else:
                path = seg
                tabPoints = None
            for l in path:
                l.prt()
            mp.millPath(path, tabPoints, False)
        self.tabPoints = []

    def dxfDrill(self, args, tap=False):
        layer = args[1]
        drill = self.dxfInput.getHoles(layer)
        self.ncInit()
        last = self.mill.last
        for d in drill:
            self.holeCount = len(d.loc)
            self.mill.out.write("(drill size %6.3f holes %d)\n" % \
                                (d.size, self.holeCount))
            self.count = 0
            dLoc = d.loc
            while len(dLoc) != 0:
                minDist = MAX_VALUE
                index = 0
                for (i, loc) in enumerate(dLoc):
                    dist = xyDist(last, loc)
                    # dprt("%d last %7.4f %7.4g loc %7.4f %7.4f dist %7.4f" % \
                    #       (i, last[0], last[1], loc[0], loc[1], dist))
                    if dist < minDist:
                        minDist = dist
                        index = i
                loc = dLoc.pop(index)
                # dprt("%d loc %7.4f %7.4f" % (index, loc[0], loc[1]))
                last = loc
                self.drill(loc, tap)

    def dxfMillHole(self, args, drill=None):
        if drill is None:
            layer = args[1]
            drill = self.dxfInput.getHoles(layer)
        self.ncInit()
        last = self.mill.last
        mp = self.getMillPath()
        for d in drill:
            if d.size < self.holeMin or \
               d.size >= self.holeMax:
                continue
            self.mill.out.write("(drill size %6.3f holes %d)\n" % \
                                (d.size, len(d.loc)))
            dLoc = d.loc
            n = 1
            while len(dLoc) != 0:
                minDist = MAX_VALUE
                index = 0
                for (i, loc) in enumerate(dLoc):
                    dist = xyDist(last, loc)
                    if dist < minDist:
                        minDist = dist
                        index = i
                loc = dLoc.pop(index)
                self.draw.hole((loc[0], loc[1]), d.size)
                self.mill.out.write("(hole %d at %7.4f, %7.4f)\n" % \
                               (n, loc[0], loc[1]))
                last = loc
                size = (d.size - self.endMillSize - self.finishAllowance) / 2.0
                a = Arc(loc, size, 0.0, 360.0)
                if self.pauseCenter:
                    mill = self.mill
                    mill.safeZ()
                    mill.move(loc)
                    mill.moveZ(self.pauseHeight)
                    mill.pause()
                path = []
                path.append(a)
                if self.tabs != 0:
                    self.tabPoints = []
                    a0 = 0.0
                    step = radians(360.0 / self.tabs)
                    for i in range(self.tabs):
                        x = loc[0] + size * cos(a0)
                        y = loc[1] + size * sin(a0)
                        self.tabPoints.append((x, y))
                        a0 += step
                mp.millPath(path, self.tabPoints)
                n += 1
        self.tabPoints = []

    def dxfTap(self, args):
        self.dxfDrill(args, True)

    def outputFile(self, args):
        self.end()
        if self.draw is not None:   # close drawing files
            self.draw.close()
            self.draw = None
        self.tabInit()          # reset tabs
        self.finishAllowance = 0.0 # reset finish allowance
        l = args[0]
        fileName = l.split(' ', 1)[-1]
        if fileName.startswith('*'):
            fileName = self.baseName + fileName[1:]
        else:
            fileName = self.dirPath + os.sep + fileName
        self.outFileName = fileName

    def setFont(self, args):
        if len(args) >= 2:
            fontFile = args[1]
        else:
            fontFile = "rowmans.jhf"
        fontFile = os.path.join(self.runPath, fontFile)
        self.ncInit()
        self.font = Font(self.mill, self.draw, fontFile)
        self.font.offset()

    def engrave(self, args):
        if len(args) >= 2:
            name = args[1] + ".py"
            file = os.path.join(getcwd(),  name)
            if not os.path.isfile(file):
                file = os.path.join(self.runPath, name)
            module = load_source("module", file)
            # print(dir(module))
            # for m in inspect.getmembers(module, inspect.isclass):
            #     print(m)
            self.engrave = module.Engrave(cfg)
            self.engrave.setup()
        else:
            if self.engrave is not None:
                self.ncInit()
                self.engrave.engrave()

    def load(self, args):
        if len(args) >= 2:
            moduleName = args[1]
            name = moduleName + ".py"
            fileName = os.path.join(getcwd(),  name)
            if not os.path.isfile(fileName):
                fileName = os.path.join(self.runPath, name)
            module = load_source(moduleName, fileName)
            # print(dir(module))
            for (name, val) in inspect.getmembers(module, inspect.isclass):
                if val.__module__ == moduleName:
                    # print("class %s" % (name))
                    cmd = "module.%s(cfg)" % (name)
                    c = eval(cmd)
                    cmd = "self.%s = c" % (moduleName)
                    exec(cmd)
                    self.addCommands(c.cmds)

    def setProbe(self, args):
        self.probe = int(args[1]) != 0

    def setProbeDepth(self, args):
        self.probeDepth = float(args[1])

    def setLevel(self, args):
        self.probeData = args[1]
        self.level = True
        
class Drill():
    def __init__(self, size):
        self.size = size
        self.loc = []

    def addLoc(self, p):
        self.loc.append(p)

T_START = 0
T_TAB_END = 1
T_RAMP = 2

class MillPath():
    def __init__(self, cfg):
        self.cfg = cfg
        self.mill = cfg.mill

    def config(self, cfg=None):
        cfg = self.cfg
        self.cfgDepth = cfg.depth
        self.depth = cfg.depth
        self.depthPass = cfg.depthPass
        self.rampAngle = cfg.rampAngle
        self.tanRampAngle = tan(cfg.rampAngle)
        self.tabs = cfg.tabs
        self.tabWidth = cfg.tabWidth + cfg.endMillSize
        self.tabDepth = cfg.tabDepth

    def init(self, closed=True):
        self.config()
        self.closed = closed
        self.passNum = 0
        self.passes = 0
        self.rampDist = 0.0
        self.currentDepth = 0.0
        self.lastDepth = 0.0
        self.last = 0.0
        self.ramp = False
        self.done = False
        self.tab = False

    def rampSetup(self):
        self.ramp = False
        self.millRamp = False
        self.rampClean = []
        # if self.closed and self.rampAngle != 0.0:
        if self.rampAngle != 0:
            dist = abs(self.depthPass) / self.tanRampAngle
            if dist > self.totalLength:
                self.depthPass = self.totalLength * self.tanRampAngle
            dprt("rampDist %7.4f totalLength %7.4f depthPass %7.4f" % \
                  (dist, self.totalLength, self.depthPass))
        if self.cfg.shortRamp:
            return(self.rampLineShort)
        else:
            return(self.rampLine)

    def passSetup(self):
        self.absDepth = abs(self.depth)
        self.finalPass = 0.0
        if self.tabs != 0:
            self.finalPass = self.tabDepth
            self.absDepth -= self.finalPass
            self.depth += self.finalPass
        tmp = self.absDepth / self.depthPass
        if tmp - floor(tmp) < 0.002:
            self.passes = int(floor(tmp))
        else:
            self.passes = int(ceil(tmp))
        self.passCount = self.passes
        dprt("passes %d cfgDepth %6.4f depth %6.4f " \
              "depthPass %6.4f finalPass %6.4f" % \
              (self.passes, self.cfgDepth, self.depth, \
               self.depthPass, self.finalPass))
        self.rampPass = 0
        self.tabPass = 0
        # if self.closed and self.rampAngle != 0.0 and not self.cfg.shortRamp:
        if self.rampAngle != 0.0 and not self.cfg.shortRamp:
            self.rampPass += 1
            self.passCount += 1
        if self.tabs != 0:
            if self.rampPass != 0:
                self.rampPass += 1
            self.tabPass += 1
            self.passCount += 1

    def tabSetup(self, path):
        self.tabRamp = 0.0
        self.tabRampDist = 0.0
        self.tabRampEnd = 0.0
        self.tabRampDepth = 0.0
        self.tabRampClean = []
        self.tabNum = 0
        self.tabState = T_START
        
        tabPos = self.tabPos
        if self.tabs != 0 or tabPos is not None:
            if self.cfg.alternate:
                ePrint("***error no tabs with alternate")
                return
            self.tabRamp = 0.0
            if self.rampAngle != 0.0:
                self.tabRamp = self.tabDepth / self.tanRampAngle

            if tabPos is not None:
                d = self.tabWidth / 2.0
                for (i, p)  in enumerate(tabPos):
                    p -= d
                    if p < 0:
                        p += self.totalLength
                    tabPos[i] = p
                tabPos.sort()
                self.tabPos = tabPos
            else:
                tabDist = self.totalLength / self.tabs
                tabLoc = 0.0
                tabLoc = tabDist / 2.0 - self.tabWidth
                for i in range(self.tabs):
                    self.tabPos.append(tabLoc)
                    dprt("tab %2d loc %7.4f" % (i, tabLoc))
                    tabLoc += tabDist

            if len(self.tabPos) != 0:     # if tabs
                if self.closed:
                    if self.tabPos[0] != 0.0:
                        d = self.tabPos[0]
                        while True:
                            l = path.pop(0)
                            if l.length - d > MIN_DIST:
                                (l0, l1) = l.split(d)
                                path.append(l0)
                                path.insert(0, l1)
                                l.mill(self.mill, None, "rs1")
                                break
                            else:
                                d -= l.length
                                path.append(l)
                                l.mill(self.mill, None, "rs0")
                        d = self.tabPos[0]
                        for i in range(len(self.tabPos)):
                            self.tabPos[i] -= d
                        self.tabLength = self.tabWidth
                        self.tabState = T_TAB_END
                else:
                    self.tabState = T_START

    def tabRampInit(self):
        d = self.tabRamp / 2.0
        if self.tabPos[0] < d:
            self.tabPos[0] = d
        self.tabRampDist = d
        dprt("tabRampDist %7.4f" % (self.tabRampDist))
        self.tabRampDepth = 0.0
        self.tabRampClean = []

    def calcPassDepth(self):
        # calculate pass depth
        if self.tab:
            self.currentDepth = self.cfgDepth
        else:
            if abs(self.currentDepth - self.depthPass) < self.absDepth:
                self.currentDepth -= self.depthPass
            else:
                self.currentDepth = self.depth

        self.mill.out.write("(pass %d depth %7.4f" % \
                           (self.passNum, self.currentDepth))

        dprt("passNum %d lastDepth %6.4f currentDepth %6.4f" % \
              (self.passNum, self.lastDepth, self.currentDepth))

    def calcPassRamp(self):     # ramp calculations for pass
        if self.tab:            # if tab pass
            return
        # if self.closed and self.rampAngle != 0.0: # if ramp configured
        if self.rampAngle != 0.0: # if ramp configured
            self.ramp = True
            passDepth = self.currentDepth - self.lastDepth
            if self.millRamp:   # if last pass
                self.rampDist = self.lastRamp
            else:               # if not last pass
                self.rampDist = abs(passDepth) / self.tanRampAngle
                if self.cfg.shortRamp:
                    self.rampDist /= 2.0
                    self.lastRamp = 0.0
                else:
                    self.lastRamp = self.rampDist
            self.rampDepth = 0.0

            self.mill.out.write(" passDepth %7.4f rampDist %6.4f " \
                                "millRamp %s" % \
                                (passDepth, self.rampDist, self.millRamp))

            dprt("passDepth %6.4f rampDist %6.4f millRamp %s" % \
                    (passDepth, self.rampDist, self.millRamp))
        else:
            self.ramp = False

    def rampLine(self, l):
        if self.rampDist <= l.length: # if ramp fits in this line
            (l0, l1) = l.split(self.rampDist)
            comment = 'r0 %d' % (l.index)
            if self.millRamp:   # if final pass for ramp
                self.millRamp = False
                self.done = True
                self.millSeg(l0, None, comment)
            else:               # if not final pass
                cfg.draw.drawX(l0.p1, 'R', True)
                self.millSeg(l0, self.currentDepth, comment)
                if abs(l1.length) > MIN_DIST:
                    self.millSeg(l1, None, comment)
            self.ramp = False
            self.rampDist = 0.0
        else:                   # if ramp does not fit in line
            self.rampDist -= l.length
            if not self.millRamp: # if not final pass for ramp
                self.rampDepth += l.length * self.tanRampAngle
            comment = 'r1 %d' % (l.index)
            self.millSeg(l, self.lastDepth - self.rampDepth, comment)

    def rampLineShort(self, l):
        d = self.rampDist
        if l.length >= d:         # if ramp fits
            (l0, l1) = l.split(d)
            cfg.draw.drawX(l0.p1, 'R', True)
            self.rampClean.append(l0)
            self.rampDist = 0.0
            self.ramp = False
            self.passLoc += d
            self.rampSeg(l0, "r1")
            self.cleanRamp()
            comment = 'r0 %d' % (l.index)
            self.millSeg(l1, None, comment)
        else:
            self.rampDist -= l.length
            self.passLoc += l.length
            self.rampClean.append(l)
            self.rampSeg(l, "r0")

    def rampSeg(self, l, comment):
        self.rampDepth += l.length * self.tanRampAngle
        l.mill(self.mill, self.lastDepth - self.rampDepth, comment)

    def cleanRamp(self):
        for l in reverseSeg(self.rampClean):
            l.prt
            self.rampSeg(l, "rc0")
        if abs(self.currentDepth -
               (self.lastDepth - self.rampDepth)) > MIN_DIST:
            self.mill.plungeZ(self.currentDepth)

        for l in self.rampClean:
            l.prt()
            l.mill(self.mill, None, "rc1")
        self.rampClean = []

    def tabLine(self, l):
        dprt()
        dprt("tabLine passLoc %7.4f" % (self.passLoc))
        l.prt()
        tabState = self.tabState
        while True:
            length = l.length
            if self.tabNum < self.tabs:
                tabPos = self.tabPos[self.tabNum]
            else:
                tabPos = self.totalLength
            dprt("%2d %d %s length %7.4f passLoc %7.4f, %7.4f " \
                  "pos %7.4f" % \
                  (l.index, self.tabNum, ('str', 'end', 'rmp')[tabState], \
                   length, self.passLoc, self.passLoc + length, tabPos))
            if tabState == T_START: # start tab
                if tabPos < (self.passLoc + length): # if tab in this line
                    d = tabPos - self.passLoc
                    dprt("%d tabPos %6.3f passLoc %6.3f " \
                          "d %6.3f l %6.3f" % \
                          (self.tabNum, tabPos, self.passLoc, \
                           d, length))
                    if d > MIN_DIST:
                        (l0, l1) = l.split(d)
                        cfg.draw.drawX(l0.p1, "%d" % (self.tabNum))
                        comment = "ts0 t %d l %d" % (self.tabNum, l.index)
                        depth = self.currentDepth + self.tabDepth
                        self.millSeg(l0, None, comment)
                        self.mill.moveZ(depth)
                        l = l1
                    else:       # if no tab
                        cfg.draw.drawX(l.p0, "%d" % (self.tabNum))
                    self.tabLength = self.tabWidth
                    tabState = T_TAB_END
                else:
                    if self.tabNum == 0:
                        self.mill.plungeZ(self.currentDepth)
                    comment = "ts1 t %d l %d" % (self.tabNum, l.index)
                    self.millSeg(l, None, comment)
                    break
            elif tabState == T_TAB_END: # end tab
                d = self.tabLength
                if length > d:  # if tab fits in this line
                    (l0, l1) = l.split(d)
                    cfg.draw.drawX(l0.p1, "%d" % (self.tabNum))
                    comment = "te0 t %d l %d" % (self.tabNum, l.index)
                    self.millSeg(l0, None, comment)
                    l = l1
                    self.tabNum += 1
                    if self.tabRamp == 0.0: # if no tab ramp
                        self.mill.plungeZ(self.currentDepth)
                        tabState = T_START
                    else:       # if tab ramp present
                        self.tabRampInit()
                        tabState = T_RAMP
                else:           # if tab does not fine in this line
                    comment = "te1 t %d l %d" % (self.tabNum, l.index)
                    self.millSeg(l, None, comment)
                    break
            elif tabState == T_RAMP: # generate tab ramp
                d = self.tabRampDist
                if length >= d: # if ramp fits in this line
                    (l0, l1) = l.split(d)
                    self.tabRampClean.append(l0)
                    cfg.draw.drawX(l0.p1, "r")
                    self.tabRampDist = 0.0
                    self.passLoc += d
                    self.tabRampSeg(l0, "tr1")
                    self.cleanTabRamp()
                    l = l1
                    tabState = T_START
                else:           # if ramp does not fit in line
                    self.tabRampDist -= length
                    self.tabRampClean.append(l)
                    self.tabRampSeg(l, "tr0")
                    self.passLoc += length
                    break
            if self.passLoc >= self.totalLength:
                break
        
        self.tabState = tabState

    def tabRampSeg(self, l, comment):
        self.tabRampDepth += l.length * self.tanRampAngle
        # dprt("d %7.4f tabRampDist %7.4f tabRampDepth %7.4f" % \
        #       (depth, self.tabRampDist, self.tabRampDepth))
        comment += " t %d l %d %7.4f" % (self.tabNum, l.index, l.length)
        l.mill(self.mill, self.lastDepth - self.tabRampDepth, comment)

    def cleanTabRamp(self):
        dprt("cleanTabRamp")
        for l in reverseSeg(self.tabRampClean):
            l.prt()
            self.tabRampSeg(l, "trc0")
        if abs(self.currentDepth -
               (self.lastDepth - self.tabRampDepth)) > MIN_DIST:
            self.mill.plungeZ(self.currentDepth)
            
        for l in self.tabRampClean:
            l.prt()
            l.mill(self.mill, None, "trc1")
        self.tabRampClean = []

    def calcTabPos(self, path, tabPoints):
        self.tabs = 0
        tabPos = None
        if tabPoints is not None and len(tabPoints) != 0:
            dprt("calcTabPos %d" % (len(tabPoints)))
            for (i, p) in enumerate(tabPoints):
                dprt("%d p %7.4f, %7.4f" % (i, p[0], p[1]))
            for l in path:
                l.prt()
            totalLength = 0.0
            i = 0
            tabPos = []
            # prev = path[-1]
            dprt("match points to path")
            for l in path:
                for (j, p) in enumerate(tabPoints):
                    dp = l.pointDistance(p)
                    # if dp is not None:
                    #     dprt("%d %d dp %7.4f p %7.4f, %7.4f" % \
                    #           (i, j, dp, p[0], p[1]))
                    if dp is not None and abs(dp) < MIN_DIST:
                        d = l.startDist(p)
                        dprt("%d startDist %7.4f p %7.4f, %7.4f" % \
                              (i, d, p[0], p[1]))
                        dTab = totalLength + l.startDist(p)
                        tabPos.append(dTab)
                        # dprt("%d %d dp %7.4f dTab %7.4f p %7.4f, %7.4f" % \
                        #       (j, i, dp, dTab, p[0], p[1]))
                        i += 1
                        
                totalLength += l.length
            dprt("%d totalLength %7.4f" % (i, totalLength))

            tabPos = set(tabPos)
            tabPos = list(tabPos)
            self.tabs = self.cfg.tabs = len(tabPos)
            tabPos.sort()
            for (i, d) in enumerate(tabPos):
                dprt("%d d %7.4f" % (i, d))
        self.tabPos = tabPos

    def millSeg(self, l, zEnd=None, comment=None):
        l.prt()
        # dprt("millSeg p %7.4f, %7.4f %s" % (l.p0[0], l.p0[1], comment))
        l.mill(self.mill, zEnd, comment)
        self.passLoc += l.length

    def millPath(self, path, tabPoints=None, closed=True):
        cfg = self.cfg
        if not cfg.output:
            return
        dprt("millPath")
        self.init(closed)
        closed = self.closed

        dprt("combine arcs")
        path0 = combineArcs(path)

        mill = self.mill
        if closed:
            path0 = rotateMinDist(mill.last, path0)
        else:
            if xyDist(mill.last, path0[-1].p0) < xyDist(mill.last, path0[0].p0):
                path0 = reverseSeg(path0)

        out = self.mill.out
        for l in path0:
            out.write("(")
            l.prt(out, ")\n")

        self.calcTabPos(path0, tabPoints)

        self.totalLength = pathLength(path0)
        if True:
            draw = cfg.draw
            (x, y) = path0[0].p0
            d = 0.050
            last = draw.last
            draw.move((x - d, y - d))
            draw.line((x, y))
            draw.line((x + d, y - d))
            dir = pathDir(path0)
            draw.add(dxf.text("start %s" % (oStr(dir)), (x, y - d), 0.010, \
                              alignpoint=(x, y - d), halign=CENTER, \
                              layer = 'TEXT'))
            draw.move(last)

        rampLine = self.rampSetup()
        self.passSetup()

        if cfg.pauseCenter and len(path0) == 1:
            mill.move(path0[0].p0)
        else:
            mill.safeZ()
            mill.move(path0[0].p0)
            if cfg.pause:
                mill.moveZ(cfg.pauseHeight)
                mill.pause()
            mill.zTop()

        while True:
            if self.passCount == 0:
                break

            p = path0[0].p0
            if abs(mill.last[0] - p[0]) > MIN_DIST or \
               abs(mill.last[1] - p[1]) > MIN_DIST:
                mill.retract()
                mill.move(p)
                mill.moveZ(self.lastDepth + cfg.pauseHeight, "moveZ 1")
                mill.plungeZ(self.lastDepth)

            if self.passCount == self.rampPass:
                self.millRamp = True
            if self.passCount == self.tabPass:
                self.ramp = False
                self.tab = True
                self.tabSetup(path0)
                # break
            dprt("passCount %d millRamp %s tab %s" % \
                  (self.passCount, self.millRamp, self.tab))
            self.passCount -= 1

            self.calcPassDepth()
            self.calcPassRamp()
            if self.tab:
                out.write(" tabs %d w %5.3f d %5.3f r %5.3f" % \
                          (self.tabs, self.tabWidth, \
                           self.tabDepth, self.tabRamp))
            out.write(")\n")

            if not self.tab and not self.ramp:
                mill.plungeZ(self.currentDepth)

            self.tabNum = 0
            self.passLoc = 0.0
            for l in path0:
                # ramp and tab calculations
                if self.ramp:   # if ramp
                    rampLine(l)
                elif self.tab:  # if tabs
                    self.tabLine(l)
                else:       # no ramp or tabs
                    self.millSeg(l, None, '%d' % l.index)

                # done removing final ramp
                if self.done:
                    self.done = False
                    break

            if cfg.alternate:
                path0 = reverseSeg(path0)
            self.lastDepth = self.currentDepth
            self.passNum += 1
        out.write("\n")

class Draw():
    def __init__(self, d=None, svg=None):
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

    def open(self, file, drawDxf=True, drawSvg=True):
        if drawSvg:
            svgFile = file + ".svg"
            try:
                self.svg = Drawing(svgFile, profile='full', fill='black')
                self.path = Path(stroke_width=.5, stroke='black', fill='none')
            except IOError:
                self.svg = None
                self.path = None
                ePrint("svg file open error %s" % (svgFile))

        if drawDxf:
            dxfFile = file + "_ngc.dxf"
            try:
                self.d = dxf.drawing(dxfFile)
                self.layers = ['BORDER', 'PATH', 'HOLE', 'TEXT']
                for l in self.layers:
                    self.d.add_layer(l)
            except IOError:
                self.d = None
                ePrint("dxf file open error %s" % (dxfFile))

    def close(self):
        if self.d is not None:
            dprt("save drawing file");
            self.d.save()
            self.d = None

        if self.svg is not None:
            self.svg.add(self.path)
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
            elif orientation == O_CENTER or orientation == O_POINT:
                p0 = (-xSize/2, -ySize/2)
                p1 = (xSize/2, -ySize/2)
                p2 = (xSize/2, ySize/2)
                p3 = (-xSize/2, ySize/2)
            else:
                ePrint("invalid orientation")
            self.d.add(dxf.line(p0, p1, layer='BORDER'))
            self.d.add(dxf.line(p1, p2, layer='BORDER'))
            self.d.add(dxf.line(p2, p3, layer='BORDER'))
            self.d.add(dxf.line(p3, p0, layer='BORDER'))

    def materialOutline(self, lines):
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
            for l in lines:
                (start, end) = l
                self.d.add(dxf.line(cfg.dxfInput.fix(start), \
                                    cfg.dxfInput.fix(end), layer='BORDER'))

    def move(self, end):
        if self.enable:
            if self.svg is not None:
                self.path.push('M', self.scaleOffset(end))
                # dprt("svg move %7.4f %7.4f" % self.scaleOffset(end))
            # dprt("   move %7.4f %7.4f" % end)
            self.last = end

    def line(self, end):
        if self.enable:
            if self.svg is not None:
                self.path.push('L', self.scaleOffset(end))
                # dprt("svg line %7.4f %7.4f" % self.scaleOffset(end))
            if self.d is not None:
                self.d.add(dxf.line(self.last, end, layer='PATH'))
            # dprt("   line %7.4f %7.4f" % end)
            self.last = end

    def arc(self, end, center):
        if self.enable:
            r = xyDist(end, center)
            if self.svg is not None:
                self.path.push_arc(self.scaleOffset(end), 0, r, \
                                    large_arc=True, angle_dir='+', \
                                    absolute=True)
            if self.d is not None:
                p0 = self.last
                p1 = end
                if xyDist(p0, p1) < MIN_DIST:
                    self.d.add(dxf.circle(r, center, layer='PATH'))
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
                    self.d.add(dxf.arc(r, center, a0, a1, layer='PATH'))
                self.last = end

    def circle(self, end, r, l='HOLE'):
        if self.enable:
            if self.d is not None:
                if not l in self.layers:
                    self.d.add_layer(l)
                self.d.add(dxf.circle(r, end, layer=l))
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
                self.d.add(dxf.line(self.last, end, layer='PATH'))
                self.d.add(dxf.circle(drillSize / 2, end, layer='HOLE'))
        self.last = end

    def text(self, txt, p0, height):
        if self.enable:
            if self.d is not None:
                self.d.add(dxf.text(txt, p0, height, layer='TEXT'))

    def add(self, entity):
        if self.enable:
            if self.d is not None:
                self.d.add(entity)

    def drawCross(self, p):
        global lCount
        (x, y) = p
        dprt("cross %2d %7.4f, %7.4f" % (lCount, x, y))
        labelP(p, "%d" % (lCount))
        last = self.last
        self.move((x - 0.02, y))
        self.line((x + 0.02, y))
        self.move((x, y - 0.02))
        self.line((x, y + 0.02))
        lCount += 1
        self.move(last)

    def drawX(self, p, txt, swap=False):
        (x, y) = p
        xOfs = 0.020
        yOfs = 0.010
        if swap:
            (xOfs, yOfs) = (yOfs, xOfs)
        last = self.last
        self.move((x - xOfs, y - yOfs))
        self.line((x + xOfs, y + yOfs))
        self.move((x - xOfs, y + yOfs))
        self.line((x + xOfs, y - yOfs))
        self.move(p)
        self.text('%s' % (txt), (x + xOfs, y - yOfs), .010)
        self.move(last)

    def drawCircle(self, p, d=0.010, layer='DBG', txt=None):
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

class Dxf():
    def __init__(self, d=None, svg=None):
        self.dwg = None
        self.modelspace = None
        self.xOffset = 0.0
        self.yOffset = 0.0
        self.xMul = 1.0
        self.yMul = 1.0
        self.xMax = 0.0
        self.xMin = 0.0
        self.yMax = 0.0
        self.yMin = 0.0
        self.xSize = 0.0
        self.ySize = 0.0

    def open(self, inFile, layers, materialLayer):
        self.dwg = dwg = ReadFile(inFile)
        self.modelspace = modelspace = dwg.modelspace()
        xMax = MIN_VALUE
        xMin = MAX_VALUE
        yMax = MIN_VALUE
        yMin = MAX_VALUE
        self.material = []
        checkLayers = len(layers) != 0
        for e in modelspace:
            type = e.dxftype()
            layer = e.get_dxf_attrib("layer")
            if layer == materialLayer:
                pass
            elif checkLayers:
                if not layer in layers:
                    continue
            if type == 'LINE':
                (x0, y0) = e.get_dxf_attrib("start")[:2]
                (x1, y1) = e.get_dxf_attrib("end")[:2]
                xMax = max(xMax, x0, x1)
                xMin = min(xMin, x0, x1)
                yMax = max(yMax, y0, y1)
                yMin = min(yMin, y0, y1)
                if layer == materialLayer:
                    self.material.append(((x0, y0), (x1, y1)))
            elif type == 'CIRCLE':
                (xCen, yCen) = e.get_dxf_attrib("center")[:2]
                radius = e.get_dxf_attrib("radius")
                xMax = max(xMax, xCen + radius)
                xMin = min(xMin, xCen - radius)
                yMax = max(yMax, yCen + radius)
                yMin = min(yMin, yCen - radius)
            elif type == 'ARC':
                (xCen, yCen) = e.get_dxf_attrib("center")[:2]
                radius = e.get_dxf_attrib("radius")
                a0 = e.get_dxf_attrib("start_angle")
                a1 = e.get_dxf_attrib("end_angle")
                if a1 < a0:
                    a1 += 360.0
                # dprt("a0 %5.1f a1 %5.1f total %5.1f " \
                #      "x %7.4f y %7.4f r %7.4f" % \
                #       (fix(a0), fix(a1), a1 - a0, xCen, yCen, radius))
                prev = a = a0
                while True:
                    if a % 90 > .001:
                        a = ceil(a / 90) * 90
                    else:
                        a += 90
                    if a >= a1:
                        break
                    # dprt("(%5.1f, %5.1f)" % (fix(prev), fix(a)), end=" ")
                    x = radius * cos(radians(prev)) + xCen
                    y = radius * sin(radians(prev)) + yCen
                    # dprt("(%5.1f, %5.2f, %5.2f)" % (fix(prev), x, y), end=" ")
                    xMax = max(xMax, x)
                    xMin = min(xMin, x)
                    yMax = max(yMax, y)
                    yMin = min(yMin, y)
                    prev = a
                # dprt("(%5.1f, %5.1f)\n" % (fix(prev), fix(a1)))
                x = radius * cos(radians(prev)) + xCen
                y = radius * sin(radians(prev)) + yCen
                # dprt("(%5.1f, %5.2f, %5.2f)" % (fix(prev), x, y), end=" ")
                xMax = max(xMax, x)
                xMin = min(xMin, x)
                yMax = max(yMax, y)
                yMin = min(yMin, y)

                x = radius * cos(radians(a1)) + xCen
                y = radius * sin(radians(a1)) + yCen
                # dprt("(%5.1f, %5.2f, %5.2f)\n" % (fix(prev), x, y))
                xMax = max(xMax, x)
                xMin = min(xMin, x)
                yMax = max(yMax, y)
                yMin = min(yMin, y)
            elif type == 'LWPOLYLINE':
                for (x0, y0) in e.get_rstrip_points():
                    xMax = max(x0, xMax)
                    xMin = min(x0, xMin)
                    yMax = max(y0, yMax)
                    yMin = min(y0, yMin)

        self.xMin = xMin
        self.xMax = xMax
        self.yMin = yMin
        self.yMax = yMax
        dprt("xMin %f yMin %f" % (xMin, yMin))
        dprt("xMax %f yMax %f" % (xMax, yMax))
        self.xSize = xMax - xMin
        self.ySize = yMax - yMin
        dprt("xSize %5.3f ySize %6.3f" % (self.xSize, self.ySize))

    def setOrientation(self, orientation=0, layer=None):
        # dprt("\nmin (%7.4f, y %7.4f) max (%7.4f, y %7.4f)\n" % \
        #       (self.xMin, self.yMin, self.xMax, self.yMax))
              
        # for (start, end) in self.material:
        #     dprt("(%7.4f, y %7.4f) (%7.4f, y %7.4f))" % \
        #         (start[0], start[1], end[0], end[1]))
            
        self.xMul = 1
        self.yMul = 1
        if orientation == 0:            # manual mill vice
            self.xMul = 1
            self.yMul = -1
            self.xOffset = -self.xMin
            self.yOffset = self.yMax
        elif orientation == 1:          # upper left
            self.xOffset = -self.xMin
            self.yOffset = -self.yMax
        elif orientation == 2:          # lower left
            self.xOffset = -self.xMin
            self.yOffset = -self.yMin
        elif orientation == 3:          # center
            self.xOffset = -(self.xMin + (self.xMax - self.xMin) / 2)
            self.yOffset = -(self.yMin + (self.yMax - self.yMin) / 2)
        elif orientation == 4:
            if layer is not None:
                for e in self.modelspace:
                    if layer != e.get_dxf_attrib("layer"):
                        continue
                    if e.dxftype() == 'CIRCLE' or e.dxftype() == 'ARC':
                        (x, y) = e.get_dxf_attrib("center")[:2]
                        self.xOffset = -x
                        self.yOffset = -y

        dprt("%d xOffset %7.4f yOffset %7.4f\n" % \
               (orientation, self.xOffset, self.yOffset))

        # for i, (start, end) in enumerate(self.material):
        #     self.material[i] = (self.fix(start), self.fix(end))

        # for (start, end) in self.material:
        #     dprt("(%7.4f, y %7.4f) (%7.4f, y %7.4f))" % \
        #         (start[0], start[1], end[0], end[1]))
            
    def fix(self, point):
        (x, y) = point
        # x = int(x * 10000) / 10000.0
        # y = int(y * 10000) / 10000.0
        return((self.xMul * x + self.xOffset, \
                self.yMul * y + self.yOffset))

    def scale(self, point, scale=1):
        (x, y) = point
        return((int(x * scale), int(y * scale)))

    def getPoints(self, layer):
        points = []
        for e in self.modelspace:
            # dprt("layer %s" % (e.get_dxf_attrib("layer")))
            if layer != e.get_dxf_attrib("layer"):
                continue
            type = e.dxftype()
            if type == 'CIRCLE':
                (xCen, yCen) = self.fix(e.get_dxf_attrib("center")[:2])
                points.append((xCen, yCen))
        return(points)

    def getHoles(self, layer):
        holes = []
        for e in self.modelspace:
            # dprt("layer %s" % (e.get_dxf_attrib("layer")))
            if layer != e.get_dxf_attrib("layer"):
                continue
            type = e.dxftype()
            if type == 'CIRCLE':
                p = self.fix(e.get_dxf_attrib("center")[:2])
                radius = e.get_dxf_attrib("radius")
                drillSize = radius * 2.0
                for h in holes:
                    if abs(drillSize - h.size) < MIN_DIST:
                        h.addLoc(p)
                        break
                else:
                    d = Drill(drillSize)
                    holes.append(d)
                    d.addLoc(p)
        return(holes)

    def getPath(self, layer, circle=False):
        # dprt("getPath %s" % (layer))
        # find everything that matches layer
        linNum = 0
        entities = []
        for e in self.modelspace:
            # dprt("layer %s" % (e.get_dxf_attrib("layer")))
            if layer != e.get_dxf_attrib("layer"):
                continue
            type = e.dxftype()
            if type == 'LINE':
                l0 = Line(self.fix(e.get_dxf_attrib("start")[:2]), \
                          self.fix(e.get_dxf_attrib("end")[:2]), \
                          linNum, e)
            elif type == 'ARC':
                center = self.fix(e.get_dxf_attrib("center")[:2])
                radius = e.get_dxf_attrib("radius")
                startAngle = e.get_dxf_attrib("start_angle")
                endAngle = e.get_dxf_attrib("end_angle")
                l0 = Arc(center, radius, startAngle, endAngle, \
                         linNum, e)
            elif type == 'CIRCLE':
                if circle:
                    p = self.fix(e.get_dxf_attrib("center")[:2])
                    radius = e.get_dxf_attrib("radius")
                    l0 = Arc(p, radius, 0.0, 360.0, linNum, e)
                else:
                    continue
            elif type == 'LWPOLYLINE':
                prev = None
                if e.closed:
                    prev = e[-1][:2]
                for p in e.get_rstrip_points():
                    if prev is not None:
                        l0 = Line(self.fix(prev), self.fix(p), linNum, e)
                        entities.append(l0)
                        linNum += 1
                    prev = p
                continue
            else:
                continue
            # l0.prt()
            entities.append(l0)
            linNum += 1
        # dprt()

        # create unconnected segments

        segments = []
        segCount = 0
        for l0 in entities:
            found = False
            segNum = []
            for (i, seg) in enumerate(segments):
                j = 0
                lineCount = len(seg)
                while j < lineCount:
                    l1 = seg[j]
                    # l1.prt()
                    for p0 in (l0.p0, l0.p1):
                        for p1 in (l1.p0, l1.p1):
                            if xyDist(p0, p1) <= MIN_DIST:
                                # dprt("match seg %d ind %d l0 %d l1 %d" % \
                                #       (i, j, l0.index, l1.index))
                                # dflush()
                                if not i in segNum:
                                    segNum.append(i)
                                if not found:
                                    found = True
                                    seg.append(l0)
                                break
                    j += 1
            if not found:
                seg = []
                seg.append(l0)
                segments.append(seg)
                # dprt("add segment %d" % (segCount))
                segCount += 1
            else:
                if len(segNum) > 1:
                    # dprt(segNum)
                    # dflush()
                    seg = []
                    for i in reversed(segNum):
                        for line in segments.pop(i):
                            seg.append(line)
                    segments.append(seg)
            # dprt()

        # connect segments together in order

        j = 0
        for seg in segments:
            points = []
            for l0 in seg:
                self.addPoint(points, l0.p0)
                self.addPoint(points, l0.p1)
            # for (p, count) in points:
            #     dprt("%7.4f %7.4f %d" % (p[0], p[1], count))
            # dprt()
            p = points[0]
            for (p, count) in points:
                if count == 1:
                    break

            newSeg = []
            path = []
            while True:
                path.append(p)
                if len(seg) == 0:
                    break
                i = 0
                for l0 in seg:
                    (start, end) = (l0.p0, l0.p1)
                    if xyDist(p, start) <= MIN_DIST:
                        p = end
                        newSeg.append(l0)
                        break
                    if xyDist(p, end) <= MIN_DIST:
                        p = start
                        # dprt("swap %d %s" % \
                        #        (l0.index, ('line', 'arc')[l0.type]))
                        l0.swap()
                        newSeg.append(l0)
                        break
                    i += 1
                if i < len(seg):
                    seg.pop(i)
                else:
                    # dprt("segment out of range %d" % (i))
                    pass
            segments[j] = newSeg
            j += 1
            # dprt()

        # for (i, seg) in enumerate(segments):
        #     dprt("seg %d" % (i))
        #     for l0 in seg:
        #         l0.prt()
        #     dprt()
        return(segments)

    def addPoint(self, points, p):
        found = False
        for (i, (p0, count)) in enumerate(points):
            if xyDist(p, p0) < MIN_DIST:
                found = True
                count += 1
                points[i] = (p0, count)
                break
        if not found:
            points.append((p, 1))

    # def printSeg(self, l):
    #     dprt("%2d p0 %7.4f, %7.4f - p1 %7.4f, %7.4f %s" % \
    #            (l.index, l.p0[0], l.p0[1], l.p1[0], l.p1[1], l.str))

    # def segments(self, layer):
    #     segments = []
    #     linNum = 0
    #     for e in self.modelspace:
    #         type = e.dxftype()
    #         if type == 'LINE' and e.get_dxf_attrib("layer") == layer:
    #             l0 = (self.fix(e.get_dxf_attrib("start")[:2]), \
    #                   self.fix(e.get_dxf_attrib("end")[:2]), \
    #                   e, linNum)
    #             dprt("%d   l0 p0 %7.4f, %7.4f - p1 %7.4f, %7.4f" %\
    #                   (linNum, l0[0][0], l0[0][1], l0[1][0], l0[1][1]))
    #             dflush()
    #             linNum += 1
    #             found = False
    #             segNum = []
    #             for (i, seg) in enumerate(segments):
    #                 j = 0
    #                 lineCount = len(seg)
    #                 while j < lineCount:
    #                     l1 = seg[j]
    #                     dprt("%d %d l1 p0 %7.4f, %7.4f - p1 %7.4f, %7.4f" % \
    #                           (i, j, l1[0][0], l1[0][1], l1[1][0], l1[1][1]))
    #                     dflush()
    #                     for p0 in l0[:2]:
    #                         for p1 in l1[:2]:
    #                             dprt("       p0 %7.4f, %7.4f - " \
    #                                   "p1 %7.4f, %7.4f" % \
    #                                   (p0[0], p0[1], p1[0], p1[1]))
    #                             dflush()
    #                             if xyDist(p0, p1) <= MIN_DIST:
    #                                 dprt("match %d %d" % (l0[3], l1[3]))
    #                                 dflush()
    #                                 segNum.append(i)
    #                                 if not found:
    #                                     found = True
    #                                     seg.append(l0)
    #                                 break
    #                     j += 1
    #             if not found:
    #                 seg = []
    #                 seg.append(l0)
    #                 segments.append(seg)
    #             else:
    #                 if len(segNum) > 1:
    #                     dprt(segNum)
    #                     dflush()
    #                     seg = []
    #                     for i in reversed(segNum):
    #                         for line in segments.pop(i):
    #                             seg.append(line)
    #                     segments.append(seg)
    #             dprt()

    #     j = 0
    #     for seg in segments:
    #         points = []
    #         for (start, end, e, linNum) in seg:
    #             self.addPoint(points, start)
    #             self.addPoint(points, end)
    #         for (p, count) in points:
    #             dprt("%7.4f %7.4f %d" % (p[0], p[1], count))
    #         dprt()

    #         p = points[0]
    #         for (p, count) in points:
    #             if count == 1:
    #                 break

    #         newSeg = []
    #         path = []
    #         while True:
    #             path.append(p)
    #             if len(seg) == 0:
    #                 break
    #             i = 0
    #             for (start, end, e, linNum) in seg:
    #                 if p[0] == start[0] and p[1] == start[1]:
    #                     p = end
    #                     newSeg.append((start, end, e, linNum))
    #                     break
    #                 if p[0] == end[0] and p[1] == end[1]:
    #                     p = start
    #                     newSeg.append((end, start, e, linNum))
    #                     break
    #                 i += 1
    #             seg.pop(i)
    #         segments[j] = newSeg
    #         j += 1

    #     for seg in segments:
    #         for (start, end, e, lineNum) in seg:
    #             dprt("%d start %7.4f, %7.4f - end %7.4f, %7.4f" % \
    #                   (lineNum, start[0], start[1], end[0], end[1]))
    #         dprt()

    # def getLines(self, layer):
    #     line = []
    #     for e in self.modelspace:
    #         type = e.dxftype()
    #         if type == 'LINE' and e.get_dxf_attrib("layer") == layer:
    #             start = e.get_dxf_attrib("start")[:2]
    #             end = e.get_dxf_attrib("end")[:2]
    #             line.append((self.fix(start), self.fix(end)))

    #     i = 0
    #     prev = (0, 0)
    #     while i < len(line):
    #         j = i
    #         minDist = MAX_VALUE
    #         # print "i %d %7.4f %7.4f" % (i, prev[0], prev[1])
    #         while j < len(line):
    #             (start, end) = line[j]
    #             d0 = xyDist(prev, start)
    #             d1 = xyDist(prev, end)
    #             # dprt("j %d d0 %7.4f d1 %7.4f start %7.4f, %7.4f - "\
    #             #        "end %7.4f, %7.4f" % \
    #             #        (j, d0, d1, start[0], start[1], end[0], end[1]))
    #             if d0 < minDist or d1 < minDist:
    #                 minJ = j
    #                 if d1 < d0:
    #                     minDist = d1
    #                     nextLine = (end, start)
    #                 else:
    #                     minDist = d0
    #                     nextLine = (start, end)
    #             j += 1
    #         # print "i %d minJ %d minDist %7.4f" % (i, minJ, minDist)
    #         # print
    #         line[minJ] = line[i]
    #         line[i] = nextLine
    #         prev  = nextLine[1]
    #         i += 1
    #     # print

    #     # for (start, end) in line:
    #     #     dprt("start %7.4f, %7.4f - end %7.4f, %7.4f" % \
    #     #            (start[0], start[1], end[0], end[1]))
    #     return line

class MainFrame(wx.Frame): 
    def __init__(self, parent, title): 
        super(MainFrame, self).__init__(parent, title = title)
        self.Maximize(True)
        self.InitUI() 
        # colors = wx.lib.colourdb.getColourList()
        # for line in colors:
        #     print line
        # dflush()
         
    def InitUI(self): 
        global cfg, inFile
        self.zoom = False
        self.left = None
        self.Bind(wx.EVT_PAINT, self.OnPaint) 
        self.Centre() 
        cfg.open(inFile)
        self.Bind(wx.EVT_LEFT_UP, self.OnMouseEvent)
        self.Show(True)

    def OnMouseEvent(self, e):
        x = e.GetX()
        # if not self.zoom:
        #     self.zoom = True
        #     self.offset = x > self.tc.xBase
        # else:
        #     self.zoom = False
        #     self.offset = False
        # self.tc.setZoomOffset(self.zoom, self.offset)
        self.Refresh()

    def OnPaint(self, e): 
        dc = wx.PaintDC(self) 
        dc.SetMapMode(wx.MM_TEXT)
        brush = wx.Brush("white")
        dc.SetBackground(brush)  
        dc.Clear() 
        # self.tc.calcScale()
        # self.tc.draw(dc)
        
        # color = wx.Colour(255,0,0)
        # dc.SetTextForeground(color) 
        # dc.DrawText("Hello wxPython",10,10)
        # dc.DrawLine(10,10, 100,10)

if len(sys.argv) <= 1:
    exit()

cfg = Config()
cfg.parseCmdLine()

if cfg.gui:
    ex = wx.App() 
    MainFrame(None,'Drawing demo') 
    ex.MainLoop()
else:
    cfg.open()
