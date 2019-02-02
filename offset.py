from __future__ import print_function

from math import atan2, degrees, hypot, sqrt
from geometry import ARC, CCW, CW, LINE, MAX_VALUE, MIN_DIST, MIN_VALUE
from geometry import Arc, Line, Point
from geometry import calcAngle, combineArcs, eqnLine, newPoint, orientation, \
    oStr, pathDir, reverseSeg, splitArcs, xyDist
from dbgprt import dprt, dprtSet, ePrint
from sortedlist import SortedList
from collections import namedtuple

LEFT      = 0
RIGHT     = 1
INTERSECT = 2

evtStr = ('L', 'R', 'I')

EventPair = namedtuple('EventPair', ['start', 'end'])
Intersection = namedtuple('Intersection', ['loc', 'p', 'l0', 'l1'])

keyScale = None

class Offset():
    def __init__(self, cfg):
        self.cfg = cfg
        self.dir = None
        self.dist = 0.0
        self.scale = 10000
        self.splitArcAngle = 90
        self.keyScale = None
        self.cmds = \
        (
            ('dxfoffset', self.offset), \
            ('offsetdist', self.setOffsetDist), \
            ('offsetdir', self.setOffsetDir), \
            ('offsetintersect', self.offsetIntersect), \
            ('offsetlinearc', self.lineArcTest), \
            ('offsetarcarc', self.arcArcTest), \
        )
        self.intersections = None
        self.dbgIntersection = None
        self.setKeyScale(100)
        self.dbg = True
        self.drawInitial = True
        self.dbgOffset = False
        self.drawOffset = False
        self.dbgIntersect = False
        self.intersectReturn = False
        self.drawSplitLines = False
        self.dbgPolygons = False
        self.drawFinalPoly = True
        self.drawWindingNum = False
        dprtSet(True)

    def setOffsetDist(self, args):
        self.dist = self.cfg.evalFloatArg(args[1])

    def setOffsetDir(self, args):
        val = args[1].lower()
        if val == "cw":
            self.dir = CW
        elif val == "ccw":
            self.dir = CCW
        else:
            self.dir = None

    def setKeyScale(self, scale):
        global keyScale
        self.keyScale = scale
        keyScale = scale

    def offset(self, args):
        if self.dist == 0:
            return
        cfg = self.cfg
        cfg.ncInit()
        layer = cfg.getLayer(args)
        segments = cfg.dxfInput.getPath(layer, dbg=True)

        distance = self.dist
        direction = self.dir
        if direction is None:
            direction = CCW if distance > 0 else CW
        else:
            distance = abs(distance)
            if direction == CW:
                distance = -distance

        passes = MAX_VALUE
        if len(args) > 2:
            passes = cfg.evalIntArg(args[2])

        dbgPass = MAX_VALUE
        if len(args) > 3:
            dbgPass = cfg.evalIntArg(args[3])

        total = 0
        count = 0
        while len(segments) > 0:
            dprt("***count %d*** %d" % (count, len(segments[0])))
            finalPolygons = self.offsetPath(segments, direction, distance)
            if finalPolygons is None:
                break
            if len(finalPolygons) == 0:
                break
            total += distance
            segments = finalPolygons
            count += 1
            if count >= passes:
                break
            if count >= dbgPass:
                self.drawOffset = True
                self.dbgIntersect = True
                self.drawSplitLines = True
                self.drawWindingNum = True

    def offsetPath(self, segments, direction, distance):
        cfg = self.cfg
        dbgOffset = self.dbgOffset # ++dbg++
        drawOffset = self.drawOffset
        if dbgOffset and drawOffset:
            drawX = cfg.draw.drawX
        for seg in segments:
            newSeg = splitArcs(seg, self.splitArcAngle)

            for i, l in enumerate(newSeg):
                l.index = i
            
            curDir = pathDir(newSeg, False)
            if curDir == 0:
                ePrint("###direction error###")
            if curDir != direction:
                newSeg = reverseSeg(newSeg)
            if dbgOffset:
                dprt("direction %s" % (oStr(direction)))

            (p, chkList) = self.insidePoint(newSeg)
            wNInitial = windingNumber(p, chkList, self.scale, dbg=False)
            if wNInitial == 1:
                wNDirection = CCW
            elif wNInitial == -1:
                wNDirection = CW
            else:
                wNDirection = None
            dprt("wNInitial %2d wNDirection %s" % \
                 (wNInitial, oStr(wNDirection)))

            prevL = newSeg[-1]
            prevL1 = prevL.parallel(distance)
            oSeg = []
            for (n, l) in enumerate(newSeg):
                if self.drawInitial:
                    l.draw()
                    if dbgOffset:
                        l.label()
                (x0, y0) = prevL.p0
                (x1, y1) = l.p0
                (x2, y2) = l.p1
                o = orientation(prevL.p0, l.p0, l.p1)
                a0 = atan2(y0 - y1, x0 - x1)
                a1 = atan2(y2 - y1, x2 - x1)
                if dbgOffset:
                    prevL.prt()
                    l.prt()
                    dprt("0 (%7.4f %7.4f) 1 (%7.4f %7.4f) "\
                            "2 (%7.4f %7.4f)" % \
                            (x0, y0, x1, y1, x2, y2))
                    dprt("n %2d a0 %7.2f a1 %7.2f a1-a0 %7.2f "\
                            "orientation %s" % \
                            (n, degrees(a0), degrees(a1), \
                            degrees(a0 - a1), oStr(o)))
                l1 = l.parallel(distance)
                if l1 is None:
                    l0 = Line(l.p0, l.p1)
                    l1 = l0.parallel(distance)
                if dbgOffset:
                    l1.prt()
                    dprt("%2d %2d dist %7.4f" % \
                         (prevL.index, l.index, xyDist(prevL1.p1, l1.p0)))
                    if drawOffset:
                        l1.draw()
                        l1.label(str(l1.index))
                if xyDist(prevL1.p1, l1.p0) > MIN_DIST:
                    if o == direction: # convex
                        lEnd = Line(prevL1.p1, l.p0)
                        lStr = Line(l.p0, l1.p0)
                        oSeg.append(lEnd)
                        oSeg.append(lStr)

                        if dbgOffset:
                            dprt("convex")
                            if drawOffset:
                                lEnd.draw()
                                drawX(prevL1.p1, str(-n))
                                lStr.draw()
                                drawX(l1.p0, str(n))
                    else:           # concave
                        if direction == CCW:
                            a1 = degrees(calcAngle(l.p0, prevL1.p1))
                            a0 = degrees(calcAngle(l.p0, l1.p0))
                            aDir = CW
                        else:
                            a0 = degrees(calcAngle(l.p0, prevL1.p1))
                            a1 = degrees(calcAngle(l.p0, l1.p0))
                            aDir = CCW
                        lArc = Arc(l.p0, abs(distance), a0, a1, \
                                    direction=aDir)

                        if dbgOffset:
                            dprt("concave")
                            dprt("n %2d a0 %7.2f a1 %7.2f %s" % \
                                    (n, a0, a1, oStr(aDir)))
                            lArc.prt()
                            if drawOffset:
                                drawX(l.p0, "C")
                                drawX(prevL1.p1, "0")
                                drawX(l1.p0, "1")
                                lArc.draw()
                        oSeg.append(lArc)
                oSeg.append(l1)
                prevL = l
                prevL1 = l1

            # if dbgOffset:
            #     return
            
            oldSeg = oSeg
            oSeg = splitArcs(oldSeg, self.splitArcAngle)
            
            dbgIntersect = self.dbgIntersect # ++dbg++
            for n, l in enumerate(oSeg):
                l.index = n
                l.prt()
                if dbgIntersect:
                    l.draw()
                    l.label()
                    # cfg.draw.drawX(l.p0, str(n))

            self.intersections = []
            self.findIntersections(oSeg)

            if dbgIntersect:
                dprt("\nintersections")
                for n, i in enumerate(self.intersections):
                    dprt("%2d (%7.4f %7.4f) %2d %2d" %
                         (n, i.loc.x, i.loc.y, i.l0.index, i.l1.index))
                    cfg.draw.drawX(i.loc, "")
                if self.intersectReturn:
                    return

            dprt("\npoints")
            for (loc, _, l0, l1) in self.intersections:
                dprt("(%7.4f %7.4f) %2d %2d" % \
                     (loc.x, loc.y, l0.index, l1.index))

            dprt("\nsplit lines")
            oSeg1 = []
            for l in oSeg:
                points = []
                for (loc, _, l0, l1) in self.intersections:
                    if l.index == l0.index or l.index == l1.index:
                        points.append(loc)

                if len(points) != 0:
                    while len(points) != 0:
                        minDist = MAX_VALUE
                        for i, loc in enumerate(points):
                            d = xyDist(l.p0, loc)
                            if d < minDist:
                                minDist = d
                                splitLoc = loc
                                index = i
                        points.pop(index)
                        l0 = l.splitPoint(splitLoc)
                        if l0.length > MIN_DIST:
                            oSeg1.append(l0)
                if l.length > MIN_DIST:
                    oSeg1.append(l)

            dprt("\nOseg1")
            for l in oSeg1:
                if l is not None:
                    l.prt()
                else:
                    dprt("missing")
            
            dprt()
            pToLine = {}
            oSeg2 = []
            scale = self.scale * self.keyScale
            ptIndex = 0
            for i, l in enumerate(oSeg1):
                l.index = i
                if self.drawSplitLines:
                    l.draw()
                    l.label()
                l0 = IntLine(l, self.scale)
                oSeg2.append(l0)

                p0 = l0.p0
                key = p0.y + p0.x * scale
                if not key in pToLine:
                    pToLine[key] = PointLine(p0, l0, ptIndex)
                    # cfg.draw.drawX(l.p0, str(i))
                    l0.p0Index = ptIndex
                    ptIndex += 1
                else:
                    pL = pToLine[key]
                    pL.append(l0)
                    l0.p0Index = pL.index

                p1 = l0.p1
                key = p1.y + p1.x * scale
                if not key in pToLine:
                    pToLine[key] = PointLine(p1, l0, ptIndex)
                    # cfg.draw.drawX(l.p1, str(i))
                    l0.p1Index = ptIndex
                    ptIndex += 1
                else:
                    pL = pToLine[key]
                    pL.append(l0)
                    l0.p1Index = pL.index
                l0.prt()

            pLine = [None] * len(pToLine)
            # for (_, pL) in pToLine.iteritems():
            for (_, pL) in pToLine.items():
                pLine[pL.index] = pL

            dprt()
            for pL in pLine:
                p = pL.p
                dprt("%2d (%6d %6d) - (" % (pL.index, p.x, p.y), end='')
                for i, intLine in enumerate(pL.l):
                    if i != 0:
                        dprt(", ", end='')
                    dprt("%2d" % (intLine.l.index,), end='')
                dprt(")")

            dbgPolygons = self.dbgPolygons
            polyList = []
            dprt("\nlink segments into polygons")
            for i in range(len(oSeg2)): # while lines to process
                index = i               # set place to start
                poly = []
                while True:		# while not at end
                    iL = oSeg2[index]   # get next segment
                    if iL is None:      # if no segment
                        break           # exit loop
                    oSeg2[index] = None # mark as processed
                    iL.prt()
                    p1Index = iL.p1Index    # get point index
                    poly.append(iL.l)         # append to polygon
                    pL = pLine[p1Index]     # look up point
                    for l in pL.l: 	    # loop over connected lines
                        # l.l.prt()
                        index = l.l.index   # get the line index
                        if iL.l.index == index: # if same line
                            continue            # skip
                        if len(pL.l) == 2:      # if only two lines
                            break
                        (x0, y0) = iL.p1      # point location
                        (x1, y1) = l.p0       # start of line
                        if ((x0 == x1) and (y0 == y1) and # if line start
                            not iL.l.colinear(l.l)): # and not colinear
                            break
                    else:
                        dprt("not found")
                if len(poly) != 0:
                    polyList.append(poly)
                    dprt()
                    
            dprt("polyList %d" % (len(polyList)))
            dprt("calculate polygon winding number")
            finalPolygons = []
            for poly in polyList:
                # direction = pathDir(poly)
                # dprt("direction %s" % (oStr(direction)))
                for l in poly:
                    l.prt()
                if True:
                    (p, chkList) = self.insidePoint(poly)
                    if p is not None:
                        wN = windingNumber(p, chkList, self.scale, dbg=False)
                        if wN == wNInitial:
                            newPoly = combineArcs(poly)
                            finalPolygons.append(newPoly)
                        dprt("wN %2d (%7.4f %7.4f)" % (wN, p.x, p.y))
                        if self.drawWindingNum:
                            self.cfg.draw.drawX(p, str(wN))
                dprt()

            if self.drawFinalPoly:
                for poly in finalPolygons:
                    for l in poly:
                        l.draw()
                        l.label()
            return finalPolygons

    def findIntersections(self, seg):
        pointData = open("points.dat", "wb")
        self.dbgIntersection = []
        self.evtList = evtList = SortedList()
        self.evtArray = [None] * len(seg)
        for l in seg:
            scale = self.scale
            p0 = newPoint(l.p0, scale)
            p1 = newPoint(l.p1, scale)
            if pointData != None:
                pointData.write(b"%6d,%6d,%6d,%6d\n" % \
                                (p0.x, p0.y, p1.x, p1.y))
            x0 = p0.x
            x1 = p1.x
            if x0 < x1:
                self.addEvent(p0, p1, l)
            elif x1 < x0:
                self.addEvent(p1, p0, l)
            else:
                if p0.y < p1.y:
                    self.addEvent(p0, p1, l)
                else:
                    self.addEvent(p1, p0, l)
        if pointData != None:
            pointData.close()
        
        # evtList = sorted(evtList, key=lambda l: (l.p.x, l.p.y))
        dprt()
        for l in evtList:
            l.prt()

        self.sweepList = sweepList = SortedList()
        dprt()
        lastX = 0
        dbgList = []
        self.event = 0
        while len(evtList) > 0:
            evt = evtList.pop(0)
            evt.event = False
            self.curX = evt.p.x
            dprt("%2d" % (self.event), end=' ')
            evt.prt(end=' ')
            if evt.evtType == LEFT:
                sweepList.add(evt)
                index = sweepList.bisect_left(evt)
                sweepLen = len(sweepList)
                self.sweepPrt(evt, sweepLen, index)
                l = evt.l
                vertical = abs(l.p0.x - l.p1.x) < MIN_DIST
                idxLeft = index - 1
                y = None
                while idxLeft >= 0:
                    evtLeft = sweepList[idxLeft]
                    if y is None:
                        y = evtLeft.p.y
                        self.intersect(evtLeft, evt, 0)
                    else:
                        if y == evtLeft.p.y:
                            self.intersect(evtLeft, evt, 1)
                        elif vertical:
                            self.intersect(evtLeft, evt, 2)
                        else:
                            break
                    idxLeft -= 1

                sweepLen = len(sweepList)
                idxRight = index + 1
                y = None
                while idxRight < sweepLen:
                    evtRight = sweepList[idxRight]
                    if y is None:
                        y = evtRight.p.y
                        self.intersect(evt, evtRight, 3)
                    else:
                        if y == evt.p.y:
                            self.intersect(evt, evtRight, 4)
                        elif vertical:
                            self.intersect(evtLeft, evt, 5)
                        else:
                            break
                    idxRight += 1

                self.listPrt()
            elif evt.evtType == RIGHT:
                index = sweepList.bisect_left(evt)
                sweepLen = len(sweepList)
                self.sweepPrt(evt, sweepLen, index)
                try:
                    curEvt = sweepList[index]
                except IndexError:
                    pass
                if curEvt.key != evt.key:
                    ePrint("remove key error %2d %9d %2d %9d" % \
                           (evt.index, evt.key, curEvt.index, curEvt.key))
                    
                if index > 0:
                    idxLeft = index - 1
                    idxRight = index + 1
                    if idxRight < sweepLen:
                        evtLeft = sweepList[idxLeft]
                        evtRight = sweepList[idxRight]
                        self.intersect(evtLeft, evtRight, 6)
                sweepList.pop(index)
                self.listPrt()
            elif evt.evtType == INTERSECT:
                sweepLen = len(sweepList)
                self.sweepPrt(evt, sweepLen)
                if self.curX >= lastX:
                    evt0 = evt.evt0
                    evt1 = evt.evt1                

                    dbgTxt = "(%2d %2d)" % (evt0.index, evt1.index)
                    dbgTxt += " ("
                    for n, e in enumerate(sweepList):
                        if n != 0:
                            dbgTxt += " "
                        dbgTxt += "%2d" % (e.index)
                    dbgTxt += ")"

                    (x, y) = evt.p
                    key = y * self.keyScale
                    index0 = sweepList.bisect_left(evt0)
                    dbgTxt += " (%2d" % (index0)
                    if index0 < sweepLen:
                        evtP0 = sweepList[index0]
                        if evt0.key == evtP0.key:
                            sweepList.pop(index0)
                            evt0.key = key + 1
                            # evt0.p = Point(x, y + 1)
                            self.evtArray[evt0.index].end.key = evt0.key
                            sweepList.add(evt0)

                    index1 = sweepList.bisect_left(evt1)
                    dbgTxt += " %2d)" % (index1)
                    if index1 < sweepLen:
                        evtP1 = sweepList[index1]
                        if evt1.key == evtP1.key:
                            sweepList.pop(index1)
                            evt1.key = key - 1
                            # evt1.p = Point(x, y - 1)
                            self.evtArray[evt1.index].end.key = evt1.key
                            sweepList.add(evt1)

                    dbgTxt += " (%2d %2d)" % (evt1.index, evt0.index)
                    dbgTxt += " ("
                    for n, e in enumerate(sweepList):
                        if n != 0:
                            dbgTxt += " "
                        dbgTxt += "%2d" % (e.index)
                    dbgTxt += ")"

                    index = sweepList.bisect_left(evt1)
                    dbgTxt += " (%2d -> %2d)" % (evt1.index, index)
                    indexP = index - 1
                    if indexP >= 0:
                        evtP = sweepList[indexP]
                        dbgTxt += " (%2d %2d)" % (evtP.index, evt1.index)
                        self.intersect(evtP, evt1, 7)

                    indexN = index + 2
                    if indexN < sweepLen:
                        evtN = sweepList[indexN]
                        dbgTxt += " (%2d %2d)" % (evt0.index, evtN.index)
                        self.intersect(evt0, evtN, 8)
                self.listPrt()
                dbgList.append(dbgTxt)
            lastX = self.curX
            self.event += 1
        dprt()
        for txt in dbgList:
            dprt(txt)

        dprt()
        for i, (e, n, idx0, idx1, flag) in enumerate(self.dbgIntersection):
            dprt("%3d %2d (%2d %2d) %s %d" % \
                 (i, e, idx0, idx1, str(flag)[0], n))
        dprt("sweepLen %d" % (len(sweepList)))

    def addEvent(self, p0, p1, l):
        evtStr = Event(p0, l, LEFT)
        evtEnd = Event(p1, l, RIGHT, evtStr.key)
        evtStr.evtEnd = evtEnd
        self.evtList.add(evtStr)
        self.evtList.add(evtEnd)
        self.evtArray[l.index] = EventPair(evtStr, evtEnd)

    def intersect(self, evt0, evt1, n):
        l0 = evt0.l
        l1 = evt1.l
        if (xyDist(l0.p1, l1.p0) < MIN_DIST or
            xyDist(l1.p1, l0.p0) < MIN_DIST):
            self.dbgIntersection.append((self.event, n, l0.index, \
                                         l1.index, False))
            return
        self.dbgIntersection.append((self.event, n, l0.index, \
                                     l1.index, True))

        if l0.type == LINE:
            if l1.type == LINE:
                loc = lineIntersection(l0, l1)
                if isinstance(loc, int) and loc == 1:
                    return None
                    # return self.colinear(evt0, evt1)
            else:
                loc = lineArcTest(l0, l1)
        else:
            if l1.type == LINE:
                loc = lineArcTest(l1, l0)
            else:
                loc = arcArcTest(l0, l1)

        if loc is not None:
            self.iEvt(loc, evt0, evt1)

