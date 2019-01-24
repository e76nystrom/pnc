from __future__ import print_function

from math import atan2, degrees
from geometry import ARC, CCW, CW, LINE
from geometry import Arc, Line
from geometry import calcAngle, orientation, newPoint, oStr, pathDir, \
    reverseSeg, splitArcs
from dbgprt import dprt, dprtSet, ePrint
# from sortedcontainers import SortedDict, SortedList
from sortedlist import SortedList
# from operator import attrgetter
from sweepLine import line_intersections

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
                l.draw()
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
        for l in seg:
            l.draw()
            cfg.draw.drawX(l.p0, str(l.index))
            l.prt()
            lineSegment.append((l.p0, l.p1))
        self.findIntersections(seg)
        line_intersections(lineSegment)

    def findIntersections(self, seg):
        segList = []
        for l in seg:
            scale = self.scale
            p0 = l.p0
            p1 = l.p1
            x0 = int(p0[0] * scale)
            x1 = int(p1[0] * scale)
            if x0 < x1:
                key = int(p0[1] * scale) * 100 + l.index
                segList.append(self.Segment(p0, l, key, True, scale))
                segList.append(self.Segment(p1, l, key, False, scale))
            elif x1 < x0:
                key = int(p1[1] * scale) * 100 + l.index
                segList.append(self.Segment(p1, l, key, True, scale))
                segList.append(self.Segment(p0, l, key, False, scale))
            else:
                y0 = int(p0[1] * scale)
                y1 = int(p1[1] * scale)
                if y0 < y1:
                    key = int(p0[1] * scale) * 100 + l.index
                    segList.append(self.Segment(p0, l, key, True, scale))
                    segList.append(self.Segment(p1, l, key, False, scale))
                else:
                    key = int(p1[1] * scale) * 100 + l.index
                    segList.append(self.Segment(p1, l, key, True, scale))
                    segList.append(self.Segment(p0, l, key, False, scale))
        
        segList = sorted(segList, key=lambda l: (l.p.x, l.p.y))
        for l in segList:
            l.prt()

        # sweepList = SortedDict()
        # dprt()
        # for l in segList:
        #     l.prt()
        #     # dprt("x %8d y %8d %d %s" % (l.p.x, l.p.y, l.index, l.left))
        #     # l.l.prt()
        #     if l.left:
        #         sweepList[l.key] = l
        #         listLen = len(sweepList)
        #         index = sweepList.index(l.key)
        #         idxLeft = sweepList.bisect_left(l.key)
        #         idxRight = sweepList.bisect_right(l.key)
                
        #         dprt("insert %2d x %6d len %d (%d %d %d)" % \
        #              (l.index, l.p.x, listLen, idxLeft, index, idxRight))
                
        #         if idxLeft != index:
        #             itemLeft = sweepList.peekitem(idxLeft)[1]
        #             dprt("intersect (%2d %2d) (%2d %2d)" % \
        #                  (index, idxLeft, l.index, itemLeft.index))
                    
        #         if idxRight < listLen:
        #             itemRight = sweepList.peekitem(idxRight)[1]
        #             dprt("intersect (%2d %2d) (%2d %2d)" % \
        #                  (index, idxRight, l.index, itemRight.index))
        #     else:
        #         listLen = len(sweepList)
        #         index = sweepList.index(l.key)
        #         idxLeft = sweepList.bisect_left(l.key)
        #         idxRight = sweepList.bisect_right(l.key)
        #         dprt("delete %2d x %6d len %d (%d %d %d)" % \
        #              (l.index, l.p.x, listLen, idxLeft, index, idxRight))
        #         if index != idxLeft and \
        #            idxRight < listLen and \
        #            idxLeft != idxRight:
        #             itemLeft = sweepList.peekitem(idxLeft)[1]
        #             itemRight = sweepList.peekitem(idxRight)[1]
        #             dprt("intersect (%2d %2d) (%2d %2d)" % \
        #                  (idxLeft, idxRight, itemLeft, itemRight))
        #         sweepList.pop(l.key)
        #     dprt()
        # print("length %d" % (len(sweepList)))
        
        self.sweepList = sweepList = SortedList()
        dprt()
        for l in segList:
            l.prt(end=' ')
            if l.left:
                sweepList.add(l)
                index = sweepList.bisect_left(l)
                listLen = len(sweepList)
                self.sweepPrt("i", l, listLen, index)
                if index > 0:
                    idxLeft = index - 1
                    itemLeft = sweepList[idxLeft]
                    # dprt("intersect l (%2d %2d) (%2d %2d)" % \
                    #      (index, idxLeft, l.index, itemLeft.index))
                    loc0 = self.intersect(l.l, itemLeft.l)
                    self.intersectionPrt(index, idxLeft, loc0)
                else:
                    self.noIntersection()

                idxRight = index + 1
                if idxRight < listLen:
                    itemRight = sweepList[idxRight]
                    # dprt("intersect r (%2d %2d) (%2d %2d)" % \
                    #      (index, idxRight, l.index, itemRight.index))
                    loc1 = self.intersect(l.l, itemRight.l)
                    self.intersectionPrt(index, idxRight, loc1)
                else:
                    self.noIntersection()
                self.listPrt(sweepList)
            else:
                index = sweepList.bisect_left(l)
                listLen = len(sweepList)
                self.sweepPrt("d", l, listLen, index)
                item = sweepList[index]
                if item.key != l.key:
                    ePrint("key error")
                if index > 0:
                    idxLeft = index - 1
                    idxRight = index + 1
                    if idxRight < listLen:
                        itemLeft = sweepList[idxLeft]
                        itemRight = sweepList[idxRight]
                        # dprt("intersect d (%2d %2d) (%2d %2d)" % \
                        #      (idxLeft, idxRight, \
                        #       itemLeft.index, itemRight.index))
                        loc = self.intersect(itemLeft.l, itemRight.l)
                        self.intersectionPrt(idxLeft, idxRight, loc)
                    else:
                        self.noIntersection()
                else:
                        self.noIntersection()
                self.noIntersection()
                self.listPrt(sweepList)
                sweepList.pop(index)
            # dprt()
        print("length %d" % (len(sweepList)))

    def sweepPrt(self, string, l, listLen, sweepIndex):
        dprt("%s %2d x %6d l %2d i %2d" % \
             (string, l.index, l.p.x, listLen, sweepIndex), end='')

    def listPrt(self, sweepList):
        dprt(" (", end='')
        for (i, s) in enumerate(sweepList):
            if i != 0:
                dprt(", ", end='')
            dprt("%2d" % (s.l.index), end='')
            dprt(" %5d" % (s.p.y), end='')
        dprt(")")

    def intersectionPrt(self, idx0, idx1, loc):
        item0 = self.sweepList[idx0].index
        item1 = self.sweepList[idx1].index
        dprt(" (%2d %2d) (%2d %2d)" % (idx0, idx1, item0, item1), end='')
        if loc is not None:
            dprt(" (%5.2f %5.2f)" % (loc[0], loc[1]), end='')
        else:
            dprt("              ", end='')

    def noIntersection(self):
        dprt("                ", end='')
        dprt("              ", end='')

    class Segment:
        def __init__(self, p, l, key, left, scale=None):
            self.p = newPoint(p, scale)
            self.l = l
            self.index = l.index
            self.left = left
            self.key = key

        def __gt__(self, other):
            # if not isinstance(other, self.Segment):
            #     raise Exception("")
            # else:
            return self.key > other.key

        def __lt__(self, other):
            # if not isinstance(other, self.Segment):
            #     raise Exception("")
            # else:
            return self.key < other.key

        def prt(self, end='\n'):
            dprt("p (%6d %6d) %2d %s" % \
                 (self.p.x, self.p.y, self.index, str(self.left)[0]), end)

    # class SegmentList:

    def intersect(self, l0, l1):
        if l0.type == LINE:
            if l1.type == LINE:
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
        self.cfg.draw.drawX(iPt, "%d-%d" % (l0.index, l1.index))
        return iPt

    def lineArcIntersection(self, l0, l1):
        pass

    def arcArcIntersection(self, l0, l1):
        pass

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
