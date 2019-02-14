from __future__ import print_function

from collections import namedtuple
from math import atan2, degrees, hypot, sqrt

from dbgprt import dprt, dprtSet, ePrint
from geometry import (ARC, CCW, CW, LINE, MAX_VALUE, MIN_DIST, MIN_VALUE, Arc,
                      Line, Point, calcAngle, combineArcs, eqnLine, newPoint,
                      orientation, oStr, pathDir, reverseSeg, splitArcs,
                      xyDist)
from poly_point_isect import isect_polygon, isect_segments
from sortedlist import SortedList

RIGHT     = 0                   # priority order of events
INTERSECT = 1
LEFT      = 2

evtStr = ('R', 'I', 'L')

EventPair = namedtuple('EventPair', ['start', 'end'])
Intersection = namedtuple('Intersection', ['loc', 'p', 'l0', 'l1'])

keyScale = None
keyOffset = None

realX = 0.0
scale = 10000

before = False
evtDbg = False

class Offset():
    def __init__(self, cfg):
        self.cfg = cfg
        self.dir = None
        self.dist = 0.0
        self.outside = False
        self.scale = 10000
        self.splitArcAngle = 90
        self.minLength = 0.002
        self.keyScale = None
        self.keyOffset = None
        self.passNum = 0
        self.cmds = \
        (
            ('dxfoffset', self.offset), \
            ('offsetdist', self.setOffsetDist), \
            ('offsetdir', self.setOffsetDir), \
            ('offsetoutside', self.setOffsetOutside), \
            ('offsetscale', self.setOffsetScale), \
            ('offsetintersect', self.offsetIntersect), \
            ('offsetlinearc', self.lineArcTest), \
            ('offsetarcarc', self.arcArcTest), \
            ('offsetwindingnum', self.windingNumTest), \
            ('offsetsplitarcangle', self.setSplitArcAngle), \
            ('drawinitial', self.setDrawInitial), \
            ('dbgoffset', self.setDbgOffset), \
            ('drawoffset', self.setDrawOffset), \
            ('offsetreturn', self.setOffsetReturn), \
            ('dbgintersect', self.setDbgIntersect), \
            ('intersectreturn', self.setIntersectReturn), \
            ('drawsplitlines', self.setDrawSplitLines), \
            ('dbgpolygons', self.setDbgPolygons), \
            ('drawfinalpolygon', self.setDrawFinalPolygon), \
            ('drawwindingnum', self.setDrawWindingNum), \
            # ('', self.set), \
        )
        self.intersections = None
        self.dbgIntersection = None
        self.setKeyScale(10)
        self.dbg = True
        self.drawInitial = True
        self.dbgOffset = False
        self.drawOffset = False
        self.offsetReturn = False
        self.dbgIntersect = False
        self.intersectReturn = False
        self.drawSplitLines = False
        self.dbgPolygons = False
        self.drawFinalPoly = True
        self.drawWindingNum = False
        dprtSet(True)

    def offset(self, args):
        if self.dist == 0:
            return
        cfg = self.cfg
        cfg.ncInit()
        layer = cfg.getLayer(args)
        segments = cfg.dxfInput.getPath(layer, dbg=False)

        direction = self.dir
        if direction is None:
            direction = CCW

        distance = abs(self.dist)
        if self.outside:             # outside ^    cw <-|
            if direction == CCW:     #  dir cw | dir ccw |
                distance = -distance #  ccw <- |         v
        else:
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
            self.passNum = count
            total += distance
            dprt("***pass %d*** distance %7.4f " \
                 "segments %d segment[0] len %d" % \
                 (count, total, len(segments), len(segments[0])))
            finalPolygons = self.offsetPath(segments, direction, \
                                            distance, self.outside)
            if finalPolygons is None:
                break
            if len(finalPolygons) == 0:
                break
            segments = finalPolygons
            count += 1
            if count >= passes:
                break
            if count >= dbgPass:
                self.drawOffset = True
                self.dbgIntersect = True
                self.drawSplitLines = True
                self.drawWindingNum = True

    def offsetPath(self, segments, direction, distance, outside):
        cfg = self.cfg
        dbgOffset = self.dbgOffset
        drawOffset = self.drawOffset
        if dbgOffset and drawOffset:
            drawX = cfg.draw.drawX
        finalPolygons = []
        initialLayer = "%02dinitial" % (self.passNum)
        for seg in segments:
            dprt("\noriginal path")
            for l in seg:
                l.prt()
                if self.drawInitial:
                    l.draw(initialLayer)
                    l.label(layer=initialLayer)

            newSeg = splitArcs(seg, self.splitArcAngle)

            dprt("\npath with split arcs")
            for i, l in enumerate(newSeg):
                l.index = i
                l.prt()
            
            curDir = pathDir(newSeg, False)
            if curDir == 0:
                ePrint("###direction error###")
            if curDir != direction:
                newSeg = reverseSeg(newSeg)
            if dbgOffset:
                dprt("direction %s distance %7.4f" % \
                     (oStr(direction), distance))

            (p, chkList) = self.insidePoint(newSeg)
            wNInitial = windingNumber(p, chkList, self.scale, dbg=True)
            if wNInitial == 1:
                wNDirection = CCW
            elif wNInitial == -1:
                wNDirection = CW
            else:
                wNDirection = None
            dprt("wNInitial %2d wNDirection %s direction %s" % \
                 (wNInitial, oStr(wNDirection), oStr(direction)))

            offsetIntersect = False # +++dbg+++
            dprt("\ncreate offset path")
            if self.passNum == 7:
                dprt("break point for pass")
            skip = False
            i = -1
            while True:
                prevL = newSeg[i]
                l1 = prevL.parallel(distance, direction, outside)
                if l1 is not None:
                    prevP = l1.p1
                    prevL1 = l1
                    break
                i -= 1
            lastLoc = None
            oSeg = []
            offsetLayer = "%02dOffset" % (self.passNum)
            splitLayer = "%02dsplit" % (self.passNum)
            for (n, l) in enumerate(newSeg):
                if dbgOffset:
                    l.draw(splitLayer)
                    l.label(layer=splitLayer)

                l1 = l.parallel(distance, direction, outside)
                if l1 is None:
                    if xyDist(prevP, l.c) > MIN_DIST:
                        if not offsetIntersect:
                            l1 = Line(prevP, l.c)
                            oSeg.append(l1)
                            prevP = l.c
                            skip = True
                            # if dbgOffset and drawOffset:
                            #     l1.draw(offsetLayer)
                    continue

                if dbgOffset:
                    dprt()
                    l1.prt()
                    dprt("(%2d -> %2d) dist %7.4f" % \
                         (prevL.index, l.index, xyDist(prevP, l1.p0)))
                    # if drawOffset:
                    #     l1.draw(offsetLayer)
                    #     l1.label(str(l1.index), layer=offsetLayer)

                if xyDist(prevP, l1.p0) > MIN_DIST:
                    if prevL.type == LINE:
                        p0 = prevL.p0
                    else:
                        p0 = prevL.tangent(False, 0.1, offsetLayer, True)
                    (x0, y0) = p0
                    (x1, y1) = l.p0
                    if l.type == LINE:
                        p2 = l.p1
                    else:
                        p2 = l.tangent(True, 0.1, offsetLayer, True)
                    (x2, y2) = p2

                    o = orientation(p0, l.p0, p2)
                    if dbgOffset:
                        a0 = atan2(y0 - y1, x0 - x1)
                        a1 = atan2(y2 - y1, x2 - x1)
                        dprt()
                        prevL.prt()
                        l.prt()
                        dprt("0 (%7.4f %7.4f) 1 (%7.4f %7.4f) "\
                                "2 (%7.4f %7.4f)" % \
                                (x0, y0, x1, y1, x2, y2))
                        dprt("n %2d a0 %7.2f a1 %7.2f a1-a0 %7.2f "\
                                "orientation %s" % \
                                (n, degrees(a0), degrees(a1), \
                                degrees(a0 - a1), oStr(o)))

                    if ((not outside and o == direction) or
                        (outside and o != direction)): # convex
                        if offsetIntersect:
                            loc = self.pathIntersect(prevL1, l1)
                            if loc is not None:
                                prevL1.updateP1(loc)
                                l1.updateP0(loc)
                                if lastLoc is None:
                                    lastLoc = loc
                        elif not skip:
                            lEnd = Line(prevP, l.p0)
                            lStr = Line(l.p0, l1.p0)
                            oSeg.append(lEnd)
                            oSeg.append(lStr)
                            if dbgOffset:
                                dprt("convex")
                                # if drawOffset:
                                #     lEnd.draw(offsetLayer)
                                #     drawX(prevP, str(-n), layer=offsetLayer)
                                #     lStr.draw(offsetLayer)
                                #     drawX(l1.p0, str(n), layer=offsetLayer)
                        else:
                            skip = False
                            if xyDist(prevP, l1.p0) > MIN_DIST:
                                l = Line(prevP, l1.p0)
                                oSeg.append(l)
                                # if dbgOffset and drawOffset:
                                #     l.draw(offsetLayer)
                    else:           # concave
                        if ((not outside and direction == CCW) or
                            (outside and direction == CW)):
                            a1 = degrees(calcAngle(l.p0, prevP))
                            a0 = degrees(calcAngle(l.p0, l1.p0))
                            aDir = CW
                        else:
                            a0 = degrees(calcAngle(l.p0, prevP))
                            a1 = degrees(calcAngle(l.p0, l1.p0))
                            aDir = CCW
                        lArc = Arc(l.p0, abs(distance), a0, a1, \
                                    direction=aDir)

                        if dbgOffset:
                            dprt("concave")
                            dprt("n %2d a0 %7.2f a1 %7.2f %s" % \
                                    (n, a0, a1, oStr(aDir)))
                            lArc.prt()
                            # if drawOffset:
                            #     drawX(l.p0, "C", layer=offsetLayer)
                            #     drawX(prevP, "0", layer=offsetLayer)
                            #     drawX(l1.p0, "1", layer=offsetLayer)
                            #     lArc.draw(offsetLayer)
                        oSeg.append(lArc)
                oSeg.append(l1)
                prevL = l
                prevL1 = l1
                prevP = l1.p1
            if lastLoc is not None:
                prevL1.updateP1(lastLoc)

            if dbgOffset:
                if drawOffset:
                    for l in oSeg:
                        l.draw(layer=offsetLayer)
                        l.label(layer=offsetLayer)
                if self.offsetReturn:
                    return
            
            oldSeg = oSeg
            oSeg = splitArcs(oldSeg, self.splitArcAngle)
            
            dbgIntersect = self.dbgIntersect # ++dbg++
            if dbgIntersect:
                intersectLayer = "%02dIntersect" % (self.passNum)
                dprt("\nlines for intersection pass %d" % (self.passNum))
            self.cfg.draw.drawX(l.p0, "pass %d" % (self.passNum))
            for n, l in enumerate(oSeg):
                l.index = n
                l.prt()
                if dbgIntersect:
                    l.draw(intersectLayer)
                    l.label(layer=intersectLayer)
                    # cfg.draw.drawX(l.p0, str(n))

            isectPolygon = False
            if isectPolygon:
                points = []
                for l in oSeg:
                    points.append(l.p0)
                tmp = isect_polygon(points)

            self.intersections = []
            self.findIntersections(oSeg)

            if isectPolygon:
                dprt("\nisect_polygon intersections")
                for n, (x, y) in enumerate(tmp):
                    dprt("%2d (%7.4f %7.4f)" % (n, x, y))

            if dbgIntersect:
                dprt("\nintersections")
                for n, i in enumerate(self.intersections):
                    dprt("%2d (%7.4f %7.4f) %2d %2d" %
                         (n, i.loc.x, i.loc.y, i.l0.index, i.l1.index))
                    cfg.draw.drawX(i.loc, "", layer=intersectLayer)
                if self.intersectReturn:
                    return

            dprt("\npoints")
            for (loc, _, l0, l1) in self.intersections:
                dprt("(%7.4f %7.4f) %2d %2d" % \
                     (loc.x, loc.y, l0.index, l1.index))

            dprt("\npassNum %d split lines" % (self.passNum))
            oSeg1 = []
            for l in oSeg:
                # if self.passNum == -1 and l.index == 14:
                #     ePrint("splitLines break pass %d index %d" % \
                #            (self.passNum, self.event))

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

            dprt("\npassNum %d oSeg1 split lines" % (self.passNum))
            for l in oSeg1:
                if l is not None:
                    l.prt()
                else:
                    dprt("oSeg1 missing")
            
            dprt("\ninteger point line list")
            pToLine = {}
            oSeg2 = []
            scale = self.scale * self.keyScale
            ptIndex = 0
            splitLayer = "%02dSplit" % (self.passNum)
            for i, l in enumerate(oSeg1):
                if self.drawSplitLines:
                    l.draw(splitLayer)
                    l.label("%d->%d" % (l.index, i), layer=splitLayer)
                l.index = i
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

            dprt("\npoint to line list")
            for pL in pLine:
                p = pL.p
                dprt("%2d (%6d %6d) - (" % (pL.index, p.x, p.y), end='')
                for i, intLine in enumerate(pL.l):
                    if i != 0:
                        dprt(", ", end='')
                    dprt("%2d" % (intLine.l.index,), end='')
                dprt(")")

            dbgPolygons = self.dbgPolygons
            if dbgPolygons:
                dprt("\nlink segments into polygons")
                polyCount = 0
            polyList = []
            ref = []
            for l in oSeg2:
                ref.append(l.l)
            for i in range(len(oSeg2)): # while lines to process
                index = i               # set place to start
                poly = []
                while True:		# while not at end
                    iL = oSeg2[index]   # get next segment
                    if iL is None:      # if no segment
                        break           # exit loop
                    oSeg2[index] = None # mark as processed
                    p1Index = iL.p1Index    # get point index
                    poly.append(iL.l)       # append to polygon
                    pL = pLine[p1Index]     # look up point
                    if dbgPolygons:
                        dprt("p%2d " % (p1Index), end='')
                        iL.prt()
                    for i, l in enumerate(pL.l): # loop over connected lines
                        index = l.l.index   # get the line index
                        if iL.l.index == index: # if same line
                            continue            # skip
                        if len(pL.l) == 2:      # if only two lines
                            break
                        if dbgPolygons:
                            dprt("l%2d" % (i), end=' ')
                            l.prt()
                        (x0, y0) = iL.p1      # point location
                        (x1, y1) = l.p0       # start of line
                        if (x0 == x1) and (y0 == y1): # if line start
                            l0 = iL.l
                            l1 = l.l
                            if l0.type == l1.type:
                                if not l0.colinear(l1): # and not colinear
                                    break
                            elif l0.type == LINE:
                                if not lineArcTangent(l0, l1):
                                    break
                            else:
                                if not lineArcTangent(l1, l0):
                                    break
                    else:
                        dprt("not found")
                        break
                    if dbgPolygons:
                        dprt()
                if len(poly) >= 3:
                    if dbgPolygons:
                        dprt("polygon %d linked %d" % (polyCount, len(poly)))
                        polyCount += 1
                        for l in poly:
                            l.prt()
                    result = self.insidePoint(poly)
                    if result is not None:
                        p = result[0]
                        wN = windingNumber(p, ref, self.scale, dbg=False)
                        dprt("wN %2d (%7.4f %7.4f)" % (wN, p.x, p.y))
                        if (outside and abs(wN) == 1 or
                            not outside and wN == wNInitial):
                            polyList.append(poly)
                        if self.drawWindingNum:
                            self.cfg.draw.drawX(p, str(wN), layer=splitLayer)
                        if dbgPolygons:
                            dprt()
                else:
                    if len(poly) > 0:
                        dprt("bad polygon")
                        for l in poly:
                            l.prt()
                    
            if dbgPolygons:
                dprt("polyList %d" % (len(polyList)))
                dprt("calculate polygon winding number")
            for pN, poly in enumerate(polyList):
                if dbgPolygons:
                    dprt("polygon %d" % (pN))
                    for l in poly:
                        l.prt()

                if True:
                    dprt("\nremoving short segments")
                    newPoly = []
                    n = 0
                    removed = 0
                    update = False
                    index = 1
                    dprt("find starting point")
                    while True:
                        l = poly[-index]
                        l.prt()
                        if l.length > self.minLength:
                            prevL = l
                            index -= 1
                            if index != 0:
                                poly = poly[-index:] + poly[:-index]
                            break
                        index += 1
                    dprt()
                    prevL.prt()
                    dprt()
                    for i, l in enumerate(poly):
                        if l.length < self.minLength:
                            removed += 1
                            update = True
                            dprt("r %2d" % (removed), end=' ')
                            l.prt()
                            continue
                        if update:
                            update = False
                            if prevL.type == LINE:
                                if l.type == LINE:
                                    (x0, y0) = prevL.p1
                                    (x1, y1) = l.p0
                                    p = Point((x0 + x1) / 2, (y0 + y1) / 2)
                                    prevL.updateP1(p)
                                    l.updateP0(p)
                                else:
                                    prevL.updateP1(l.p0)
                            else:
                                if l.type == LINE:
                                    l.updateP0(prevL.p1)
                                else:
                                    l0 = Line(prevL.p1, l.p0, n)
                                    n += 1
                                    newPoly.append(l0)
                                    dprt("a    ", end='')
                                    l0.prt()
                        dprt("s %2d" % (n), end=' ')
                        l.prt()
                        l.index = n
                        newPoly.append(l)
                        n += 1
                        prevL = l
                    if removed != 0:
                        polyList[pN] = newPoly
                        poly = newPoly

                    if dbgPolygons and removed > 0:
                        dprt("\nshort segments removed %d" % (removed))
                        for l in newPoly:
                            l.prt()

                result = self.insidePoint(poly, True)
                if result is not None:
                    (p, chkList) = result
                    wN = windingNumber(p, chkList, self.scale, dbg=False)
                    if wN == wNInitial:
                        newPoly = combineArcs(poly)
                        finalPolygons.append(newPoly)
                    if dbgPolygons:
                        dprt("wN %2d (%7.4f %7.4f)" % (wN, p.x, p.y))
                        if self.drawWindingNum:
                            self.cfg.draw.drawX(p, str(wN))
                if dbgPolygons:
                    dprt()

        if self.drawFinalPoly:
            for poly in finalPolygons:
                finalLayer = "%02dFinal" % (self.passNum)
                for l in poly:
                    l.draw(layer=finalLayer)
                    l.label(layer=finalLayer)
        return finalPolygons

    def pathIntersect(self, l0, l1):
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
        return loc

    def findIntersections(self, seg):
        global before, evtDbg
        pointData = open("points.dat", "wb")
        self.dbgIntersection = []
        self.evtList = evtList = SortedList()
        self.evtArray = [None] * len(seg)
        for l in seg:
            l.setupEquation()
            scale = self.scale
            p0 = newPoint(l.p0, scale)
            p1 = newPoint(l.p1, scale)
            if pointData != None:
                pointData.write(b"%6d,%6d,%6d,%6d\n" % \
                                (p0.x, p0.y, p1.x, p1.y))
            (x0, y0) = p0
            (x1, y1) = p1
            if x0 < x1:
                self.addEvent(p0, p1, l.p0, l.p1, l)
            elif x1 < x0:
                self.addEvent(p1, p0, l.p1, l.p0, l)
            else:
                if p0.y < p1.y:
                    self.addEvent(p0, p1, l.p0, l.p1, l)
                else:
                    self.addEvent(p1, p0, l.p1, l.p0, l)
        if pointData != None:
            pointData.close()
        
        dprt("\nsweep line event list")
        for n, e in enumerate(evtList):
            dprt("%3d" % (n), end=' ')
            e.prt(end='')
            if e.evtType == LEFT:
                l = e.l
                if l.type == LINE:
                    dprt(" m %7.4f b %7.4f %s" % \
                         (l.m, l.b, str(l.vertical)[0]), end='')
            dprt()
            
        self.sweepList = sweepList = SortedList()
        dprt("\npass %d sweep line processing" % (self.passNum))
        lastX = 0
        dbgList = []
        self.event = 0
        self.lastX = MIN_VALUE
        while len(evtList) > 0:
            global realX
            evt = evtList.pop(0)
            evt.event = False
            self.curX = evt.p.x
            realX = evt.loc.x
            dprt("%3d" % (self.event), end=' ')
            evt.prt(end=' ')
            if self.passNum == -1 and self.event == 57:
                ePrint("findIntersections break pass %d event %d" % \
                       (self.passNum, self.event))


            if evt.evtType == LEFT:
                before = False
                self.updateSweepY(evt.loc.x)
                sweepList.add(evt)
                index = sweepList.bisect_left(evt)
                sweepLen = len(sweepList)
                self.sweepPrt(evt, sweepLen, index)
                l = evt.l
                (x, y) = evt.p
                vertical = abs(l.p0.x - l.p1.x) < MIN_DIST
                idxLeft = index - 1
                y0 = None
                while idxLeft >= 0:
                    evtLeft = sweepList[idxLeft]
                    if not (x == evtLeft.p.x and y == evtLeft.p.y):
                        if y0 is None:
                            y0 = evtLeft.p.y
                            self.intersect(evtLeft, evt, 0)
                        else:
                            if y0 == evtLeft.p.y:
                                self.intersect(evtLeft, evt, 1)
                            elif vertical:
                                self.intersect(evtLeft, evt, 2)
                            else:
                                break
                    idxLeft -= 1

                sweepLen = len(sweepList)
                y0 = None
                idxRight = index + 1
                while idxRight < sweepLen:
                    evtRight = sweepList[idxRight]
                    if not(x == evtRight.p.x and y == evtRight.p.y):
                        if y0 is None:
                            y0 = evtRight.p.y
                            self.intersect(evt, evtRight, 3)
                        else:
                            if y0 == evtRight.p.y:
                                self.intersect(evt, evtRight, 4)
                            elif vertical:
                                self.intersect(evt, evtRight, 5)
                            else:
                                break
                    idxRight += 1
                self.listPrt()
                if vertical:
                    sweepList.remove(evt)
            elif evt.evtType == RIGHT:
                index = self.sweepFind(evt)
                sweepLen = len(sweepList)
                self.sweepPrt(evt, sweepLen, index)
                    
                (x, y) = self.evtArray[evt.index].start.p
                y0 = None
                idxLeft = index - 1
                while idxLeft >= 0:
                    evtLeft = sweepList[idxLeft]
                    if not (x == evtLeft.p.x and y == evtLeft.p.y):
                        if y0 is None:
                            y0 = evtLeft.p.y
                        elif y0 != evtLeft.p.y:
                            break
                    y1 = None
                    idxRight = index + 1
                    while idxRight < sweepLen:
                        evtRight = sweepList[idxRight]
                        if not (x == evtRight.p.x and y == evtRight.p.y):
                            if y1 is None:
                                y1 = evtRight.p.y
                            elif y1 != evtRight.p.y:
                                break
                            self.intersect(evtLeft, evtRight, 6)
                        idxRight += 1
                    idxLeft -= 1
                sweepList.pop(index)
                self.listPrt()
            elif evt.evtType == INTERSECT:
                sweepLen = len(sweepList)
                self.sweepPrt(evt, sweepLen)
                dbgTxt = ""
                if self.curX >= lastX:
                    evt0 = evt.evt0
                    evt1 = evt.evt1

                    dbgTxt = "%3d (%2d %2d)" % \
                        (self.event, evt0.index, evt1.index)
                    if (evt0.slope > MIN_VALUE and
                        evt1.slope > MIN_VALUE): # if neither is vertical
                        dbgTxt += " ("
                        for n, e in enumerate(sweepList):
                            if n != 0:
                                dbgTxt += " "
                            dbgTxt += "%2d" % (e.index)
                        dbgTxt += ")"

                        # y = int(round(evt.loc.y * self.scale))
                        index0 = self.sweepFind(evt0)
                        evt0Sweep = sweepList.pop(index0)
                        # before = False
                        # try:
                        #     evt0Sweep = self.evtArray[evt0.index].start
                        #     index0 = sweepList.index(evt0Sweep)
                        #     dbgTxt += " (%2d" % (index0)
                        #     # evtP0 = sweepList[index0]
                        #     sweepList.pop(index0)
                        #     # evt0.y = y
                        # except ValueError:
                        #     self.eventError(evt0Sweep, "intersect 0")


                        index1 = self.sweepFind(evt1)
                        evt1Sweep = sweepList.pop(index1)
                        # try:
                        #     evt1Sweep = self.evtArray[evt1.index].start
                        #     index1 = sweepList.index(evt1Sweep)
                        #     dbgTxt += " %2d)" % (index1)
                        #     # evtP1 = sweepList[index1]
                        #     sweepList.pop(index1)
                        #     # evt1.y = y
                        # except ValueError:
                        #     self.eventError(evt1Sweep, "intersect 1")
                        before = False
                        x = evt.loc.x
                        evt0.updateY(x)
                        evt1.updateY(x)
                        self.updateSweepY(x)
                        sweepList.add(evt0)
                        sweepList.add(evt1)

                        if evt.save:
                            before = False
                            dbgTxt += " (%2d %2d)" % (evt1.index, evt0.index)
                            dbgTxt += " ("
                            for n, e in enumerate(sweepList):
                                if n != 0:
                                    dbgTxt += " "
                                dbgTxt += "%2d" % (e.index)
                            dbgTxt += ")"

                            if False:
                                dprt()
                                self.sweepListPrt()
                                evtDbg = False
                            try:
                                index = sweepList.index(evt1)
                                evtDbg = False
                            except ValueError:
                                evtDbg = False
                                self.eventError(evt1, "intersect 2")
                            # index = sweepList.bisect_left(evt1)
                            dbgTxt += " (%2d -> %2d)" % (evt1.index, index)
                            indexP = index - 1
                            if indexP >= 0:
                                evtP = sweepList[indexP]
                                dbgTxt += " (%2d %2d)" % (evtP.index, \
                                                          evt1.index)
                                self.intersect(evtP, evt1, 7)

                            indexN = index + 2
                            if indexN < sweepLen:
                                evtN = sweepList[indexN]
                                dbgTxt += " (%2d %2d)" % (evt0.index, \
                                                          evtN.index)
                                self.intersect(evt0, evtN, 8)
                self.listPrt()
                if len(dbgTxt) > 0:
                    dbgList.append(dbgTxt)
            self.lastX = self.curX
            self.event += 1
        dprt("\nsweepLen %d" % (len(sweepList)))
        dprt("\nsweep line intersections")
        for txt in dbgList:
            dprt(txt)
        self.dbgIntersectPrt()

    def sweepFind(self, evt):
        evtSweep = self.evtArray[evt.index].start
        for i, e in enumerate(self.sweepList):
            if evtSweep.index == e.index:
                return i
        else:
            dprt()
            evt.prt()
            self.sweepListPrt()
            raise ValueError("not found")
        return None
        # try:
        #     if self.passNum == 0 and self.event == 17:
        #         dprt()
        #         self.sweepListPrt()
        #         evtDbg = True
        #     # index = sweepList.bisect_left(evtSweep)
        #     index = sweepList.index(evtSweep)
        #     evtDbg = False
        #     curEvt = sweepList[index]
        #     if curEvt.index != evt.index:
        #         ePrint("remove error %2d evt index %3d "\
        #                "curEvt index %2d" % \
        #                (index, evt.index, curEvt.index))
        # except ValueError:
        #     evtDbg = False
        #     self.eventError(evtSweep, "remove error")
    
    def updateSweepY(self, x):
        if self.curX != self.lastX:
            e0 = None
            before = False
            for e in self.sweepList: # for all in list
                e.updateY(x)
                if False and e0 is not None:
                    # if e.y == e0.y:
                    #     e0.y -= 1
                    if e0 > e:
                        dprt()
                        self.sweepListPrt()
                        dprt("y %6d s %7.3f x0 %6d x1 %6d" %
                             (e0.y, e0.slope, e0.p.x, e0.p1.x), end=' ')
                        e0.l.prt(eol=' ')
                        e0.prt()
                        dprt("y %6d s %7.3f x0 %6d x1 %6d" %
                             (e.y, e.slope, e.p.x, e.p1.x), end=' ')
                        e.l.prt(eol=' ')
                        e.prt()
                        raise ValueError("sweep list out of order")
                e0 = e
                    
    def dbgIntersectPrt(self):
        dprt("\nsweep line intersection checks")
        for i, (e, n, curX, idx0, idx1, flag) in \
            enumerate(self.dbgIntersection):
            dprt("%3d %2d %6d (%2d %2d) %s %d" % \
                 (i, e, curX, idx0, idx1, str(flag)[0], n))

    def eventError(self, evt, text):
        dprt("\n%s before %s" % (text, before))
        evt.prt()
        dprt()
        self.sweepListPrt()
        dprt()
        for e in self.sweepList:
            dprt("y %6d s %7.3f x0 %6d x1 %6d" %
                 (e.y, e.slope, e.p.x, e.p1.x), end=' ')
            e.l.prt(eol=' ')
            e.prt()
        self.dbgIntersectPrt()
        raise ValueError("event error")

    def addEvent(self, p0, p1, loc0, loc1, l):
        evtStr = Event(p0, p1, loc0, l, LEFT)
        evtEnd = Event(p1, p0, loc1, l, RIGHT)
        self.evtList.add(evtStr)
        if evtStr.slope > -MAX_VALUE:
            self.evtList.add(evtEnd)
        else:
            evtEnd = evtStr
        self.evtArray[l.index] = EventPair(evtStr, evtEnd)

    def intersect(self, evt0, evt1, n):
        l0 = evt0.l
        l1 = evt1.l
        if xyDist(l0.p0, l1.p1) < MIN_DIST:
            self.dbgIntersection.append((self.event, n, self.curX, l0.index, \
                                         l1.index, False))
            # self.iEvt(l0.p0, evt0, evt1, False)
            return
        elif xyDist(l0.p1, l1.p0) < MIN_DIST:
            self.dbgIntersection.append((self.event, n, self.curX, l0.index, \
                                         l1.index, False))
            # self.iEvt(l0.p1, evt0, evt1, False)
            return

        self.dbgIntersection.append((self.event, n, self.curX, l0.index, \
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

    def swap(self, loc, evt0, evt1):
        sweepList = self.sweepList
        y = int(round(evt0.l.yValue(loc.x) * self.scale))
        try:
            before = True
            evt0Sweep = self.evtArray[evt0.index].start
            index0 = sweepList.index(evt0Sweep)
            sweepList.pop(index0)
            evt0.y = y
            evt0Sweep.y = y
            before = False
            sweepList.add(evt0)
        except ValueError:
            self.eventError(evt0Sweep, "swap 0")

        y = int(round(evt1.l.yValue(loc.x) * self.scale))
        try:
            before = True
            evt1Sweep = self.evtArray[evt1.index].start
            index1 = sweepList.index(evt1Sweep)
            sweepList.pop(index1)
            evt1.y = y
            evt1Sweep.y = y
            before = False
            sweepList.add(evt1)
        except ValueError:
            self.eventError(evt1Sweep, "swap 1")

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
            e.event = False          # chg to sweep
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
                              newPoint(l0End, scale), l1End, l1)
            else:
                l0End = l0.p0
                l1.updateP1(l1End) # start of l1
                l1.updateP0(l0End) # end of l1
                l0.updateP0(l1Str) # end of l0
                self.addEvent(newPoint(l0End, scale), \
                              newPoint(l1End, scale), l0End, l1)

        else:
            pass
            # else
            #  remove l0 end from evt list
            #  add another start for l1 at l0 end
        return None

    def iEvt(self, loc, evt0, evt1, save=True):
        if loc is not None:
            # if evt0.p.y > evt1.p.y:
            #     dprt("iEvt segments out of order")
            p = newPoint(loc, self.scale)
            if p.x >= self.curX:
                for _, pI, _, _ in self.intersections:
                    if p.x == pI.x and p.y == pI.y:
                        return
                evt = Intersect(p, loc, evt0, evt1, save)
                self.evtList.add(evt)
                if save:
                    self.intersectionPrt(evt0.index, evt1.index, loc)
                    self.intersections.append(Intersection(loc, p, \
                                                       evt0.l, evt1.l))
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
            dprt("%2d %7d" % (s.l.index, s.y), end='')
        dprt(")")

    def sweepListPrt(self, sweepList=None):
        if sweepList is None:
            sweepList = self.sweepList
        e0 = None
        for e in sweepList:
            e.prt(end='')
            if e0 is not None:
                dprt(" %s" % (str(e > e0)[0]), end='')
            e0 = e
            dprt()
            
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

    def isectListPrt(self):
        for i, (loc, _, l0, l1) in enumerate(self.intersections):
            dprt("%2d (%7.4f %7.4f) (%2d %2d)" % \
                 (i, loc.x, loc.y, l0.index, l1.index))

    def insidePoint(self, seg, dbg=False):
        global before
        drawTest = False
        if dbg:
            dprt("\ninsidePoint")
        self.evtList = evtList = SortedList()
        self.evtArray = {}
        for l in seg:
            global scale
            l.setupEquation()
            scale = self.scale
            p0 = newPoint(l.p0, scale)
            p1 = newPoint(l.p1, scale)
            x0 = p0.x
            x1 = p1.x
            if x0 < x1:
                self.addInsideEvent(p0, p1, l.p0, l)
            elif x1 < x0:
                self.addInsideEvent(p1, p0, l.p1, l)
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
        chkList = None
        before = False
        while len(evtList) > 0:
            global realX
            evt = evtList.pop(0)
            evt.event = False
            realX = evt.loc.x
            x = evt.p.x
            sweepLen = len(sweepList)
            if sweepLen >= 2 and ((sweepLen & 1)) == 0:
                if x != x0:
                    d = x - x0
                    if d > maxDist:
                        maxDist = d
                        xTest = (x + x0) / (2.0 * self.scale)
                        chkList = []
                        for e in sweepList:
                            chkList.append(e.l)
            if evt.evtType == LEFT:
                x0 = x
                self.sweepList.add(evt)
                if dbg:
                    self.intCount = 2
                    self.sweepPrt(evt, sweepLen, 0)
                    self.listPrt()
            elif evt.evtType == RIGHT:
                try:
                    if dbg:
                        self.intCount = 2
                        self.sweepPrt(evt, sweepLen, 0)
                    evtStr = self.evtArray[evt.index]
                    sweepList.remove(evtStr)
                    if dbg:
                        self.listPrt()
                except ValueError:
                    dprt("\ninsidePoint list error")
                    evt.prt()
                    dprt()
                    self.sweepListPrt()
            x0 = x
        if chkList is not None:
            lTest = Line((xTest, minY), (xTest, maxY))
            if drawTest:
                lTest.draw()
            yList = []
            for l in chkList:
                p = self.insideIntersect(lTest, l)
                if p is not None:
                    yList.append(p.y)
            yList = sorted(yList)
            if len(yList) >= 2:
                p = Point(xTest, (yList[0] + yList[1]) / 2.0)
            else:
                return None
        else:
            return None
        if dbg:
            dprt("\ninsidePoint maxDist %6d (%7.4f %7.4f)" % \
                 (maxDist, p.x, p.y))
            for l in chkList:
                l.prt()
            dprt()
        sweepList.clear()
        return(p, chkList)

    def addInsideEvent(self, p0, p1, loc, l):
        evtStr = Event(p0, p1, loc, l, LEFT)
        evtEnd = Event(p1, p0, loc, l, RIGHT)
        self.evtList.add(evtStr)
        self.evtList.add(evtEnd)
        if evtStr.index in self.evtArray:
            print("error")
        self.evtArray[evtStr.index] = evtStr

    def setOffsetDist(self, args):
        self.dist = self.cfg.evalFloatArg(args[1])

    def setOffsetOutside(self, args):
        self.outside = self.cfg.evalBoolArg(args[1])

    def setOffsetDir(self, args):
        val = args[1].lower()
        if val == "cw":
            self.dir = CW
        elif val == "ccw":
            self.dir = CCW
        else:
            self.dir = None

    def setSplitArcAngle(self, args):
        self.splitArcAngle = self.cfg.evalIntArg(args[1])

    def setOffsetScale(self, args):
        self.scale = self.cfg.evalIntArg(args[1])

    def setKeyScale(self, scale):
        global keyOffset, keyScale
        self.keyScale = keyScale = scale
        self.keyOffset = keyOffset = scale / 2

    def setDrawInitial(self, args):
        self.drawInitial = self.cfg.evalBoolArg(args[1])
            
    def setDbgOffset(self, args):
        self.dbgOffset = self.cfg.evalBoolArg(args[1])

    def setDrawOffset(self, args):
        self.drawOffset = self.cfg.evalBoolArg(args[1])

    def setOffsetReturn(self, args):
        self.offsetReturn = self.cfg.evalBoolArg(args[1])

    def setDbgIntersect(self, args):
        self.dbgIntersect = self.cfg.evalBoolArg(args[1])

    def setIntersectReturn(self, args):
        self.intersectReturn = self.cfg.evalBoolArg(args[1])

    def setDrawSplitLines(self, args):
        self.drawSplitLines = self.cfg.evalBoolArg(args[1])

    def setDbgPolygons(self, args):
        self.dbgPolygons = self.cfg.evalBoolArg(args[1])

    def setDrawFinalPolygon(self, args):
        self.drawFinalPolygon = self.cfg.evalBoolArg(args[1])

    def setDrawWindingNum(self, args):
        self.drawWindingNum = self.cfg.evalBoolArg(args[1])

    def offsetIntersect(self, args):
        cfg = self.cfg
        cfg.ncInit()
        layer = cfg.getLayer(args)
        seg = cfg.dxfInput.getObjects(layer)
        lineSegment = []
        dprt()
        for l in seg:
            l.draw()
            # l.label(h=0.025)
            cfg.draw.drawX(l.p0, str(l.index))
            l.prt()
            lineSegment.append((l.p0, l.p1))

        isectSegments = True
        if isectSegments:
            segments = []
            points = []

            for l in seg:
                segments.append((l.p0, l.p1))
                points.append(l.p0)
            # tmp = isect_segments(segments)
            try:
                tmp = isect_polygon(points)
            except AssertionError:
                tmp = None

        if isectSegments and tmp is not None:
            dprt("\nisect_segments")
            for (x, y) in tmp:
                dprt("%7.4f %7.4f" % (x, y))

        self.intersections = []
        self.findIntersections(seg)
        for loc, _, _, _ in self.intersections:
            cfg.draw.drawX(loc)

        if isectSegments:
            dprt("\nisect_segments")
            for (x, y) in tmp:
                dprt("%7.4f %7.4f" % (x, y))

        dprt("\nintersections")
        for n, i in enumerate(self.intersections):
            dprt("%2d (%7.4f %7.4f) %2d %2d" %
                 (n, i.loc.x, i.loc.y, i.l0.index, i.l1.index))

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

    def windingNumTest(self, args):
        cfg = self.cfg
        cfg.ncInit()
        layer = args[1]
        refCircle = cfg.dxfInput.getObjects(layer)
        layer = args[2]
        segments = cfg.dxfInput.getPath(layer, dbg=False)

        p = refCircle[0].c

        for seg in segments:
            wN = windingNumber(p, seg, self.scale, True)
            dprt("wN %3.1f" % (wN))

        p = Point(0, 0)

        p0 = Point(-0.25, 0.25)
        p1 = Point( 0.00, 0.50)
        p2 = Point(-0.25, 0.75)

        l0 = Line(p0, p1, 0)
        l1 = Line(p1, p2, 1)
        seg = (l0, l1)
        windingNumber(p, seg, self.scale, True)
        
        l0 = Line(p2, p1, 0)
        l1 = Line(p1, p0, 1)
        seg = (l0, l1)
        windingNumber(p, seg, self.scale, True)

        p3 = Point( 0.25, 0.25)
        p4 = Point( 0.25, 0.75)

        l0 = Line(p3, p1, 0)
        l1 = Line(p1, p4, 1)
        seg = (l0, l1)
        windingNumber(p, seg, self.scale, True)

        l0 = Line(p4, p1, 0)
        l1 = Line(p1, p3, 1)
        seg = (l0, l1)
        windingNumber(p, seg, self.scale, True)

        p5 = Point( 0.0, 0.25)
        p6 = Point( 0.0, 0.75)

        l0 = Line(p0, p5, 1)
        l1 = Line(p5, p6, 2)
        l2 = Line(p6, p2, 3)
        seg = (l0, l1, l2)
        windingNumber(p, seg, self.scale, True)

        l0 = Line(p3, p5, 1)
        l1 = Line(p5, p6, 2)
        l2 = Line(p6, p4, 3)
        seg = (l0, l1, l2)
        windingNumber(p, seg, self.scale, True)

class Event:
    def __init__(self, p, p1, loc, l, evtType):
        self.evtType = evtType
        self.p = p
        self.p1 = p1
        self.y = p.y
        self.loc = loc
        self.l = l
        self.index = l.index
        self.event = True
        p0 = l.p0
        p1 = l.p1
        dx = p1.x - p0.x
        dy = p1.y - p0.y
        if abs(dx) < MIN_DIST:
            self.slope = MIN_VALUE
        elif abs(dy) < MIN_DIST:
            self.slope = 0
        else:
            self.slope = dy / dx

    def updateY(self, x):
        self.y = int(round(self.l.yValue(x) * scale))

    def prt(self, end='\n'):
        dprt("(%6d %6d) (%6d %6d) %7s %2d %6d %s" % \
             (self.p.x, self.p.y, self.p1.x, self.p1.y, \
              ("%7.3f" % self.slope) if self.slope > -MAX_VALUE else "vert", \
              self.index, self.y, evtStr[self.evtType]), end)

    def __str__(self):
        return("p (%6d %6d) %2d %9d %s" % \
               (self.p.x, self.p.y, self.index, self.y, \
                evtStr[self.evtType]))

    def __gt__(self, other):
        if self.event:
            if self.p.x == other.p.x:
                if self.evtType == other.evtType:
                    if self.p.y == other.p.y:
                        return self.slope > other.slope
                    else:
                        return self.p.y > other.p.y
                else:
                    return self.evtType > other.evtType
            else:
                return self.p.x > other.p.x
        else:
            if self.y == other.y:
                if self.slope == other.slope:
                    if self.p.x == other.p.x:
                        x = 3
                        val = (self.p1.x > other.p1.x if before else \
                                self.p1.x < other.p1.x)
                    else:
                        x = 2
                        val = (self.p.x > other.p.x if before else \
                                self.p.x < other.p.x)
                else:
                    x = 1
                    val = (self.slope < other.slope if before else \
                            self.slope > other.slope)
            else:
                x = 0
                val = self.y > other.y
            if evtDbg:
                dprt("%2d _gt_ %2d %s %d" % \
                     (self.index, other.index, str(val)[0], x))
            return val

    def __lt__(self, other):
        if self.event:
            if self.p.x == other.p.x:
                if self.evtType == other.evtType:
                    if self.p.y == other.p.y:
                        return self.slope < other.slope
                    else:
                        return self.p.y < other.p.y
                else:
                    return self.evtType < other.evtType
            else:
                return self.p.x < other.p.x
        else:
            if self.y == other.y:
                if self.slope == other.slope:
                    if self.p.x == other.p.x:
                        x = 3
                        val = (self.p1.x < other.p1.x if before else \
                               self.p1.x > other.p1.x)
                    else:
                        x = 2
                        val = (self.p.x < other.p.x if before else \
                               self.p.x > other.p.x)
                else:
                    x = 1
                    val = (self.slope > other.slope if before else \
                           self.slope < other.slope)
            else:
                x = 0
                val = self.y < other.y
            if evtDbg:
                dprt("%2d _lt_ %2d %s %d (%6d < %6d)" % \
                     (self.index, other.index, str(val)[0], x,
                      self.y, other.y), end='')
                if x == 1:
                    s = (self.slope, other.slope) if before else \
                        (self.slope, other.slope)
                    dprt(" %s (%7.3f < %7.3f)" % \
                         (('a', 'b')[before], s[0], s[1]), end='')
                dprt()
            return val

    def __eq__(self, other):
        if self.event:
            if self.p.x == other.p.x:
                if self.p.y == other.p.y:
                    return self.index == other.index
            return False
        else:
            x = 0
            val = self.index == other.index
            if evtDbg:
                dprt("%2d _eq_ %2d %s %d" % \
                     (self.index, other.index, str(val)[0], x))
            return val

class Intersect:
    def __init__(self, p, loc, evt0, evt1, save):
        self.evtType = INTERSECT
        self.p = p
        self.p1 = Point(0, 0)
        self.loc = loc
        self.evt0 = evt0
        self.evt1 = evt1
        self.save = save
    
    def prt(self, end='\n', l=False):
        evt0 = self.evt0
        evt1 = self.evt1
        dprt("(%6d %6d) %23s %2d %2d     I" % \
             (self.p.x, self.p.y, "", evt0.index, evt1.index), end='')
        if l:
            dprt(" %2d %2d" % (self.evt0.index, self.evt1.index), '')
        dprt(end=end)

    def __str__(self):
        return("p (%6d %6d)              %s" % \
               (self.p.x, self.p.y, \
                evtStr[self.evtType]))

    def __gt__(self, other):
        if self.p.x == other.p.x:
            # return self.p.y > other.p.y
            return False
        else:
            return self.p.x > other.p.x

    def __lt__(self, other):
        if self.p.x == other.p.x:
            return True
            # return self.p.y < other.p.y
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

def relPoint(p, p0, scale):
    return (int(round(p.x * scale)) - p0.x, int(round(p.y * scale)) - p0.y)
        
def windingNumber(p, poly, scale, dbg=False):
    (x, y) = pInt = newPoint(p, scale)
    if dbg:
        dprt("\npolygon input to windingNumber")
        for l in poly:
            l.prt()
        dprt("\npoint for winding number test")
        dprt("p (%7.4f %7.4f) (%6d %6d)" % (p.x, p.y, x, y))
        dprt("\nwinding number test")
    wN = 0
    for l in poly:
        (x0, y0) = relPoint(l.p0, pInt, scale)
        (x1, y1) = relPoint(l.p1, pInt, scale)
        if dbg:
            dprt("%2d (%6d %6d) (%6d %6d)" % \
                 (l.index, x0, y0, x1, y1), end='')
        if x0 != x1:
            if (x0 < 0 and x1 > 0 or \
                x1 < 0 and x0 > 0):
                    r = y0 + x0 * float(y1 - y0) / float(x0 - x1)
                    if r > 0:
                        if x1 < 0:
                            wN += 1
                        else:
                            wN -= 1
                    if dbg:
                        dprt(" r %6.0f wN %2d" % (r, wN), end='')
            elif x0 == 0 and y0 > 0:
                wN += 0.5 if x1 > 0 else -0.5
                if dbg:
                    dprt(" x0 %6d y0 %6d wN %4.1f" % (x0, y0, wN), end='')
            elif x1 == 0 and y1 > 0:
                wN += 0.5 if x0 < 0 else -0.5
                if dbg:
                    dprt(" x1 %6d y1 %6d wN %4.1f" % (x0, y0, wN), end='')
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

def lineArcTangent(l, a):
    (x0, y0) = l.p0             # start and end
    (x1, y1) = l.p1

    (i, j) = a.c                # center of arc
    x0 -= i                     # subtract center of arc
    y0 -= j
    x1 -= i
    y1 -= j

    (m, b, _) = eqnLine((x0, y0), (x1, y1)) # equation of line
    qA = 1 + m*m
    qB = 2 * m * b
    qC = b*b - a.r*a.r
    sqrTerm = qB*qB - 4 * qA * qC
    qA *= 2

    return abs(sqrTerm) < MIN_DIST

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
        try:
            h = sqrt(r0*r0 - d0*d0)  # distance perpindicular to  center line
        except ValueError:
            dprt("ValueError")
            return None
        # dprt("d %6.3f d0 %6.3f h %6.3f" % (d, d0, h))

        pa = Point(d0 * cosA + h * sinA + i, \
                   d0 * sinA - h * cosA + j)

        pb = Point(d0 * cosA - h * sinA + i, \
                   d0 * sinA + h * cosA + j)

        if a0.onSegment(pa) and a1.onSegment(pa):
            return pa

        if a0.onSegment(pb) and a1.onSegment(pb):
            return pb
    return None