# l0 l0Str ---------------------------------------- l0End
# l1              l1Str --------------- l1End
# l0 l0Str ------ l1str
# l1                                    l1End ----- l0End

    def colinear(self, evt0, evt1):
        if evt1.l.length > evt0.l.length:
            (evt0, evt1) = (evt1, evt0)
        l0 = evt0.l
        l1 = evt1.l
        scale = self.scale
        if l1.p1.x < l0.p1.x: # if l1 end < l0 end
            e = self.evtArray[evt0.index].end # get l0 end
            index = self.evtList.bisect_left(e)
            self.evtList.pop(index) # remove from event list
            e.event = False
            self.sweepList.remove(e) # remove from sweep list

            e = self.evtArray[evt1.index].end # get l1 end
            index = self.evtList.bisect_left(e)
            self.evtList.pop(index)  # rm end from evt
            e.event = False          # chg to key
            self.sweepList.remove(e) # rm end from sweep

            (l1Str, l1End) = (l1.p0, l1.p1)
            if l1.p0.x > l1.p1.x:
                (l1Str, l1End) = (l1End, l1Str)

            if l0.p0.x < l0.p1.x: # update end point of l0
                l0End = l0.p1
                l1.updateP0(l1End) # start of l1
                l1.updateP1(l0End) # end of l1
                l0.updateP1(l1Str) # end of l0
                self.addEvent(newPoint(l1End, scale), \
                              newPoint(l0End, scale), l1)
            else:
                l0End = l0.p0
                l1.updateP1(l1End) # start of l1
                l1.updateP0(l0End) # end of l1
                l0.updateP0(l1Str) # end of l0
                self.addEvent(newPoint(l0End, scale), \
                              newPoint(l1End, scale), l1)

        else:
            pass
            # else
            #  remove l0 end from evt list
            #  add another start for l1 at l0 end
        return None

    def iEvt(self, loc, evt0, evt1):
        if loc is not None:
            if evt0.key > evt1.key:
                dprt("iEvt segments out of order")
            p = newPoint(loc, self.scale)
            if p.x >= self.curX:
                for _, pI, _, _ in self.intersections:
                    if p.x == pI.x and p.y == pI.y:
                        return
                evt = Intersect(p, loc, evt0, evt1)
                self.intersectionPrt(evt0.index, evt1.index, loc)
                # self.cfg.draw.drawX(loc, str(self.intCount))
                self.evtList.add(evt)
                self.intersections.append(Intersection(loc, p, evt0.l, evt1.l))
                self.intCount += 1

    def sweepPrt(self, evt, sweepLen, sweepIndex=None):
        self.intCount = 0
        dprt("%s " % (evtStr[evt.evtType]), end='')
        if evt.evtType != INTERSECT:
            dprt("%2d x %6d l %2d i %2d" % \
                 (evt.index, evt.p.x, sweepLen, sweepIndex), end='')
        else:
            dprt("   x %6d l %2d     " % \
                 (evt.p.x, sweepLen), end='')

    def listPrt(self):
        while self.intCount < 2:
            self.intCount += 1
            self.noIntersection()
        dprt(" (", end='')
        for (i, s) in enumerate(self.sweepList):
            if i != 0:
                dprt(", ", end='')
            dprt("%2d %7d" % (s.l.index, s.key), end='')
        dprt(")")

    def sweepListPrt(self):
        for e in self.sweepList:
            e.prt()

    def evtListPrt(self):
        for evt in self.evtList:
            evt.prt()

    def evtArrayPrt(self):
        for n, (evtStr, evtEnd) in enumerate(self.evtArray):
            dprt("%2d" % (n), end=' ')
            evtStr.prt(end=' ')
            evtEnd.prt()
        
    def intersectionPrt(self, index0, index1, loc):
        dprt(" (%2d %2d)" % (index0, index1), end='')
        
        if loc is not None:
            dprt(" (%5.2f %5.2f)" % (loc.x, loc.y), end='')
        else:
            dprt("              ", end='')

    def noIntersection(self):
        dprt("        ", end='')
        dprt("              ", end='')

    def insidePoint(self, seg, dbg=False):
        drawTest = False
        if dbg:
            dprt("\ninsidePoint")
        self.evtList = evtList = SortedList()
        self.evtArray = [None] * len(seg)
        for l in seg:
            scale = self.scale
            p0 = newPoint(l.p0, scale)
            p1 = newPoint(l.p1, scale)
            x0 = p0.x
            x1 = p1.x
            if x0 < x1:
                self.addInsideEvent(p0, p1, l)
            elif x1 < x0:
                self.addInsideEvent(p1, p0, l)
        if dbg:
            x0 = evtList[0].p.x
            d = 0
            sweepLen = 0
            for e in evtList:
                if e.p.x != x0:
                    d = e.p.x - x0
                dprt("%6d %2d " % (d, sweepLen), end='')
                e.prt(end=' ')
                e.l.prt()

                if e.evtType == LEFT:
                    sweepLen += 1
                elif e.evtType == RIGHT:
                    sweepLen -= 1
                x0 = e.p.x
            dprt()
        self.sweepList = sweepList = SortedList()
        minY = min(seg, key=lambda l: l.p0.y).p0.y - .1
        maxY = max(seg, key=lambda l: l.p0.y).p0.y + .1
        x0 = 0
        p = None
        d = 0
        maxDist = MIN_VALUE
        chkList = []
        while len(evtList) > 0:
            evt = evtList.pop(0)
            evt.event = False
            x = evt.p.x
            sweepLen = len(sweepList)
            if sweepLen >= 2 and ((sweepLen & 1)) == 0:
                if x != x0:
                    d = x - x0
                    if d > maxDist:
                        maxDist = d
                        xTest = (x + x0) / (2.0 * self.scale)
                        lTest = Line((xTest, minY), (xTest, maxY))
                        if drawTest:
                            lTest.draw()
                        l0 = sweepList[0].l
                        l1 = sweepList[1].l
                        pMin = self.insideIntersect(lTest, l0)
                        pMax = self.insideIntersect(lTest, l1)
                        if pMin is not None and pMax is not None:
                            p = Point(xTest, (pMax.y + pMin.y) / 2.0)
                            chkList = []
                            for e in sweepList:
                                chkList.append(e.l)
                        else:
                            dprt("insidePoint error x0 %6d x %6d %2d %2d" % \
                                 (x0, x, l0.index, l1.index))
                            lTest.prt()
                            l0.prt()
                            l1.prt()
                            break
            if evt.evtType == LEFT:
                x0 = x
                self.sweepList.add(evt)
                if dbg:
                    self.sweepPrt(evt, sweepLen, 0)
                    self.listPrt(sweepList)
            elif evt.evtType == RIGHT:
                try:
                    if dbg:
                        self.sweepPrt(evt, sweepLen, 0)
                    sweepList.remove(evt)
                    if dbg:
                        self.listPrt(sweepList)
                except ValueError:
                    self.listPrt(sweepList)
                    dprt("insidePoint list error")
                    evt.prt()
            x0 = x
        if dbg:
            dprt("\ninsidePoint maxDist %6d (%7.4f %7.4f)" % \
                 (maxDist, p.x, p.y))
            for l in chkList:
                l.prt()
            dprt()
        sweepList.clear()
        return(p, chkList)

    def addInsideEvent(self, p0, p1, l):
        evtStr = Event(p0, l, LEFT)
        evtEnd = Event(p1, l, RIGHT, evtStr.key)
        self.evtList.add(evtStr)
        self.evtList.add(evtEnd)

    def offsetIntersect(self, args):
        cfg = self.cfg
        cfg.ncInit()
        layer = cfg.getLayer(args)
        seg = cfg.dxfInput.getObjects(layer)
        lineSegment = []
        dprt()
        for l in seg:
            l.draw()
            l.label()
            # cfg.draw.drawX(l.p0, str(l.index))
            l.prt()
            lineSegment.append((l.p0, l.p1))
        self.intersections = []
        self.findIntersections(seg)
        for loc, _, _, _ in self.intersections:
            cfg.draw.drawX(loc)

    def insideIntersect(self, l0, l1):
        if l0.type == LINE:
            if l1.type == LINE:
                loc = lineIntersection(l0, l1)
                if isinstance(loc, int):
                    return None
                return loc
            else:
                return lineArcTest(l0, l1)
        else:
            if l1.type == LINE:
                return lineArcTest(l1, l0)
            else:
                return arcArcTest(l0, l1)

    def lineArcTest(self, args):
        cfg = self.cfg
        cfg.ncInit()
        layer = cfg.getLayer(args)
        seg = cfg.dxfInput.getObjects(layer)
        lines = []
        arcs = []
        for l in seg:
            l.prt()
            if l.type == LINE:
                lines.append(l)
                l.draw()
            elif l.type == ARC:
                arcs.append(l)

        dprt()
        arcsIn = arcs
        arcs = splitArcs(arcsIn, self.splitArcAngle)
        for a in arcs:
            a.draw()

        for a in arcs:
            dprt()
            a.prt()
            for l in lines:
                l.prt()
                p = lineArcTest(l, a)
                if p is not None:
                    cfg.draw.drawX(p, '')
                    
    def arcArcTest(self, args):
        cfg = self.cfg
        cfg.ncInit()
        layer = args[1]
        refArc = cfg.dxfInput.getObjects(layer)
        layer = args[2]
        testArc = cfg.dxfInput.getObjects(layer)

        refArc = splitArcs(refArc, self.splitArcAngle)
        testArc = splitArcs(testArc, self.splitArcAngle)

        for a in refArc:
            a.draw()

        for a in testArc:
            a.draw()

        for a0 in refArc:
            dprt()
            a0.prt()
            for a1 in testArc:
                a1.prt()
                p = arcArcTest(a0, a1)
                if p is not None:
                    cfg.draw.drawX(p, '')

