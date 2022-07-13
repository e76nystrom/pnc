from dbgprt import dprt, dprtSet, ePrint
from geometry import (ARC, CCW, CW, INDEX_MARKER, LINE, MAX_VALUE, MIN_DIST,
                      MIN_VALUE, Arc, Line, createPath, inside, oStr,
                      reverseSeg, splitArcs, xyDist)

XPLUS_YPLUS   = 0
XMINUS_YPLUS  = 1
XMINUS_YMINUS = 2
XPLUS_YMINUS  = 3
XPLUS  = 4
YPLUS  = 5
XMINUS = 6
YMINUS = 7

SIMPLE_BOX = False

class corner():
    def __init__(self, cfg):
        self.cfg = cfg
        print("corner loaded")
        self.dbg = False
        self.quadrant = None
        self.leadRadius = 0.025
        self.passOffset = 0.027
        self.maxPasses = 0
        self.alternate = True
        self.fixture = False
        self.layerNum = 0
        self.quadrantValues = \
        ( \
          ('xplus_yplus',   XPLUS_YPLUS), \
          ('xminus_yplus',  XMINUS_YPLUS), \
          ('xminus_yminus', XMINUS_YMINUS), \
          ('xplus_yminus',  XPLUS_YMINUS), \
          ('xplus',  XPLUS), \
          ('yplus',  YPLUS), \
          ('xminus', XMINUS), \
          ('yminus', YMINUS), \
        )
        self.cmds = \
        ( \
          ('corner', self.corner, True), \
          ('quadrant', self.setQuadrant), \
          ('corpasscut', self.setPassCut), \
          ('corleadradius' , self.setLead), \
          ('corpasses' , self.setPasses), \
          ('coralternatedir', self.setAlternate), \
          ('corfixture', self.setFixture), \
          # ('', self.), \
        )
        self.xMin = None
        self.yMin = None
        self.xMax = None
        self.yMax = None
        dprtSet(True)

    def setQuadrant(self, args):
        val = args[1].lower()
        self.quadrant = None
        for (x, i) in self.quadrantValues:
            if val == x:
                self.quadrant = i
                break
        if self.quadrant is None:
            ePrint("invalid quadrant %s" % val)
            raise ValueError("invalid quadrant" % val)

    def setPassCut(self, args):
        self.offset = self.cfg.evalFloatArg(args[1])

    def setLead(self, args):
        self.leadRadius = self.cfg.evalFloatArg(args[1])

    def setPasses(self, args):
        self.maxPasses = self.cfg.evalIntArg(args[1])

    def setAlternate(self, args):
        self.alternate = self.cfg.evalBoolArg(args[1])

    def setFixture(self, args):
        self.fixture = self.cfg.evalBoolArg(args[1])
          
    def corner(self, args, dbg=True):
        cfg = self.cfg
        # direction = CCW
        # if cfg.dir is not None and cfg.dir == 'CW':
        #     direction = CW
        cfg.ncInit()

        if SIMPLE_BOX:
            dxf = cfg.dxfInput
            xMin = dxf.xMin
            xMax = dxf.xMax
            yMin = dxf.yMin
            yMax = dxf.yMax

            q = self.quadrant
            if q == XPLUS_YPLUS:
                xMin = (xMax + xMin) / 2
                yMin = (yMax + yMin) / 2
            elif q == XMINUS_YPLUS:
                xMax = (xMax + xMin) / 2
                yMin = (yMax + yMin) / 2
            elif q == XMINUS_YMINUS:
                xMax = (xMax + xMin) / 2
                yMax = (yMax + yMin) / 2
            elif q == XPLUS_YMINUS:
                xMin = (xMax + xMin) / 2
                yMax = (yMax + yMin) / 2

            p0 = (xMin, yMax)
            p1 = (xMax, yMax)
            p2 = (xMax, yMin)
            p3 = (xMin, yMin)
            box = []
            box.append(Line(p0, p1))
            box.append(Line(p1, p2))
            box.append(Line(p2, p3))
            box.append(Line(p3, p0))

            dprt("\nsimple box")
            boxLayer = "%02d-00-a-box" % self.layerNum
            for l in box:
                l.prt()
                l.draw(layer=boxLayer)
            dprt()

        layer = args[1]
        segments = cfg.dxfInput.getPath(layer)
        if len(args) > 2:
            if args[2] == "break":
                ePrint("break")

        # for seg in segments:
        #     for l in seg:
        #         l.prt()
        #         l.draw()
        #     dprt()

        mp = cfg.getMillPath()
        for seg in segments:
            splitSeg = splitArcs(seg)

            xMax = yMax = MIN_VALUE
            xMin = yMin = MAX_VALUE
            for l in splitSeg:
                l.prt()
                for (x, y) in (l.p0, l.p1):
                    if x > xMax:    # check x
                        xMax = x
                    if x < xMin:
                        xMin = x
                    if y > yMax:    # check y
                        yMax = y
                    if y < yMin:
                        yMin = y
            (self.xMin, self.yMin) = (xMin, yMin)
            (self.xMax, self.yMax) = (xMax, yMax)
            dprt("xMin %7.4f xMax %7.4f ymin %7.4f yMax %7.4f" % \
                 (self.xMin, self.xMax, self.yMin, self.yMax))
            dxf = self.cfg.dxfInput
            dprt("xMin %7.4f xMax %7.4f ymin %7.4f yMax %7.4f" % \
                 (dxf.xMin, dxf.xMax, dxf.yMin, dxf.yMax))

            # for l in splitSeg:
            #     l.draw()

            if not SIMPLE_BOX:
                box = self.createBox(splitSeg)
                if box is None:
                    continue
                dprt("\ngeneral box")
                boxLayer = "%02d-00-a-box" % self.layerNum
                for l in box:
                    l.prt()
                    l.draw(layer=boxLayer)
                dprt()

            seg1 = []
            for l in splitSeg:
                (x0, y0) = l.p0
                (x1, y1) = l.p1
                if l.type == ARC:
                    p = ((x0 + x1) / 2, (y0 + y1) / 2)
                    if (inside(p, box) & 1) == 0:
                        continue
                elif l.type == LINE:
                    if (inside(l.p0, box) & 1) == 0 and \
                       (inside(l.p1, box) & 1) == 0:
                        continue
                seg1.append(l)

            dprt("seg len %d" % (len(seg1)))
            if len(seg1) == 0:
                continue

            # for l in seg1:
            #     l.prt()
            #     l.draw()

            dprt("closePath")
            self.closePath(seg1)

            closeLayer = "%02d-00-b-close" % self.layerNum
            for l in seg1:
                l.prt()
                l.draw(layer=closeLayer)

            if self.quadrant <= XPLUS_YMINUS:
                self.setTrim()

            offset = cfg.endMillSize / 2.0 + cfg.finishAllowance

            passes = self.maxPasses
            # passOffset = self.passOffset
            if passes == 0:
                dprt("\nfind max dist")
                maxD = MIN_VALUE
                for l in seg1:
                    if l.index <= INDEX_MARKER:
                        continue
                    d = l.pointDistance((self.trimX, self.trimY))
                    if d is not None:
                        l.prt()
                        dprt("d %7.4f" % (d))
                    maxD = max(maxD, d)

                total = maxD - offset
                passes = int(round(total / self.passOffset))
                # passOffset = total / passes
                dprt("maxD %7.4f total %7.4f passes %d passOffset %7.4f" % \
                     (maxD, total, passes, self.passOffset))

            path = []
            for i in range(passes):
                dprt("\npass %2d offset %7.4f\n" % (i, offset))
                seg2 = createPath(seg1, offset, outside=True, keepIndex=True,
                                  split=False, dbg=True)[0]

                pathLayer = "%02d-%02d-c-path" % (self.layerNum, i)
                for l in seg2:
                    l.draw(layer=pathLayer)

                if self.quadrant <= XPLUS_YMINUS:
                    dprt()
                    seg3 = self.trim(seg2)
                    trimLayer = "%02d-%02d-d-trim" % (self.layerNum, i) 
                    for l in seg3:
                        l.draw(layer=trimLayer)
                        l.label(layer=trimLayer)
                else:
                    seg3 = []
                    for l in seg2:
                        if l.index <= INDEX_MARKER:
                            continue
                        seg3.append(l)

                print("seg3Len %d" % (len(seg3)))
                if len(seg3) == 0:
                    break

                path.append(seg3)

                # dprt()
                # for l in seg3:
                #     l.prt()
                #     l.draw()

                offset += self.passOffset

            cfg.mill.write("(corner %s)\n" % \
                           (self.quadrantValues[self.quadrant][0]))
            if self.alternate:
                finalPath = []
                lastPoint = None
                for (i, seg) in enumerate(path):
                    if (i & 1) != 0:
                        seg = reverseSeg(seg)
                    if lastPoint is not None:
                        finalPath.append(Line(lastPoint, seg[0].p0))
                    finalPath += seg
                    lastPoint = finalPath[-1].p1
                finalPath = reverseSeg(finalPath, makeCopy=False)

                if self.quadrant <= XPLUS_YMINUS:
                    self.addEntry(finalPath)
                    self.addExit(finalPath)
                else:
                    self.addEntry1(finalPath)
                    self.addExit1(finalPath)

                dprt()
                finalLayer = "%02d-%02d-e-final" % (self.layerNum, i)
                for l in finalPath:
                    l.prt()
                    l.draw(layer=finalLayer)

                mp.millPath(finalPath, closed=False, minDist=False)
            else:
                for seg in reversed(path):
                    if self.quadrant <= XPLUS_YMINUS:
                        self.addEntry(seg)
                        self.addExit(seg)
                    else:
                        self.addEntry1(seg)
                        self.addExit1(seg)

                    dprt()
                    finalLayer = "%02d-%02d-e-final" % (self.layerNum, i)
                    for l in seg:
                        l.prt()
                        l.draw(layer=finalLayer)
                    mp.millPath(seg, closed=False, minDist=False)
        self.layerNum += 1

    def addEntry(self, path):
        l = path[0]
        (x, y) = l.p0
        dx = x - l.p1[0]
        dy = y - l.p1[1]
        r = self.leadRadius
        if abs(x - self.trimX) < MIN_DIST:
            if self.xPlus:
                x += r
                if dy > 0:
                    a0 = 90;  a1 = 180; direction = CCW; en = 0
                else:
                    a0 = 180; a1 = 270; direction = CW;  en = 1
            else:
                x -= r
                if dy < 0:
                    a0 = 270; a1 = 360; direction = CCW; en = 2
                else:
                    a0 = 0;   a1 = 90;  direction = CW;  en = 3
        elif abs(y - self.trimY) < MIN_DIST:
            if self.yPlus:
                y += r
                if dx < 0:
                    a0 = 180; a1 = 270; direction = CCW; en = 4
                else:
                    a0 = 270; a1 = 360; direction = CW;  en = 5
            else:
                y -= r
                if dx > 0:
                    a0 = 0;   a1 = 90;  direction = CCW; en = 6
                else:
                    a0 = 90;  a1 = 180; direction = CW;  en = 7
        else:
            ePrint("addEntry error x %7.4f xTrim %7.4f y %7.4f yTrim %7.4f" % \
                   (x, self.trimX, y, self.trimY))
            return
        dprt("entry %d direction %s" % (en, oStr(self.cfg.dir)))
        l = Arc((x, y), r, a0, a1, direction=direction)
        path.insert(0, l)

    def addEntry1(self, path):
        q = self.quadrant
        (x, y) = path[0].p0
        (xEnd, yEnd) = path[-1].p1
        r = self.leadRadius
        if q == XPLUS:
            if y > yEnd:
                y += r
                a0 = 180; a1 = 270; direction = CCW; en = 0
            else:
                y -= r
                a0 = 90;  a1 = 180; direction = CW;  en = 1
        elif q == YPLUS:
            if x > xEnd:
                x += r
                a0 = 180; a1 = 270; direction = CW;  en = 4
            else:
                x -= r
                a0 = 270; a1 = 360; direction = CCW; en = 5
        elif q == XMINUS:
            if y > yEnd:
                y += r
                a0 = 270; a1 = 360; direction = CW;  en = 2
            else:
                y -= r
                a0 = 0;   a1 = 90;  direction = CCW; en = 3
        elif q == YMINUS:
            if x > xEnd:
                x += r
                a0 = 90;  a1 = 180; direction = CCW; en = 6
            else:
                x -= r
                a0 = 0;   a1 = 90;  direction = CW;  en = 7
        dprt("entry %d direction %s" % (en, oStr(self.cfg.dir)))
        l = Arc((x, y), r, a0, a1, direction=direction)
        path.insert(0, l)

    def addExit(self, path):
        l = path[-1]
        (x, y) = l.p1
        dx = x - l.p0[0]
        dy = y - l.p0[1]
        r = self.leadRadius
        if abs(x - self.trimX) < MIN_DIST:
            if self.xPlus:
                x += r
                if dy > 0:
                    a0 = 90;  a1 = 180; direction = CW;  ex = 0
                else:
                    a0 = 180; a1 = 270; direction = CCW; ex = 1
            else:
                x -= r
                if dy < 0:
                    a0 = 270; a1 = 360; direction = CW;  ex = 2
                else:
                    a0 = 0;   a1 = 90;  direction = CCW; ex = 3
        elif abs(y - self.trimY) < MIN_DIST:
            if self.yPlus:
                y += r
                if dx < 0:
                    a0 = 180; a1 = 270; direction = CW;  ex = 4
                else:
                    a0 = 270; a1 = 360; direction = CCW; ex = 5
            else:
                y -= r
                if dx > 0:
                    a0 = 0;   a1 = 90;  direction = CW;  ex = 6
                else:
                    a0 = 90;  a1 = 180; direction = CCW; ex = 7
        else:
            ePrint("error")
            return
        dprt("exit %d direction %s" % (ex, oStr(self.cfg.dir)))
        l = Arc((x, y), r, a0, a1, direction=direction)
        path.append(l)

    def addExit1(self, path):
        q = self.quadrant
        (x, y) = path[-1].p1
        (xStr, yStr) = path[0].p0
        r = self.leadRadius
        if q == XPLUS:
            if y > yStr:
                y += r
                a0 = 180; a1 = 270; direction = CW;  ex = 0
            else:
                y -= r
                a0 = 90;  a1 = 180; direction = CCW; ex = 1
        elif q == YPLUS:
            if x > xStr:
                x += r
                a0 = 180; a1 = 270; direction = CCW; ex = 4
            else:
                x -= r
                a0 = 270; a1 = 360; direction = CW;  ex = 5
        elif q == XMINUS:
            if y > yStr:
                y += r
                a0 = 270; a1 = 360; direction = CCW; ex = 2
            else:
                y -= r
                a0 = 0;   a1 = 90;  direction = CW;  ex = 3
        elif q == YMINUS:
            if x > xStr:
                x += r
                a0 = 90;  a1 = 180; direction = CW;  ex = 6
            else:
                x -= r
                a0 = 0;   a1 = 90;  direction = CCW; ex = 7
        dprt("exit %d direction %s" % (ex, oStr(self.cfg.dir)))
        l = Arc((x, y), r, a0, a1, direction=direction)
        path.append(l)

    def trim(self, path):
        dprt("trim start %d trimX %7.4f trimy %7.4f xPlus %5s yPlus %5s" % \
             (self.layerNum, self.trimX, self.trimY, self.xPlus, self.yPlus))
        if self.layerNum == 3:
            dprt("break")
        rtnPath = []
        for l in path:
            if l.index == INDEX_MARKER:
                continue
            if l.type == ARC:
                if xyDist((self.trimX, self.trimY), l.c) < l.r:
                    continue
            # elif l.type == LINE:
            #     rtnPath.append(l)
            #     continue
            dprt()
            l.prt()
            dprt("horz trim")
            l1 = l.horizontalTrim(self.trimY, self.yPlus)
            if l1 != None:
                l1.prt()
                dprt("vert trim")
                l1 = l.verticalTrim(self.trimX, self.xPlus)
                if l1 != None:
                    l1.prt()
                    rtnPath.append(l1)
                else:
                    dprt("vert returned None")
            else:
                dprt("horz returned None")
        dprt("\ntrim done")
        return(rtnPath)

    def createBox(self, path):
            if self.fixture:
                (xMin, yMin) = (self.xMin, self.yMin)
                (xMax, yMax) = (self.xMax, self.yMax)
            else:
                dxf = self.cfg.dxfInput
                (xMin, yMin) = (dxf.xMin, dxf.yMin)
                (xMax, yMax) = (dxf.xMax, dxf.yMax)
            q = self.quadrant
            if q <= XPLUS_YMINUS:
                p = self.findQuadrantPoints(path)
                if p is None:
                    return(None)
                if q == XPLUS_YPLUS:
                    (xMin, yMin) = p
                elif q == XMINUS_YPLUS:
                    (xMax, yMin) = p
                elif q == XMINUS_YMINUS:
                    (xMax, yMax) = p
                elif q == XPLUS_YMINUS:
                    (xMin, yMax) = p
                p0 = (xMin, yMax)
                p1 = (xMax, yMax)
                p2 = (xMax, yMin)
                p3 = (xMin, yMin)
            else:
                p0 = (xMin, yMax)
                p1 = (xMax, yMax)
                p2 = (xMax, yMin)
                p3 = (xMin, yMin)
                (xStr, yStr) = path[0].p0
                (xEnd, yEnd) = path[-1].p1
                if q == XPLUS:
                    if abs(xStr - xEnd) > MIN_DIST:
                        if xEnd < xStr:
                            xStr = xEnd
                    p0 = (xStr, yMax)
                    p3 = (xStr, yMin)
                elif q == YPLUS:
                    if abs(yStr - yEnd) > MIN_DIST:
                        if yEnd < yStr:
                            yStr = yEnd
                    p2 = (xMax, yStr)
                    p3 = (xMin, yStr)
                elif q == XMINUS:
                    if abs(xStr - xEnd) > MIN_DIST:
                        if xEnd > xStr:
                            xStr = xEnd
                    p1 = (xStr, yMax)
                    p2 = (xStr, yMin)
                elif q == YMINUS:
                    if abs(yStr - yEnd) > MIN_DIST:
                        if yEnd > yStr:
                            yEnd = yStr
                    p0 = (xMin, yStr)
                    p1 = (xMax, yStr)
            box = []
            box.append(Line(p0, p1))
            box.append(Line(p1, p2))
            box.append(Line(p2, p3))
            box.append(Line(p3, p0))
            return(box)

    def findQuadrantPoints(self, path):
        if not self.fixture:
            if not self.pathInQuadrant(path):
                return(None)
        q = self.quadrant
        if q == XPLUS_YPLUS:
            pX = self.getPtForMaxX(path)
            pY = self.getPtForMaxY(path)
        elif q == XMINUS_YPLUS:
            pX = self.getPtForMinX(path)
            pY = self.getPtForMaxY(path)
        elif q == XMINUS_YMINUS:
            pX = self.getPtForMinX(path)
            pY = self.getPtForMinY(path)
        elif q == XPLUS_YMINUS:
            pX = self.getPtForMaxX(path)
            pY = self.getPtForMinY(path)
        elif q == XPLUS:
            pass
        elif q == YPLUS:
            pass
        elif q == XMINUS:
            pass
        elif q == YMINUS:
            pass
        (x, y) = (pY[0], pX[1])
        return((x, y))

    def pathInQuadrant(self, path):
        dxf = self.cfg.dxfInput
        q = self.quadrant
        if q == XPLUS_YPLUS:
            result = abs(self.xMax - dxf.xMax) < MIN_DIST and \
                     abs(self.yMax - dxf.yMax) < MIN_DIST
        elif q == XMINUS_YPLUS:
            result = abs(self.xMin - dxf.xMin) < MIN_DIST and \
                     abs(self.yMax - dxf.yMax) < MIN_DIST
        elif q == XMINUS_YMINUS:
            result = abs(self.xMin - dxf.xMin) < MIN_DIST and \
                     abs(self.yMin - dxf.yMin) < MIN_DIST
        elif q == XPLUS_YMINUS:
            result = abs(self.xMax - dxf.xMax) < MIN_DIST and \
                     abs(self.yMin - dxf.yMin) < MIN_DIST
        elif q == XPLUS:
            result = abs(self.xMax - dxf.xMax) < MIN_DIST
        elif q == YPLUS:
            result = abs(self.yMax - dxf.yMax) < MIN_DIST
        elif q == XMINUS:
            result = abs(self.xMin - dxf.xMin) < MIN_DIST
        elif q == YMINUS:
            result = abs(self.yMin - dxf.yMin) < MIN_DIST
        return(result)

    def getPtForMinX(self, path):
        minX = MAX_VALUE
        for l in path:
            if l.p0[0] < minX:
                p = l.p0
                minX = l.p0[0]
            if l.p1[0] < minX:
                p = l.p1
                minX = l.p1[0]
        return(p)

    def getPtForMaxX(self, path):
        maxX = MIN_VALUE
        for l in path:
            if l.p0[0] > maxX:
                p = l.p0
                maxX = l.p0[0]
            if l.p1[0] > maxX:
                p = l.p1
                maxX = l.p1[0]
        return(p)

    def getPtForMinY(self, path):
        minY = MAX_VALUE
        for l in path:
            if l.p0[1] < minY:
                p = l.p0
                minY = l.p0[1]
            if l.p1[1] < minY:
                p = l.p1
                minY = l.p1[1]
        return(p)
                
    def getPtForMaxY(self, path):
        maxY = MIN_VALUE
        for l in path:
            if l.p0[1] > maxY:
                p = l.p0
                maxY = l.p0[1]
            if l.p1[1] > maxY:
                p = l.p1
                maxY = l.p1[1]
        return(p)

    def setTrim(self):
        cfg = self.cfg
        dxf = cfg.dxfInput
        draw = cfg.draw
        offset = self.cfg.endMillSize / 2.0
        if self.fixture:
            (xMin, yMin) = (self.xMin, self.yMin)
            (xMax, yMax) = (self.xMax, self.yMax)
        else:
            (xMin, yMin) = (dxf.xMin, dxf.yMin)
            (xMax, yMax) = (dxf.xMax, dxf.yMax)
        dprt("xMin %7.4f xMax %7.4f ymin %7.4f yMax %7.4f" % \
             (dxf.xMin, dxf.xMax, dxf.yMin, dxf.yMax))
        q = self.quadrant
        trimLayer = "%02d-00-*-trim" % self.layerNum
        if q == XPLUS_YPLUS:
            self.xPlus = True
            self.yPlus = True
            self.trimX = xMax + offset
            self.trimY = yMax + offset
            self.refY = self.minY
            draw.move((xMin, self.trimY))
            draw.line((self.trimX, self.trimY), layer=trimLayer)
            draw.line((self.trimX, self.refY), layer=trimLayer)
        elif q == XMINUS_YPLUS:
            self.xPlus = False
            self.yPlus = True
            self.trimX = xMin - offset
            self.trimY = yMax + offset
            self.refY = self.minY
            draw.move((xMax, self.trimY))
            draw.line((self.trimX, self.trimY), layer=trimLayer)
            draw.line((self.trimX, self.refY), layer=trimLayer)
        elif q == XMINUS_YMINUS:
            self.xPlus = False
            self.yPlus = False
            self.trimX = xMin - offset
            self.trimY = yMin - offset
            self.refY = self.maxY
            draw.move((xMax, self.trimY))
            draw.line((self.trimX, self.trimY), layer=trimLayer)
            draw.line((self.trimX, self.refY), layer=trimLayer)
        elif q == XPLUS_YMINUS:
            self.xPlus = True
            self.yPlus = False
            self.trimX = xMax + offset
            self.trimY = yMin - offset
            self.refY = self.maxY
            draw.move((xMin, self.trimY))
            draw.line((self.trimX, self.trimY), layer=trimLayer)
            draw.line((self.trimX, self.refY), layer=trimLayer)
        elif q == XPLUS:
            pass
        elif q == YPLUS:
            pass
        elif q == XMINUS:
            pass
        elif q == YMINUS:
            pass

    def closePath(self, path):
        q = self.quadrant
        if q <= XPLUS_YMINUS:
            if q == XPLUS_YPLUS:
                p = (self.setMinX(path), self.setMinY(path))
            elif q == XMINUS_YPLUS:
                p = (self.setMaxX(path), self.setMinY(path))
            elif q == XMINUS_YMINUS:
                p = (self.setMaxX(path), self.setMaxY(path))
            elif q == XPLUS_YMINUS:
                p = (self.setMinX(path), self.setMaxY(path))
            pStr = path[0].p0
            pEnd = path[-1].p1
            path.append(Line(pEnd, p, i=INDEX_MARKER))
            path.append(Line(p, pStr, i=INDEX_MARKER))
        else:
            path[0].prt()
            path[-1].prt()
            (xStr, yStr) = pStr = path[0].p0
            (xEnd, yEnd) = pEnd = path[-1].p1
            dprt("xStr %7.4f yStr %7.4f xEnd %7.4f yEnd %7.4f" %
                 (xStr, yStr, xEnd, yEnd))
            if q == XPLUS:
                if abs(xStr - xEnd) < MIN_DIST:
                    path.append(Line(pEnd, pStr, i=INDEX_MARKER))
                else:
                    if xStr < xEnd:
                        l0Vertical = True
                        p = (xStr, yEnd)
                    else:
                        l0Vertical = False
                        p = (xEnd, yStr)
                    dprt("x %7.4f y %7.4f" % p)
                    l0 = Line(pEnd, p, i=INDEX_MARKER)
                    l1 = Line(p, pStr, i=INDEX_MARKER)
                    if l0Vertical:
                        l0.index -= 1
                    else:
                        l1.index -= 1
                    path.append(l0)
                    path.append(l1)
            elif q == YPLUS:
                if abs(yStr - yEnd) < MIN_DIST:
                    path.append(Line(pEnd, pStr, i=INDEX_MARKER))
                else:
                    if yStr < yEnd:
                        l0Horizontal = True
                        p = (xEnd, yStr)
                    else:
                        l0Horizontal = False
                        p = (xStr, yEnd)
                    dprt("x %7.4f y %7.4f" % p)
                    l0 = Line(pEnd, p, i=INDEX_MARKER)
                    l1 = Line(p, pStr, i=INDEX_MARKER)
                    if l0Horizontal:
                        l0.index -= 1
                    else:
                        l1.index -= 1
                    path.append(l0)
                    path.append(l1)
            elif q == XMINUS:
                if abs(xStr - xEnd) < MIN_DIST:
                    path.append(Line(pEnd, pStr, i=INDEX_MARKER))
                else:
                    if xEnd > xStr:
                        l0Vertical = False
                        p = (xEnd, yStr)
                    else:
                        l0Vertical = True
                        p = (xStr, yEnd)
                    dprt("x %7.4f y %7.4f" % p)
                    l0 = Line(pEnd, p, i=INDEX_MARKER)
                    l1 = Line(p, pStr, i=INDEX_MARKER)
                    if l0Vertical:
                        l0.index -= 1
                    else:
                        l1.index -= 1
                    path.append(l0)
                    path.append(l1)
                pass
            elif q == YMINUS:
                if abs(yStr - yEnd) < MIN_DIST:
                    path.append(Line(pEnd, pStr, i=INDEX_MARKER))
                else:
                    if yEnd > yStr:
                        l0Horizontal = True
                        p = (xStr, yEnd)
                    else:
                        l0Horizontal = False
                        p = (xEnd, yStr)
                    dprt("x %7.4f y %7.4f" % p)
                    l0 = Line(pEnd, p, i=INDEX_MARKER)
                    l1 = Line(p, pStr, i=INDEX_MARKER)
                    if l0Horizontal:
                        l0.index -= 1
                    else:
                        l1.index -= 1
                    path.append(l0)
                    path.append(l1)
            dprt()

    def setMinX(self, path):
        minX = MAX_VALUE
        for l in path:
            x0 = l.p0[0]
            x1 = l.p1[0]
            minX = min(minX, x0, x1)
        self.minX = minX
        return(minX)

    def setMaxX(self, path):
        maxX = MIN_VALUE
        for l in path:
            x0 = l.p0[0]
            x1 = l.p1[0]
            maxX = max(maxX, x0, x1)
        self.maxX = maxX
        return(maxX)

    def setMinY(self, path):
        minY = MAX_VALUE
        for l in path:
            y0 = l.p0[1]
            y1 = l.p1[1]
            minY = min(minY, y0, y1)
        self.minY = minY
        return(minY)

    def setMaxY(self, path):
        maxY = MIN_VALUE
        for l in path:
            y0 = l.p0[1]
            y1 = l.p1[1]
            maxY = max(maxY, y0, y1)
        self.maxY = maxY
        return(maxY)
