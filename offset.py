from __future__ import print_function

from math import atan2, degrees
from geometry import ARC, CCW, CW, LINE, MIN_DIST
from geometry import Arc, Line
from geometry import calcAngle, orientation, newPoint, oStr, pathDir, \
    reverseSeg, splitArcs, xyDist
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
        )
        self.dbg = True
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
            
        drawX = cfg.draw.drawX
        for seg in segments:
            newSeg = splitArcs(seg)
            curDir = pathDir(newSeg, self.dbg)
            if curDir != direction:
                newSeg = reverseSeg(newSeg)
            dprt("direction %s" % (oStr(direction)))
            prevL = newSeg[-1]
            prevL1 = prevL.parallel(distance)
            oSeg = []
            for (n, l) in enumerate(newSeg):
                # l.draw()
                if prevL.type == LINE and l.type == LINE:
                    (x0, y0) = prevL.p0
                    (x1, y1) = l.p0
                    (x2, y2) = l.p1
                    o = orientation(prevL.p0, l.p0, l.p1)
                    a0 = atan2(y0 - y1, x0 - x1)
                    a1 = atan2(y2 - y1, x2 - x1)
                    # prevL.prt()
                    # l.prt()
                    dprt("0 (%7.4f %7.4f) 1 (%7.4f %7.4f) 2 (%7.4f %7.4f)" % \
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
                # l1.draw()
                if o == direction: # convex
                    dprt("convex")
                    lEnd = Line(prevL1.p1, l.p0)
                    # lEnd.draw()
                    # drawX(prevL1.p1, str(-n))
                    lStr = Line(l.p0, l1.p0)
                    # lStr.draw()
                    # drawX(l1.p0, str(n))
                    oSeg.append(lEnd)
                    oSeg.append(lStr)
                else:           # concave
                    dprt("concave")
                    # drawX(l.p0, "C")
                    # drawX(prevL1.p1, "0")
                    # drawX(l1.p0, "1")
                    if direction == CCW:
                        a1 = degrees(calcAngle(l.p0, prevL1.p1))
                        a0 = degrees(calcAngle(l.p0, l1.p0))
                        aDir = CW
                    else:
                        a0 = degrees(calcAngle(l.p0, prevL1.p1))
                        a1 = degrees(calcAngle(l.p0, l1.p0))
                        aDir = CCW
                    dprt("n %2d a0 %7.2f a1 %7.2f %s" % (n, a0, a1, oStr(aDir)))
                    lArc = Arc(l.p0, abs(distance), a0, a1, direction=aDir)
                    lArc.prt()
                    # lArc.draw()
                    oSeg.append(lArc)
                oSeg.append(l1)
                prevL = l
                prevL1 = l1
                
            for n, l in enumerate(oSeg):
                l.index = n
                l.prt()
                l.draw()
                drawX(l.p0, str(n))

            self.findIntersections(oSeg)

    def offsetIntersect(self, args):
        cfg = self.cfg
        cfg.ncInit()
        layer = cfg.getLayer(args)
        seg = cfg.dxfInput.getLines(layer)
        lineSegment = []
        dprt()
        for l in seg:
            l.draw()
            cfg.draw.drawX(l.p0, str(l.index))
            l.prt()
            lineSegment.append((l.p0, l.p1))
        self.findIntersections(seg)
        # line_intersections(lineSegment)

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
            self.intCount = 0
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

                evt0 = evt.evt0
                evt1 = evt.evt1
                sweepList.remove(evt.evt0)
                sweepList.remove(evt.evt1)
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
            # dprt()
        print("length %d" % (len(sweepList)))

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
            evt = Intersect(p, loc, evt0, evt1)
            if p.x > self.curX:
                self.intCount += 1
                self.intersectionPrt(evt0.index, evt1.index, loc)
                self.evtList.add(evt)
            a = 1

    def eventPrt(self):
        for evt in self.evtList:
            evt.prt()
        
    def sweepPrt(self, string, evt, sweepLen, sweepIndex=None):
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
        if l0.type == LINE:
            if l1.type == LINE:
                # if abs(l0.index - l1.index) == 1:
                #     return None
                return self.lineIntersection(l0, l1)
            else:
                return self.lineArcIntersection(l0, l1)
        else:
            if l1.type == LINE:
                return self.lineArcIntersection(l1, l0)
            else:
                return self.arcArcIntersection(l0, l1)

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
        self.cfg.draw.drawX(iPt, "%d-%d" % (l0.index, l1.index))
        return iPt

    def lineArcIntersection(self, l0, l1):
        pass

    def arcArcIntersection(self, l0, l1):
        pass

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
        