class Event:
    def __init__(self, p, l=None, evtType=None, key=None):
        self.evtType = evtType
        self.p = p
        self.l = l
        if l is not None:
            self.index = l.index
            self.event = True
            if key is None:
                self.key = self.p.y * keyScale + l.index
            else:
                self.key = key
        else:
            self.evtType = INTERSECT
            self.event = False
            self.key = self.p.y * keyScale
            self.index = -1
            self.l = None
            
    def prt(self, end='\n'):
        dprt("p (%6d %6d) %2d %9d %s" % \
                (self.p.x, self.p.y, self.index, self.key, \
                evtStr[self.evtType]), end)

    def __str__(self):
        return("p (%6d %6d) %2d %9d %s" % \
               (self.p.x, self.p.y, self.index, self.key, \
                evtStr[self.evtType]))

    def __gt__(self, other):
        # if not isinstance(other, Event):
        #     raise Exception("")
        # else:
        if self.event:
            if self.p.x == other.p.x:
                if self.p.y == oth.p.y:
                    return self.index > other.index
                else:
                    return self.p.y > other.p.y
            else:
                return self.p.x > other.p.x
        else:
            return self.key > other.key

    def __lt__(self, other):
        # if not isinstance(other, Event):
        #     raise Exception("")
        # else:
        if self.event:
            if self.p.x == other.p.x:
                if self.p.y == other.p.y:
                    return self.index < other.index
                else:
                    return self.p.y < other.p.y
            else:
                return self.p.x < other.p.x
        else:
            return self.key < other.key

    def __eq__(self, other):
        # if not isinstance(other, Event):
        #     raise Exception("")
        # else:
        if self.event:
            if self.p.x == other.p.x:
                if self.p.y == other.p.y:
                    return self.index == other.index
            return False
        else:
            return self.key == other.key

