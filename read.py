#!/cygdrive/c/Python310/Python.exe

import sys
import re
from collections import namedtuple
from math import hypot
from operator import itemgetter
from enum import Enum
from ezdxf.enums import TextEntityAlignment

from dbgprt import dprt, dprtSet

FUNC = 0

END_SEC      = "ENDSEC"

BLOCK_RECORD = "BLOCK_RECORD"
END_TAB      = "ENDTAB"

BLOCK        = "BLOCK"
END_BLK      = "ENDBLK"

DIMENSION    = "DIMENSION"
M_TEXT       = "MTEXT"
LINE         = "LINE"

READ_DIM =   "ReadDim"

# data types
STRING   = 1
NAME     = 2
HANDLE   = 5
LAYER    = 8
X_LOC    = 10
X_END    = 11
X_DEF    = 13
Y_LOC    = 20
Y_END    = 21
Y_DEF    = 23
DIM_TYPE = 70
REF      = 330

DIM_MASK = 0x7
ORDINATE = 6

DimResult = namedtuple('DimResult', ['val', 'text', 'name'])

class Func(Enum):
    NONE         = 0
    DIM          = 1
    TXT          = 2
    LINE         = 3
    BLOCK_RECORD = 4
    BLOCK        = 5
    END_BLOCK    = 6

