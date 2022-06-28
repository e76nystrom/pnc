#!/cygdrive/c/Python39/Python.exe
#!/cygdrive/c/DevSoftware/Python/Python36-32/Python.exe
#!/usr/local/bin/python2.7
################################################################################

import glob
# from imp import load_source
# import importlib.machinery
import importlib
import inspect
import os
import platform
import random
import re
import subprocess
import sys
import wx
# import wx.lib.colourdb
import traceback
from collections import namedtuple
from math import ceil, cos, floor, radians, sin, tan
from os import getcwd

# from sys import stdout
from dxfwrite import CENTER
from dxfwrite import DXFEngine as dxf
from ezdxf import readfile as ReadFile

import geometry
from dbgprt import dclose, dflush, dprt, dprtSet, ePrint
from draw import Draw
from geometry import (ARC, CCW, CW, MAX_VALUE, MIN_DIST, MIN_VALUE, Arc, Line,
                      newPoint, combineArcs, createPath, inside, offset,
                      oStr, pathDir, pathLength, reverseSeg, rotateMinDist,
                      xyDist)
from hershey import Font
from mill import Mill
from millLines import MillLine
from offset import Offset
from orientation import (O_CENTER, O_LOWER_LEFT, O_LOWER_RIGHT, O_MAX, O_POINT,
                         O_UPPER_LEFT, O_UPPER_RIGHT)

DRILL = 0
BORE = 1
TAP = 2
TAPMATIC = 3

IF_DISABLE =        (1 << 0)
COMPONENT_DISABLE = (1 << 1)
OPERATION_DISABLE = (1 << 2)

ST_XMIN = 0
ST_XMAX = 1
ST_YMIN = 2
ST_YMAX = 3

DIR_XLT = 0
DIR_XGT = 1
DIR_YLT = 2
DIR_YGT = 3

REF_OVERALL = 0
REF_MATERIAL = 1
REF_FIXTURE = 2

HOLE_NEAREST = 0
HOLE_COLUMNS = 1
HOLE_ROWS = 2

ToolDef = namedtuple('ToolDef', ['num', 'toolType', 'toolSize', 'comment'])

# print("%s" % (os.environ['TZ'],))
# os.environ['TZ'] = 'America/Naew_York'
# print("%s" % (os.environ['TZ'],))

# dxf arcs are always counter clockwise.

dprtSet(True)
dprt("version %s" % (sys.version))