class Intersect:
    def __init__(self, p, loc, evt0, evt1):
        self.evtType = INTERSECT
        self.p = p
        self.loc = loc
        self.evt0 = evt0
        self.evt1 = evt1
    
    def prt(self, end='\n', l=False):
        evt0 = self.evt0
        evt1 = self.evt1
        dprt("p (%6d %6d) %2d %2d %s      I" % \
             (self.p.x, self.p.y, evt0.index, evt1.index, \
              str(evt0.key > evt1.key)[0]), end='')
        if l:
            dprt(" %2d %2d" % (self.evt0.index, self.evt1.index), '')
        dprt(end=end)

    def __str__(self):
        return("p (%6d %6d)              %s" % \
               (self.p.x, self.p.y, \
                evtStr[self.evtType]))

    def __gt__(self, other):
        if self.p.x == other.p.x:
            return self.p.y > other.p.y
        else:
            return self.p.x > other.p.x

    def __lt__(self, other):
        if self.p.x == other.p.x:
            return self.p.y < other.p.y
        else:
            return self.p.x < other.p.x

    def __eq__(self, other):
        if self.p.x == other.p.x:
            return self.p.y == other.p.y
        return False
        
class IntLine:
    def __init__(self, l, scale):
        self.p0 = newPoint(l.p0, scale)
        self.p1 = newPoint(l.p1, scale)
        self.p0Index = None
        self.p1Index = None
        self.l = l

    def prt(self):
        dprt("%2d (%6d %6d) (%6d %6d) (%2d %2d)" % \
             (self.l.index, self.p0.x, self.p0.y, self.p1.x, self.p1.y,
              self.p0Index, self.p1Index), " ")
        self.l.prt()