class ReadDxfDim():
    def __init__(self, draw=None):
        self.draw = draw
        self.line = 0

        self.tableFunc = Func.NONE
        self.block = None
        self.dimTable = {}
        self.handle = {}

        self.blockFunc = Func.NONE
        self.blockDim = {}

        self.blockList = None
        self.blockElement = None

        self.xMin = self.yMin = 0

        self.txtPath = []
        self.pathLookup = {}

    def getPathLookup(self):
        return self.pathLookup

    def readCodeVal(self):
        code = self.dxfFile.readline().strip()
        self.line += 1
        curLine = self.line

        if len(code) == 0:
            return None
        try:
            intCode = int(code)
            # dprt("*", code)
        except ValueError:
            dprt("value error", code)
            return None

        val = self.dxfFile.readline().strip()
        self.line += 1
        return (curLine, intCode, val)

    def readDimensions(self, fName, xOffset=None, yOffset=None, dbg=False):
        self.xOffset = xOffset
        self.yOffset = yOffset

        self.dxfFile = open(fName, 'r')

        while True:
            result = self.readCodeVal()
            if result is None:
                 return None

            (line, code, val) = result
            if val == "EOF":
                if dbg:
                    dprt("%5d %4d %s" % (line, code, val))
                break

            result = self.readCodeVal()
            if result is None:
                return None
            if code == 0:
                if val == "SECTION":
                    (line, code, val) = result
                    if code == 2:
                        if val == "HEADER":
                            self.readHeader(dbg=dbg)
                        elif val == "CLASSES":
                            self.readClasses(dbg=dbg)
                        elif val == "TABLES":
                            self.readTables(dbg=dbg)
                        elif val == "BLOCKS":
                            self.readBlocks(dbg=dbg)
                        elif val == "ENTITIES":
                            self.readEntities(dbg=dbg)
                        elif val == "OBJECTS":
                            self.readObjects(dbg=dbg)

        if self.xOffset is None:
            self.xOffset = -self.xMin
        if self.yOffset is None:
            self.yOffset = -self.yMin

        draw = self.draw

        dbg = True
        if dbg:
            dprt("\n"
                 "xMin    %7.4f yMin    %7.4f" % (self.xMin,    self.yMin))
            dprt("xOffset %7.4f yOffset %7.4f" % (self.xOffset, self.yOffset))

        dbg = True
        if dbg:
            dprt("\n" "dimLookup %d" % (len(self.dimRec)))
        dimLookup = {}
        for dim in self.dimRec:
            # noinspection PyTypeChecker
            dim[X_LOC] = x0 = float(dim[X_LOC]) + self.xOffset
            # noinspection PyTypeChecker
            dim[X_DEF] = x1 = float(dim[X_DEF]) + self.xOffset
            # noinspection PyTypeChecker
            dim[Y_LOC] = y0 = float(dim[Y_LOC]) + self.yOffset
            # noinspection PyTypeChecker
            dim[Y_DEF] = y1 = float(dim[Y_DEF]) + self.yOffset
            dimName = dim[NAME]
            dimLookup[dimName] = dim
            if dbg:
                dprt("%3s (%7.3f %7.3f) (%7.3f %7.3f)" %
                     (dimName, x0, y0, x1, y1))
            if draw is not None:
                draw.circleDxf((x1, y1), 0.020, layer=READ_DIM)
                draw.text(dimName, (x1 + .020, y1), 0.010, layer=READ_DIM)

        dbg = True
        if dbg:
            dprt("\n" "blockList %d" % (len(self.blocks)))
        self.dimTxt = []
        for blockList in self.blocks:
            if dbg:
                dprt()
            dimName = ""
            for blockElem in blockList:
                func = blockElem[FUNC]
                if dbg:
                    dprt("%-10s" % (func), end=" ")
                if func == Func.BLOCK:
                    dimName = blockElem[NAME]
                    if dbg:
                        dprt("%2s %2s" % (dimName, blockElem[REF]))
                    if not dimName in dimLookup:
                        break
                elif func == Func.TXT:
                    blockElem[X_LOC] = x0 = float(blockElem[X_LOC]) + self.xOffset
                    blockElem[Y_LOC] = y0 = float(blockElem[Y_LOC]) + self.yOffset
                    dimTxt = blockElem[STRING]
                    self.dimTxt.append((x0, y0, dimTxt, dimName))
                    txt = ("%2s %2s (%7.3f %7.3f) %s" %
                           (dimName, blockElem[REF], x0, y0, dimTxt))
                    if dbg:
                        dprt(txt)
                    if draw is not None:
                        align = TextEntityAlignment.MIDDLE_CENTER
                        draw.text(txt, (x0, y0), 0.010, layer=READ_DIM,
                                  align=align)
                elif func == Func.LINE:
                    blockElem[X_LOC] = x0 = float(blockElem[X_LOC]) + self.xOffset
                    blockElem[X_END] = x1 = float(blockElem[X_END]) + self.xOffset
                    blockElem[Y_LOC] = y0 = float(blockElem[Y_LOC]) + self.yOffset
                    blockElem[Y_END] = y1 = float(blockElem[Y_END]) + self.yOffset
                    if dbg:
                        dprt("%2s (%7.3f %7.3f) (%7.3f %7.3f)" %
                             (blockElem[REF], x0, y0 ,x1, y1))
                    if draw is not None:
                        # draw.drawCross((x0, y0), layer=READ_DIM, label=False)
                        draw.circleDxf((x0, y0), 0.010, layer=READ_DIM)
                        draw.lineDxf((x0, y0), (x1, y1), layer=READ_DIM)

        self.dimTxt.sort(key=itemgetter(0, 1))

        if dbg:
            dprt("\n" "dimTxt %d" % (len(self.dimTxt)))
            for x, y, txt, blockName in self.dimTxt:
                dprt("%7s %7.3f %7.3f %s" % (txt, x, y, blockName))

        if dbg:
            dprt("\n" "dimNameLoc %d" % (len(self.dimName)))
        self.dimNameLoc = []
        for rec in self.dimName:
            x = float(rec[X_LOC]) + self.xOffset
            y = float(rec[Y_LOC]) + self.yOffset
            txt = rec[1]
            self.dimNameLoc.append((x, y, txt))
        self.dimNameLoc.sort(key=itemgetter(0, 1))

        for x, y, txt in self.dimNameLoc:
            if dbg:
                dprt("%-5s %7.3f %7.3f" % (txt, x, y))
            if draw is not None:
                draw.drawX((x,y), txt, layer=READ_DIM)

        dbg = False
        if dbg:
            dprt("\n" "varLookup")
        varLookup = {}
        # p0 = p1 = delta = (0, 0)
        for x0, y0, var in self.dimNameLoc:
            minDist = 9999
            # minDim = 0.0
            minIndex = 0
            dimName = ""
            dimText = ""
            # dprt("\n" "(%7.3f %7.3f) %s" % (x0, y0, var))
            for j, (x1, y1, dim, name) in enumerate(self.dimTxt):
                dx = x1 - x0
                dy = y1 - y0
                dist = hypot(dx, dy)
                # dprt("%d (%7.3f %7.3f) %s dist %7.3f " %
                #       (j, x1, y1, dim, dist))
                if dist < minDist:
                    minDist = dist
                    minIndex = j
                    dimName = name
                    dimText = dim
                    # minDim = float(dim)
                    # p0 = (x0, y0)
                    # p1 = (x1, y1)
                    # delta = (dx, dy)
            del self.dimTxt[minIndex]

            if dimName in dimLookup:
                ref = dimLookup[dimName]
                minDim = 0.0
                if var.startswith('x'):
                    minDim = ref[X_DEF]
                elif var.startswith('y'):
                    minDim = ref[Y_DEF]
                varLookup[var] = DimResult(minDim, dimText, dimName)
                if dbg:
                    dprt("%4s %2d %10.6f \"%6s\" %5.3f" %
                         (var, minIndex, minDim, dimText, minDist))
            else:
                dprt("error")

        if dbg:
            dprt("\n" "varLookup")
            for key in sorted(varLookup):
                dim, dimText, dimName = varLookup[key]
                dprt("%4s %10.6f \"%6s\" %s" % (key, dim, dimText, dimName))

        dbg = True
        dbg1 = False
        if dbg:
            dprt("\n" "tstLookup")
        tstLookup = {}
        # p0 = p1 = delta = (0, 0)
        for x0, y0, var in self.dimNameLoc:
            minDist = 9999
            blockName = ""
            blockText = ""
            minIndex = -1
            minHandle = "XX"
            minText = ""
            minBlock = ""
            if dbg:
                dprt("\n" "(%7.3f %7.3f) %s" % (x0, y0, var))
            for j, block in enumerate(self.blocks):
                for blockElement in block:
                    handle = blockElement[HANDLE]
                    if blockElement[FUNC] == Func.BLOCK:
                        blockName = blockElement[NAME]
                        if dbg1:
                            dprt("\n" "block %2s %s" % (handle, blockName))
                        if not blockName in dimLookup:
                            break
                    elif blockElement[FUNC] == Func.LINE:
                        xS = blockElement[X_LOC]
                        yS = blockElement[Y_LOC]
                        distS = hypot(xS - x0, yS - y0)
                        xE = blockElement[X_END]
                        yE = blockElement[Y_END]
                        distE = hypot(xE - x0, yE - y0)
                        if dbg1:
                            dprt("line %2s (%7.3f %7.3f) %7.3f "
                                 "(%7.3f %7.3f) %7.3f" %
                                 (handle, xS, yS, distS, xE, yE, distE))
                        dist = min(distS, distE)
                        if dist < minDist:
                            if dbg1:
                                dprt("dist %7.3f minDist %7.3f" %
                                     (dist, minDist))
                            minDist = dist
                            minHandle = handle
                            minText = blockText
                            minBlock = blockName
                            # minElement = blockElement
                            minIndex = j
                    elif blockElement[FUNC] == Func.TXT:
                        xTxt = blockElement[X_LOC]
                        yTxt = blockElement[Y_LOC]
                        blockText = blockElement[STRING]
                        if dbg1:
                            dprt("txt  %2s (%7.3f %7.3f) \"%6s\"" %
                                 (handle, xTxt, yTxt, blockText))

            ref = dimLookup[minBlock]
            minDim = 0.0
            if var.startswith('x'):
                minDim = ref[X_DEF]
            elif var.startswith('y'):
                minDim = ref[Y_DEF]

            if dbg:
                dprt("%3s %3s %2d  %4s %10.6f \"%6s\" %7.3f" %
                     (minBlock, minHandle, minIndex, var, minDim,
                      minText, minDist))
            tstLookup[var] = DimResult(minDim, minText, minBlock)

        if dbg:
            dprt("\n" "tstLookup %d" % (len(tstLookup)))
            for key in sorted(tstLookup):
                dimVal, dimTxt, dimName = tstLookup[key]
                dprt("%4s %10.6f \"%6s\" %s" % (key, dimVal, dimTxt, dimName))

        if dbg:
            dprt("\n" "pathLookup %d" % (len(self.txtPath)))
        if len(self.txtPath) != 0:
            pathLookup = {}
            for txtEntity in self.txtPath:
                x = float(txtEntity[X_LOC]) + self.xOffset
                y = float(txtEntity[Y_LOC]) + self.yOffset
                txt = txtEntity[STRING]
                pathLookup[txt] = (x, y)
            self.pathLookup = pathLookup

            if dbg:
                for key in sorted(pathLookup):
                    (x, y) = pathLookup[key]
                    dprt("%-6s (%7.3f %7.3f)" % (key, x, y))
                dprt()
        else:
            self.pathLookup = None

        return tstLookup

    def addHandle(self, entity):
        if HANDLE in entity:
            handle = entity[HANDLE]
            self.handle[HANDLE] = handle
        else:
            handle = "XX"

        return handle

    def readHeader(self, dbg=False):
        if dbg:
            dprt("\n" "header")
        while True:
            result = self.readCodeVal()
            if result is None:
                return False

            (line, code, val) = result
            if code == 0:
                if dbg:
                    dprt("%5d %4d %s" % (line, code, val))
                if val == END_SEC:
                    return True

    def readClasses(self, dbg=False):
        if dbg:
            dprt("\n" "classes")
        while True:
            result = self.readCodeVal()
            if result is None:
                return False

            (line, code, val) = result
            if code == 0:
                if dbg:
                    dprt("%5d %4d %s" % (line, code, val))
                if val == END_SEC:
                    return True

    def dimTableAdd(self):
        if self.block is not None and len(self.block) != 0:
            if NAME in self.block:
                tmp = self.block[NAME]
                if tmp[0] == 'D':
                    self.dimTable[tmp] = self.block
                    handle = self.addHandle(self.block)
                    dprt("dimTable %s add %s\n" % (handle, tmp))
        self.block = {}

    def readTables(self, dbg=False):
        if dbg:
            dprt("\n" "tables")
        self.tableFunc = Func.NONE
        while True:
            result = self.readCodeVal()
            if result is None:
                return False

            (line, code, val) = result
            if code == 0:
                if dbg:
                    dprt("%5d %4d %s" % (line, code, val))
                if val == "TABLE":
                    pass
                elif val == BLOCK_RECORD:
                    self.dimTableAdd()
                    self.tableFunc = Func.BLOCK_RECORD
                elif val == END_TAB:
                    self.dimTableAdd()
                    self.tableFunc = Func.NONE
                elif val == END_SEC:
                    break
                else:
                    self.tableFunc = Func.NONE
            else:
                if self.tableFunc == BLOCK_RECORD:
                    self.block[code] = val
                    if dbg:
                        dprt("%5d %4d %s" % (line, code, val))

        if dbg:
            dprt()
            for key in sorted(self.dimTable):
                block = self.dimTable[key]
                dprt("%3s %3s %3s" % (key, block[NAME], block[HANDLE]))

            dprt()
            for key in sorted(self.handle):
                block = self.handle[key]
                dprt("%3s %3s %3s" % (key, block[NAME], block[HANDLE]))

        return True

    def readBlocks(self, dbg=False):
        if dbg:
            dprt("\n" "blocks")
        self.blockFunc = Func.NONE
        self.blockList = None
        self.blockElement = None
        self.blocks = []
        while True:
            result = self.readCodeVal()
            if result is None:
                return False

            (line, code, val) = result
            if code == 0:
                if self.blockList is not None:
                    blockElement = self.blockElement
                    if blockElement is not None:
                        if FUNC in blockElement:
                            func = blockElement[FUNC]
                            self.blockList.append(blockElement)
                            handle = self.addHandle(blockElement)
                            if dbg:
                                dprt("blockList %2s add %s" %
                                     (handle, str(func)))
                    self.blockElement = {}
                    if dbg:
                        dprt()
                if dbg:
                    dprt("%5d %4d %s" % (line, code, val))
                if val == BLOCK:
                    self.blockFunc = Func.BLOCK
                    self.blockList = []
                    self.blockElement = {FUNC: Func.BLOCK}
                elif val == M_TEXT:
                    self.blockFunc = Func.TXT
                    self.blockElement[FUNC] = Func.TXT
                elif val == LINE:
                    self.blockFunc = Func.LINE
                    self.blockElement[FUNC] = Func.LINE
                elif val == END_BLK:
                    self.blockFunc = Func.NONE
                    if len(self.blockList) > 1:
                        self.blocks.append(self.blockList)
                elif val == END_SEC:
                    break
                else:
                    self.blockFunc = Func.NONE
            else:
                if self.blockFunc == Func.BLOCK:
                    self.blockElement[code] = val
                    if dbg:
                        dprt("%5d %4d %s" % (line, code, val))
                elif self.blockFunc == Func.LINE:
                    self.blockElement[code] = val
                    if dbg:
                        dprt("%5d %4d %s" % (line, code, val))
                elif self.blockFunc == Func.TXT:
                    if code == 1:
                        # {\fMicrosoft Sans Serif|b0|i0|c0|p0;.000}
                        match = re.match(r"{.*?;([.\d]+)", val)
                        if match is None:
                            self.blockFunc = Func.NONE
                            self.blockElement = None
                        else:
                            result = match.groups()
                            if len(result) == 1:
                                val = result[0]

                    if self.blockElement is not None:
                        self.blockElement[code] = val
                        if dbg:
                            dprt("%5d %4d %s" % (line, code, val))

        return True

    def readEntities(self, dbg=False):
        if dbg:
            dprt("\n" "entities")
        self.func = Func.NONE
        self.dimRec = []
        self.dimName = []
        self.txtPath = []
        self.txtEntity = None
        self.dimEntity = None
        self.lineEntity = None
        self.xMin = 999
        self.yMin = 999
        while True:
            result = self.readCodeVal()
            if result is None:
                return False

            (line, code, val) = result
            if code == 0:
                if self.func == Func.DIM:
                    dimType = int(self.dimEntity[DIM_TYPE])
                    if (dimType & DIM_MASK) == ORDINATE:
                        self.dimRec.append(self.dimEntity)
                        handle = self.addHandle(self.dimEntity)
                        if dbg:
                            dprt("add %2s dim %s\n" %
                                 (handle, self.dimEntity[NAME]))
                    else:
                        if dbg:
                            dprt("skip %s\n" % (self.dimEntity[NAME]))
                elif self.func == Func.TXT:
                    txtStr = self.txtEntity[STRING]
                    # {\fArial|b0|i0|c0|p0;\C7;yMin}
                    match = re.match(r"{.*?;.*?;([(\s\w)]*)", txtStr)
                    if match is not None:
                        result = match.groups()
                        if len(result) == 1:
                            txtStr = result[0]
                            ch = txtStr[0]
                            if ch == '(':
                                txtStr = txtStr[1:-1]
                                self.txtEntity[STRING] = txtStr
                                self.txtPath.append(self.txtEntity)
                                if dbg:
                                    dprt("add txtPath %s\n" % (txtStr))
                            elif ch.isalpha():
                                self.txtEntity[STRING] = txtStr
                                self.dimName.append(self.txtEntity)
                                handle = self.addHandle(self.txtEntity)
                                if dbg:
                                    dprt("add %2s txt %s\n" % (handle, txtStr))
                            else:
                                if dbg:
                                    dprt("skip %s" % (txtStr))
                elif self.func == Func.LINE:
                    l = self.lineEntity
                    layer = l[LAYER]
                    if (layer == "Material" or
                        layer == "Fixture" or
                        layer == "Construction"):
                        if dbg:
                            dprt("line skip %s\n" % (layer))
                    else:
                        x0 = float(l[X_LOC])
                        y0 = float(l[Y_LOC])
                        x1 = float(l[X_END])
                        y1 = float(l[Y_END])
                        self.xMin = min(self.xMin, x0, x1)
                        self.yMin = min(self.yMin, y0, y1)
                        if dbg:
                            dprt("line %7.3f %7.3f) (%7.3f %7.3f) %s\n" %
                                 (x0, y0, x1, y1, layer))

                if dbg:
                    dprt("%5d %4d %s" % (line, code, val))
                if val == DIMENSION:
                    self.func = Func.DIM
                    self.dimEntity = {}
                elif val == M_TEXT:
                    self.func = Func.TXT
                    self.txtEntity = {}
                elif val == LINE:
                    self.func = Func.LINE
                    self.lineEntity = {}
                elif val == END_SEC:
                    break
                else:
                    self.func = Func.NONE
            else:
                if self.func == Func.DIM:
                    if code < 1000:
                        self.dimEntity[code] = val
                        if dbg:
                            dprt("%5d %4d %s" % (line, code, val))
                elif self.func == Func.TXT:
                    self.txtEntity[code] = val
                    if dbg:
                        dprt("%5d %4d %s" % (line, code, val))
                elif self.func == Func.LINE:
                    self.lineEntity[code] = val

        return True

    def readObjects(self, dbg=False):
        if dbg:
            dprt("\n" "object")
        while True:
            result = self.readCodeVal()
            if result is None:
                return False

            (line, code, val) = result
            if code == 0:
                # dprt("%5d %4d %s" % (line, code, val))
                if val == END_SEC:
                    return True

if __name__ == '__main__':

    if len(sys.argv) >= 2:
        fileName = sys.argv[1]
    else:
        fileName = "test/DimensionTest.dxf"

    dprtSet(True)
    dxf = ReadDxfDim()

    dxf.readDimensions(fileName, None, None)
