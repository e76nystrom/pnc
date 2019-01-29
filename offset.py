from __future__ import print_function

from math import atan2, degrees, hypot, sqrt
from geometry import ARC, CCW, CW, LINE, MAX_VALUE, MIN_DIST, MIN_VALUE
from geometry import Arc, Line
from geometry import calcAngle, eqnLine, newPoint, orientation, \
    oStr, pathDir, reverseSeg, splitArcs, xyDist
from dbgprt import dprt, dprtSet, ePrint
# from sortedcontainers import SortedDict, SortedList
from sortedlist import SortedList
# from operator import attrgetter
# from sweepLine import line_intersections
from collections import namedtuple

LEFT      = 0
RIGHT     = 1
INTERSECT = 2

evtStr = ('L', 'R', 'I')

EventPair = namedtuple('EventPair', ['start', 'end'])
Intersection = namedtuple('Intersection', ['loc', 'p', 'l0', 'l1'])

class Offset():
    def __init__(self, cfg):
        self.cfg = cfg
        self.dir = None
        self.dist = 0.0
        self.scale = 10000
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
        self.dbg = True
        dprtSet(True)

    def offsetIntersect(self, args):
        cfg = self.cfg
        cfg.ncInit()
        layer = cfg.getLayer(args)
        seg = cfg.dxfInput.getLines(layer)
        lineSegment = []
        dprt()
        for l in seg:
            l.draw()
            # cfg.draw.drawX(l.p0, str(l.index))
            l.prt()
            lineSegment.append((l.p0, l.p1))
        self.findIntersections(seg)

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
        arcs = splitArcs(arcsIn, 90)
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

        refArc = splitArcs(refArc, 90)
        testArc = splitArcs(testArc, 90)

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
            
        dbgOffset = False       # ++dbg++
        if dbgOffset:
            drawX = cfg.draw.drawX
        for seg in segments:
            newSeg = splitArcs(seg)
            curDir = pathDir(newSeg)
            if curDir != direction:
                newSeg = reverseSeg(newSeg)
            if dbgOffset:
                dprt("direction %s" % (oStr(direction)))
            prevL = newSeg[-1]
            prevL1 = prevL.parallel(distance)
            oSeg = []
            for (n, l) in enumerate(newSeg):
                if dbgOffset:
                    l.draw()
                    l.label(str(l.index))
                # if prevL.type == LINE and l.type == LINE:
                if True:
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
                elif prevL.type == ARC and l.type == LINE:
                    pass
                elif prevL.type == LINE and l.type == ARC:
                    pass
                elif prevL.type == ARC and l.type == ARC:
                    pass
                l1 = l.parallel(distance)
                if l1 is None:
                    continue
                if dbgOffset:
                    l1.draw()
                    l1.label(str(l1.index))
                    l1.prt()
                dprt("%2d %2d dist %7.4f" % \
                     (prevL.index, l.index, xyDist(prevL1.p1, l1.p0)))
                if xyDist(prevL1.p1, l1.p0) > MIN_DIST:
                    if o == direction: # convex
                        lEnd = Line(prevL1.p1, l.p0)
                        if dbgOffset:
                            dprt("convex")
                            lEnd.draw()
                            drawX(prevL1.p1, str(-n))
                        lStr = Line(l.p0, l1.p0)
                        if dbgOffset:
                            lStr.draw()
                            drawX(l1.p0, str(n))
                        oSeg.append(lEnd)
                        oSeg.append(lStr)
                    else:           # concave
                        if dbgOffset:
                            dprt("concave")
                            drawX(l.p0, "C")
                            drawX(prevL1.p1, "0")
                            drawX(l1.p0, "1")
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
                            dprt("n %2d a0 %7.2f a1 %7.2f %s" % \
                                    (n, a0, a1, oStr(aDir)))
                            lArc.prt()
                            lArc.draw()
                        oSeg.append(lArc)
                oSeg.append(l1)
                prevL = l
                prevL1 = l1

            if dbgOffset:
                return
            
            oldSeg = oSeg
            oSeg = splitArcs(oldSeg, 45)
            
            dbgIntersect = False # ++dbg++
            for n, l in enumerate(oSeg):
                l.index = n
                l.prt()
                l.draw()
                if dbgIntersect:
                    l.label(str(n))
                    cfg.draw.drawX(l.p0, str(n))

            self.intersections = []
            self.findIntersections(oSeg)

            if dbgIntersect:
                return

            dprt("\npoints")
            for (loc, _, l0, l1) in self.intersections:
                dprt("(%7.4f %7.4f) %2d %2d" % \
                     (loc[0], loc[1], l0.index, l1.index))

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
                        oSeg1.append(l0)
                oSeg1.append(l)

            dprt("\nOseg1")
            for l in oSeg1:
                if l is not None:
                    l.prt()
                    l.draw()
                    # l.label(str(l.index))
                else:
                    dprt("missing")
            
            dprt()
            pToLine = {}
            oSeg2 = []
            
            scale = self.scale * 100
            ptIndex = 0
            for i, l in enumerate(oSeg1):
                l.index = i
                l.label(str(l.index))
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
            for (_, pL) in pToLine.iteritems():
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

            polyList = []
            dprt()
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
                    
            dprt("\npolyList %d" % (len(polyList)))
            for poly in polyList:
                dprt()
                # direction = pathDir(poly)
                # dprt("direction %s" % (oStr(direction)))
                for l in poly:
                    l.prt()
                if True:
                    p = self.insidePoint(poly)
                    if p is not None:
                        wN = windingNum(p, poly)
                        cfg.draw.drawX(p, str(wN))
                        dprt("wN %2d (%7.4f %7.4f)" % (wN, p[0], p[1]))

    def findIntersections(self, seg):
        self.evtList = evtList = SortedList()
        self.evtArray = [None] * len(seg)
        for l in seg:
            scale = self.scale
            p0 = newPoint(l.p0, scale)
            p1 = newPoint(l.p1, scale)
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
        
        # evtList = sorted(evtList, key=lambda l: (l.p.x, l.p.y))
        dprt()
        for l in evtList:
            l.prt()

        self.sweepList = sweepList = SortedList()
        dprt()
        while len(evtList) > 0:
            evt = evtList.pop(0)
            self.curX = evt.p.x
            evt.event = False
            evt.prt(end=' ')
            if evt.evtType == LEFT:
                sweepList.add(evt)
                index = sweepList.bisect_left(evt)
                sweepLen = len(sweepList)
                self.sweepPrt("l", evt, sweepLen, index)
                l = evt.l
                if index > 0:
                    idxLeft = index - 1
                    evtLeft = sweepList[idxLeft]
                    loc0 = self.intersect(l, evtLeft.l)
                    self.iEvt(loc0, evt, evtLeft)

                vertical = abs(l.p0[0] - l.p1[0]) < MIN_DIST
                idxRight = index
                while True:
                    idxRight += 1
                    if idxRight >= sweepLen:
                        break
                    evtRight = sweepList[idxRight]
                    loc1 = self.intersect(l, evtRight.l)
                    self.iEvt(loc1, evt, evtRight)
                    if not vertical:
                        break

                self.listPrt(sweepList)
            elif evt.evtType == RIGHT:
                index = sweepList.bisect_left(evt)
                sweepLen = len(sweepList)
                self.sweepPrt("r", evt, sweepLen, index)
                curEvt = sweepList[index]
                if curEvt.key != evt.key:
                    ePrint("key error")
                    
                if index > 0:
                    idxLeft = index - 1
                    idxRight = index + 1
                    if idxRight < sweepLen:
                        evtLeft = sweepList[idxLeft]
                        evtRight = sweepList[idxRight]
                        loc = self.intersect(evtLeft.l, evtRight.l)
                        self.iEvt(loc, evtLeft, evtRight)
                self.listPrt(sweepList)
                sweepList.pop(index)
            elif evt.evtType == INTERSECT:
                sweepLen = len(sweepList)
                self.sweepPrt("i", evt, sweepLen)
                if self.curX > lastX:
                    evt0 = evt.evt0
                    evt1 = evt.evt1
                    try:
                        sweepList.remove(evt.evt0)
                    except ValueError:
                        dprt("\nerror removing ", end='')
                        evt.evt0.prt()
                    try:
                        sweepList.remove(evt.evt1)
                    except ValueError:
                        dprt("\nerror removing ", end='')
                        evt.evt1.prt()
                    # if evt0.key > evt1.key:
                    (evt0, evt1) = (evt1, evt0)
                    key = evt.p.y * 100
                    evt0.key = key
                    evt1.key = key + 1
                    self.evtArray[evt0.index].end.key = evt0.key
                    self.evtArray[evt1.index].end.key = evt1.key
                    sweepList.add(evt0)
                    sweepList.add(evt1)
                
                    index = sweepList.bisect_left(evt0)
                    if index > 0:
                        idxLeft = index - 1
                        evtLeft = sweepList[idxLeft]
                        loc = self.intersect(evt0.l, evtLeft.l)
                        self.iEvt(loc, evt, evtLeft)
                
                    index += 1
                    idxRight = index + 1
                    if idxRight < sweepLen:
                        evtRight = sweepList[idxRight]
                        loc = self.intersect(evt1.l, evtRight.l)
                        self.iEvt(loc, evt, evtRight)
                self.listPrt(sweepList)
            lastX = self.curX
            # dprt()
        dprt("sweepLen %d" % (len(sweepList)))

    def addEvent(self, p0, p1, l):
        evtStr = Event(p0, l, LEFT)
        evtEnd = Event(p1, l, RIGHT, evtStr.key)
        evtStr.evtEnd = evtEnd
        self.evtList.add(evtStr)
        self.evtList.add(evtEnd)
        self.evtArray[l.index] = EventPair(evtStr, evtEnd)

    def iEvt(self, loc, evt0, evt1):
        if loc is not None:
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

    def eventPrt(self):
        for evt in self.evtList:
            evt.prt()
        
    def sweepPrt(self, string, evt, sweepLen, sweepIndex=None):
        self.intCount = 0
        if evt.evtType != INTERSECT:
            dprt("%s %2d x %6d l %2d i %2d" % \
                 (string, evt.index, evt.p.x, sweepLen, sweepIndex), end='')
        else:
            dprt("%s    x %6d l %2d     " % \
                 (string, evt.p.x, sweepLen), end='')

    def listPrt(self, sweepList):
        while self.intCount < 2:
            self.intCount += 1
            self.noIntersection()
        dprt(" (", end='')
        for (i, s) in enumerate(sweepList):
            if i != 0:
                dprt(", ", end='')
            if s.evtType != INTERSECT:
                dprt("%2d" % (s.l.index), end='')
            else:
                dprt("  ", end='')
            dprt(" %5d" % (s.p.y), end='')
        dprt(")")

    def intersectionPrt(self, index0, index1, loc):
        dprt(" (%2d %2d)" % (index0, index1), end='')
        
        if loc is not None:
            dprt(" (%5.2f %5.2f)" % (loc[0], loc[1]), end='')
        else:
            dprt("              ", end='')

    def noIntersection(self):
        dprt("        ", end='')
        dprt("              ", end='')

    def intersect(self, l0, l1):
        # distance = xyDist(l0.p1, l1.p0)
        # dprt("\nintersect %2d %2d d %7.4f" % (l0.index, l1.index, distance))
        if (xyDist(l0.p1, l1.p0) < MIN_DIST or
            xyDist(l1.p1, l0.p0) < MIN_DIST):
            return None
        if l0.type == LINE:
            if l1.type == LINE:
                # if abs(l0.index - l1.index) == 1:
                #     return None
                return self.lineIntersection(l0, l1)
            else:
                # return self.lineIntersection(l0, l1)
                return lineArcTest(l0, l1)
        else:
            if l1.type == LINE:
                # return self.lineIntersection(l0, l1)
                return lineArcTest(l1, l0)
            else:
                return arcArcTest(l0, l1)

    def lineIntersection(self, l0, l1):
        p0 = l0.p0
        p1 = l0.p1
        p2 = l1.p0
        p3 = l1.p1
        s10_x = p1[0] - p0[0]
        s10_y = p1[1] - p0[1]
        s32_x = p3[0] - p2[0]
        s32_y = p3[1] - p2[1]

        denom = s10_x * s32_y - s32_x * s10_y

        if denom == 0:
            return None         # collinear

        denomPositive = denom > 0

        s02_x = p0[0] - p2[0]
        s02_y = p0[1] - p2[1]

        s_numer = s10_x * s02_y - s10_y * s02_x

        if (s_numer < 0) == denomPositive:
            return None         # no collision

        t_numer = s32_x * s02_y - s32_y * s02_x

        if (t_numer < 0) == denomPositive:
            return None         # no collision

        if (s_numer > denom) == denomPositive or \
           (t_numer > denom) == denomPositive:
            return None         # no collision

        # collision detected

        t = t_numer / denom

        iPt = (p0[0] + (t * s10_x), p0[1] + (t * s10_y))
        # dprt("intersection %2d %2d (%7.4f %7.4f)" %
        #      (l0.index, l1.index, iPt[0], iPt[1]))
        if xyDist(iPt, p0) < MIN_DIST or \
           xyDist(iPt, p1) < MIN_DIST:
            return None
        # self.cfg.draw.drawX(iPt, "%d-%d" % (l0.index, l1.index))
        return iPt

    def lineArcIntersection(self, l0, l1):
        pass

    def arcArcIntersection(self, l0, l1):
        pass

    def insidePoint(self, seg):
        drawTest = False
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
        self.sweepList = sweepList = SortedList()
        x0 = None
        p = None
        while len(evtList) > 0:
            evt = evtList.pop(0)
            if len(sweepList) >= 2:
                xTest = (evt.p.x + x0) / (2.0 * self.scale)
                lTest = Line((xTest, 0), (xTest, self.cfg.dxfInput.ySize))
                if drawTest:
                    lTest.draw()
                l0 = sweepList[0].l
                l1 = sweepList[1].l
                pMin = self.insideIntersect(lTest, l0)
                pMax = self.insideIntersect(lTest, l1)
                if pMin is not None and pMax is not None:
                    p = (xTest, (pMax[1] + pMin[1]) / 2.0)
                    break
                else:
                    lTest.prt()
                    l0.prt()
                    l1.prt()
                    dprt("insidePoint error")
                    break
            if evt.evtType == LEFT:
                x0 = evt.p.x
                self.sweepList.add(evt)
                self.sweepPrt("l", evt, len(sweepList), 0)
                self.listPrt(sweepList)
            elif evt.evtType == RIGHT:
                try:
                    sweepList.remove(evt)
                except:
                    dprt("list error")
                evtList.clear()
        sweepList.clear()
        return(p)

    def addInsideEvent(self, p0, p1, l):
        evtStr = Event(p0, l, LEFT)
        evtEnd = Event(p1, l, RIGHT, evtStr.key)
        self.evtList.add(evtStr)
        self.evtList.add(evtEnd)

    def insideIntersect(self, l0, l1):
        if l0.type == LINE:
            if l1.type == LINE:
                return self.lineIntersection(l0, l1)
            else:
                # return lineArcTest(l0, l1)
                return self.lineIntersection(l0, l1)
        else:
            if l1.type == LINE:
                # return lineArcTest(l1, l0)
                return self.lineIntersection(l1, l0)
            else:
                return arcArcTest(l0, l1)