class PointLine:
    def __init__(self, p, l, ptIndex):
        self.p = p
        self.index = ptIndex
        self.l = []
        self.l.append(l)

    def append(self, l):
        self.l.append(l)
        
def windingNumber(p, poly, scale, dbg=False):
    (x, y) = newPoint(p, scale)
    l = poly[0]
    # (x0, y0) = newPoint(l.p0, scale)
    # x0 -= x
    # y0 -= y
    wN = 0
    if dbg:
        dprt("\nwindingNum\n")
        for l in poly:
            l.prt()
        dprt("\np (%7.4f %7.4f) (%6d %6d)\n" % (p.x, p.y, x, y))
    for l in poly:
        (x0, y0) = newPoint(l.p0, scale)
        x0 -= x
        y0 -= y
        (x1, y1) = newPoint(l.p1, scale)
        x1 -= x
        y1 -= y
        if dbg:
            dprt("%2d (%6d %6d) (%6d %6d)" % \
                 (l.index, x0, y0, x1, y1), end='')
        if (x0 < 0 and x1 > 0 or \
            x1 < 0 and x0 > 0):
            if x0 != x1:
                r = y0 + x0 * float(y1 - y0) / float(x0 - x1)
                if r > 0:
                    if x1 < 0:
                        wN += 1
                    else:
                        wN -= 1
                if dbg:
                    dprt(" r %6.0f wN %2d" % (r, wN), end='')
        # (x0, y0) = (x1, y1)
        if dbg:
            dprt()
    return wN