class Config():
    def __init__(self):
        geometry.cfg = self     # set config for geometry module
        self.reSeq = False      # resequence input file
        self.gui = False        # start in gui
        self.error = False      # initialize error flag
        self.mill = None        # Mill class
        self.printGCode = False # print gcode
        self.draw = None        # Draw class
        self.drawDxf = False    # create dxf drawing
        self.drawSvg = False    # create svg drawing
        self.oneDxf = False     # combine output into one dxf
        self.slot = None        # Slot class
        self.move = None        # Move class
        self.mp = None          # millPath class
        self.line = None        # millLine class
        self.layers = []        # layers to use in dxf file
        self.materialLayer = 'Material' # material layer
        self.fixtureLayer = 'Fixture'   # fixture layer
        self.reference = REF_OVERALL    # origin reference
        self.dxfInput = None    # dxf input class
        self.init = False       # ncinit has been called
        self.output = True      # produce output in millPath
        self.dxfFile = None     # dxf file from args
        self.fileName = None    # base output file name
        self.outFileName = None # output file name
        self.d = None           # output debug dxf file
        self.svg = None         # output debug svg file
        self.path = None        # svg path
        self.lineNum = 0        # input line number
        self.slotNum = 0        # slot number
        self.test = False       # test flag
        self.orientation = None # default orientation
        self.orientationLayer = None # layer for orientation point
        self.layer = None       # layer from command line

        self.refValues = \
            (\
             (REF_OVERALL, "overall"),
             (REF_MATERIAL, "material"),
             (REF_FIXTURE, "fixture"),
            )

        self.orientationValues = (\
            (O_UPPER_LEFT, "upperleft"), \
            (O_LOWER_LEFT, "lowerleft"), \
            (O_UPPER_RIGHT, "upperright"), \
            (O_LOWER_RIGHT, "lowerright"), \
            (O_CENTER, "center"), \
            (O_POINT, "point"), \
        )

        self.holeOrderValues = (\
            (HOLE_NEAREST, "nearest"), \
            (HOLE_COLUMNS, "columns"), \
            (HOLE_ROWS, "rows"), \
        )

        self.dbg = False        # debugging output
        self.dbgFile = ""       # debug file

        self.climb = False      # climb milling
        self.dir = None         # milling direction
        self.endMillSize = 0.0  # end mill size
        self.finishAllowance = 0.0 # finish allowance
        self.alternate = False  # alternate directions on open path
        self.addArcs = False    # add arcs between line segments
        self.closeOpen = False  # close open path

        self.xSize = 0.0        # material x size
        self.ySize = 0.0        # material y size
        self.zSize = 0.0

        self.xPark = 0.0        # x park location
        self.yPark = 0.0        # y park location
        self.zPark = 1.5        # z park location

        self.xInitial = 0.0     # x initial location
        self.yInitial = 0.0     # y initial location
        self.zInitial = 1.5     # z initial location

        self.xOffset = 0.0      # drill x approach offset
        self.yOffset = 0.0      # drill y approach offset
        self.x = 0.0            # drill x location
        self.y = 0.0            # dirll y location
        self.drillSize = None   # current drill size
        self.drillAngle = 0.0   # drill point angle
        self.drillExtra = 0.0   # extra drill Depth
        self.peckDepth = 0.0    # peck depth
        self.stepProfile = None # step profile
        self.millHoleSize = None # size to mill hole
        self.holeMin = 0.0      # dxf select hole >= size
        self.holeMax = MAX_VALUE # dxf select hole < size
        self.holeOrder = HOLE_NEAREST # order of holes

        self.tapRpm = 0         # measured rpm
        self.tapTpi = 20        # threads per inch

        self.pause = False       # enable pause
        self.pauseCenter = False # pause at center of hole
        self.pauseHeight = 0.025 # height to pause at
        self.homePause = True    # start by pausing at home position

        self.tool = None        # tool number
        self.toolComment = ""   # tool comment
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
        self.evenDepth = False  # same depth for each pass

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
        self.probeFeed = 0.0    # probe feed
        self.probeTool = None   # probe tool number
        self.level = False      # probe input file
        self.probeData = None   # output from probing

        self.inFile = None      # input file
        self.outFile = None     # output file from command line

        self.ifDisable = False  # if flag
        self.componentDisable = False
        self.operationDisable = False
        self.cmdDisable = 0
        # self.ifStack = []       # stack for nested if

        self.runPath = os.path.dirname(sys.argv[0])

        self.tabInit()

        self.compNumber = None
        self.compCommment = ""
        self.opNumber = None
        self.opComment = ""

        self.oVal = 100
        self.oValStack = []

        self.cmdAction = {}
        self.gCodeAction = {}
        self.cmds = \
        ( \
            ('xpark', self.parkX), \
            ('ypark', self.parkY), \
            ('zpark', self.ParkZ), \
            ('park', self.park), \

            ('xinitial', self.initialX), \
            ('yinitial', self.initialY), \
            ('zinitial', self.initialZ), \
            ('initial', self.initial), \

            ('size', self.setSize), \
            ('drillsize', self.setDrillSize), \
            ('drillangle', self.setDrillAngle), \
            ('drillextra', self.setDrillExtra), \
            ('peckdepth', self.setPeckDepth), \
            ('millHolesize', self.setMillHoleSize), \
            ('holemin', self.setHoleMin), \
            ('holemax', self.setHoleMax), \
            ('holerange', self.setHoleRange), \
            ('holeorder', self.setHoleOrder), \

            ('coordinate', self.setCoord), \
            ('variables', self.setVariables), \

            ('safez', self.setSafeZ), \
            ('retract', self.setRetract), \
            ('top', self.setTop), \
            ('depth', self.setDepth), \
            ('depthpass', self.setDepthPass), \
            ('evendepth', self.setEvenDepth), \

            ('feed', self.setFeed), \
            ('zfeed', self.setZFeed), \

            ('speed', self.setSpeed), \
            ('delay', self.setDelay), \
            ('tool', self.setTool), \

            ('x', self.setLocX), \
            ('y', self.setLocY), \
            ('loc', self.setLoc), \
            ('xoffset', self.setXOffset), \
            ('yoffset', self.setYOffset), \
            ('drill', self.drill, True), \
            ('bore', self.bore, True), \

            ('pause', self.setPause, True), \
            ('pausecenter', self.setPauseCenter), \
            ('pauseheight', self.setPauseHeight), \
            ('homepause', self.setHomePause), \
            ('pausehere', self.pauseHere), \

            ('rampangle', self.setRampAngle), \
            ('shortramp', self.setShortRamp), \

            ('widthpasses', self.setWidthPasses), \
            ('widthperpass', self.setWidthPerPass), \
            ('width', self.setWidth), \
            ('vbit', self.setVBit), \

            ('xslot', self.xSlot, True), \
            ('yslot', self.ySlot, True), \

            ('test', self.setTest), \

            ('endmill', self.setEndMillSize), \
            ('endmillsize', self.setEndMillSize), \
            ('finish', self.setFinish), \
            ('finishallowance', self.setFinish), \

            ('tabs', self.setTabs), \
            ('tabwidth', self.setTabWidth), \
            ('tabdepth', self.setTabDepth), \

            ('direction', self.setDirection), \
            ('output', self.setOutput), \
            ('alternate', self.setAlternate), \
            ('addarcs', self.setAddArcs), \
            ('closeopen', self.setCloseOpen), \

            ('dxf', self.readDxf), \
            ('setlayers', self.setLayers), \
            ('clrlayers', self.clrLayers), \
            ('materiallayer', self.setMaterialLayer), \
            ('fixturelayer', self.setFixtureLayer), \
            ('reference', self.setRef), \
            ('orientation', self.setOrientation), \

            ('dxflines', self.dxfLine, True), \
            ('dxfgetpath', self.dxfPath), \
            ('dxftab', self.dxfTab, True), \
            ('dxfpoint', self.dxfPoint), \
            ('dxfoutside', self.dxfOutside, True), \
            ('dxfinside', self.dxfInside, True), \
            ('dxfopen', self.dxfOpen, True), \
            ('dxfdrill', self.dxfDrill, True), \
            ('dxfdrillsort', self.dxfDrillSort, True), \
            ('dxfbore', self.dxfBore, True), \
            ('dxfmillhole', self.dxfMillHole, True), \
            ('dxfsteppedhole', self.dxfSteppedHole, True), \
            ('stepprofile', self.getStepProfile), \
            ('dxftap', self.dxfTap, True), \
            ('dxftapmatic', self.dxfTapMatic, True), \
            ('tapmatic', self.tapmatic), \

            ('close', self.closeFiles), \
            ('outputfile', self.outputFile), \

            ('setfont', self.setFont), \
            ('engrave', self.engrave), \
            ('probe', self.setProbe), \
            ('probedepth', self.setProbeDepth), \
            ('probefeed', self.setProbeFeed), \
            ('probetool', self.setProbeTool), \
            ('level', self.setLevel), \

            ('drawdxf', self.setDrawDxf), \
            ('drawsvg', self.setDrawSvg), \
            ('onedxf', self.setOneDxf), \
            ('closedxf', self.closeDxf), \

            ('dbg', self.setDbg), \
            ('dbgfile', self.setDbgFile), \
            ('printgcode', self.setPrintGCode), \

            ('setx', self.setX), \
            ('sety', self.setY), \

            ('load', self.load), \

            ('var', self.var), \
            ('rm',  self.remove), \
            ('run', self.runCmd), \
            ('runscript', self.runScript), \

            ('repeat', self.repeat, True), \
            ('repeatcheck', self.repeatCheck, True), \
            ('endr', self.endRepeat, True), \

            ('if', self.cmdIf), \
            ('endif', self.cmdEndIf), \

            ('component', self.component), \
            ('operation', self.operation), \

            ('***component', self.component), \
            ('+++operation', self.operation), \
        )
        self.addCommands(self.cmds)

        self.offset = Offset(self)
        self.addCommands(self.offset.cmds)

    def addCommands(self, cmds):
        for val in cmds:
            # print("cmd %s" % val[0])
            cmd = val[0].lower()
            action = val[1]
            gCode = False
            if len(val) >= 3:
                gCode = val[2]
            # dprt("cmd %16s gCode %s" % (cmd, gCode))
            if gCode:
                self.gCodeAction[cmd] = action
            else:
                self.cmdAction[cmd] = action

    def removeCommands(self, cmds):
        for val in cmds:
            cmd = val[0].lower()
            gCode = False
            if len(val) >= 3:
                gCode = val[2]
            if gCode:
               del  self.gCodeAction[cmd]
            else:
               del self.cmdAction[cmd]

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
                    elif tmp == 'layer':
                        n += 1
                        if n < len(sys.argv):
                            self.level = True
                            self.layer = sys.argv[n]
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
                    elif tmp == "c":
                        self.linuxCNC = True
                    elif tmp == "g":
                        cfg.gui = True
                    elif tmp == 'r':
                        self.reSeq = True
                    elif tmp == 's':
                        self.drawSvg = True
                    elif tmp == 'x':
                        self.drawDxf = True
                    elif tmp == 'o':
                        n += 1
                        if n < len(sys.argv):
                            self.out = True
                            self.outFile = sys.argv[n]
                    elif tmp == 'h':
                        self.help()
            elif val.startswith('?'):
                self.help()
            else:
                inFile = val
                if ".dxf" in inFile:
                    self.dxfFile = val
                else:
                    if not re.search(r'\.[a-zA-Z0-9]*$', inFile):
                        inFile += ".pnc"
                    dprt(inFile)
                    dflush()
                    if self.inFile is None:
                        self.inFile = [inFile, ]
                    else:
                        self.inFile.append(inFile)
            n += 1

    def help(self):
        print("Usage: pnc [options] pncFile [dxfInput]")
        print(" ?            help\n" \
              " -d           debug\n" \
              " -h           help\n" \
              " -c           linuxcnc format\n" \
              " -r	     resequence input file\n" \
              " -s           output svf file\n" \
              " -x           output dxf file\n" \
              " --dbg file   debug output file\n" \
              " --dxf file   dxf input file\n" \
              " --layer layer layer for dxf commands\n" \
              " --level file level input file\n" \
              " --probe      generate probe data" \
        )
        sys.exit()

    def gpp(self, pncFile):
        if platform.system() == 'Windows':
            runDir = os.path.dirname(os.path.abspath(__file__))
            gpp = os.path.join(runDir, "gpp.exe")
        else:
            gpp = "gpp"
        gppFile = pncFile.replace(".pnc", ".gpp_pnc")
        command = (gpp, pncFile, "-o", gppFile)
        try:
            result = subprocess.check_output(command)
            if len(result) != 0:
                dprt(result)
            return(gppFile)
        except subprocess.CalledProcessError as e:
            print("return code %d\n%s\n%s" % \
                  (e.returncode, e.cmd, e.output))
            return(pncFile)

    def reSequence(self, file):
        f = open(file, 'r')
        outFile = file.replace(".pnc", ".tmp")
        backupFile = file.replace(".pnc", ".bak")
        fOut = open(outFile, 'wb')
        component = 0
        for line in f:
            l = line.strip()
            command = l.split(" ")[0].lower()
            if command == "***component":
                match = re.match(r"^\**\w+\s+(\*|\d+)\s+-?\s*(.*)$", l)
                result = match.groups()
                compComment = ""
                if match is not None:
                    if len(result) >= 2:
                        compComment = " - " + match.group(2)
                component += 1
                line = "***component %d%s\n" % (component, compComment)
                section = 1
            elif command == "+++operation":
                match = re.match(r"\+*\w+\s+(\*|[\d\.]+)\s+-?\s*(.*)$", l)
                result = match.groups()
                opComment = ""
                if match is not None:
                    if len(result) >= 2:
                        opComment = " - " + match.group(2)
                line = "+++operation %d.%d%s\n" % \
                           (component, section, opComment)
                section += 1
            fOut.write(str.encode(line))
        f.close()
        fOut.close()
        try:
            os.remove(backupFile)
        except FileNotFoundError:
            pass
        os.rename(file, backupFile)
        os.rename(outFile, file)

    def open(self):
        self.setupVars()
        for inFile in self.inFile:
            self.curInFile = inFile
            if self.reSeq:
                self.reSequence(inFile)
            gppFile = self.gpp(inFile)
            inp = open(gppFile, 'r')
            self.dirPath = os.path.dirname(inFile)
            self.fileName = os.path.basename(inFile).replace(".pnc", "")
            if self.outFile is None:
                if len(self.dirPath) != 0:
                    self.baseName = os.path.join(self.dirPath, self.fileName)
                else:
                    self.baseName = self.fileName
            else:
                self.baseName = os.path.join(self.dirPath, self.outFile)

            dprtSet(self.dbg, os.path.join(self.dirPath, self.dbgFile) \
                    if len(self.dbgFile) != 0 else "")

            multi = False
            last = ""
            for l in inp:
                self.lineNum += 1
                dprt("%2d %s" % (self.lineNum, l), end="")
                dflush()
                l = l.strip()
                line = re.sub(r"\s*#.*$", "", l) # remove comments from line
                line = re.sub(r"\s+", " ", line) # white space with one space
                if multi:                       # if continuation of prev line
                    multi = False
                    line = last + line
                    last = None
                if len(line) == 0: # if empty line
                    continue
                if line.startswith('#'):
                    continue
                if line.endswith('\\'): # if line continued
                    multi = True
                    last = line[:-1]
                    continue
                arg = line.split(' ')
                if len(arg) >= 1:
                    cmd = arg[0].lower()
                    arg[0] = line
                    try:
                        if cmd in self.cmdAction:
                            action = self.cmdAction[cmd]
                            action(arg)
                            continue
                        if self.cmdDisable == 0:
                            if cmd in self.gCodeAction:
                                action = self.gCodeAction[cmd]
                                action(arg)
                                dflush()
                                if self.error:
                                    break
                            else:
                                ePrint("%2d %s" % (self.lineNum, l))
                                ePrint("invalid cmd %s" % cmd)
                                sys.exit()
                    # except ValueError:
                    #     ePrint("Invalid argument line %d %s" % \
                    #           (self.lineNum, line))
                    # except IndexError:
                    #     ePrint("Missing argument line %d %s" % \
                    #           (self.lineNum, line))
                    except:
                        dflush()
                        dclose()
                        traceback.print_exc()
                        inp.close()
                        break
            inp.close()         # close input file
            if gppFile.endswith(".gpp_pnc"):
                os.remove(gppFile)
        try:
            self.draw.close()   # close drawing files
        except:
            pass
        dclose()                # close debug file
        self.end()              # close nc files

    def end(self):
        self.init = False
        if self.mill is not None:
            self.mill.close()
            self.mill = None
            self.mp = None
            self.oVal = 100
        self.lastX = 0.0
        self.lastY = 0.0
        if self.probe:
            if self.prb is not None:
                self.prb.write("(PROBECLOSE)\n")
                self.prb.close()
                self.prb = None
            self.probe = False

    def ncInit(self):
        mill = self.mill
        if mill is not None:
            mill.setCoordinate(self.coordinate)
        if self.init:
            return
        self.init = True

        draw = self.draw
        if draw is None:
            self.draw = draw = Draw(self)
            geometry.draw = draw

        draw.open(self.outFileName, self.drawDxf, self.drawSvg)

        dxfInput = self.dxfInput
        if dxfInput is not None:
            if len(dxfInput.material) != 0:
                draw.materialOutline(dxfInput.material)
            else:
                draw.material(dxfInput.xSize, dxfInput.ySize)

            if len(dxfInput.fixture) != 0:
                draw.materialOutline(dxfInput.fixture)

        draw.move((self.xInitial, self.yInitial))

        outFile = self.outFileName + ".ngc"
        if mill is None:
            self.mill = mill = Mill(self, outFile)
        else:
            mill.init(outFile)
        mill.setSpeed(self.speed)
        self.openOutput = False

        if self.probe:
            self.probeInit()

    def probeInit(self):
        probeFile = self.outFileName + "-prb.ngc"
        self.prb = prb = Mill(self, probeFile, False)
        prb.write("(PROBEOPEN %s.prb)\n" % (probeFile))
        tool = self.probeTool
        if tool is not None:
            #out.blankLine()
            prb.write("G30 (Go to preset G30 location)\n")
            prb.write("T %d M6 G43 H %d\n" % (tool, tool))
            #out.blankLine()
        return(prb)

    def probeOpen(self):
        probeData = self.probeData
        if not os.path.isfile(probeData):
            fileDir = os.path.dirname(probeData)
            if len(fileDir) == 0:
                probeData = os.path.join(self.dirPath, probeData)
        try:
            inp = open(probeData, 'r')
            return(inp)
        except IOError:
            ePrint("probe data file %s not found" % (self.probeData))
        return(None)

    def cmdIf(self, args):
        # self.ifStack.append(self.ifDisable)
        if not self.evalBoolArg(args[1]):
            self.cmdDisable |= IF_DISABLE

    def cmdEndIf(self, _):
        self.cmdDisable &= ~IF_DISABLE
        # self.ifDisable = ifStack.pop()

    def setX(self, args):
        coordinate = self.evalIntArg(args[1])
        xVal = self.evalFloatArg(args[2])
        mill = self.mill
        if mill is not None:
            mill.setX(coordinate, xVal)

    def setY(self, args):
        coordinate = self.evalIntArg(args[1])
        yVal = self.evalFloatArg(args[2])
        mill = self.mill
        if mill is not None:
            mill.setY(coordinate, yVal)

    def parkX(self, args):
        self.xPark = self.evalFloatArg(args[1])

    def parkY(self, args):
        self.yPark = self.evalFloatArg(args[1])

    def ParkZ(self, args):
        self.zPark = self.evalFloatArg(args[1])

    def park(self, args):
        result = self.getLocation(args, [self.xPark, self.yPark, self.zPark])
        (self.xPark, self.yPark, self.zPark) = result

    def initialX(self, args):
        self.xInitial = self.evalFloatArg(args[1])

    def initialY(self, args):
        self.yInitial = self.evalFloatArg(args[1])

    def initialZ(self, args):
        self.zInitial = self.evalFloatArg(args[1])

    def initial(self, args):
        result = self.getLocation(args, [self.xInitial, \
                                         self.yInitial, self.zInitial])
        (self.xInitial, self.yInitial, self.zInitial) = result

    def getLocation(self, args, result=None):
        if result is None:
            result = [0.0, 0.0, 0.0]
        self.reLoc = (r"^.*? +([xyzXYZ])\s*([a-zA-Z0-9\(\)\.\-]+)\s*" \
                      r"([xyzXYZ]*)\s*([a-zA-Z0-9\(\)\.\-]*)\s*" \
                      r"([xyzXYZ]*)\s*([a-zA-Z0-9\(\)\.\-]*)")
        match = re.match(self.reLoc, args[0])
        if match is not None:
            groups = len(match.groups())
            i = 1
            while i <= groups:
                axis = match.group(i).lower()
                i += 1
                if len(axis) == 0:
                    break
                if i > groups:
                    break
                if match.group(i) == 'cur':
                    if axis == 'x':
                        val = self.mill.last[0]
                    elif axis == 'y':
                        val = self.mill.last[1]
                    elif axis == 'z':
                        val = self.mill.lastZ
                else:
                    val = self.evalFloatArg(match.group(i))
                i += 1
                if axis == 'x':
                    result[0] = val
                elif axis == 'y':
                    result[1] = val
                elif axis == 'z':
                    result[2] = val
        return(result)

    def setSize(self, args):
        self.ncInit()
        self.xSize = self.evalFloatArg(args[1])
        self.ySize = self.evalFloatArg(args[2])
        if len(args) >= 4:
            self.zSize = self.evalFloatArg(args[3])

        mill = self.mill
        mill.write("(material size x %0.3f y %0.3f" % \
                   (self.xSize, self.ySize))
        if self.zSize != 0:
            mill.write(" z %0.3f" % (self.zSize))
        mill.write(")\n")
        self.draw.material(self.xSize, self.ySize)

    def setDrillSize(self, args):
        self.drillSize = self.evalFloatArg(args[1])

    def setDrillAngle(self, args):
        self.drillAngle = radians(self.evalFloatArg(args[1])) / 2

    def setDrillExtra(self, args):
        self.drillExtra = self.evalFloatArg(args[1])

    def setPeckDepth(self, args):
        self.peckDepth = -abs(self.evalFloatArg(args[1]))

    def setCoord(self, args):
        self.coordinate = self.evalIntArg(args[1])

    def setVariables(self, args):
        self.variables = self.evalBoolArg(args[1])

    def setSafeZ(self, args):
        self.safeZ = self.evalFloatArg(args[1])

    def setRetract(self, args):
        self.retract = self.evalFloatArg(args[1])

    def setTop(self, args):
        self.top = self.evalFloatArg(args[1])

    def setDepth(self, args):
        self.depth = self.evalFloatArg(args[1])

    def setFeed(self, args):
        self.feed = self.evalFloatArg(args[1])

    def setZFeed(self, args):
        self.zFeed = self.evalFloatArg(args[1])

    def setSpeed(self, args):
        self.speed = self.evalFloatArg(args[1])
        if self.mill is not None:
            self.mill.setSpeed(self.speed)

    def setDelay(self, args):
        self.delay = self.evalFloatArg(args[1])

    def setTool(self, args):
        if len(args) >= 2:
            # match = re.match(r"^[a-zA-z]+ +[0-9]+ +(.*)$", args[0])
            match = re.match(r"^\w+ +(\w*[\d\w]+)+ *(.*)$", args[0])
            comment = ""
            if match is not None:
                tool = match.group(1)
                comment = match.group(2)
                if tool[0].isalpha():
                    toolDef = eval(tool)
                    self.tool = int(toolDef.num)
                    toolType = toolDef.toolType
                    if toolType == 'm':
                        self.endMillSize = toolDef.toolSize
                    elif toolType == 'd':
                        self.drillSize = toolDef.toolSize
                    else:
                        ePrint("invalid tool type")
                    if len(comment) == 0:
                        self.toolComment = toolDef.comment
                else:
                    self.tool = int(tool)
                    self.toolComment = comment
            else:
                self.toolComment = ""
            if self.mill is not None:
                self.mill.toolChange(self.tool, self.toolComment)
        else:
            self.tool = None
            self.toolComment = ""

    def setLoc(self, args):
        self.x = self.evalFloatArg(args[1])
        self.y = self.evalFloatArg(args[2])

    def setLocX(self, args):
        self.x = self.evalFloatArg(args[1])

    def setLocY(self, args):
        self.y = self.evalFloatArg(args[1])

    def setXOffset(self, args):
        self.xOffset = self.evalFloatArg(args[1])

    def setYOffset(self, args):
        self.yOffset = self.evalFloatArg(args[1])

    def setRampAngle(self, args):
        self.rampAngle = radians(self.evalFloatArg(args[1]))

    def setEndMillSize(self, args):
        self.endMillSize = self.evalFloatArg(args[1])

    def setMillHoleSize(self, args):
        self.millHoleSize = self.evalFloatArg(args[1])

    def setHoleMin(self, args):
        if len(args) >= 2:
            self.holeMin = self.evalFloatArg(args[1])
        else:
            self.holeMin = 0.0

    def setHoleMax(self, args):
        if len(args) >= 2:
            self.holeMax = self.evalFloatArg(args[1])
        else:
            self.holeMax = MAX_VALUE

    def setHoleRange(self, args):
        if len(args) >= 2:
            if args[1] == "*":
                self.holeMin = self.drillSize
            else:
                self.holeMin = self.evalFloatArg(args[1])
            if len(args) >= 3:
                val = args[2]
                if val.startswith("+-"):
                    val = self.evalFloatArg(val[2:])
                    self.holeMax = self.holeMin + val
                    self.holeMin -= val
                else:
                    self.holeMax = self.evalFloatArg(args[2])
            else:
                self.holeMax = self.holeMin + MIN_DIST
                self.holeMin -= MIN_DIST
        else:
            self.holeMin = 0.0
            self.holeMax = MAX_VALUE

    def setHoleOrder(self, args):
        val = args[1].lower()
        for (i, x) in self.holeOrderValues:
            if val == x:
                self.holeOrder = i
                val = None
                break

    def setDepthPass(self, args):
        self.depthPass = abs(self.evalFloatArg(args[1]))

    def setEvenDepth(self, args):
        self.evenDepth = self.evalBoolArg(args[1])

    def setWidth(self, args):
        self.width = abs(self.evalFloatArg(args[1]))

    def setVBit(self, args):
        self.vBit = radians(abs(self.evalFloatArg(args[1])))

    def setWidthPasses(self, args):
        self.widthPasses = self.evalIntArg(args[1])

    def setWidthPerPass(self, args):
        self.widthPerPass = self.evalFloatArg(args[1]) / 2

    def setPause(self, args):
        self.pause = self.evalBoolArg(args[1])

    def pauseHere(self, args):
        mill = self.mill
        result = self.getLocation(args, [mill.last[0],
                                         mill.last[1], self.safeZ])
        (xPause, yPause, zPause) = result
        mill.moveZ(zPause)
        mill.move((xPause, yPause))
        speed = mill.speed
        mill.setSpeed(0)
        mill.pause()
        mill.setSpeed(speed)

    def setHomePause(self, args):
        self.homePause = self.evalBoolArg(args[1])

    def setTest(self, args):
        self.test = self.evalBoolArg(args[1])

    def setDirection(self, args):
        direction = args[1].lower()
        if direction == 'climb':
            self.climb = True
            self.dir = None
        elif direction == 'normal':
            self.climb = False
            self.dir = None
        elif direction == 'cw':
            self.dir = CW
            self.climb = None
        elif direction == 'ccw':
            self.dir = CCW
            self.climb = None
        else:
            ePrint("invalid direction %s" % direction)

    def setFinish(self, args):
        self.finishAllowance = self.evalFloatArg(args[1])

    def setTabs(self, args):
        self.tabs = self.evalIntArg(args[1])

    def setTabWidth(self, args):
        self.tabWidth = self.evalFloatArg(args[1])

    def setTabDepth(self, args):
        self.tabDepth = self.evalFloatArg(args[1])

    def setOutput(self, args):
        self.output = self.evalBoolArg(args[1])

    def setAlternate(self, args):
        self.alternate = self.evalBoolArg(args[1])

    def setAddArcs(self, args):
        self.addArcs = self.evalBoolArg(args[1])

    def setCloseOpen(self, args):
        self.closeOpen = self.evalBoolArg(args[1])

    def setShortRamp(self, args):
        self.shortRamp = self.evalBoolArg(args[1])

    def setPauseCenter(self, args):
        self.pauseCenter = self.evalBoolArg(args[1])

    def setPauseHeight(self, args):
        self.pauseHeight = self.evalFloatArg(args[1])

    def setDrawDxf(self, args):
        self.drawDxf = self.evalBoolArg(args[1])

    def setDrawSvg(self, args):
        self.drawSvg = self.evalBoolArg(args[1])

    def setOneDxf(self, args):
        self.oneDxf = self.evalBoolArg(args[1])
        if not self.oneDxf:
            self.closeDxf(None)

    def closeDxf(self, _):
        if self.draw is not None:
            self.draw.close()
            self.draw = None

    def setDbg(self, args):
        self.dbg = self.evalBoolArg(args[1])
        dprtSet(dbgFlag=self.dbg)

    def setDbgFile(self, args):
        self.dbgFile = os.path.join(self.dirPath, args[1])
        self.dbg = True
        dprtSet(self.dbg, dFile=self.dbgFile)

    def setPrintGCode(self, args):
        self.printGCode = self.evalBoolArg(args[1])

    def drill(self, args=None, op=DRILL, size=None):
        self.ncInit()
        if args is not None:
            if len(args) >= 2:
                self.x = self.evalFloatArg(args[1])
            if len(args) >= 3:
                self.y = self.evalFloatArg(args[2])
        if size is None:
            size = self.drillSize
        self.count += 1
        mill = self.mill
        gMove = "0"
        if abs(mill.last[1] - self.y) < MIN_DIST:
            if self.xOffset != 0:
                mill.write("g0 x %7.4f\n" % (self.x - self.xOffset))
                gMove = "1"
                mill.setFeed(self.feed)
            mill.write("g%s x %7.4f\n" % (gMove, self.x))
            mill.last = (self.x, self.y)
        elif abs(mill.last[0] - self.x) < MIN_DIST:
            if self.yOffset != 0:
                mill.write("g0 y %7.4f\n" % (self.y - self.yOffset))
                gMove = "1"
                mill.setFeed(self.feed)
            mill.write("g%s y %7.4f\n" % (gMove, self.y))
            mill.last = (self.x, self.y)
        else:
            if mill.last[0] != self.x and mill.last[1] != self.y:
                if self.xOffset != 0 or self.yOffset != 0:
                    mill.write("g0 x %7.4f y %7.4f\n" % \
                               (self.x - self.xOffset, self.y - self.yOffset))
                    gMove = "1"
                    mill.setFeed(self.feed)
                mill.write("g%s x %7.4f y %7.4f\n" % (gMove, self.x, self.y))
                mill.last = (self.x, self.y)
        self.draw.hole((self.x, self.y), size)
        holeCount = ("/%d" % (self.holeCount)) if self.holeCount is not None \
                    else ""
        comment = "hole %d%s x %7.4f y %7.4f" % \
                  (self.count, holeCount, self.x, self.y)
        if op == DRILL:
            offset = 0
            if self.drillAngle != 0.0:
                offset += -(size / 2) / tan(self.drillAngle)
                dprt("drill size %7.4f z offset %7.4f" % (size, offset))
            if self.drillExtra != 0.0:
                offset += self.drillExtra
                dprt("drill z offset %7.4f" % (offset))
            if self.pause:
                mill.moveZ(self.pauseHeight)
                mill.write("m0 (pause)\n")
            mill.zTop()
            if self.peckDepth == 0 or self.peckDepth <= self.depth:
                mill.zDepth(offset, comment=comment)
            else:
                self.depth += offset
                peckDepth = self.peckDepth
                n = int(ceil(self.depth / self.peckDepth))
                peckDepth = self.depth / n
                d = peckDepth
                for i in range(n):
                    mill.plungeZ(d, comment)
                    mill.zTop()
                    # mill.moveZ(d)
                    d += peckDepth
        elif op == BORE:
            mill.setSpeed(self.speed)
            mill.zTop()
            mill.zDepth()
            mill.setSpeed(0)
            mill.retract()
            mill.retract()
        elif op == TAP:
            mill.write("m0 (pause insert tap)\n")
            if self.variables:
                z = "[#%s + #%s]" % (self.topVar, self.depthVar)
            else:
                z = "%7.4f" % (self.top + self.depth)
            mill.write("g0 z %s\t(%s)\n" % (z, comment))
            mill.write("m0 (pause tap hole)\n")
            mill.retract()
            mill.write("m0 (pause remove tap)\n")
        elif op == TAPMATIC:
            mill.setSpeed(self.speed)
            if self.pause:
                mill.moveZ(self.pauseHeight)
                mill.write("m0 (pause)\n")
            mill.moveZ(self.tapHeight, comment)
            mill.write("f %5.3f\n" % (self.tapFeed))
            mill.write("g1 z %7.4f\n" % (self.depth))
            mill.write("f %5.3f\n" % (2 * self.tapFeed))
            mill.write("g1 z %7.4f\n" % (self.tapHeight))
            mill.retract()
            mill.write("m0 (pause)\n")
        mill.blankLine()

    def bore(self, args):
        self.drill(args, BORE)

    def getMillPath(self):
        if self.mp is None:
            self.mp = MillPath(self)
        self.mp.config(self)
        return(self.mp)

    def millSlot(self, p, width, length, comment):
        self.slotNum + 1
        self.mill.write("(%s %2d width %0.3f length %0.3f "\
                        "at x %0.3f y %0.3f)\n" % \
                        (comment, self.slotNum, width, length, \
                         self.x, self.y))
        self.mill.write("(endMill %0.3f depth %0.3f depthPass %0.3f)\n" % \
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
        width = self.evalFloatArg(args[1])
        length = self.evalFloatArg(args[2])
        # self.slotNum += 1
        # self.mill.write("(xSlot %2d width %0.3f length %0.3f "\
        #               "at x %0.3f y %0.3f)\n" % \
        #               (slotNum, width, length, self.x, self.y))
        # self.mill.write("(endMill %0.3f depth %0.3f depthPass %0.3f)\n" % \
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
        width = self.evalFloatArg(args[1])
        length = self.evalFloatArg(args[2])
        # self.slotNum += 1
        # self.mill.write("(ySlot %2d width %0.3f length %0.3f "\
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
        # self.mill.write("(endMill %0.3f depth %0.3f depthPass %0.3f)\n" % \
        #           (self.endMillSize, self.depth, self.depthPass))
        # ncInit()
        # if self.slot is None:
        #     self.slot = Slot(self.mill, self.draw)
        # self.slot.ySlot(width, length)

    def setLayers(self, args):
        for l in args[1:]:
            self.layers.append(l)

    def clrLayers(self, _):
        self.layers = []

    def setMaterialLayer(self, args):
        self.materialLayer = self.evalStringArg(args[1])

    def setFixtureLayer(self, args):
        self.fixtureLayer = self.evalStringArg(args[1])

    def setRef(self, args):
        # if self.dxfInput is not None:
        #     ePrint("set reference before dxf file openned")
        #     self.error = True
        #     return
        
        val = args[1].lower()
        for (i, x) in self.refValues:
            if val == x:
                self.reference = i
                break

    def setOrientation(self, args):
        val = args[1].lower()
        for (i, x) in self.orientationValues:
            if val == x:
                self.orientation = i
                val = None
                break
        if val is not None:
            self.orientation = self.evalIntArg(args[1])
            if self.orientation >= 0 or \
               self.orientation < O_MAX:
                ePrint("invalid orientation %d" % (self.orientation))
                self.orientation = None
        layer = None
        if self.orientation == O_POINT:
            self.orientationLayer = layer = args[2]
        if self.dxfInput is not None:
            self.dxfInput.setOrientation(self.orientation, layer)

    def readDxf(self, args):
        if self.orientation is None:
            self.error = True
            ePrint("orientation not set")
            dflush()
        l = args[0]
        fileName = l.split(' ', 1)[-1]
        if fileName == "*":
            if self.dxfFile is not None:
                if re.search(r"\.dxf$", self.dxfFile):
                    fileName = self.dxfFile
                else:
                    fileName = self.dxfFile + ".dxf"
            else:
                fileName = self.fileName + ".dxf"

        fileDir = os.path.dirname(fileName)
        if len(fileDir) == 0 and len(self.dirPath) != 0:
            fileName = os.path.join(self.dirPath, fileName)

        if self.outFile is None:
            if fileName == "*":
                if self.dxfFile is not None:
                    self.baseName = fileName.replace(".dxf", "")
                else:
                    self.baseName = fileName
            else:
                self.baseName = fileName.split('.')[0]
        else:
            baseDir = os.path.dirname(self.baseName)
            if len(baseDir) == 0 and len(self.dirPath) != 0:
                self.baseName = os.path.join(self.dirPath, self.baseName)

        dprt("fileName %s" % fileName)
        dprt("baseName %s" % self.baseName)

        self.dxfInput = Dxf(self)
        self.materialLayer = "Material"
        self.fixtureLayer = "Fixture"
        self.dxfInput.open(fileName, self.reference)
        self.dxfInput.setOrientation(self.orientation, self.orientationLayer)

    def dxfLine(self, args):
        self.ncInit()
        if self.line is None:
            self.line = MillLine(self, self.mill, self.draw)
        self.line.millLines(args[1])

    def getLayer(self, args):
        if len(args) <= 1:
            return(None)
        layer = args[1]
        if layer == '*':
            if self.layer is not None:
                layer = self.layer
            else:
                ePrint("layer not specified")
                sys.exit()
        elif layer.lower() == "none":
            layer = None
        return(layer)

    def dxfPath(self, args):
        layer = self.getLayer(args)
        self.segments = self.dxfInput.getPath(layer)

    def dxfPoint(self, args):
        x = self.evalFloatArg(args[1])
        y = self.evalFloatArg(args[2])
        inside((x, y), self.segments[0])

    def dxfTab(self, args):
        layer = args[1]
        self.tabPoints = self.dxfInput.getPoints(layer)
        self.tabs = len(self.tabPoints)
        dbg = True
        if dbg:
            dprt("\ntabs %d" % (self.tabs))
            for (i, p) in enumerate(self.tabPoints):
                dprt("%2d p %7.4f, %7.4f" % (i, p[0], p[1]))
                # cfg.draw.drawX(p, "t%d" % (i))
            dprt()

    def dxfOutside(self, args):
        layer = self.getLayer(args)
        offset = self.endMillSize / 2 + self.finishAllowance
        self.segments = self.dxfInput.getPath(layer, True)
        self.ncInit()
        mp = self.getMillPath()
        while len(self.segments) != 0:
            last = self.mill.last
            minDist = MAX_VALUE
            index = 0
            for (i, seg) in enumerate(self.segments):
                d = xyDist(last, seg[0].p0)
                if d < minDist:
                    minDist = d
                    index = i
                    # print("index %d minDist %7.4f" % (i, minDist))
            seg = self.segments.pop(index)
            dprt("seg %d" % (index))
            if xyDist(seg[0].p0, seg[-1].p1) > MIN_DIST:
                ePrint("dxfOutside - segment not closed skipping")
                continue
            (path, tabPoints) = createPath(seg, offset, True, self.tabPoints, \
                                           addArcs=self.addArcs, \
                                           closeOpen = self.closeOpen)
            mp.millPath(path, tabPoints)
        self.tabPoints = []

    def dxfInside(self, args):
        layer = self.getLayer(args)
        offset = self.endMillSize / 2 + self.finishAllowance
        self.segments = self.dxfInput.getPath(layer, True)
        tmp = []
        for seg in self.segments:
            if len(seg) >= 3:
                tmp.append(seg)
        self.segments = tmp
        self.ncInit()
        mp = self.getMillPath()
        while len(self.segments) != 0:
            last = self.mill.last
            minDist = MAX_VALUE
            index = 0
            for (i, seg) in enumerate(self.segments):
                d = xyDist(last, seg[0].p0)
                if d < minDist:
                    minDist = d
                    index = i
                    # print("index %d minDist %7.4f*++*" % (i, minDist))
            seg = self.segments.pop(index)
            dprt("seg %d" % (index))
            if xyDist(seg[0].p0, seg[-1].p1) > MIN_DIST:
                ePrint("dxfInside - segment not closed skipping")
                continue
            (path, tabPoints) = createPath(seg, offset, False, self.tabPoints, \
                                           addArcs=self.addArcs, \
                                           closeOpen = self.closeOpen)
            mp.millPath(path, tabPoints)
        self.tabPoints = []

    def openSetup(self, args):
        startList = ("xmin", "xmax", "ymin", "ymax")
        dirList = ("xlt", "xgt", "ylt", "ygt")
        if len(args) < 4:
            return False
        start = args[2].lower()
        self.startType = None
        for i, val in enumerate(startList):
            if start == val:
                self.startType = i
                break
        direction = args[3].lower()
        self.dirType = None
        for i, val in enumerate(dirList):
            if direction == val:
                self.dirType = i
                break
        return True

    def openPoint(self, seg, dist):
        startType = self.startType
        p0 = seg[0].p0
        p1 = seg[-1].p1
        reverse = False
        if startType == ST_XMIN:
            if p0.x > p1.x:
                reverse = True
        elif startType == ST_XMAX:
            if p0.x < p1.x:
                reverse = True
        elif startType == ST_YMIN:
            if p0.y > p1.y:
                reverse = True
        elif startType == ST_YMAX:
            if p0.y < p1.Y:
                reverse = True
        if reverse:
            seg = reverseSeg(seg)
        p = seg[0].p0
        dirType = self.dirType
        if dirType == DIR_XLT:
            p = newPoint((p.x - dist, p.y))
        elif dirType == DIR_XGT:
            p = newPoint((p.x + dist, p.y))
        elif dirType == DIR_YLT:
            p = newPoint((p.x, p.y - dist))
        elif dirType == DIR_YGT:
            p = newPoint((p.x, p.y + dist))
        return p

    def dxfOpen(self, args):
        layer = self.getLayer(args)
        dist = self.endMillSize / 2.0 + self.finishAllowance
        d = self.endMillSize / 2.0 + 0.125
        self.segments = self.dxfInput.getPath(layer)
        if len(self.segments) == 0:
            return
        # self.points = self.dxfInput.getPoints(layer)
        # self.points = self.dxfInput.getLabel(layer)
        if not self.openSetup(args):
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
            dprt()
            l = seg[0].extend(d, True)
            seg.insert(0, l)
            l = seg[-1].extend(d, False)
            seg.append(l)
            # points = self.points[0] if len(self.points) > 0 else None
            point = self.openPoint(seg, dist)
            self.draw.drawX(point)
            (path, tabPoints) \
                = createPath(seg, dist, False, self.tabPoints, False, \
                             point, addArcs=self.addArcs)
            # else:
            #     path = seg
            #     tabPoints = None
            for l in path:
                l.prt()
            mp.millPath(path, tabPoints, False)
        self.tabPoints = []

    def orderHoles(self, dLoc, dbg=False):
        result = []
        if self.holeOrder == HOLE_NEAREST:
            last = self.mill.last
            while len(dLoc) != 0:
                minDist = MAX_VALUE
                index = 0
                for (i, loc) in enumerate(dLoc):
                    dist = xyDist(last, loc)
                    if dbg:
                        dprt("%d last %7.4f %7.4f " \
                             "loc %7.4f %7.4f dist %7.4f" % \
                             (i, last[0], last[1], loc[0], loc[1], dist))
                    if dist < minDist:
                        minDist = dist
                        index = i
                loc = dLoc.pop(index)
                result.append(loc)
                if dbg:
                    dprt("%d loc %7.4f %7.4f" % (index, loc[0], loc[1]))
                last = loc
        elif self.holeOrder == HOLE_COLUMNS:
            dLoc.sort(key=lambda loc: (loc.x, loc.y))
            lastX = dLoc[0].x
            reverse = False
            colStart = 0
            result = []
            iFinal = len(dLoc) - 1
            for i, loc in enumerate(dLoc):
                if (lastX != loc.x) or (i == iFinal):
                    print(reverse, colStart, i)
                    lastX = loc.x
                    if reverse:
                        for j in range(i if i == iFinal else i-1, \
                                       colStart-1, -1):
                            result.append(dLoc[j])
                    else:
                        for j in range(colStart, i):
                            result.append(dLoc[j])
                    reverse = not reverse
                    colStart = i
        elif self.holeOrder == HOLE_ROWS:
            dLoc.sort(key=lambda loc: (loc.y, loc.x))
            lastY = dLoc[0].y
            reverse = False
            rowStart = 0
            result = []
            iFinal = len(dLoc) - 1
            for i, loc in enumerate(dLoc):
                if (lastY != loc.y) or (i == iFinal):
                    print(reverse, rowStart, i)
                    lastY = loc.y
                    if reverse:
                        for j in range(i if i == iFinal else i-1, \
                                       rowStart-1, -1):
                            result.append(dLoc[j])
                    else:
                        for j in range(rowStart, i):
                            result.append(dLoc[j])
                    reverse = not reverse
                    rowStart = i
        return(result)

    def resetHoleVars(self):
        self.holeMin = 0.0
        self.holeMax = MAX_VALUE
        self.millHoleSize = None

    def dxfDrill(self, args, op=DRILL):
        dbg = False
        layer = cfg.getLayer(args)
        drill = self.dxfInput.getHoles(layer, self.holeMin, self.holeMax, \
                                       dbg=False)
        self.ncInit()
        last = self.mill.last
        for d in drill:
            self.holeCount = len(d.loc)
            print("holes %d" % (self.holeCount))
            if op == DRILL:
                self.mill.write("(drill size %6.3f holes %d)\n" % \
                                (d.size, self.holeCount))
            elif op == BORE:
                self.mill.write("(bore size %6.3f holes %d)\n" % \
                                (d.size, self.holeCount))
            self.count = 0

            # dLoc = d.loc
            # while len(dLoc) != 0:
            #     minDist = MAX_VALUE
            #     index = 0
            #     for (i, loc) in enumerate(dLoc):
            #         dist = xyDist(last, loc)
            #         if dbg:
            #             dprt("%d last %7.4f %7.4f " \
            #                  "loc %7.4f %7.4f dist %7.4f" % \
            #                  (i, last[0], last[1], loc[0], loc[1], dist))
            #         if dist < minDist:
            #             minDist = dist
            #             index = i
            #     loc = dLoc.pop(index)
            #     if dbg:
            #         dprt("%d loc %7.4f %7.4f" % (index, loc[0], loc[1]))
            #     last = loc

            result = self.orderHoles(d.loc)
            for loc in result:
                (self.x, self.y) = loc
                self.drill(None, op, d.size)
        self.resetHoleVars()

    def dxfDrillSort(self, args, op=DRILL):
        dbg = False
        layer = cfg.getLayer(args)
        drill = self.dxfInput.getHoles(layer, self.holeMin, self.holeMax, \
                                       dbg=False)
        self.ncInit()
        last = self.mill.last

        for d in drill:
            dLoc = d.loc
            dLoc.sort(key=lambda loc: (loc.x, loc.y))
            lastX = dLoc[0].x
            reverse = False
            colStart = 0
            result = []
            iFinal = len(dLoc) - 1
            for i, loc in enumerate(dLoc):
                if (lastX != loc.x) or (i == iFinal):
                    print(reverse, colStart, i)
                    lastX = loc.x
                    if reverse:
                        for j in range(i if i == iFinal else i-1, \
                                       colStart-1, -1):
                            result.append(dLoc[j])
                    else:
                        for j in range(colStart, i):
                            result.append(dLoc[j])
                    reverse = not reverse
                    colStart = i

            for loc in result:
                (self.x, self.y) = loc
                self.drill(None, op, d.size)
        self.resetHoleVars()

    def dxfMillHole(self, args, drill=None):
        if drill is None:
            layer = cfg.getLayer(args)
            drill = self.dxfInput.getHoles(layer, cfg.holeMin, cfg.holeMax)
        self.ncInit()
        last = self.mill.last
        mp = self.getMillPath()
        for d in drill:
            if d.size < self.holeMin or \
               d.size >= self.holeMax:
                continue
            hSize = d.size if self.millHoleSize is None else self.millHoleSize
            size = (hSize - self.endMillSize - self.finishAllowance) / 2.0
            if size <= 0:
                ePrint("endmill %6.4f to big for hole %6.4f with "\
                       "finishAllowace %6.4f" % \
                       (self.endMillSize, hSize, self.finishAllowance))
                sys.exit()
            self.mill.write("(drill size %6.3f hole size %6.3f "\
                            "holes %d)\n" % \
                            (hSize, size * 2 + self.endMillSize, \
                             len(d.loc)))
            # dLoc = d.loc
            # n = 1
            # while len(dLoc) != 0:
            #     minDist = MAX_VALUE
            #     index = 0
            #     for (i, loc) in enumerate(dLoc):
            #         dist = xyDist(last, loc)
            #         if dist < minDist:
            #             minDist = dist
            #             index = i
            #     loc = dLoc.pop(index)

            n = 1
            result = self.orderHoles(d.loc)
            for loc in result:
                self.draw.hole((loc[0], loc[1]), hSize)
                self.mill.write("(hole %d at %7.4f, %7.4f)\n" % \
                                (n, loc[0], loc[1]))
                last = loc
                # hSize = d.size if millSize is None else millSize
                # if size <= 0:
                #     ePrint("endmill %6.4f to big for hole %6.4f with "\
                #            "finishAllowace %6.4f" % \
                #            (self.endMillSize, hSize, self.finisAllowance))
                #     sys.exit()
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
            pass
        self.tabPoints = []
        self.resetHoleVars()

    # stepProfile ((depth1, diam1), ... (depthN, diamN))
    def getStepProfile(self, args):
        expr = r"^\w+\s+(.*)"
        m = re.match(expr, args[0])
        if m:
            self.stepProfile = self.evalListArg(m.group(1))
        else:
            self.stepProfile = None

    def dxfSteppedHole(self, args, drill=None):
        if drill is None:
            layer = self.getLayer(args)
            drill = self.dxfInput.getHoles(layer, cfg.holeMin, cfg.holeMax)
        self.ncInit()
        last = self.mill.last
        mp = self.getMillPath()
        ncWrite = self.mill.write
        for d in drill:
            # dLoc = d.loc
            # n = 1
            # numHoles = len(dLoc)
            # while len(dLoc) != 0:
            #     minDist = MAX_VALUE
            #     index = 0
            #     for (i, loc) in enumerate(dLoc):
            #         dist = xyDist(last, loc)
            #         if dist < minDist:
            #             minDist = dist
            #             index = i
            #     loc = dLoc.pop(index)

            result = self.orderHoles(d.loc)
            for n, loc in enumerate(result):
                ncWrite("(hole %2d of %2d steps %d x %7.4f, y %7.4f)\n\n" % \
                        (n, len(result), len(self.stepProfile), \
                         loc[0], loc[1]))
                last = loc
                if self.pauseCenter:
                    mill = self.mill
                    mill.safeZ()
                    mill.move(loc)
                    mill.moveZ(self.pauseHeight)
                    mill.pause()
                for (j, (depth, hSize)) in enumerate(self.stepProfile):
                    ncWrite("(step %d depth %6.4f size %6.4f)\n\n" % \
                            (j+1, depth, hSize))
                    size = (hSize - self.endMillSize - \
                            self.finishAllowance) / 2.0
                    self.draw.hole((loc[0], loc[1]), hSize)
                    if size <= 0:
                        ePrint("endmill %6.4f to big for hole %6.4f with "\
                               "finishAllowace %6.4f" % \
                               (self.endMillSize, hSize, self.finishAllowance))
                        sys.exit()
                    self.depth = depth
                    a = Arc(loc, size, 0.0, 360.0, i=n)
                    path = []
                    path.append(a)
                    mp.millPath(path, None)
                    self.mill.move(loc)
                    self.mill.zTop()
                n += 1
        self.resetHoleVars()

    def dxfBore(self, args):
        self.dxfDrill(args, BORE)

    def dxfTap(self, args):
        self.dxfDrill(args, TAP)

    def dxfTapMatic(self, args):
        self.dxfDrill(args, TAPMATIC)

    def tapmatic(self, args):
        self.tapHeight = self.evalFloatArg(args[1])
        self.tapRpm = self.evalFloatArg(args[2])
        self.tapTpi = self.evalFloatArg(args[3])
        self.tapFeed = self.tapRpm / self.tapTpi

    def closeFiles(self, _):
        self.dxfInput = None
        self.holeCount = None
        self.count = 0
        if self.draw is not None:
            self.draw.close()
            self.draw = None
        if self.mill is not None:
            self.mill.close()
            self.mill = None
            self.oVal = 100
        self.mp = None
        self.init = False

    def outputFile(self, args):
        self.end()
        draw = self.draw
        if draw is not None:
            if self.oneDxf:
                draw.nextLayer()
            else:
                draw.close()
                self.draw = None
        self.tabInit()          # reset tabs
        self.finishAllowance = 0.0 # reset finish allowance
        l = args[0]
        fileName = l.split(' ', 1)[-1]
        if fileName.startswith('*'):
            if fileName.endswith("$"):
                fileName = (self.baseName + fileName[1:-1] + \
                            ("%0.3f" % (self.drillSize))[2:])
            elif fileName.endswith("$M"):
                fileName = (self.baseName + fileName[1:-2] + \
                            ("%0.3f" % (self.endMillSize))[2:] + "M")
            else:
                fileName = self.baseName + fileName[1:]
        else:
            if len(os.path.dirname(fileName)) == 0:
                fileName = os.path.join(self.dirPath, fileName)
            fileName = os.path.join(self.dirPath, fileName)
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
            moduleFile = os.path.join(getcwd(),  name)
            if not os.path.isfile(moduleFile):
                moduleFile = os.path.join(self.runPath, name)
            # module = load_source("module", moduleFile)
            module = importlib.abc.Loader.exec_module("module", moduleFile)
            # print(dir(module))
            # for m in inspect.getmembers(module, inspect.isclass):
            #     print(m)
            self.engraveModule = module.Engrave(self)
            self.engraveModule.setup()
        else:
            if self.engraveModule is not None:
                self.ncInit()
                self.engraveModule.engrave()

    def load(self, args, dbg=False):
        if len(args) >= 2:
            moduleName = args[1]
            self.loadModule(moduleName)

    def loadModule(self, moduleName, dbg=True):
        loaded =  moduleName in sys.modules
        name = moduleName + ".py"
        fileName = os.path.join(getcwd(),  name)
        if not os.path.isfile(fileName):
            fileName = os.path.join(self.runPath, name)
        # module = load_source(moduleName, fileName)
        loader = importlib.machinery.SourceFileLoader(moduleName, fileName)
        module = loader.load_module()
        if not loaded:
            if dbg:
                dprt(dir(module))
            for (name, val) in inspect.getmembers(module, inspect.isclass):
                if dbg:
                    dprt("class %s module %s" % (name, val.__module__))
                if val.__module__ == moduleName and \
                   (name[0].lower() + name[1:]) == moduleName:
                    cmd = "module.%s(cfg)" % (name)
                    c = eval(cmd)
                    cmd = "self.%s = c" % (moduleName)
                    exec(cmd)
                    self.addCommands(c.cmds)
                    break
        return(module)

    def var(self, args):
        expr = r"var\s+(\w+)\s+(.+)"
        m = re.match(expr, args[0])
        if m:
            var = m.group(1)
            expression = m.group(2)
            try:
                val = eval(expression)
                globals()[var] = val
                return
            except:
                traceback.print_exc()
            sys.exit()

    def evalFloatArg(self, arg):
        try:
            argLC = arg.lower()
            if argLC == "none":
                return(None)
            metric = 1.0
            pos = argLC.find("mm")
            if  pos > 0:
                metric = 25.4
                arg = arg[:pos] + arg[pos + 2:]
            val = float(eval(arg)) / metric
            dprt("evalFloatArg %s %7.4f" % (arg, val))
            return(val)
        except NameError:
            ePrint("nameError in %s" % arg)
        except SyntaxError:
            ePrint("syntaxError in %s" % arg)
        except:
            traceback.print_exc()
        sys.exit()

    def evalIntArg(self, arg):
        try:
            if arg.lower() == "none":
                return(None)
            val = int(eval(arg))
            dprt("evalIntArg %s %d" % (arg, val))
            return(val)
        except NameError:
            print("nameError in %s" % arg)
        except SyntaxError:
            print("syntaxError in %s" % arg)
        except:
            traceback.print_exc()
        sys.exit()

    def evalStringArg(self, arg):
        try:
            if arg.lower() == "none":
                return(None)
            val = str(arg)
            dprt("evalStrArg %s %s" % (arg, val))
            return(val)
        except NameError:
            print("nameError in %s" % arg)
        except SyntaxError:
            print("syntaxError in %s" % arg)
        except:
            traceback.print_exc()
        sys.exit()

    def evalBoolArg(self, arg):
        try:
            if arg.lower() == "none":
                return(None)
            val = eval(arg) != 0
            dprt("evalBoolArg %s %s" % (arg, val))
            return(val)
        except NameError:
            print("nameError in %s" % arg)
        except SyntaxError:
            print("syntaxError in %s" % arg)
        except:
            traceback.print_exc()
        sys.exit()

    def evalListArg(self, arg):
        try:
            if arg.lower() == "none":
                return(None)
            val = eval(arg)
            dprt("evalListArg %s %s" % (arg, val))
            return(val)
        except NameError:
            print("nameError in %s" % arg)
        except SyntaxError:
            print("syntaxError in %s" % arg)
        except:
            traceback.print_exc()
        sys.exit()

    def setProbe(self, args):
        self.probe = self.evalBoolArg(args[1])

    def setProbeDepth(self, args):
        self.probeDepth = self.evalFloatArg(args[1])

    def setProbeFeed(self, args):
        self.probeFeed = self.evalFloatArg(args[1])

    def setProbeTool(self, args):
        self.probeTool = self.evalIntArg(args[1])

    def setLevel(self, args):
        self.probeData = args[1]
        self.level = True

    def remove(self, args):
        expr = r"^\w+\s+(.*)"
        m = re.match(expr, args[0])
        if m:
            files = glob.glob(os.path.join(self.dirPath, m.group(1)))
            for f in files:
                dprt("remove %s" % (f,))
                os.remove(f)

    def runCmd(self, args):
        currentDir = os.getcwd()
        dprt("currentDir %s" % (currentDir,))
        if len(self.dirPath) != 0:
            dprt("dirPath %s" % (self.dirPath,))
            dflush()
            os.chdir(self.dirPath)
        cmd = ["bash", "-c",]
        script = ""
        for i in range(1, len(args)):
            script += args[i] + " "
        cmd.append(script)
        try:
            result = subprocess.check_output(cmd)
            dprt("%s" % (result,), end="")
        except subprocess.CalledProcessError as e:
            ePrint("return code %d\n%s\n%s" % (e.returncode, e.cmd, e.output))
        os.chdir(currentDir)

    def runScript(self, args):
        currentDir = os.getcwd()
        if len(self.dirPath) != 0:
            dprt("dirPath %s" % (self.dirPath,))
            dflush()
            os.chdir(self.dirPath)
        if os.path.isfile(args[1]):
            cmd = ["bash", "-c",]
            script = ""
            for i in range(1, len(args)):
                script += args[i] + " "
            cmd.append(script)
            try:
                result = subprocess.check_output(cmd)
                dflush()
                dprt("%s" % (result,), end="")
            except subprocess.CalledProcessError as e:
                ePrint("return code %d\n%s\n%s" % \
                       (e.returncode, e.cmd, e.output))
        os.chdir(currentDir)

    def nextOVal(self):
        val = self.oVal
        self.oVal += 10
        return(val)

    def pushOVal(self, oVal):
        self.oValStack.append(oVal)

    def popOVal(self):
        return(self.oValStack.pop())

    def curOVal(self):
        return(self.oValStack[-1])

    def repeat(self, args):
        self.ncInit()
        mill = self.mill
        mill.blankLine()
        mill.write("#<count> = %d\n" % self.evalIntArg(args[1]))
        oVal = self.nextOVal()
        self.pushOVal(oVal)
        mill.write("o%d while [#<count> gt 0]\n" % (oVal))
        mill.blankLine()

    def repeatCheck(self, args):
        mill = self.mill
        mill.blankLine()
        mill.safeZ()
        mill.blankLine()
        oVal = self.nextOVal()
        rptOVal = self.curOVal()
        # mill.write("o%d if [#<count> gt 0]\n" % (oVal))
        mill.setSpeed(0)
        mill.blankLine()
        mill.write("#<count> = [#<count> - 1]\n")
        mill.write("o%d if [#<count> le 0]\n" % (oVal))
        mill.write(" o%d break\n" % (rptOVal))
        mill.write("o%d endif\n" % (oVal))
        mill.blankLine()
        mill.pause()
        mill.setSpeed(cfg.speed)
        mill.blankLine()

    def endRepeat(self, args):
        mill = self.mill
        # mill.blankLine()
        # mill.safeZ()
        # mill.blankLine()
        # mill.write("#<count> = [#<count> - 1]\n")
        # oVal = self.nextOVal()
        # rptOVal = self.popOVal()
        # mill.write("o%d if [#<count> gt 0]\n" % (oVal))
        # mill.setSpeed(0)
        # mill.pause()
        # mill.setSpeed(cfg.speed)
        # mill.write("o%d endif\n" % (oVal))
        mill.blankLine()
        mill.safeZ()
        mill.blankLine()
        oVal = self.nextOVal()
        rptOVal = self.curOVal()
        # mill.write("o%d if [#<count> gt 0]\n" % (oVal))
        mill.setSpeed(0)
        mill.blankLine()
        mill.write("#<count> = [#<count> - 1]\n")
        mill.write("o%d if [#<count> le 0]\n" % (oVal))
        mill.write(" o%d break\n" % (rptOVal))
        mill.write("o%d endif\n" % (oVal))
        mill.blankLine()
        mill.pause()
        mill.setSpeed(cfg.speed)
        mill.write("o%d endwhile\n" % (rptOVal))
        mill.blankLine()

    def component(self, args):
        # exp = r"^\w+\s+(\*|\d+)\s+(.*)$"
        exp = r"^\**\w+\s+(\*|[\d\.]+)\s+-?\s*([\w \.-]*)\s*,?\s*(.*)$"
        match = re.match(exp, args[0])
        if match is not None:
            result = match.groups()
            self.compNumber = None
            self.compComment = ""
            if len(result) >= 1:
                self.compNumber = match.group(1)
                if self.compNumber == '*':
                    self.compNumber = None
                if len(result) >= 2:
                    self.compComment = " - " + match.group(2)
                self.cmdDisable &= ~COMPONENT_DISABLE
                if len(result) >= 3:
                    val = match.group(3)
                    if len(val) > 0:
                        if not self.evalBoolArg(val):
                            self.cmdDisable |= COMPONENT_DISABLE

    def operation(self, args):
        # exp = r"^\w+\s+(\*|[\d\.]+)\s+(.*)$"
        exp = r"^\+*\w+\s+(\*|[\d\.]+)\s+-?\s*([/\w \.-]*)\s*,?\s*(.*)$"
        match = re.match(exp, args[0])
        if match is not None:
            result = match.groups()
            self.opNumber = None
            self.opComment = None
            if len(result) >= 1:
                self.opNumber = match.group(1)
                if self.opNumber == '*':
                    self.opNumber = None
                if len(result) >= 2:
                    self.opComment = " - " + match.group(2)
                self.cmdDisable &= ~OPERATION_DISABLE
                if len(result) >= 3:
                    val = match.group(3)
                    if len(val) > 0:
                        if not self.evalBoolArg(val):
                            self.cmdDisable |= OPERATION_DISABLE

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
        # absDepth, cfg, cfgDepth, closed, currentDepth, depth, depthPass,
        # done, finalPass, last, lastDepth, lastRamp, mill, millRamp,
        # passCount, passLoc, passNum, ramp, rampAngle, rampClean,
        # rampDepth, rampDist, rampPass, tab, tabDepth, tabNum, tabPass,
        # tabPos, tabWidth, tabs, tanRampAngle, totalLength

    def config(self, cfg=None):
        if cfg is None:
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
        self.lastRamp = 0.0
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
            passes = int(floor(tmp))
        else:
            passes = int(ceil(tmp))
        self.passCount = passes

        if self.cfg.evenDepth:
            self.depthPass = self.absDepth / passes

        dprt("passCount %d cfgDepth %6.4f depth %6.4f " \
              "depthPass %6.4f finalPass %6.4f" % \
              (self.passCount, self.cfgDepth, self.depth, \
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

        self.mill.blankLine()
        self.mill.write("(pass %2d depth %7.4f" % \
                        (self.passNum, self.currentDepth))

        dprt("passNum %d lastDepth %6.4f currentDepth %6.4f" % \
              (self.passNum, self.lastDepth, self.currentDepth))

    def calcPassRamp(self):     # ramp calculations for pass
        if self.tab:            # if tab pass
            return
        # if self.closed and self.rampAngle != 0.0: # if ramp configured
        # self.lastRamp = 0.0
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

            self.mill.write(" passDepth %7.4f rampDist %6.4f " \
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
            l.prt()
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
                # for (j, p) in enumerate(tabPoints)
                for p in tabPoints:
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
        dprt("%d %s " % (self.passCount, str(self.ramp)[0]), end='')
        l.prt()
        # dprt("millSeg p %7.4f, %7.4f %s" % (l.p0[0], l.p0[1], comment))
        l.mill(self.mill, zEnd, comment)
        self.passLoc += l.length

    def millPath(self, path, tabPoints=None, closed=True, minDist=True):
        cfg = self.cfg
        if not cfg.output:
            return
        dprt("millPath")
        self.init(closed)

        dprt("combine arcs")
        path0 = combineArcs(path)

        mill = self.mill
        if minDist:
            if closed:
                path0 = rotateMinDist(mill.last, path0)
            else:
                if xyDist(mill.last, path0[-1].p0) < \
                   xyDist(mill.last, path0[0].p0):
                    path0 = reverseSeg(path0)

        mill.write("(endMillSize %5.3f finishAllowance %5.3f)\n" % \
                   (cfg.endMillSize, cfg.finishAllowance))
        for l in path0:
            mill.write("(")
            l.prt(mill, ")\n")
        mill.blankLine()

        self.calcTabPos(path0, tabPoints)

        self.totalLength = pathLength(path0)
        if True:
            draw = cfg.draw
            (x, y) = path0[0].p0
            d = 0.050
            last = draw.last
            draw.move((x - d, y - d))
            l = draw.lDebug
            draw.line((x, y), layer=l)
            draw.line((x + d, y - d), layer=l)
            direction = pathDir(path0)
            draw.add(dxf.text("start %s" % (oStr(direction)), \
                              (x, y - d), 0.010, \
                              alignpoint=(x, y - d), halign=CENTER, \
                              layer = draw.lText))
            draw.move(last)

        rampLine = self.rampSetup()
        self.passSetup()

        if cfg.pauseCenter and len(path0) == 1:
            mill.move(path0[0].p0)
        else:
            #mill.safeZ()
            l = path0[0]
            p = l.p0
            if l.type == ARC:
                dist = xyDist(l.c, mill.last)
                if dist > (l.r + cfg.endMillSize / 2.0):
                    mill.safeZ()
                    # mill.retract(comment="r1")
                else:
                    mill.zTop("mp 1")
            else:
                dist = xyDist(p, mill.last)
                # dprt("millPath dist %7.4f last (%7.4f, %7.4f) "\
                #      "p (%7.4f, %7.4f)" %\
                #      (dist, mill.last[0], mill.last[1], p[0], p[1]))
                if dist > cfg.endMillSize:
                    mill.retract(comment="r2")
                else:
                    mill.zTop("mp 2")
            mill.move(p)
            if cfg.pause:
                mill.moveZ(cfg.pauseHeight)
                mill.pause()
            mill.zTop("mp 3")

        while True:
            if self.passCount == 0:
                break

            p = path0[0].p0
            dist = xyDist(p, mill.last)
            if dist > MIN_DIST:
                if dist > cfg.endMillSize:
                    mill.retract(comment="r3")
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
                mill.write(" tabs %d w %5.3f d %5.3f r %5.3f" % \
                          (self.tabs, self.tabWidth, \
                           self.tabDepth, self.tabRamp))
            mill.write(")\n")

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
        mill.blankLine()
        # for var, _ in inspect.getmembers(self):
        #     if var.startswith("__"):
        #         continue
        #     tmp = "callable(self." + var + ")"
        #     if eval(tmp):
        #         continue
        #     print(var)
        # pass

class Point():
    def __init__(self, p, l, end, index):
        self.index = index
        self.p = p
        self.ends = 0
        self.l = [None, None]
        self.lIndex = [-1, -1]
        self.lEnd = [0, 0]
        self.add(l, end)

    def add(self, l, end):
        i = self.ends
        if i < 2 and self.l[i] is None:
            self.l[i] = l
            self.lIndex[i] = l.index
            self.lEnd[i] = end
            self.ends += 1
        else:
            dprt("err, end %d pt %d" % (end, self.index))
            self.prt()

    def prt(self):
        dprt("point %2d ends %d (%7.4f %7.4f) "\
             "connects line %2d:%d to %2d:%d" % \
             (self.index, self.ends, self.p[0], self.p[1], \
              self.lIndex[0], self.lEnd[0], \
              self.lIndex[1], self.lEnd[1]))

class LinePoints():
    def __init__(self, l):
        self.p = [None, None]
        self.pIndex = [-1, -1]
        self.l = l
        self.index = l.index

    def add(self, p, end):
        self.p[end] = p
        self.pIndex[end] = p.index

    def next(self, dbg=False):
        if self.p[0].l[1] is None:
            self.swap()
        if dbg:
            self.dbgPrt()
        return(self.p)

    def dbgPrt(self):
        (p0, p1) = self.p
        dprt("line %2d from p0 %2d l0 %2d l1 %2d " \
             "to p1 %2d l0 %2d l1 %2d" % \
             (self.index, p0.index, p0.lIndex[0], p0.lIndex[1], \
              p1.index, p1.lIndex[0], p1.lIndex[1]))

    def swap(self):
        self.l.swap()
        self.p = [self.p[1], self.p[0]]
        self.pIndex = [self.pIndex[1], self.pIndex[0]]
        return(self.p)

    def prt(self):
        dprt("line %2d is from point %2d to point %2d" % \
             (self.index, self.pIndex[0], self.pIndex[1]))

class Dxf():
    def __init__(self, cfg):
        self.cfg = cfg
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
        self.mXMin = MAX_VALUE
        self.mXMax = MIN_VALUE
        self.mYMin = MAX_VALUE
        self.mYMax = MIN_VALUE
        self.fXMin = MAX_VALUE
        self.fXMax = MIN_VALUE
        self.fYMin = MAX_VALUE
        self.fYMax = MIN_VALUE

    def open(self, inFile, ref):
        self.inFile = inFile
        self.dwg = dwg = ReadFile(inFile)
        self.modelspace = modelspace = dwg.modelspace()
        cfg = self.cfg
        xMax = yMax =  MIN_VALUE
        xMin = yMin = MAX_VALUE
        self.material = []
        mXMax = mYMax = MIN_VALUE
        mXMin = mYMin = MAX_VALUE
        self.fixture = []
        fXMax = fYMax = MIN_VALUE
        fXMin = fYMin = MAX_VALUE
        checkLayers = len(cfg.layers) != 0
        for e in modelspace:
            dxfType = e.dxftype()
            layer = e.get_dxf_attrib("layer")
            if layer == cfg.materialLayer:
                pass
            elif checkLayers:
                if not layer in cfg.layers:
                    continue
            if dxfType == 'LINE':
                # (x0, y0) = e.get_dxf_attrib("start")[:2]

                x0 = e.get_dxf_attrib("start")[0]
                y0 = e.get_dxf_attrib("start")[1]
                x1 = e.get_dxf_attrib("end")[0]
                y1 = e.get_dxf_attrib("end")[1]
                if layer == cfg.fixtureLayer:
                    dprt("f (x0 %7.4f y0 % 7.4f) (x1 %7.4f y1 % 7.4f)" % \
                         (x0, y0, x1, y1))
                    self.fixture.append(((x0, y0), (x1, y1)))
                    fXMax = max(fXMax, x0, x1)
                    fXMin = min(fXMin, x0, x1)
                    fYMax = max(fYMax, y0, y1)
                    fYMin = min(fYMin, y0, y1)
                    continue
                if layer == cfg.materialLayer:
                    dprt("m (x0 %7.4f y0 % 7.4f) (x1 %7.4f y1 % 7.4f)" % \
                         (x0, y0, x1, y1))
                    self.material.append(((x0, y0), (x1, y1)))
                    mXMax = max(mXMax, x0, x1)
                    mXMin = min(mXMin, x0, x1)
                    mYMax = max(mYMax, y0, y1)
                    mYMin = min(mYMin, y0, y1)
                xMax = max(xMax, x0, x1)
                xMin = min(xMin, x0, x1)
                yMax = max(yMax, y0, y1)
                yMin = min(yMin, y0, y1)
            elif dxfType == 'CIRCLE':
                if layer == cfg.fixtureLayer:
                    continue
                xCen = e.get_dxf_attrib("center")[0]
                yCen = e.get_dxf_attrib("center")[1]
                radius = e.get_dxf_attrib("radius")
                xMax = max(xMax, xCen + radius)
                xMin = min(xMin, xCen - radius)
                yMax = max(yMax, yCen + radius)
                yMin = min(yMin, yCen - radius)
            elif dxfType == 'ARC':
                xCen = e.get_dxf_attrib("center")[0]
                yCen = e.get_dxf_attrib("center")[1]
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
            elif dxfType == 'LWPOLYLINE':
                # for (x0, y0) in e.get_rstrip_points():
                for (x0, y0) in e.vertices():
                    xMax = max(x0, xMax)
                    xMin = min(x0, xMin)
                    yMax = max(y0, yMax)
                    yMin = min(y0, yMin)

        if  ref == REF_OVERALL:
            self.xMin = xMin
            self.xMax = xMax
            self.yMin = yMin
            self.yMax = yMax
        elif ref == REF_MATERIAL:
            if len(self.material) != 0:
                self.mXMin = mXMin
                self.mXMax = mXMax
                self.mYMin = mYMin
                self.mYMax = mYMax
            else:
                ePrint("material layer not defined")
                self.error = True
        elif ref == REF_FIXTURE:
            if len(self.fixture) != 0:
                self.fXMin = fXMin
                self.fXMax = fXMax
                self.fYMin = fYMin
                self.fYMax = fYMax
            else:
                ePrint("fixture layer not defined")
                self.error = True

        dprt("xMin %f yMin %f" % (xMin, yMin))
        dprt("xMax %f yMax %f" % (xMax, yMax))
        self.xSize = xMax - xMin
        self.ySize = yMax - yMin
        dprt("xSize %5.3f ySize %6.3f" % (self.xSize, self.ySize))

    def setOrientation(self, orientation=0, layer=None):
        dprt("\nmin (x %7.4f, y %7.4f) max (x %7.4f, y %7.4f)\n" % \
              (self.xMin, self.yMin, self.xMax, self.yMax))

        print("material\n")
        for (start, end) in self.material:
            dprt("(%7.4f, y %7.4f) (%7.4f, y %7.4f))" % \
                (start[0], start[1], end[0], end[1]))
        print()

        self.xMul = 1
        self.yMul = 1
        if len(self.fixture) != 0:
            (xMin, yMin) = (self.fXMin, self.fYMin)
            (xMax, yMax) = (self.fXMax, self.fYMax)
        else:
            (xMin, yMin) = (self.xMin, self.yMin)
            (xMax, yMax) = (self.xMax, self.yMax)
        if orientation == O_UPPER_LEFT:
            self.xOffset = -xMin
            self.yOffset = -yMax
        elif orientation == O_LOWER_LEFT:
            self.xOffset = -xMin
            self.yOffset = -yMin
        elif orientation == O_UPPER_RIGHT:
            self.xOffset = -xMax
            self.yOffset = -yMax
        elif orientation == O_LOWER_RIGHT:
            self.xOffset = -xMax
            self.yOffset = -yMin
        elif orientation == O_CENTER:
            self.xOffset = -(xMin + (xMax - xMin) / 2)
            self.yOffset = -(yMin + (yMax - yMin) / 2)
        elif orientation == O_POINT:
            if layer is not None:
                for e in self.modelspace:
                    if layer != e.get_dxf_attrib("layer"):
                        continue
                    if e.dxftype() == 'CIRCLE' or e.dxftype() == 'ARC':
                        x = e.get_dxf_attrib("center")[0]
                        y = e.get_dxf_attrib("center")[1]
                        self.xOffset = -x
                        self.yOffset = -y

        self.xMin += self.xOffset
        self.xMax += self.xOffset
        self.yMin += self.yOffset
        self.yMax += self.yOffset

        dprt("%d xOffset %7.4f yOffset %7.4f" % \
               (orientation, self.xOffset, self.yOffset))

    def fix(self, point):
        (x, y) = point
        # x = int(x * 10000) / 10000.0
        # y = int(y * 10000) / 10000.0
        return(newPoint((self.xMul * x + self.xOffset, \
                         self.yMul * y + self.yOffset)))

    def scale(self, point, scale=1):
        (x, y) = point
        return((int(x * scale), int(y * scale)))

    def getPoints(self, layer):
        points = []
        for e in self.modelspace:
            # dprt("layer %s" % (e.get_dxf_attrib("layer")))
            if layer != e.get_dxf_attrib("layer"):
                continue
            dxfType = e.dxftype()
            if dxfType == 'CIRCLE':
                xCen = e.get_dxf_attrib("center")[0]
                yCen = e.get_dxf_attrib("center")[1]
                points.append((xCen, yCen))
        return(points)

    def getLabel(self, layer):
        points = []
        for e in self.modelspace:
            # dprt("layer %s" % (e.get_dxf_attrib("layer")))
            # if layer != e.get_dxf_attrib("layer"):
            #     continue
            dxfType = e.dxftype()
            if dxfType == 'MTEXT':
                tmp = e.text
                if layer in tmp:
                    x = e.get_dxf_attrib("insert")[0]
                    y = e.get_dxf_attrib("insert")[1]
                    (xCen, yCen) = self.fix((x, y))
                    points.append((xCen, yCen))
        return(points)

    def getHoles(self, layer, holeMin, holeMax, dbg=False):
        if dbg:
            dprt("getHoles holeMin %6.4f holeMax %6.4f" % (holeMin, holeMax))
        cfg = self.cfg
        size = None
        maxSize = None
        holes = []
        if size is not None:
            if maxSize is None:
                maxSize = size + MIN_DIST
                minSize = size - MIN_DIST
            else:
                minSize = size
        for e in self.modelspace:
            dxfType = e.dxftype()
            if dbg:
                dprt("layer %s type %s" % \
                     (e.get_dxf_attrib("layer"), type))
            if (layer is None) or (layer == e.get_dxf_attrib("layer")):
                if dxfType == 'CIRCLE' or dxfType == 'ARC':
                    xCen = e.get_dxf_attrib("center")[0]
                    yCen = e.get_dxf_attrib("center")[1]
                    p = self.fix((xCen, yCen))
                    radius = e.get_dxf_attrib("radius")
                    if dxfType == 'ARC':
                        a0 = e.get_dxf_attrib("start_angle")
                        a1 = e.get_dxf_attrib("end_angle")
                        # print("a0 %6.2f a1 %6.2f r %6.4f" % (a0, a1, radius))
                        continue
                    drillSize = radius * 2.0
                    if dbg:
                        dprt("diameter %6.4f x %7.4f y %7.4f" % \
                             (drillSize, p[0], p[1]))
                    if drillSize < holeMin or drillSize > holeMax:
                        continue
                    found = False
                    for h in holes:
                        if abs(drillSize - h.size) < MIN_DIST:
                            h.addLoc(p)
                            found = True
                            break
                    if not found: # if holeSize not found
                        d = Drill(drillSize)
                        holes.append(d)
                        d.addLoc(p)
        if dbg:
            for d in holes:
                dprt("size %7.4f holes %d" % (d.size, len(d.loc)))
        return(holes)

    def getCircles(self, layer=None):
        circles = []
        for e in self.modelspace:
            # dprt("layer %s" % (e.get_dxf_attrib("layer")))
            if (layer is None) or (layer == e.get_dxf_attrib("layer")):
                dxfType = e.dxftype()
                if dxfType == 'CIRCLE' or dxfType == 'ARC':
                    xCen = e.get_dxf_attrib("center")[0]
                    yCen = e.get_dxf_attrib("center")[1]
                    p = self.fix((xCen, yCen))
                    radius = e.get_dxf_attrib("radius")
                    circles.append((p, 2*radius))
        return(circles)

    def getObjects(self, layer=None):
        objects = []
        linNum = 0
        for e in self.modelspace:
            # dprt("layer %s" % (e.get_dxf_attrib("layer")))
            if layer != e.get_dxf_attrib("layer"):
                continue
            dxfType = e.dxftype()
            if dxfType == 'LINE':
                p0 = self.fix((e.get_dxf_attrib("start")[0], \
                               e.get_dxf_attrib("start")[1]))
                p1 = self.fix((e.get_dxf_attrib("end")[0], \
                               e.get_dxf_attrib("end")[1]))
                l0 = Line(p0, p1, linNum, e)
            elif dxfType == 'ARC':
                xCen = e.get_dxf_attrib("center")[0]
                yCen = e.get_dxf_attrib("center")[1]
                center = self.fix((xCen, yCen))
                radius = e.get_dxf_attrib("radius")
                startAngle = e.get_dxf_attrib("start_angle")
                endAngle = e.get_dxf_attrib("end_angle")
                l0 = Arc(center, radius, startAngle, endAngle, \
                         linNum, e)
            elif dxfType == 'CIRCLE':
                xCen = e.get_dxf_attrib("center")[0]
                yCen = e.get_dxf_attrib("center")[1]
                p = self.fix((xCen, yCen))
                radius = e.get_dxf_attrib("radius")
                l0 = Arc(p, radius, 0.0, 360.0, linNum, e)
                linNum += 1
            elif dxfType == 'LWPOLYLINE':
                prev = None
                vertices = list(e.vertices())
                if e.closed:
                    prev = vertices[-1]
                # for p in e.get_rstrip_points():
                for p in vertices:
                    if prev is not None:
                        l0 = Line(self.fix(prev), self.fix(p), linNum, e)
                        objects.append(l0)
                        linNum += 1
                    prev = p
                continue
            else:
                continue
            objects.append(l0)
            linNum += 1
        return(objects)

    def getPath(self, layer, circle=False, dbg=True, rand=False):
        if dbg:
            dprt("getPath %s" % (layer))
        # find everything that matches layer
        linNum = 0
        entities = []
        for e in self.modelspace:
            dxfType = e.dxftype()
            if True and dbg:
                dprt("dxfType %-10s layer %s" % \
                     (dxfType, e.get_dxf_attrib("layer")))
            if layer != e.get_dxf_attrib("layer"):
                continue
            if dxfType == 'LINE':
                p0 = self.fix((e.get_dxf_attrib("start")[0], \
                               e.get_dxf_attrib("start")[1]))
                p1 = self.fix((e.get_dxf_attrib("end")[0], \
                               e.get_dxf_attrib("end")[1]))
                l0 = Line(p0, p1, linNum, e)
            elif dxfType == 'ARC':
                xCen = e.get_dxf_attrib("center")[0]
                yCen = e.get_dxf_attrib("center")[1]
                center = self.fix((xCen, yCen))
                radius = e.get_dxf_attrib("radius")
                startAngle = e.get_dxf_attrib("start_angle")
                endAngle = e.get_dxf_attrib("end_angle")
                if (abs(startAngle - 0) < MIN_DIST) and \
                   (abs(endAngle - 360) < MIN_DIST) and \
                   not circle:
                    continue
                l0 = Arc(center, radius, startAngle, endAngle, \
                         linNum, e)
            elif dxfType == 'CIRCLE':
                if circle:
                    xCen = e.get_dxf_attrib("center")[0]
                    yCen = e.get_dxf_attrib("center")[1]
                    p = self.fix((xCen, yCen))
                    radius = e.get_dxf_attrib("radius")
                    l0 = Arc(p, radius, 0.0, 360.0, linNum, e)
                else:
                    continue
            elif dxfType == 'LWPOLYLINE':
                prev = None
                vertices = list(e.vertices())
                if e.closed:
                    prev = vertices[-1]
                # for p in e.get_rstrip_points():
                for p in vertices:
                    if prev is not None:
                        l0 = Line(self.fix(prev), self.fix(p), linNum, e)
                        entities.append(l0)
                        linNum += 1
                    prev = p
                continue
            else:
                continue
            if dbg:
                l0.prt()
            entities.append(l0)
            linNum += 1
        if dbg:
            dprt()

        # remove duplicates

        i = 0
        remove = False
        while i < len(entities):
            l0 = entities[i]
            j = i + 1
            while j < len(entities):
                l1 = entities[j]
                if (l0.type == l1.type) and \
                   (xyDist(l0.p0, l1.p0) < MIN_DIST) and \
                   (xyDist(l0.p1, l1.p1) < MIN_DIST):
                    if dbg:
                        dprt("rem %d" % (l1.index))
                        l1.prt()
                    entities.pop(j)
                    remove = True
                    continue
                j += 1
            i += 1

        if remove:
            for (i, l0) in enumerate(entities):
                l0.index = i

        if dbg and rand:
            dprt("testing randomize list")
            random.shuffle(entities)
            for (i, l0) in enumerate(entities):
                l0.index = i
                l0.prt()
            dprt()

        return(self.connect1(entities, dbg))

    def connect0(self, entities, dbg=False):
        for l0 in entities:
            l0.prt()
        dprt()

        segments = []
        segCount = 0
        for l0 in entities:
            l0.prt()
            found = False
            segNum = []
            for (i, seg) in enumerate(segments): # i is segment number
                if dbg:
                    dprt("check seg %d" % i)
                j = 0
                lineCount = len(seg)
                while j < lineCount:
                    l1 = seg[j]
                    l1.prt()
                    for p0 in (l0.p0, l0.p1):
                        for p1 in (l1.p0, l1.p1):
                            if xyDist(p0, p1) <= MIN_DIST:
                                if dbg:
                                    dprt("match seg %d ind %d l0 %d l1 %d" % \
                                         (i, j, l0.index, l1.index))
                                    dflush()
                                if not i in segNum:
                                    segNum.append(i)
                                    if dbg:
                                        dprt("add %d to seg %d\n" % \
                                             (l0.index, l1.index))
                                if not found:
                                    found = True
                                    seg.append(l0)
                                    if dbg:
                                        dprt("add %d to seg %d\n" % \
                                             (l0.index, i))
                                break
                    j += 1
            if not found:
                seg = []
                seg.append(l0)
                segments.append(seg)
                if dbg:
                    dprt("add %d to new segment %d\n" % (l0.index, segCount))
                segCount += 1
            else:
                if len(segNum) > 1:
                    if dbg:
                        dprt(segNum)
                        dflush()
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
            if dbg:
                for (p, count) in points:
                    dprt("%7.4f %7.4f %d" % (p[0], p[1], count))
                dprt()
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
                        if dbg:
                            dprt("swap %d %s" % \
                                 (l0.index, ('line', 'arc')[l0.type]))
                        l0.swap()
                        newSeg.append(l0)
                        break
                    i += 1
                if i < len(seg):
                    seg.pop(i)
                else:
                    if dbg:
                        dprt("segment out of range %d" % (i))
            segments[j] = newSeg
            j += 1
            if dbg:
                dprt()

        if dbg:
            for (i, seg) in enumerate(segments):
                dprt("seg %d" % (i))
                for l0 in seg:
                    l0.prt()
                dprt()
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

    def connect1(self, entities, dbg=False):
        if dbg:
            for l0 in entities:
                l0.prt()
            dprt()

        points = []
        linePoints = []
        index = 0
        for l0 in entities:
            if dbg:
                l0.prt()
            lPt = LinePoints(l0)
            linePoints.append(lPt)
            for (end, pl) in enumerate((l0.p0, l0.p1)):
                found = False
                for pt in points:
                    if xyDist(pl, pt.p) < MIN_DIST:
                        if dbg:
                            dprt("fnd pt %2d (%8.4f %8.4f) for line %2d:%d" % \
                                 (pt.index, pl[0], pl[1], l0.index, end))
                        found = True
                        pt.add(l0, end)
                        lPt.add(pt, end)
                        break
                if not found:
                    if dbg:
                        dprt("new pt %2d (%8.4f %8.4f) for line %2d:%d" % \
                             (index, pl[0], pl[1], l0.index, end))
                    pt = Point(pl, l0, end, index)
                    points.append(pt)
                    lPt.add(pt, end)
                    index += 1
            if dbg:
                dprt()
                dflush()

        if dbg:
            for l0 in entities:
                l0.prt()
            dprt()

            for p in points:
                p.prt()
            dprt()

            for lPt in linePoints:
                lPt.prt()
            dprt()

        segments = []

        for index in range(len(entities)):
            if dbg:
                print("index %d" % (index,))
            l0 = entities[index] # take line off list
            if l0 is not None:   # if entry
                start = index = l0.index # save start index
                lastPoint = linePoints[index].p[0]
                seg = []         # initialize segment list
                while True:
                    entities[index] = None  # clear entry
                    seg.append(l0)          # append to segment list
                    (p0, p1) = linePoints[index].next(dbg) # get next point
                    if dbg:
                        dprt("line %2d lastPoint %2d p0 %2d p1 %2d" % \
                             (index, lastPoint.index, p0.index, p1.index))
                        l0.prt()

                    if p1.ends == 1:         # if end of of line
                        index = seg[0].index # get index of fisrt
                        if not dbg:
                            (p0, p1) = linePoints[index].p
                        else:
                            lPt = linePoints[index] # look up points
                            lPt.prt()
                            (p0, p1) = lPt.p
                            p0.prt()
                            p1.prt()

                        if p0.ends == 1: # if both are end of line
                            break        # done

                        for i in range(len(seg)-1, -1, -1):
                            l0 = seg.pop(i)
                            linePoints[l0.index].swap()
                            seg.append(l0)

                        index = seg[-1].index
                        p = p0
                    else:
                        p = p0 if p0 is not lastPoint else p1

                    if p.lIndex[0] != index: # if l0 not the same line
                        (l0, end) = (p.l[0], p.lEnd[0]) # use l0 for next
                    else:
                        (l0, end) = (p.l[1], p.lEnd[1]) # use l1 for next

                    index = l0.index   # get index
                    if end != 0:       # if next end to end 0
                        linePoints[index].swap() # swap ends

                    if index == start: # if back at start
                        break          # done
                    lastPoint = p      # set new last point
                    if dbg:
                        dprt()
                segments.append(seg)   # save segment
                if dbg:
                    dprt()
                    for l0 in seg:
                        linePoints[l0.index].prt()
                        l0.prt()
                    dprt()
        if dbg:
            dprt()
            dflush()

        return(segments)

    def getLines(self, layer, uniCode=False):
        line = []
        lineNum = 0
        lineType = 'LINE'
        if uniCode:
            layer = layer.decode('utf-8')
            lineType = lineType.decode('utf-8')
        for e in self.modelspace:
            dxfType = e.dxftype()
            if dxfType == lineType and e.get_dxf_attrib("layer") == layer:
                p0 = self.fix((e.get_dxf_attrib("start")[0], \
                               e.get_dxf_attrib("start")[1]))
                p1 = self.fix((e.get_dxf_attrib("end")[0], \
                               e.get_dxf_attrib("end")[1]))
                l0 = Line(p0, p1, lineNum, e)
                lineNum += 1
                line.append(l0)
        return line

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
        # self.Maximize(True)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.InitUI()

    def onClose(self, event):
        self.Destroy()

        # colors = wx.lib.colourdb.getColourList()
        # for line in colors:
        #     print line
        # dflush()

    def InitUI(self):
        panel = wx.Panel(self)

        self.sizerV = sizerV = wx.BoxSizer(wx.VERTICAL)

        panel.SetSizer(sizerV)

        sizerH = wx.BoxSizer(wx.HORIZONTAL)

        txt = wx.StaticText(panel, -1, "Test")
        sizerH.Add(txt, flag=wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=2)

        sizerV.Add(sizerH, flag=wx.CENTER|wx.ALL, border=2)

        self.sizerV.Fit(self)

#         global cfg, inFile
#         self.zoom = False
#         self.left = None
#         self.Bind(wx.EVT_PAINT, self.OnPaint)
#         self.Centre()
#         cfg.open(inFile)
#         self.Bind(wx.EVT_LEFT_UP, self.OnMouseEvent)
        self.Show(True)

#     def OnMouseEvent(self, e):
#         x = e.GetX()
#         # if not self.zoom:
#         #     self.zoom = True
#         #     self.offset = x > self.tc.xBase
#         # else:
#         #     self.zoom = False
#         #     self.offset = False
#         # self.tc.setZoomOffset(self.zoom, self.offset)
#         self.Refresh()

#     def OnPaint(self, e):
#         dc = wx.PaintDC(self)
#         dc.SetMapMode(wx.MM_TEXT)
#         brush = wx.Brush("white")
#         dc.SetBackground(brush)
#         dc.Clear()
#         # self.tc.calcScale()
#         # self.tc.draw(dc)

#         # color = wx.Colour(255,0,0)
#         # dc.SetTextForeground(color)
#         # dc.DrawText("Hello wxPython",10,10)
#         # dc.DrawLine(10,10, 100,10)

if len(sys.argv) <= 1:
    exit()

cfg = Config()
cfg.parseCmdLine()

if cfg.gui:

    if False:
        app = wx.App()
        window = wx.Frame(None, title = "wxPython Frame", size = (300,200))
        panel = wx.Panel(window)
        label = wx.StaticText(panel, label = "Hello World", pos = (100,50))
        window.Show(True)
        app.MainLoop()
    else:
        ex = wx.App()
        MainFrame(None,'Drawing demo')
        ex.MainLoop()
else:
    cfg.open()