# inline int isLeft( Point P0, Point P1, Point P2 )
# {
#     return ( (P1.x - P0.x) * (P2.y - P0.y)
#             - (P2.x -  P0.x) * (P1.y - P0.y) );
# }

# // wn_PnPoly(): winding number test for a point in a polygon
# //      Input:   P = a point,
# //               V[] = vertex points of a polygon V[n+1] with V[n]=V[0]
# //      Return:  wn = the winding number (=0 only when P is outside)

# int wn_PnPoly( Point P, Point* V, int n )
# {
#  int    wn = 0;    // the  winding number counter

#  // loop through all edges of the polygon
#  for (int i = 0; i < n; i++)	// edge from V[i] to  V[i+1]
#   {
#   if (V[i].y <= P.y)		// start y <= P.y
#   {
#    if (V[i + 1].y  > P.y)	// an upward crossing
#     if (isLeft( V[i], V[i+1], P) > 0)  // P left of  edge
#      ++wn;			// have  a valid up intersect
#   }
#   else				// start y > P.y (no test needed)
#   {
#    if (V[i + 1].y  <= P.y)	// a downward crossing
#     if (isLeft(V[i], V[i + 1], P) < 0) // P right of  edge
#      --wn;			// have  a valid down intersect
#   }
#  }
#  return wn;
# }