def lineIntersection(l0, l1):
    p0 = l0.p0
    p1 = l0.p1
    p2 = l1.p0
    p3 = l1.p1
    s10_x = p1.x - p0.x
    s10_y = p1.y - p0.y
    s32_x = p3.x - p2.x
    s32_y = p3.y - p2.y

    denom = s10_x * s32_y - s32_x * s10_y

    if abs(denom) < MIN_DIST:
        return 1                # collinear

    denomPositive = denom > 0

    s02_x = p0.x - p2.x
    s02_y = p0.y - p2.y

    s_numer = s10_x * s02_y - s10_y * s02_x

    if (s_numer < 0) == denomPositive:
        return None             # no collision

    t_numer = s32_x * s02_y - s32_y * s02_x

    if (t_numer < 0) == denomPositive:
        return None             # no collision

    if (s_numer > denom) == denomPositive or \
        (t_numer > denom) == denomPositive:
        return None             # no collision

    # collision detected

    t = t_numer / denom

    iPt = Point(p0.x + (t * s10_x), p0.y + (t * s10_y))
    # dprt("intersection %2d %2d (%7.4f %7.4f)" %
    #      (l0.index, l1.index, iPt.x, iPt.y))
    if xyDist(iPt, p0) < MIN_DIST or \
        xyDist(iPt, p1) < MIN_DIST:
        return None
    return iPt

