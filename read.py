#!/cygdrive/c/Python310/Python.exe

import sys
import re
from math import hypot
from operator import itemgetter
from enum import Enum

FUNC = 0

END_SEC = "ENDSEC"

BLOCK_RECORD = "BLOCK_RECORD"
END_TAB      = "ENDTAB"

BLOCK   = "BLOCK"
END_BLK = "ENDBLK"

DIMENSION = "DIMENSION"
M_TEXT    = "MTEXT"
LINE      = "LINE"

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

class Func(Enum):
    NONE         = 0
    DIM          = 1
    TXT          = 2
    LINE         = 3
    BLOCK_RECORD = 4
    BLOCK        = 5
    END_BLOCK    = 6

class ReadDxf:
    def __init__(self):
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

    def readCodeVal(self):
        code = self.dxfFile.readline().strip()
        self.line += 1
        curLine = self.line

        if len(code) == 0:
            return None
        try:
            intCode = int(code)
            # print("*", code)
        except ValueError:
            print("value error", code)
            return None

        val = self.dxfFile.readline().strip()
        self.line += 1
        return (curLine, intCode, val)

    @staticmethod
    def floatStr(x):
        return float(x)

    def process(self, fName):
        self.dxfFile = open(fName, 'r')

        while True:
            result = self.readCodeVal()
            if result is None:
                 return False

            (line, code, val) = result
            if val == "EOF":
                print("%5d %4d %s" % (line, code, val))
                break

            result = self.readCodeVal()
            if result is None:
                return False
            if code == 0:
                if val == "SECTION":
                    (line, code, val) = result
                    if code == 2:
                        if val == "HEADER":
                            self.readHeader()
                        elif val == "CLASSES":
                            self.readClasses()
                        elif val == "TABLES":
                            self.readTables()
                        elif val == "BLOCKS":
                            self.readBlocks()
                        elif val == "ENTITIES":
                            self.readEntities()
                        elif val == "OBJECTS":
                            self.readObjects()

        print("\n" "xMin %7.4f yMin %7.4f" % (self.xMin, self.yMin))

        for blockList in self.blocks:
            print()
            for blockElem in blockList:
                func = blockElem[FUNC]
                print("%-10s" % (func), end=" ")
                if func == Func.BLOCK:
                    print("%2s %s" %
                          (blockElem[REF], blockElem[NAME]))
                elif func == Func.TXT:
                    blockElem[X_LOC] = x0 = float(blockElem[X_LOC]) - self.xMin
                    blockElem[Y_LOC] = y0 = float(blockElem[Y_LOC]) - self.yMin
                    print("%2s (%7.3f %7.3f) %s" %
                          (blockElem[REF], x0, y0, blockElem[STRING]))
                elif func == Func.LINE:
                    blockElem[X_LOC] = x0 = float(blockElem[X_LOC]) - self.xMin
                    blockElem[X_END] = x1 = float(blockElem[X_END]) - self.xMin
                    blockElem[Y_LOC] = y0 = float(blockElem[Y_LOC]) - self.yMin
                    blockElem[Y_END] = y1 = float(blockElem[Y_END]) - self.yMin
                    print("%2s (%7.3f %7.3f) (%7.3f %7.3f)" %
                          (blockElem[REF], x0, y0 ,x1, y1))

        print("\n" "dimRec")
        dimLookup = {}
        for dim in self.dimRec:
            # noinspection PyTypeChecker
            dim[X_LOC] = x0 = float(dim[X_LOC]) - self.xMin
            # noinspection PyTypeChecker
            dim[X_DEF] = x1 = float(dim[X_DEF]) - self.xMin
            # noinspection PyTypeChecker
            dim[Y_LOC] = y0 = float(dim[Y_LOC]) - self.yMin
            # noinspection PyTypeChecker
            dim[Y_DEF] = y1 = float(dim[Y_DEF]) - self.yMin
            dimName = dim[NAME]
            dimLookup[dimName] = dim
            print("%2s (%7.3f %7.3f) (%7.3f %7.3f)" %
                  (dimName, x0, y0, x1, y1))

        self.dimNameLoc = []
        for rec in self.dimName:
            x = float(rec[X_LOC]) - self.xMin
            y = float(rec[Y_LOC]) - self.yMin
            txt = rec[1]
            self.dimNameLoc.append((x, y, txt))
        self.dimNameLoc.sort(key=itemgetter(0, 1))

        print("\n" "dimNameLoc")
        for x, y, txt in self.dimNameLoc:
            print("%-5s %7.3f %7.3f" % (txt, x, y))

        self.dimTxt = []
        blockName = ""
        for block in self.blocks:
            for blockElement in block:
                if blockElement[FUNC] == Func.BLOCK:
                    blockName = blockElement[NAME]
                elif blockElement[FUNC] == Func.TXT:
                    x = blockElement[X_LOC]
                    y = blockElement[Y_LOC]
                    txt = blockElement[STRING]
                    self.dimTxt.append((x, y, txt, blockName))
        self.dimTxt.sort(key=itemgetter(0, 1))

        print("\n" "dimTxt")
        for x, y, txt, blockName in self.dimTxt:
            print("%-5s %7.3f %7.3f %s" % (txt, x, y, blockName))

        print()
        varLookup = {}
        # p0 = p1 = delta = (0, 0)
        for x0, y0, var in self.dimNameLoc:
            minDist = 9999
            # minDim = 0.0
            minIndex = 0
            dimName = ""
            # print("\n" "(%7.3f %7.3f) %s" % (x0, y0, var))
            for j, (x1, y1, dim, name) in enumerate(self.dimTxt):
                dx = x1 - x0
                dy = y1 - y0
                dist = hypot(dx, dy)
                # print("%d (%7.3f %7.3f) %s dist %7.3f " %
                #       (j, x1, y1, dim, dist))
                if dist < minDist:
                    minDist = dist
                    minIndex = j
                    dimName = name
                    # minDim = float(dim)
                    # p0 = (x0, y0)
                    # p1 = (x1, y1)
                    # delta = (dx, dy)
            del self.dimTxt[minIndex]

            ref = dimLookup[dimName]
            minDim = 0.0
            if var.startswith('x'):
                minDim = ref[X_DEF]
            elif var.startswith('y'):
                minDim = ref[Y_DEF]

            varLookup[var] = (minDim, dimName)
            print("%4s %2d %10.6f %5.3f" %
                  (var, minIndex, minDim, minDist))

        print("\n" "varLookup")
        for key in sorted(varLookup):
            dim, dimName = varLookup[key]
            ref = dimLookup[dimName]
            refDim = 0.0
            if key.startswith('x'):
                refDim = ref[X_DEF]
            elif key.startswith('y'):
                refDim = ref[Y_DEF]
            print("%4s %10.6f %2s %10.6f" % (key, dim, dimName, refDim))

        print()
        tstLookup = {}
        dbg = False
        # p0 = p1 = delta = (0, 0)
        for x0, y0, var in self.dimNameLoc:
            minDist = 9999
            blockText = ""
            minIndex = -1
            minHandle = "XX"
            minText = ""
            minBlock = ""
            if dbg:
                print("\n" "(%7.3f %7.3f) %s" % (x0, y0, var))
            for j, block in enumerate(self.blocks):
                for blockElement in block:
                    handle = blockElement[HANDLE]
                    if blockElement[FUNC] == Func.BLOCK:
                        blockName = blockElement[NAME]
                        if dbg:
                            print("\n" "block %2s %s" % (handle, blockName))
                    elif blockElement[FUNC] == Func.LINE:
                        xS = blockElement[X_LOC]
                        yS = blockElement[Y_LOC]
                        distS = hypot(xS - x0, yS - y0)
                        xE = blockElement[X_END]
                        yE = blockElement[Y_END]
                        distE = hypot(xE - x0, yE - y0)
                        if dbg:
                            print("line %2s (%7.3f %7.3f) %7.3f "
                                  "(%7.3f %7.3f) %7.3f" %
                                  (handle, xS, yS, distS, xE, yE, distE))
                        dist = min(distS, distE)
                        if dist < minDist:
                            if dbg:
                                print("dist %7.3f minDist %7.3f" %
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
                        if dbg:
                            print("txt  %2s (%7.3f %7.3f) \"%6s\"" %
                                  (handle, xTxt, yTxt, blockText))

            ref = dimLookup[minBlock]
            minDim = 0.0
            if var.startswith('x'):
                minDim = ref[X_DEF]
            elif var.startswith('y'):
                minDim = ref[Y_DEF]

            print("%2s %2s %2d  %4s %10.6f \"%6s\" %7.3f" %
                  (minBlock, minHandle, minIndex, var, minDim,
                   minText, minDist))
            tstLookup[var] = (minDim, minText)

        print("\n" "tstLookup")
        for key in sorted(tstLookup):
            dimVal, dimTxt = tstLookup[key]
            print("%4s %10.6f \"%6s\"" % (key, dimVal, dimTxt))

        return True

    def addHandle(self, entity):
        if HANDLE in entity:
            handle = entity[HANDLE]
            self.handle[HANDLE] = handle
        else:
            handle = "XX"

        return handle

    def readHeader(self):
        print("\n" "header")
        while True:
            result = self.readCodeVal()
            if result is None:
                return False

            (line, code, val) = result
            if code == 0:
                print("%5d %4d %s" % (line, code, val))
                if val == END_SEC:
                    return True

    def readClasses(self):
        print("\n" "classes")
        while True:
            result = self.readCodeVal()
            if result is None:
                return False

            (line, code, val) = result
            if code == 0:
                print("%5d %4d %s" % (line, code, val))
                if val == END_SEC:
                    return True

    def dimTableAdd(self):
        if self.block is not None and len(self.block) != 0:
            if NAME in self.block:
                tmp = self.block[NAME]
                if tmp[0] == 'D':
                    self.dimTable[tmp] = self.block
                    handle = self.addHandle(self.block)
                    print("dimTable %s add %s\n" % (handle, tmp))
        self.block = {}

    def readTables(self):
        print("\n" "tables")
        self.tableFunc = Func.NONE
        while True:
            result = self.readCodeVal()
            if result is None:
                return False

            (line, code, val) = result
            if code == 0:
                print("%5d %4d %s" % (line, code, val))
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
                    print("%5d %4d %s" % (line, code, val))

        print()
        for key in sorted(self.dimTable):
            block = self.dimTable[key]
            print("%3s %3s %3s" % (key, block[NAME], block[HANDLE]))

        print()
        for key in sorted(self.handle):
            block = self.handle[key]
            print("%3s %3s %3s" % (key, block[NAME], block[HANDLE]))

        return True

    def readBlocks(self):
        print("\n" "blocks")
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
                            print("blockList %2s add %s" %
                                  (handle, str(func)))
                    self.blockElement = {}
                    print()
                print("%5d %4d %s" % (line, code, val))
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
                    print("%5d %4d %s" % (line, code, val))
                elif self.blockFunc == Func.LINE:
                    self.blockElement[code] = val
                    print("%5d %4d %s" % (line, code, val))
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
                        print("%5d %4d %s" % (line, code, val))

        return True

    def readEntities(self):
        print("\n" "entities")
        self.func = Func.NONE
        self.dimRec = []
        self.dimName = []
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
                        print("add %2s dim %s\n" %
                              (handle, self.dimEntity[NAME]))
                    else:
                        print("skip\n")
                elif self.func == Func.TXT:
                    self.dimName.append(self.txtEntity)
                    txtStr = self.txtEntity[STRING]
                    # {\fArial|b0|i0|c0|p0;\C7;yMin}
                    match = re.match(r"{.*?;.*?;(\w*)", txtStr)
                    if match is not None:
                        result = match.groups()
                        if len(result) == 1:
                            txtStr = result[0]
                            self.txtEntity[STRING] = txtStr
                    handle = self.addHandle(self.txtEntity)
                    print("add %2s txt %s\n" % (handle, txtStr))
                elif self.func == Func.LINE:
                    l = self.lineEntity
                    x0 = float(l[X_LOC])
                    y0 = float(l[Y_LOC])
                    x1 = float(l[X_END])
                    y1 = float(l[Y_END])
                    self.xMin = min(self.xMin, x0, x1)
                    self.yMin = min(self.yMin, y0, y1)
                    print()

                print("%5d %4d %s" % (line, code, val))
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
                        print("%5d %4d %s" % (line, code, val))
                elif self.func == Func.TXT:
                    self.txtEntity[code] = val
                    print("%5d %4d %s" % (line, code, val))
                elif self.func == Func.LINE:
                    self.lineEntity[code] = val

        return True

    def readObjects(self):
        print("\n" "object")
        while True:
            result = self.readCodeVal()
            if result is None:
                return False

            (line, code, val) = result
            if code == 0:
                # print("%5d %4d %s" % (line, code, val))
                if val == END_SEC:
                    return True

if __name__ == '__main__':

    if len(sys.argv) >= 2:
        fileName = sys.argv[1]
    else:
        fileName = "test/DimensionTest.dxf"

    dxf = ReadDxf()

    dxf.process(fileName)