def isLeft(p0, p1, p2):
    return ((p1[0] - p0[0]) * (p2[1] - p0[1])
             - (p2[0] -  p0[0]) * (p1[1] - p0[1]))

def windingNum(p, seg):
    wN = 0
    for l in seg:
        p0 = l.p0
        p1 = l.p1
        if p0[1] <= p[1]:       # start y <= p.y
            if p1[1]  > p[1]:	# an upward crossing
                if isLeft(p0, p1, p) > 0: # p left of edge
                    wN += 1     # have a valid up intersect
        else:                   # start y > p.y (no test needed)
            if p1[1] <= p[1]:	# a downward crossing
                if isLeft(p0, p1, p) < 0: # p right of edge
                    wN -= 1     # have  a valid down intersect
    return wN

class Event:
    def __init__(self, p, l, evtType, key=None):
        self.evtType = evtType
        self.p = p
        self.l = l
        self.index = l.index
        self.event = True
        if key is None:
            self.key = self.p.y * 100 + l.index
        else:
            self.key = key

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
                return self.p.y < other.p.y
            else:
                return self.p.x < other.p.x
        else:
            return self.key < other.key

class Intersect:
    def __init__(self, p, loc, evt0, evt1):
        self.evtType = INTERSECT
        self.p = p
        self.loc = loc
        self.evt0 = evt0
        self.evt1 = evt1
        self.event = True
    
    def prt(self, end='\n', l=False):
        dprt("p (%6d %6d)        %2d %2d I" % \
             (self.p.x, self.p.y, self.evt0.index, self.evt1.index), end='')
        if l:
            dprt(" %2d %2d" % (self.evt0.index, self.evt1.index), '')
        dprt(end=end)

    def __str__(self):
        return("p (%6d %6d)    %9d %s" % \
               (self.p.x, self.p.y, self.key, \
                evtStr[self.evtType]))

    def __gt__(self, other):
        if self.event:
            if self.p.x == other.p.x:
                return self.p.y > other.p.y
            else:
                return self.p.x > other.p.x
        else:
            return self.key > other.key

    def __lt__(self, other):
        if self.event:
            if self.p.x == other.p.x:
                return self.p.y < other.p.y
            else:
                return self.p.x < other.p.x
        else:
            return self.key < other.key

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
        