def lineArcTest(l, a):
    (x0, y0) = l.p0             # start and end
    (x1, y1) = l.p1

    (i, j) = a.c                # center of arc
    x0 -= i                     # subtract center of arc
    y0 -= j
    x1 -= i
    y1 -= j

    (m, b, xGreater) = eqnLine((x0, y0), (x1, y1)) # equation of line
    qA = 1 + m*m
    qB = 2 * m * b
    qC = b*b - a.r*a.r
    sqrTerm = qB*qB - 4 * qA * qC
    qA *= 2

    if abs(sqrTerm) < MIN_DIST: # if tangent
        if xGreater:
            x = -qB / qA
            y = m * x + b
        else:
            y = -qB / qA
            x = m * y + b
        x += i
        y += j
        p = Point(x, y)

        if l.onSegment(p):
            if a.onSegment(p):
                return p
        return None

    if sqrTerm < 0:             # no intersection
        return None

    sqrTerm = sqrt(sqrTerm)     # if two intersections
    plus = (-qB + sqrTerm) / qA
    minus = (-qB - sqrTerm) / qA
    if xGreater:                # if using y = mx + b
        xP = plus
        yP = m * xP + b
        xM = minus
        yM = m * xM + b
    else:                       # if using x = my + b
        yP = plus
        xP = m * yP + b
        yM = minus
        xM = m * yM + b

    pP = Point(xP + i, yP + j)
    pM = Point(xM + i, yM + j)

    if a.onSegment(pP):
        p = pP
    elif a.onSegment(pM):
        p = pM
    else:
        p = None

    if p is not None:
        if l.onSegment(p):
            return p
    return None