def lineArcTest(l, a):
    (x0, y0) = a.p0
    (x1, y1) = a.p1
    # xAMin = min(x0, x1)
    # xAMax = max(x0, x1)
    # yAMin = min(y0, y1)
    # yAMax = max(y0, y1)

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
        p = (x, y)

        # d0 = xyDist(p, l.p0)
        # d1 = xyDist(p, l.p1)
        # if abs(l.length - (d0 + d1)) < MIN_DIST:
        #     if (x < xAMin or xAMax < x or
        #          y < yAMin or yAMax < y):
        #         return(None)
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

    pP = (xP + i, yP + j)
    pM = (xM + i, yM + j)
               
    # pP = (xP, yP)
    # pM = (xM, yM)
    # dP = xyDist(pP, l.p0) + xyDist(pP, l.p1)
    # dM = xyDist(pM, l.p0) + xyDist(pM, l.p1)
    if l.onSegment(pP):
        p = pP
    elif l.onSegment(pM):
        p = pM
    else:
        p = None

    if p is not None:
        if a.onSegment(p):
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

    delta = abs(d - (r0 + r1))
    if delta > MIN_DIST:        # if no intersection
        return None

    if d < abs(r0 - r1):        # one circle wihin another
        return None
    
    if d < MIN_DIST and abs(r0 - r1) < MIN_DIST: # coincident
        return None
            
    d0 = (d*d + r0*r0 - r1*r1) / (2 * d) # distance along center line
    
    cosA = dx / d
    sinA = dy / d

    if abs(delta) < MIN_DIST: # one solution
        p = (d0 * cosA + i, d0 * sinA + j)
        if a0.onSegment(p) and a1.onSegment(p):
            return(p)
    else:
        h = sqrt(r0*r0 - d0*d0)  # distance perpindicular to  center line
        # dprt("d %6.3f d0 %6.3f h %6.3f" % (d, d0, h))

        pa = (d0 * cosA + h * sinA + i, \
              d0 * sinA - h * cosA + j)

        pb = (d0 * cosA - h * sinA + i, \
              d0 * sinA + h * cosA + j)

        if a0.onSegment(pa) and a1.onSegment(pa):
            return pa

        if a1.onSegment(pb) and a1.onSegment(pb):
            return pb
    return None