# arc arc intersection
#
# Let the centers be: (a,b), (c,d)
# Let the radii be: r, s

#   e = c - a                          [difference in x coordinates]
#   f = d - b                          [difference in y coordinates]
#   p = sqrt(e^2 + f^2)                [distance between centers]
#   k = (p^2 + r^2 - s^2)/(2p)         [distance from center 1 to line
#                                       joining points of intersection]
#   sin(angle) = f/p
#   cos(angle) = e/p
#
#   x = a + k(e/p) + (f/p)sqrt(r^2 - k^2)
#   y = b + k(f/p) - (e/p)sqrt(r^2 - k^2)
# or
#   x = a + k(e/p) - (f/p)sqrt(r^2 - k^2)
#   y = b + k(f/p) + (e/p)sqrt(r^2 - k^2)

# cos(a + b) = cos(a) cos(b)   sin(a) sin(b)
# sin(a + b) = sin(a) cos(b) + cos(a) sin(b)

# x = r cos a
# y = r sin a

# x' = r cos ( a + b ) = r cos a cos b - r sin a sin b
# y' = r sin ( a + b ) = r sin a cos b + r cos a sin b

# hence:
# x' = x cos b - y sin b
# y' = y cos b + x sin b

# x^2 + y^2 = r^2
# (x - p)^2 + y^2 = s^2
# subtract equations
# x^2 - 2*p*x + p^2 + y^2 - x^2 - y^2 = s^2 - r^2
# -2*p*x + p^2 = s^2 - r^2
# x = (s^2 - r^2 - p^2) / -2p
# x = (p^2 + r^2 - s^2) / 2*p

def arcArcTest(a0, a1):
    (i, j) = a0.c               # arc 0
    r0 = a0.r
    (x1, y1) = a1.c             # arc 1
    r1 = a1.r
    dx = x1 - i                # x distance
    dy = y1 - j                # y distance

    d = hypot(dx ,dy)           # center distance

    delta = (d - (r0 + r1))
    if delta > MIN_DIST:        # if too far apart
        return None

    if d < abs(r0 - r1):        # one circle within another
        return None
    
    if d < MIN_DIST and abs(r0 - r1) < MIN_DIST: # coincident
        return None
            
    d0 = (d*d + r0*r0 - r1*r1) / (2 * d) # distance along center line
    
    cosA = dx / d
    sinA = dy / d

    if abs(delta) < MIN_DIST: # if two circles touching
        p = Point(d0 * cosA + i, d0 * sinA + j)
        if a0.onSegment(p) and a1.onSegment(p):
            return(p)
    else:
        h = sqrt(r0*r0 - d0*d0)  # distance perpindicular to  center line
        # dprt("d %6.3f d0 %6.3f h %6.3f" % (d, d0, h))

        pa = Point(d0 * cosA + h * sinA + i, \
                   d0 * sinA - h * cosA + j)

        pb = Point(d0 * cosA - h * sinA + i, \
                   d0 * sinA + h * cosA + j)

        if a0.onSegment(pa) and a1.onSegment(pa):
            return pa

        if a1.onSegment(pb) and a1.onSegment(pb):
            return pb
    return None

                    # index0 = sweepList.bisect_left(evt0)
                    # dbgTxt += " (%2d" % (index0)
                    # if index0 < sweepLen:
                    #     evtP0 = sweepList[index0]
                    #     if evt0.key == evtP0.key:
                    #         sweepList.pop(index0)
                    #         sweepLen -= 1
                    #         index1 = sweepList.bisect_left(evt1)
                    #         if index1 < sweepLen:
                    #             dbgTxt += " %2d)" % (index1)
                    #             evtP1 = sweepList[index1]
                    #             if evt1.key == evtP1.key:
                    #                 sweepList.pop(index1)
                    #                 (x, y) = evt.p
                    #                 key = y * self.keyScale
                    #                 evt0.key = key + 1
                    #                 evt0.p = Point(x, y + 1)
                    #                 evt1.key = key - 1
                    #                 evt1.p = Point(x, y - 1)
                    #                 self.evtArray[evt0.index].end.key = evt0.key
                    #                 self.evtArray[evt1.index].end.key = evt1.key
                    #                 sweepList.add(evt0)
                    #                 sweepList.add(evt1)
                    #             else:
                    #                 sweepList.add(evt0)
                    #         else:
                    #             sweepList.add(evt0)
                    #     sweepLen = len(sweepList)