# TWO_PI = 2 * pi

# def is_convex_polygon(polygon):
#     """Return True if the polynomial defined by the sequence of 2D
#     points is 'strictly convex': points are valid, side lengths non-
#     zero, interior angles are strictly between zero and a straight
#     angle, and the polygon does not intersect itself.

#     NOTES:  1.  Algorithm: the signed changes of the direction angles
#                 from one side to the next side must be all positive or
#                 all negative, and their sum must equal plus-or-minus
#                 one full turn (2 pi radians). Also check for too few,
#                 invalid, or repeated points.
#             2.  No check is explicitly done for zero internal angles
#                 (180 degree direction-change angle) as this is covered
#                 in other ways, including the `n < 3` check.
#     """
#     try:  # needed for any bad points or direction changes
#         # Check for too few points
#         if len(polygon) < 3:
#             return False
#         # Get starting information
#         old_x, old_y = polygon[-2]
#         new_x, new_y = polygon[-1]
#         new_direction = atan2(new_y - old_y, new_x - old_x)
#         angle_sum = 0.0
#         # Check each point (the side ending there, its angle), accum. angles
#         for ndx, newpoint in enumerate(polygon):
#             # Update point coordinates and side directions, check side length
#             old_x, old_y, old_direction = new_x, new_y, new_direction
#             new_x, new_y = newpoint
#             new_direction = atan2(new_y - old_y, new_x - old_x)
#             if old_x == new_x and old_y == new_y:
#                 return False  # repeated consecutive points
#             # Calculate & check the normalized direction-change angle
#             angle = new_direction - old_direction
#             if angle <= -pi:
#                 angle += TWO_PI  # make it in half-open interval (-Pi, Pi]
#             elif angle > pi:
#                 angle -= TWO_PI
#             if ndx == 0:  # if first time through loop, initialize orientation
#                 if angle == 0.0:
#                     return False
#                 orientation = 1.0 if angle > 0.0 else -1.0
#             else:  # if other time through loop, check orientation is stable
#                 if orientation * angle <= 0.0:  # not both pos. or both neg.
#                     return False
#             # Accumulate the direction-change angle
#             angle_sum += angle
#         # Check that the total number of full turns is plus-or-minus 1
#         return abs(round(angle_sum / TWO_PI)) == 1
#     except (ArithmeticError, TypeError, ValueError):
#         return False  # any exception means not a proper convex polygon

        # sweepList = SortedDict()
        # dprt()
        # for l in segList:
        #     l.prt()
        #     # dprt("x %8d y %8d %d %s" % (l.p.x, l.p.y, l.index, l.left))
        #     # l.l.prt()
        #     if l.left:
        #         sweepList[l.key] = l
        #         sweepLen = len(sweepList)
        #         index = sweepList.index(l.key)
        #         idxLeft = sweepList.bisect_left(l.key)
        #         idxRight = sweepList.bisect_right(l.key)
                
        #         dprt("insert %2d x %6d len %d (%d %d %d)" % \
        #              (l.index, l.p.x, sweepLen, idxLeft, index, idxRight))
                
        #         if idxLeft != index:
        #             itemLeft = sweepList.peekitem(idxLeft)[1]
        #             dprt("intersect (%2d %2d) (%2d %2d)" % \
        #                  (index, idxLeft, l.index, itemLeft.index))
                    
        #         if idxRight < sweepLen:
        #             itemRight = sweepList.peekitem(idxRight)[1]
        #             dprt("intersect (%2d %2d) (%2d %2d)" % \
        #                  (index, idxRight, l.index, itemRight.index))
        #     else:
        #         sweepLen = len(sweepList)
        #         index = sweepList.index(l.key)
        #         idxLeft = sweepList.bisect_left(l.key)
        #         idxRight = sweepList.bisect_right(l.key)
        #         dprt("delete %2d x %6d len %d (%d %d %d)" % \
        #              (l.index, l.p.x, sweepLen, idxLeft, index, idxRight))
        #         if index != idxLeft and \
        #            idxRight < sweepLen and \
        #            idxLeft != idxRight:
        #             itemLeft = sweepList.peekitem(idxLeft)[1]
        #             itemRight = sweepList.peekitem(idxRight)[1]
        #             dprt("intersect (%2d %2d) (%2d %2d)" % \
        #                  (idxLeft, idxRight, itemLeft, itemRight))
        #         sweepList.pop(l.key)
        #     dprt()
        # print("length %d" % (len(sweepList)))
        
