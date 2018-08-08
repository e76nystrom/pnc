from __future__ import print_function
from sys import stdout, stderr
from copy import copy
from dbgprt import dprt, dflush, ePrint
from math import acos, asin, atan2, ceil, cos, degrees, floor, hypot, \
    pi, radians, sin, sqrt

# dxf arcs are always counter clockwise.

LINE = 0
ARC = 1

MIN_DIST = .0001
MAX_VALUE = 999999
MIN_VALUE = -999999

INDEX_MARKER = -99

draw = None                     # draw class
cfg = None                      # config class

lCount = 0

# lineIndex = 0

def quadrant(p):
    (x, y) = p
    if x >= 0:
        if y >= 0:
            return(0)
        else:
            return(3)
    else:
        if y >= 0:
            return(1)
        else:
            return(3)

def degAtan2(y, x):
    a = degrees(atan2(y, x))
    if a < 0.0:
        a += 360.0
    return(a)

def xyDist(p0, p1):
    return(hypot(p0[0] - p1[0], p0[1] - p1[1]))

def calcAngle(center, point):
    dx = point[0] - center[0]
    dy = point[1] - center[1]
    # printPoint("angle point", point)
    # printPoint("center point", center)
    angle = atan2(dy, dx)
    if angle < 0:
        angle += 2 * pi
    # dprt("angle %5.1f" % (degrees(angle)))
    return(angle)

def fix(a):
    if a >= 360:
        a -= 360
    return(a)

def translate(p0, p1):
    return((p0[0] - p1[0], p0[1] - p1[1]))

def offset(p0, p1):
    return((p0[0] + p1[0], p0[1] + p1[1]))

# orientation of three points

# Let p,q and r be the three points,

# k= (q.y - p.y) * (r.x - q.x) - (q.x - p.x) * (r.y - q.y)

# if (k == 0): They are all colinear
# if (k > 0) : They are all clockwise
# if (k < 0) : They are counter clockwise

# ccw(A, B, c) = (B - A) * (C - A)
#              = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)

# def orientation1(a, b, c):
#     val = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
#     if abs(val) < MIN_DIST:
#         return(0)
#     elif val > 0:
#         return(CCW)
#     else:
#         return(CW)

# def orientation2(p1, p2, p3):
#     val = (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])
#     if abs(val) < MIN_DIST:
#         return(0)
#     elif val > 0:
#         return(CCW)
#     else:
#         return(CW)
    
# http://www.geeksforgeeks.org/orientation-3-ordered-points/
#
# // To find orientation of ordered triplet (p1, p2, p3).
# // The function returns following values
# // 0 --> p, q and r are colinear
# // 1 --> Clockwise
# // 2 --> Counterclockwise
# int orientation(Point p1, Point p2, Point p3)
# {
#     // See 10th slides from following link for derivation
#     // of the formula
#     int val = (p2.y - p1.y) * (p3.x - p2.x) -
#               (p2.x - p1.x) * (p3.y - p2.y);
#
#     if (val == 0) return 0;  // colinear
#
#     return (val > 0)? 1: 2; // clock or counterclock wise
# }

#    0123456789012
#7             p3 * (12, 7)
#6             *  |  y3 - y2
#5          *     |
#4     p2 o-------- (4, 4)
#3       o| x3 - x2
#2      o |
#1     o  | y2 - y1
#0 p1 o---- (0, 0)
#     x2 - x1

# slope of segment (p1, p2): s = (y2 - y1) / (x2 - x1)
# slope of segment (p2, p3): t = (y3 - y2) / (x3 - x2)

# Orientation test
#  counterclockwise (left turn): s < t
#  clockwise (right turn): s > t
#  collinear (left turn): s = t

# The orientation depends on whether the expression

# (y2-y1) * (x3-x2) - (y3-y2) * (x2-x1)

CW = 1
CCW = 2
BOTH = 3

def orientation(p1, p2, p3):
    val = ((p2[1] - p1[1]) * (p3[0] - p2[0]) - \
           (p3[1] - p2[1]) * (p2[0] - p1[0]))
    # dprt("val %9.6f p0 %6.3f, %6.3f p1 %6.3f, %6.3f p2 %6.3f, %6.3f" % \
    #       (val, p1[0], p2[1], p2[0], p2[1], p3[0], p3[1]))
    if abs(val) < MIN_DIST:
        return 0;
    elif val > 0:
        return CW
    else:
        return CCW

def oStr(o):
    return(('LIN', 'CW ', 'CCW')[o])

# orientation test
# p0 = (-1, 0)
# p1 = (0, 0)
# p2a = (1, 1)
# p2b = (1, -1)
# oa = orientation1(p0, p1, p2a)
# ob = orientation1(p0, p1, p2b)
# dprt("oa %d %s ob %d %s" % (oa, oStr(oa), ob, oStr(ob)))

# p0 = (0, 0)
# p1 = (4, 4)
# p2 = (12, 7)
# o = orientation(p0, p1, p2)
# dprt("o %d %s " % (o, oStr(o)))

def segOrientation(seg, index):
    # dprt("segOrientation")
    # dprt("index %3d" % (index))
    l0 = seg[index]
    index += 1
    if index > len(seg):
        index = 0
    l1 = seg[index]
    # l0.prt()
    # dprt("index %3d" % (index))
    # l1.prt()
    # dprt()
    o = orientation(l0.p0, l0.p1, l1.p1)
    return(o)

def findMinX(seg):
    dprt("findMinX")
    minX = 1000
    minY = 1000
    index = None
    for (i, l) in enumerate(seg):
        (x, y) = l.p0
        dprt("%2d %2d x %7.4f y %7.4f" % (i, l.index, x, y))
        if x < minX:
            minX = x
            minY = y
            index = i
        elif x == minX and y < minY:
            minY = y
            index = i
    dprt("index %d minX %7.4f minY %7.4f" % (index, minX, minY))
    return((index, minX))

def pathDir(seg, dbg=False):
    # dprt("pathDir")
    # index = findMaxY(seg)[0]
    # l = seg[index]
    # l.prt()
    # if l.type == ARC:
    #     dir = (CW, CCW)[l.swapped]
    # else:
    #     (x0, y0) = l.p0
    #     (x1, y1) = l.p1
    #     dx = x0 - x1
    #     dy = y0 - y1
    #     if abs(dx) < MIN_DIST:
    #         if dy > 0:
    #             dir = CW
    #         else:
    #             dir = CCW
    #     elif dx > 0:
    #         dir = CW
    #     else:
    #         dir = CCW
    #     if dbg and draw is not None:
    #         (x0, y0) = l.p0
    #         (x1, y1) = l.p1
    #         str = "%s %d p0 dy %4.1f dx %4.1f %7.4f, %7.4f p1 %7.4f %7.4f" % \
    #               (oStr(dir), l.index, dy, dx, x0, y0, x1, y1)
    #         draw.text(str, (x0 + dbg, y0 + dbg), .025)
    # dprt("maxYDir %s" % (oStr(dir)))
    # dprt()

    index = findMinX(seg)[0]
    l = seg[index]
    l.prt()
    if l.type == ARC:
        dir = (CCW, CW)[l.swapped]
        if dbg and draw is not None:
            (x0, y0) = l.p0
            str = "%3s %2d" % (oStr(dir), l.index)
            draw.text(str, (x0 + dbg, y0 + dbg), .025)
    else:
        (x0, y0) = l.p0
        (x1, y1) = l.p1
        dx = x0 - x1
        dy = y0 - y1
        if abs(dy) < MIN_DIST:
            if dx > 0:
                dir = CW
            else:
                dir = CCW
        elif dy > 0.0:
            dir = CCW
        else:
            dir = CW
        if dbg and draw is not None:
            # prev = seg[index - 1]
            # o = orientation(prev.p0, l.p0, l.p1)
            str = "%s %s %d dy %3.1f dx %3.1f p0 %7.4f, %7.4f " \
                  "p1 %7.4f %7.4f" % \
                  (oStr(dir), oStr(dir), l.index, dy, dx, x0, y0, x1, y1)
            draw.text(str, (x0 + dbg, y0 + dbg), .020)
    dprt("minXDir %s" % (oStr(dir)))
    dprt()
    return(dir)

class Line():
    def __init__(self, p0, p1, i=-1, e=None):
        self.p0 = p0
        self.p1 = p1
        self.type = LINE
        self.str = 'line'
        self.index = i
        self.e = e
        self.length = xyDist(p0, p1)
        self.text = None

    def updateP0(self, p0):
        self.p0 = p0
        self.length = xyDist(self.p0, self.p1)

    def updateP1(self, p1):
        self.p1 = p1
        self.length = xyDist(self.p0, self.p1)

    def swap(self):
        (self.p0, self.p1) = (self.p1, self.p0)

    def parallel(self, dist):
        (x0, y0) = self.p0      # start and end
        (x1, y1) = self.p1
        xM = (x0 + x1) / 2      # mid point
        yM = (y0 + y1) / 2
        d = abs(dist)
        dx = x1 - x0
        dy = y1 - y0
        if abs(dx) > abs(dy): # if x change greater
            m = -dy / dx
            yt = sqrt((d * d) / (1 + m * m))
            xt = m * yt
        else:               # if y change greater
            m = -dx / dy
            xt = sqrt((d * d) / (1 + m * m))
            yt = m * xt
        minus = False
        dir0 = orientation(self.p0, (xM, yM), (xM + xt, yM + yt))
        if dist > 0:        # if clockwise
            minus = dir0 != CCW
        else:               # if counter clockwise
            minus = dir0 != CW
        if minus:
            xt = -xt
            yt = -yt
        dir1 = orientation(self.p0, (xM, yM), (xM + xt, yM + yt))
        dprt("parallel dir %s %s" % (oStr(dir0), oStr(dir1)))
        return(Line((x0 + xt, y0 + yt), (x1 + xt, y1 + yt), self.index))

    def midPoint(self, dist=0, dbg=False):
        (x0, y0) = self.p0
        (x1, y1) = self.p1
        xM = (x0 + x1) / 2
        yM = (y0 + y1) / 2
        if dist != 0.0:
            d = abs(dist)
            dx = x1 - x0
            dy = y1 - y0
            if abs(dx) > abs(dy): # if x change greater
                m = -dy / dx
                yt = sqrt((d * d) / (1 + m * m))
                xt = m * yt
            else:               # if y change greater
                m = -dx / dy
                xt = sqrt((d * d) / (1 + m * m))
                yt = m * xt
            pa = (xM + xt, yM + yt)
            pb = (xM - xt, yM - yt)
            pM = pa
            dir = orientation(self.p0, (xM, yM), pM)
            if dist > 0:        # dist > 0 is clockwise
                if dir != CCW:
                    pM = pb
            else:               # dist < 0 is counter clockwise
                if dir != CW:
                    pM = pb
            if dbg and draw is not None:
                l = draw.lDebug
                draw.drawCircle(self.p0, layer=l)
                draw.drawCircle((xM, yM), 0.020, layer=l)
                draw.drawCircle(pM, 0.030, layer=l, txt=('+', '-')[dist < 0.0])
            dir = orientation(self.p0, (xM, yM), pM)
            if dbg:
                dprt("midPoint dir %s" % (oStr(dir)))
        else:
            pM = (xM, yM)
        return(pM)

    def linePoint(self, dist):
        (x0, y0) = self.p0
        (x1, y1) = self.p1
        dx = x1 - x0
        dy = y1 - y0
        if abs(dy) < MIN_DIST:  # horizontal
            x = dist
            y = 0
        elif abs(dx) < MIN_DIST: # vertical
            x = 0
            y = dist
        else:                   # oblique
            m = abs(dy / dx)
            x = sqrt(dist * dist / (m * m + 1))
            y = m * x
        # dprt("linePoint")
        # dprt("p0 (%7.3f, %7.3f) p1 (%7.3f, %7.3f)" % \
        #         (x0, y0, x1, y1))
        # dprt("x %7.3f y %7.3f" % (x, y))
        if x1 < x0:
            x = -x
        if y1 < y0:
            y = -y
        # dprt("x %7.3f y %7.3f" % (x, y))
        return((x0 + x, y0 + y))

    def split(self, dist):
        p = self.linePoint(dist)
        l0 = Line(self.p0, p, self.index)
        l1 = Line(p, self.p1, self.index)
        return((l0, l1))

    def intersect(self, l):
        if l.type == LINE:
            p = lineLine(self, l)
        elif l.type == ARC:
            p = lineArc(self, l, 1)
            # if p is None:
            #     dprt("l no intersection s %7.4f, %7.4f e %7.4f %7.4f" % \
            #           (self.p1[0], self.p1[1], l.p0[0], l.p1[1]))
        if p is not None:
            self.updateP1(p)    # set end of this one
            l.updateP0(p)       # set start of next one
            if l.type == ARC:
                a = degAtan2(p[1] - l.c[1], p[0] - l.c[0])
                if l.swapped:
                    l.a1 = a
                else:
                    l.a0 = a
        return(p)

    def point90(self, p, dist):
        (x0, y0) = self.p0
        (x1, y1) = self.p1
        d = abs(dist)
        dx = x1 - x0
        dy = y1 - y0
        if abs(dx) > abs(dy): # if x change greater
            m = -dy / dx
            yt = sqrt((d * d) / (1 + m * m))
            xt = m * yt
        else:               # if y change greater
            m = -dx / dy
            xt = sqrt((d * d) / (1 + m * m))
            yt = m * xt
        minus = False
        (xp, yp) = p
        dir = orientation(self.p0, (xp, yp), (xp + xt, yp + yt))
        if dist > 0:        # if clockwise
            minus = dir != CCW
        else:               # if counter clockwise
            minus = dir != CW
        if minus:
            xt = -xt
            yt = -yt
        return((xp + xt, yp + yt))

    def pointDistance(self, p):
        (x, y) = p
        (x0, y0) = self.p0
        (x1, y1) = self.p1
                      
        dx = x1 - x0
        dy = y1 - y0
        magSqr = dx * dx + dy * dy;

        u = ((x - x0) * dx + (y - y0) * dy) / float(magSqr)
        if u < 0.0 or u > 1.0:
            return(None)

        xt = x0 + u * dx
        yt = y0 + u * dy

        d = hypot(xt - x, yt - y)
        return(d);

    def startDist(self, p):
        return(xyDist(self.p0, p))

    def extend(self, dist, start):
        if start:
            p0 = self.p0
            p1 = self.p1
        else:
            p0 = self.p1
            p1 = self.p0
        (x0, y0) = p0
        (x1, y1) = p1
        dx = x1 - x0
        dy = y1 - y0
        if abs(dx) > abs(dy):
            m = dy / dx
            # b = y0 - m * x0
            x = sqrt(dist * dist / (1 + m * m))
            y = m * x
        else:
            m = dx / dy
            # b = x0 - m * y0
            y = sqrt(dist * dist / (1 + m * m))
            x = m * y
        pa = (x0 + x, y0 + y)
        pb = (x0 - x, y0 - y)
        if xyDist(pa, p1) > xyDist(pb, p1):
            p = pa
        else:
            p = pb
        if start:
            l = Line(p, p0)
        else:
            l = Line(p0, p)
        return(l)

    # a0*x + b0*y + c0 = 0
    # a1*x + b1*y + c1 = 0
    # d0 = sqrt(a0*a0 + b0*b0)
    # d1 = (+ or -) sqrt(a1*a1 + b1*b1)
    # (a0*x + b0*y + c0) / d0  = (a1*x + b1*y + c1) / d1
    # (a0*x + b0*y + c0) * d1  = (a1*x + b1*y + c1) * d0
    # d1*a0*x + d1*b0*y + d1*c0 = d0*a1*x + d0*b1*y + d0*c1
    # (d1*a0*x - d1*b0*x) = d0*a1*y - d0*b1*y + d0*c1 - d1*c0
    # (d1*a0 - d0*a1)*x = (d0*b1 - d0*b1)*y + (d0*c1 - d1*c0)
    # (d1*a0 - d0*a1)*x - (d0*b1 - d0*b1)*y - (d0*c1 - d1*c0) = 0
    # x = (((d0*b1 - d0*b1)*y = d0*c1 - d1*c0)) / (d1*a0 - d0*a1)
    #
    # coefficients for bisector equation
    #
    # ab = d1*a0 - d*a1
    # bb = -(d0*b1 - d0*b1)
    # cb = d1*c0 - d0*c1
    # ab*x + bb*y + cb = 0
    # if bb > ab
    # y = -(ab/bb)*x - cb/bb
    # m = -(ab/bb)
    # by = -(cb/bb)
    # if ab > bb
    # x = -(bb/ab)*y - cb/ab
    # m = -(bb/ab)
    # bx = -cb/ab

    # distance between line and point
    # a, b, and c are for original line x and y is the point location
    # d = abs(a*x + b*y + c) / sqrt(a^2 + b^2)
    # d*sqrt(a^2 + b^2) = abs(a*x + b*y + c)
    # d*sqrt(a^2 + b^2) - c = a*x + b*y
    # t0 =  d*sqrt(a^2 + b^2) - c
    # t1 =  -d*sqrt(a^2 + b^2) - c
    # a*x + b*x = t
    #
    # equation of bisector
    # y = m*x + by or x = m*y + bx
    #
    # a*x + b(m*x + by) = t
    # a*x + b*m*x + b*by = t
    # x*(a + b*m) = t - b*by
    # x = (t - b*by) / (a + b*m)
    # x=(t-c-(b*b0))/(a+b*m)
    
    # x = m*y + b
    # x^2 + y^2 = r^2
    # (m*y)^2 + 2*m*y*b + b^2 + y^2 = r^2
    # (1 + m^2)*y^2 + 2*m*b*y + b^2 - r^2 = 0
    # aq = 1 + m^2
    # bq = 2*b*m
    # cq = b^2 - r^2
    # -b +- sqrt(bq^2 - 4*aq*cq) / 2*a

    def bisect(self, l, dist):
        (x0, y0) = self.p0
        (x1, y1) = self.p1
        if l.type == LINE:
            (x2, y2) = l.p1
            d = abs(dist)
            dprt("d %7.4f (%7.4f %7.4f) (%7.4f %7.4f) (%7.4f %7.4f)" %
                  (d, x0, y0, x1, y1, x2, y2))
            a0 = y0 - y1
            b0 = x1 - x0
            c0 = x0*y1 - x1*y0
            dprt("a0 %7.4f b0 %7.4f c0 %7.4f" % (a0, b0, c0))

            a1 = y1 - y2
            b1 = x2 - x1
            c1 = x1*y2 - x2*y1
            dprt("a1 %7.4f b1 %7.4f c1 %7.4f" % (a1, b1, c1))

            d0 = sqrt(a0*a0 + b0*b0)
            d1 = sqrt(a1*a1 + b1*b1)

            ab = d1*a0 - d0*a1
            bb = -(d0*b1 - d1*b0)
            cb = d1*c0 - d0*c1
            dprt("ab %7.4f bb %7.4f cb %7.4f" % (ab, bb, cb))
            dprt("%7.4f" % (ab * x0 + bb * y0 + cb))
        else:
            (x2, y2) = l.c
            ab = y1 - y2
            bb = x2 - y1
            cb = x1*y2 - x2*y1
            pass
        yIntercept = abs(bb) > abs(ab)
        if yIntercept:          # y = m*x + by
            m = -(ab/bb)
            by = -(cb/bb)

            t = d*sqrt(a0*a0 + b0*b0) - c0
            xp = (t - b0*by) / (a0 + b0*m)
            yp = m * xp + by
            dprt("a %7.4f b %7.4f t %7.4f" % (a0, b0, t))
            dprt("m %7.4f by %7.4f" % (m, by))

            t = -d*sqrt(a0*a0 + b0*b0) - c0
            xm = (t - b0*by) / (a0 + b0*m)
            ym = m * xp + by
            dprt("a %7.4f b %7.4f t %7.4f" % (a0, b0, t))
            dprt("m %7.4f by %7.4f" % (m, by))
        else:                   # x = m*y + bx
            m = -(bb/ab)
            bx = -(cb/ab)
        
            t = d*sqrt(a0*a0 + b0*b0) - c0
            yp = (t - b0*bx) / (a0 + b0*m)
            xp = m * yp + bx
            dprt("a %7.4f b %7.4f t %7.4f" % (a0, b0, t))
            dprt("m %7.4f bx %7.4f" % (m, bx))

            t = -d*sqrt(a0*a0 + b0*b0) - c0
            ym = (t - b0*bx) / (a0 + b0*m)
            xm = m * yp + bx
            dprt("a %7.4f b %7.4f t %7.4f" % (a0, b0, t))
            dprt("m %7.4f bx %7.4f" % (m, bx))

        minus = False
        dir0 = orientation(self.p0, self.p1, (xp, yp))
        if dist > 0:        # if clockwise
            minus = dir0 != CCW
        else:               # if counter clockwise
            minus = dir0 != CW

        dprt("o0 %s %s (%7.4f %7.4f) b1 (%7.4f %7.4f)" % \
              (oStr(dir0), minus, xp, yp, xm, ym))
        if not minus:
            d = abs(a0*xp + b0*yp + c0) / sqrt(a0*a0 + b0*b0)
            dprt("d %7.4f" % (d))
            return(xp, yp)
        else:
            d = abs(a0*xm + b0*ym + c0) / sqrt(a0*a0 + b0*b0)
            dprt("d %7.4f" % (d))
            return(xm, ym)

    def horizontalTrim(self, yVal, yPlus):
        (x0, y0) = self.p0
        (x1, y1) = self.p1
        if yPlus:
            if (yVal <= y0) and (yVal <= y1):
                return(None)
            if (yVal >= y0) and (yVal >= y1):
                return(self)
        else:
            if (yVal >= y0) and (yVal >= y1):
                return(None)
            if (yVal <= y0) and (yVal <= y1):
                return(self)
        dx = x1 - x0
        dy = y1 - y0
        if abs(dy) < MIN_DIST:  # horizontal
            if yPlus:
                if y0 >= yPlus:
                    return(None)
                else:
                    return(self)
            else:
                if y0 <= yPlus:
                    return(None)
                else:
                    return(self)
        elif abs(dx) < MIN_DIST: # vertical
            p = (x0, yVal)
        else:
            m = dx / dy
            b = x0 - m * y0
            x = m * yVal + b
            p = (x, yVal)

        if yPlus:
            if y0 > yVal:
                self.p0 = p
            else:
                self.p1 = p
        else:
            if y0 < yVal:
                self.p0 = p
            else:
                self.p1 = p
        return(self)

    def verticalTrim(self, xVal, xPlus):
        (x0, y0) = self.p0
        (x1, y1) = self.p1
        if xPlus:
            if (xVal <= x0) and (xVal <= x1):
                return(None)
            if (xVal >= x0) and (xVal >= x1):
                return(self)
        else:
            if (xVal >= x0) and (xVal >= x1):
                return(None)
            if (xVal <= x0) and (xVal <= x1):
                return(self)
        dx = x1 - x0
        dy = y1 - y0
        if (xVal > x0) and (xVal > x1):
            return(self)
        if abs(dx) < MIN_DIST:  # vertical
            if xPlus:
                if x0 >= xPlus:
                    return(None)
                else:
                    return(self)
            else:
                if x0 <= xPlus:
                    return(None)
                else:
                    return(self)
        elif abs(dy) < MIN_DIST: # horizontal
            p = (y0, xVal)
        else:
            m = dy / dx
            b = y0 - m * x0
            y = m * xVal + b
            p = (y, xVal)

        if xPlus:
            if x0 > xVal:
                self.p0 = p
            else:
                self.p1 = p
        else:
            if x0 < xVal:
                self.p0 = p
            else:
                self.p1 = p
        return(self)

    def mill(self, mill, zEnd=None, comment=None):
        mill.cut(self.p1, zEnd, comment)

    def draw(self):
        if draw is None:
            return
        draw.move(self.p0)
        draw.line(self.p1)

    def label(self, text, layer=None):
        self.text = text
        if draw is None:
            return
        if self.length > 0.5:
            h = 0.010
            x = (self.p1[0] + self.p0[0]) / 2.0
            y = ((self.p0[1] + self.p1[1]) / 2.0) - h
            draw.text(text, (x, y), h, layer)

    def prt(self, out=None, eol="\n", prefix=None):
        str = prefix if prefix is not None else ""
        str += "%2d s%6.3f %6.3f e%6.3f %6.3f l %5.3f line %5.3f" % \
               (self.index, self.p0[0], self.p0[1], \
                self.p1[0], self.p1[1], self.length, \
                xyDist(self.p0, self.p1))
        if self.text != None:
            str += " " + self.text
        if out is None:
            dprt(str)
        else:
            out.write(str)
            out.write(eol)

# dxf arcs are always counter clockwise.

class Arc():
    def __init__(self, c, r, a0, a1, i=-1, e=None, dir=CCW):
        self.c = c
        (cX, cY) = c
        a0R = radians(a0)
        a1R = radians(a1)
        self.p0 = (cX + r * cos(a0R), \
                   cY + r * sin(a0R))
        self.p1 = (cX + r * cos(a1R), \
                   cY + r * sin(a1R))
        if dir == CW:
            (self.p0, self.p1) = (self.p1, self.p0)
            self.swapped = True
        else:
            self.swapped = False
        self.type = ARC
        self.str = 'arc'
        self.index = i
        self.r = r
        self.a0 = a0
        if a1 == 0.0:
            a1 = 360.0
        self.a1 = a1
        self.e = e
        self.arcLen = 0.0
        self.length = self.calcLen()

    def aStr(self):
        if not self.swapped:
            return(self.a0)
        else:
            return(self.a1)

    def aEnd(self):
        if not self.swapped:
            return(self.a1)
        else:
            return(self.a0)

    def updateP0(self, p):
        a = degAtan2(p[1] - self.c[1], p[0] - self.c[0])
        if not self.swapped:
            self.a0 = a
        else:
            self.a1 = a
        self.p0 = p     # set end of this object
        self.length = self.calcLen()

    def updateP1(self, p):
        a = degAtan2(p[1] - self.c[1], p[0] - self.c[0])
        if not self.swapped:
            self.a1 = a
        else:
            self.a0 = a
        self.p1 = p     # set end of this object
        self.length = self.calcLen()

    def calcLen(self):
        a1 = self.a1
        a0 = self.a0
        if abs(abs(a1 - a0) - 360.0) > MIN_DIST:
            if a1 < a0:
                a1 += 360.0
            self.arcLen = a1 - a0
            return(self.r * radians(self.arcLen))
        else:
            return(pi * 2.0 * self.r)

    def swap(self):
        (self.p0, self.p1) = (self.p1, self.p0)
        self.swapped = not self.swapped
        return(self)

    def fixDist(self, dist):
        d = abs(dist)
        minus = False
        if not self.swapped:    # if clockwise (swapped is ccw)
            minus = dist > 0.0  # dist > 0 is clockwise
            # if dist > 0.0:    # if clockwise
            #     minus = True
        else:
            minus = dist < 0.0  # dist < 0 is counter clockwise
            # if dist < 0.0:    # if counter clockwise
            #     minus = True
        if minus:
            d = -d
        return(d)

    def parallel(self, dist):
        d = self.fixDist(dist)
        r = self.r
        r += d
        if r < 0.0:
            l1 = None
        else:
            l1 = Arc(self.c, r, self.a0, self.a1, self.index)
            if self.swapped:
                l1.swap()
        return(l1)

    def midPoint(self, dist=0.0, dbg=False):
        a = radians((self.a1 + self.a0) / 2)
        if dist == 0.0:
            return(self.c[0] + self.r * cos(a), self.c[1] + self.r * sin(a))
        else:
            d = self.fixDist(dist)
            if dbg:
                pM = (self.c[0] + self.r * cos(a), \
                      self.c[1] + self.r * sin(a))
                p = (self.c[0] + (self.r + d) * cos(a), \
                     self.c[1] + (self.r + d) * sin(a))
                d0 = orientation(self.p0, pM, self.p1)
                d1 = orientation(self.p0, pM, p)
                dprt("%2d arc dir %s midPoint dir %s swapped %s" % \
                      (self.index, oStr(d0), oStr(d1), self.swapped))
                if draw is not None:
                    l = draw.lDebug
                    draw.drawCircle(self.p0, layer=l)
                    draw.drawCircle(pM, 0.020, layer=l)
                    draw.drawCircle(self.p1, 0.015, layer=l)
                    draw.drawCircle(p, 0.030, layer=l, \
                                    txt=('+', '-')[dist < 0.0])
            return(self.c[0] + (self.r + d) * cos(a), \
                   self.c[1] + (self.r + d) * sin(a))

    def linePoint(self, dist):
        r = self.r
        arcLen = dist / r
        a = radians(self.a0 + arcLen)
        x = r * cos(a) + self.c[0]
        y = r * sin(a) + self.c[1]
        return((x, y))

    def split(self, dist):
        r = self.r
        arcLen = dist / r
        # dprt("dist %7.4f r %7.4f arclen %7.4f" % (dist, r, arcLen))
        if self.swapped:
            a = degrees(radians(self.a1) - arcLen)
        else:
            a = degrees(radians(self.a0) + arcLen)
        # dprt("swapped %s a %7.3f" % (self.swapped, a))
        a0 = Arc(self.c, self.r, self.a0, a, self.index)
        a1 = Arc(self.c, self.r, a, self.a1, self.index)
        if self.swapped:
            (a0, a1) = (a1.swap(), a0.swap())
        return((a0, a1))

    def intersect(self, l):
        p = None
        if l.type == LINE:
            p = lineArc(l, self, 0)
        elif l.type == ARC:
            c0 = self.c
            c1 = l.c
            if self.r != l.r or c0[0] != c1[0] or c0[1] != c1[1]:
                p = arcArc(self, l)
        if p is not None:
            self.updateP1(p)    # update end of this one
            l.updateP0(p)       # and start of next one
        # if p is None:
        #     dprt("a no intersection s %7.4f, %7.4f e %7.4f %7.4f" % \
        #           (self.p1[0], self.p1[1], l.p0[0], l.p1[1]))
        return(p)

    def horizontalTrim(self, yVal, yPlus):
        if yPlus:
            if self.p0[1] >= yVal and self.p1[1] >= yVal:
                return(None)
        else:
            if self.p0[1] <= yVal and self.p1[1] <= yVal:
                return(None)
        (cX, cY) = self.c
        r = self.r
        y = yVal - cY
        if abs(y) > r:
            return(self)
        aRad = asin(y / r)
        xMid = (self.p0[0] + self.p1[0]) / 2 - cX
        if xMid < 0:
            aRad = pi - aRad
        a = degrees(aRad)
        if a < 0.0:
            a += 360.0
        dprt("yVal %7.4f yPlus %s y %7.4f r %7.4f a %5.1f" % \
             (yVal, yPlus, y, r, a))
        a1 = self.a1
        if a1 < self.a0:
            a1 += 360.0
        if self.a0 < a and a <= a1:
            x = r * cos(aRad)
            p = (x + cX, y + cY)
            if yPlus:
                p0 = self.p0[1] > self.p1[1]
            else:
                p0 = self.p0[1] < self.p1[1]

            if p0:
                self.p0 = p
                a0 = not self.swapped
            else:
                self.p1 = p
                a0 = self.swapped

            if a0:
                self.a0 = a
            else:
                self.a1 = a
            self.length = self.calcLen()
        return(self)
        
    def verticalTrim(self, xVal, xPlus):
        if xPlus:
            if self.p0[0] >= xVal and self.p1[0] >= xVal:
                return(None)
        else:
            if self.p0[0] <= xVal and self.p1[0] <= xVal:
                return(None)
        (cX, cY) = self.c
        r = self.r
        x = xVal - cX
        if abs(x) > r:
            return(self)
        aRad = acos(x / r)
        yMid = (self.p0[1] + self.p1[1]) / 2 - cY
        if yMid < 0:
            aRad = -aRad
        a = degrees(aRad)
        if a < 0.0:
            a += 360.0
        dprt("xVal %7.4f xPlus %s x %7.4f r %7.4f a %5.1f" % \
             (xVal, xPlus, x, r, a))
        a1 = self.a1
        if a1 < self.a0:
            a1 += 360.0
        if self.a0 < a and a <= a1:
            y = r * sin(aRad)
            p = (x + cX, y + cY)
            if xPlus:
                p0 = self.p0[0] > self.p1[0]
            else:
                p0 = self.p0[0] < self.p1[0]

            if p0:
                self.p0 = p
                a0 = not self.swapped
            else:
                self.p1 = p
                a0 = self.swapped

            if a0:
                self.a0 = a
            else:
                self.a1 = a
        return(self)

    def point90(self, p, dist):
        (i, j) = self.c
        a = atan2(p[1] - j, p[0] - i)
        d = self.fixDist(dist)
        d += self.r
        return((i + d * cos(a), j + d * sin(a)))

    def pointDistance(self, p):
        a = degAtan2(p[1] - self.c[1], p[0] - self.c[0])
        a0 = self.a0
        a1 = self.a1
        if a1 < a0:
            if a < a1:
                a += 360.0
            a1 += 360.0
        if a0 <= a and a <= a1:
            d = xyDist(p, self.c)
            # dprt("pDist %2d d %7.4f r %7.4f %7.4f " \
            #       "a0 %7.4f a %7.4f a1 %7.4f" % \
            #       (self.index, d, self.r, d - self.r, self.a0, a, self.a1))
            d -= self.r
            return(d)
        return(None)

    def startDist(self, p):
        a = degAtan2(p[1] - self.c[1], p[0] - self.c[0])
        if self.swapped:
            t = self.a1 - a
            if t < 0.0:
                t += 360.0
            dist = self.r * radians(t)
        else:
            if a < self.a0:
                a += 360.0
            t = a - self.a0
            dist = self.r * radians(t)
        # dprt("startDist %d %7.4f t %5.1f a0 %5.1f a %5.1f a1 %5.1f " \
        #       "swapped %s" % \
        #       (self.index, dist, t, self.a0, a, self.a1, self.swapped))
        return(dist)

    def extend(self, dist, start=True):
        (i, j) = self.c
        if start:
            p0 = self.p0
        else:
            p0 = self.p1
        (x0, y0) = p0
        dx = x0 - i
        dy = y0 - j
        if abs(dx) > abs(dy):
            m = -dy / dx
            ya = sqrt(dist * dist / (1 + m * m))
            xa = m * ya
        else:
            m = -dx / dy
            xa = sqrt(dist * dist / (1 + m * m))
            ya = m * xa
        pa = (x0 + xa, y0 + ya)
        pb = (x0 - xa, y0 - ya)
        # a = degAtan2(pa[1] - j, pa[0] - i)
        # b = degAtan2(pb[1] - j, pb[0] - i)
        labelP(pa, 'pa')
        labelP(pb, 'pb')
        # dprt("extend\n")
        # dprt("xx a %5.1f b %5.1f a0 %5.1f a1 %5.1f swapped %s start %s" % \
        #       (a, b, self.a0, self.a1, self.swapped, start))
        oArc = (CCW, CW)[self.swapped]
        if start:
            oa = orientation(pa, p0, self.c)
            # ob = orientation(pb, p0, self.c)
            # dprt("xx str oArc %s oa %s ob %s" % \
            #       (oStr(oArc), oStr(oa), oStr(ob)))
            if oa == oArc:
                dprt("xx pa")
                p = pa
            else:
                dprt("xx pb")
                p = pb
            l = Line(p, p0)
        else:
            oa = orientation(self.c, p0, pa)
            # ob = orientation(self.c, p0, pb)
            # dprt("xx end oArc %s oa %s ob %s" % \
            #       (oStr(oArc), oStr(oa), oStr(ob)))
            if oa == oArc:
                dprt("xx pa")
                p = pa
            else:
                dprt("xx pb")
                p = pb
            l = Line(p0, p)
        return(l)
    
    def mill(self, mill, zEnd=None, comment=None):
        mill.setArcCW(self.swapped)
        mill.arc(self.p1, self.c, zEnd, comment)
        # dprt("%2d radius %7.4f r %7.4f" % \
        #       (self.index, xyDist(self.p1, self.c), self.r))

    def draw(self):
        if draw is None:
            return
        if not self.swapped:
            draw.move(self.p0)
            draw.arc(self.p1, self.c)
        else:
            draw.move(self.p1)
            draw.arc(self.p0, self.c)

    def prt(self, out=None, eol="\n", prefix=None):
        str = prefix if prefix is not None else ""
        str += "%2d s%6.3f %6.3f e%6.3f %6.3f l %5.3f arc%s" \
               " c%6.3f%6.3f r %5.3f %4.0f %4.0f" % \
               (self.index, self.p0[0], self.p0[1], \
                self.p1[0], self.p1[1], self.length, \
                (' ', 's')[self.swapped], self.c[0], self.c[1], \
                self.r, self.a0, self.a1)
        if out is None:
            dprt(str)
        else:
            out.write(str)
            out.write(eol)

def lineLine(l0, l1):
    # dprt("intersect line line")
    # l0.prt()
    # l1.prt()
    (x0, y0) = l0.p0
    (x1, y1) = l0.p1
    (x2, y2) = l1.p0
    (x3, y3) = l1.p1
    x = None
    y = None
    if abs(x2 - x3) < MIN_DIST: # l1 vertical
        x = x2
    elif abs(y2 - y3) < MIN_DIST: # l1 horizontal
        y = y2
    else:                          # l1 oblique
        m1 = (y3 - y2) / (x3 - x2) # slope of line of l1
        b1 = y2 - m1 * x2          # intercept of l1

    if abs(x0 - x1) < MIN_DIST: # l0 vertical
        if x is not None:           # l1 vertical
            y = y2
        else:
            x = x0
            if y is not None:       # l1 horizontal
                pass
            else:               # l1 oblique
                y = m1 * x + b1
    elif abs(y0 - y1) < MIN_DIST: # l0 horizontal
        if y is not None:             # l1 horizontal
            x = x2
        else:
            y = y0
            if x is not None:       # l1 vertical
                pass
            else:               # l1 oblique
                x = (y - b1) / m1
    else:                         # l0 oblique
        m = (y1 - y0) / (x1 - x0) # slope of line l0
        b = y0 - m * x0           # intercept of l0
        if x is not None:             # l1 vertical
            y = m * x + b
        elif y is not None:         # l1 horizontalal
            x = (y - b) / m
        else:                   # l1 oblique
            if abs(m - m1) < MIN_DIST: # 
                x = x1
                y = y1
            else:
                x = (b1 - b) / (m - m1)
                y = m * x + b
    # dprt("x %7.4f y %7.4f" % (x, y))
    # dprt()
    return((x, y))              # return intersection

def lineCircle(l, c, r):
    # global lineIndex
    # dprt("lineCircle")
    # l.prt()
    (x0, y0) = translate(l.p0, c) # translate to origin
    (x1, y1) = translate(l.p1, c)
    dx = (x1 - x0)
    dy = (y1 - y0)
    # dprt("c %7.4f, %7.4f p0 %7.4f, %7.4f p1 %7.4f %7.4f " \
    #       "dx %7.4f dy %7.4f" % \
    #       (c[0], c[1], x0, y0, x1, y1, dx, dy))
    if abs(dx) < MIN_DIST:      # vertical
        x = x0
        y = 0
    elif abs(dy) < MIN_DIST:   # horizontal
        x = 0
        y = y0
    else:                       # oblique
        m = dy / dx
        b = y0 - m * x0
        m90 = -1 / m
        xa = sqrt(r * r / (m90 * m90 + 1))
        ya = m90 * xa
        xb = -xa
        yb = -ya
        da = abs(m * xa + b - ya)
        db = abs(m * xb + b - yb)
        if da < db:
            x = xa
            y = ya
        else:
            x = xb
            y = yb
        # dprt("m %7.4f b %7.4f m90 %7.4f" % (m, b, m90))
        # dprt("da %7.4f db %7.4f" % (da, db))
    # if draw is not None:
    #     drawLineCircle(m, b, r, lineIndex)
    # lineIndex += 1
    return((x + c[0], y + c[1]))

# oblique line arc intersection
#
# y = m*x + b
# r^2 = (x - i)^2 + (y - j)^2
#
# r^2 = (x^2 - 2*x*i + i^2) + (y^2 - 2*j*y + j^2)
# r^2 = (x^2 - 2*x*i + i^2) + ((m*x + b)^2 - 2*j*(m*x + b)) + j^2
# r^2 = (x^2 - 2*x*i + i^2) + (m*x^2 + 2*m*x*b + b^2) - (2*m*j*x + 2*j*b) + j^2
# 0 = x^2 - 2*x*i + i^2 + m^2*x^2 + 2*m*x*b + b^2 - 2*m*j*x - 2*j*b + j^2 - r^2
# 0 = x^2 + m^2*x^2 - 2*i*x + 2*m*b*x - 2*j*m*x + i^2 + b^2 - 2*j*b + j^2 - r^2
# quadratic form
# 0 = (m^2 + 1)*x^2 + (2*m*b - 2*j*m - 2*i)*x + (i^2 + b^2 - 2*j*b + j^2 - r^2)
# quadratic terms
# qa = m^2 + 1

# qb = 2*(m*b - m*j - i)
# qb = 2*(m*(b - j) - i)

# qc = i^2 + (b^2 - 2*j*b + j^2) - r^2
# qc = i^2 + (b - j)^2 - r^2

# t0 = b - j
# qb = 2*(m*t0 - i)
# qc = i^2 + t0^2 - r^2

def lineArc(l0, l1, end):
    # dprt("intersect line arc %d" % (end))
    # if end == 0:
    #     l1.prt()
    #     l0.prt()
    # else:
    #     l1.prt()
    #     l0.prt()
    # dflush()
    (x0, y0) = l0.p0
    (x1, y1) = l0.p1
    (i, j) = l1.c
    r = l1.r
    p = None
    if abs(x0 - x1) < MIN_DIST: # vertical
        x = x0
        t0 = x - i
        if abs(abs(t0) - r) > MIN_DIST:
            t0 = sqrt(r * r - t0 * t0)
        else:
            t0 = 0
        pa = (x, j + t0)
        pb = (x, j - t0)
    elif abs(y0 - y1) < MIN_DIST: # horizontal
        y = y0
        t0 = y - j
        if abs(t0) < r:
            if abs(abs(t0) - r) > MIN_DIST:
                t0 = sqrt(r * r - t0 * t0)
            else:
                t0 = 0
        else:
            t0 = 0
        pa = (i + t0, y)
        pb = (i - t0, y)
    else:               # oblique
        m = (y1 - y0) / (x1 - x0) # slope of line
        b = y0 - m * x0           # intercept
        t0 = b - j                # temp value
        qa = 1.0 + m * m          # quadratic a term
        qb = 2 * (m * t0 - i)     # quadratic b term
        qc = i * i + t0 * t0 - r * r # quadratic c term
        t0 = qb * qb - 4 * qa * qc
        if abs(t0) < MIN_DIST:  # tangent
            x = -qb / (2 * qa)
            pa = pb = p = (x, m * x + b)
        elif t0 > 0:            # two intersections
            t0 = sqrt(t0)
            xa = (-qb + t0) / (2 * qa) # plus solution
            pa = (xa, m * xa + b)

            xb = (-qb - t0) / (2 * qa) # minus solution
            pb = (xb, m * xb + b)
        else:
            d0 = xyDist(l0.p1, l1.p0)
            d1 = xyDist(l1.p1, l0.p0)
            dprt("no intersection d0 %7.4f d1 %7.4f" % (d0, d1))
            dflush()
            if d0 < d1:
                pass
            #     l0.pl = l1.p0
            #     p = l1.p0
            else:
                pass
            #     l0.p0 = l1.p1
            #     p = l1.p1
            return(p)
    if end == 1:
        da = xyDist(l0.p1, pa)
        db = xyDist(l0.p1, pb)
    else:
        da = xyDist(l0.p0, pa)
        db = xyDist(l0.p0, pb)
    # dprt("da %7.4f db %7.4f " % (da, db))
    if da < db:
        p = pa
    else:
        p = pb
    return(p)

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
    # OR
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

def arcArc(l0, l1):
    if (xyDist(l0.c, l1.c) < MIN_DIST) and \
       (abs(l0.r - l1.r) < MIN_DIST): # if already intersecting
        return(l0.p1)
    (x0, y0) = l0.c             # arc 0
    r0 = l0.r
    (x1, y1) = l1.c             # arc 1
    r1 = l1.r
    dx = x1 - x0                # x distance
    dy = y1 - y0                # y distance

    d = sqrt(dx * dx + dy * dy) # center distance
    d0 = (d*d + r0*r0 - r1*r1) / (2 * d) # distance along center line
    p = None
    if abs(abs(d0) - abs(r0)) < MIN_DIST: # if intersection
        # h = sqrt(r0 * r0 - d0 * d0)  # distance above center line
        h = 0
        dprt("d %6.3f d0 %6.3f h %6.3f" % (d, d0, h))

        cosA = dx / d
        sinA = dy / d

        pa = (x0 + d0 * cosA + h * sinA, \
              y0 + d0 * sinA - h * cosA)

        pb = (x0 + d0 * cosA - h * sinA, \
              y0 + d0 * sinA + h * cosA)

        da = xyDist(l0.p1, pa)
        db = xyDist(l0.p1, pb)
        if da <= db:
            p = pa
        else:
            p = pb
    return(p)

def lineLineArc(seg, l0, l1, dist, dir):
    lDir = orientation(l0.p0, l1.p0, l1.p1)
    if lDir == 0:
        return None
    flag = lDir != dir
    dprt("lineLineArc %2d %s %s %s" % (lCount, oStr(dir), oStr(lDir), flag))
    l0.prt()
    l1.prt()
    # common point is l0.p1 and l1.p0
    dbg = False
    if False:
        p = None
        c = 0
        for d0 in (dist, -dist):
            pl0 = l0.parallel(d0)
            for d1 in (dist, -dist):
                pl1 = l1.parallel(d1)
                p = lineLine(pl0, pl1)
                if p[0] is None or p[1] is None:
                    dprt("error***")
                    p = lineLine(pl0, pl1)
                if dbg and draw is not None:
                    (x, y) = p
                    draw.text('%d' % (c), (x - 0.010, y - 0.005), 0.010)
                if ((inside(p, seg, dbg) & 1) == 0) == flag:
                    break
                c += 1
            else:                   # loop ended without break
                continue
            break                   # inner loop break, done, break outer loop
    else:       
        d = dist
        if dir == CW:
            d = -d
        pl0 = l0.parallel(d)
        pl1 = l1.parallel(d)
        p = lineLine(pl0, pl1)
    if p is None:
        ePrint("+++ no intersection")
        return(None)
    # dprt("%3s p %7.4f, %7.4f d0 %6.3f d1 %6.3f" % \
    #       (oStr(lDir), p[0], p[1], d0, d1))
    # dflush()
    # if draw is not None:
    #     draw.circle(p, dist)
    p0 = lineCircle(l0, p, dist)
    p1 = lineCircle(l1, p, dist)
    (x0, y0) = translate(p0, p)
    (x1, y1) = translate(p1, p)
    a0 = degAtan2(y0, x0)
    a1 = degAtan2(y1, x1)
    if lDir == CCW:
        arc = Arc(p, dist, a0, a1)
    else:
        arc = Arc(p, dist, a1, a0)
        arc.swap()
        arc.prt()
        arc.draw()
    # if draw is not None:
    #     draw.drawCross(p)
    #     draw.drawCross(p0)
    #     draw.drawCross(p1)
    return(arc)

# x^2 + y^2 = r^2
# (x - d)^2 + y^2 = r1^2
# (x - d)^2 + (r^2 - x^2) = r1^2
# x^2 - 2*d*x + d^2 - x^2 = r1^2 - r^2
# -2*d*x + d^2 = r1^2 - r^2
# x = (r1*2 - r^2 - d^2) / -2*d
# x = (r^2 + d^2 - r1^2) / 2*d

def tangent(p, arc, dir):
    (pX, pY) = p
    (cX, cY) = arc.c
    r = arc.r
    dprt("p (%7.4f, %7.4f) c (%7.4f %7.4f) r %7.4f" % \
           (pX, pY, cX, cY, r))
    dx = pX - cX                # relative to center
    dy = pY - cY
    dprt("dx %7.4f dy %7.4f" % (dx, dy))
    d = hypot(dx, dy)           # distance between centers
    r1 = sqrt(dx*dx + dy*dy - r*r) # distance to tangent point
    dprt("d %7.4f r1 %7.4f" % (d, r1))
    a0 = atan2(dy, dx)          # rotation angle
    if abs(dx) >= abs(dy):      # if dx > dy
        x = (r*r + d*d - r1*r1) / (2.0 * d) # x value
        y = sqrt(r*r - x*x)     # y value
        a = atan2(y, x)
    else:                       # if dy > dx
        y = (r*r + d*d - r1*r1) / (2.0 * d) # x value
        x = sqrt(r*r - y*y)     # y value
        a = atan2(x, y)
    dprt("a0 %5.1f a %5.1f x %7.4f y %7.4f" % (degrees(a0), degrees(a), x, y))
    aP = a + a0                 # angle of plus point
    aM = -a + a0                # angle of minus point
    xP = r * cos(aP) + cX       # plus point
    yP = r * sin(aP) + cY
    xM = r * cos(aM) + cX       # minus point
    yM = r * sin(aM) + cY
    oP = orientation(p, (xP, yP), arc.c)
    oM = orientation(p, (xM, yM), arc.c)
    dprt("tP (%7.4f, %7.4f) oP %s tM (%7.4f, %7.4f) oM %s" % \
         (xP, yP, oStr(oP), xM, yM, oStr(oM)))
    return((xP, yP) if oP == dir else (xM, yM))

def inside(p, seg, dbg=False):
    (x, y) = p
    cross = 0
    for l in seg:
        if dbg:
            l.prt()
        (x0, y0) = l.p0
        (x1, y1) = l.p1
        cType = 0
        test = False
        type = l.type
        if type == LINE:
            if x0 == x1:        # if line vertical
                pass
            elif x0 < x1:       # if start x < end x
                if x0 < x and x <= x1: # if point lies between ends
                    test = True         # test y
            elif x1 <= x and x < x0: # if point lies between ends
                test = True           # test y
            if test:                  # if y test needed
                if y < y0 and y < y1: # if point below both ends
                    cType = 1
                    cross += 1        # line crosses
                elif y > y0 and y > y1: # if point above both ends
                    pass                # line does not cross
                else:                   # solve for intersection
                    m = (y1 - y0) / (x1 - x0) # calculate line slope
                    b = y0 - m * x0   # calculate intercept
                    yTest = m * x + b # calculate intersection
                    if y < yTest:     # if point below intersection
                        cType = 2
                        cross += 1   # line intersects
        elif type == ARC:
            (cX, cY) = l.c
            r = l.r
            d = x - cX               # distance from x to center x
            if abs(d) < r:           # if point within circle
                yTest = sqrt(r * r - d * d) # find y value
                for yCheck in (yTest, -yTest):
                    angle = degAtan2(yCheck, d)
                    yCheck += cY
                    if dbg:
                        dprt("a0 %5.1f angle %5.1f a1 %5.1f " \
                              "yCheck %6.3f %s" % \
                              (l.a0, angle, l.a1, yCheck, \
                               ('cw', 'ccw')[l.swapped]))
                    if l.a0 < angle and angle <= l.a1: # if on arc
                        if y < yCheck: # if point below intersection
                            cType = 3
                            cross += 1 # then it intersect
        if dbg:
            if cType != 0:
                dprt("cType %d cross %d" % (cType, cross))
    if dbg and draw is not None:
        dprt()
        draw.drawX(p, "i%d" % (cross))
    return(cross)

def rotateMinDist(p, seg):
    minDist = 1000
    index = 0
    for (i, l) in enumerate(seg):
        # l.prt()
        d = xyDist(p, l.p0)
        if d < minDist:
            minDist = d
            index = i
    # dprt()
    # dprt("index %2d minDist %7.4f" % (index, minDist))
    seg = seg[index:] + seg[:index]
    return(seg)

def pathLength(seg):
    totalLength = 0.0
    for l in seg:
        # l.prt()
        # if l.type == LINE:
        #     dprt("length %7.4f" % (l.length))
        # else:
        #     dprt("length %7.4f arcLen %5.1f " % (l.length, l.arcLen))
        totalLength += l.length
    #     dprt("%2d len %7.4f total %7.4f" % (l.index, l.length, totalLength))
    # dprt("totalLength %7.4f" % (totalLength))
    # dprt()
    return(totalLength)

def reverseSeg(seg, makeCopy=True):
    newSeg = []
    for l in reversed(seg):
        if makeCopy:
            l = copy(l)
        l.swap()
        newSeg.append(l)
    return(newSeg)

def splitArcs(seg):
    dprt("splitArcs in")
    newSeg = []
    i = 0
    for l in seg:
        # l.prt()
        if l.type == ARC:
            l.prt()
            a0 = degrees(calcAngle(l.c, l.p0))
            a1 = degrees(calcAngle(l.c, l.p1))
            if not l.swapped:   # clockwise
                if a1 < a0:
                    a1 += 360.0
                # dprt("a0 %5.1f a1 %5.1f total %5.1f cw" % \
                #       (fix(a0), fix(a1), a1 - a0))
                prev = a = a0
                while True:
                    if a % 90 > .001:
                        a = ceil(a / 90) * 90
                    else:
                        a += 90
                    if a >= a1:
                        break
                    # dprt("(%5.1f, %5.1f)" % (fix(prev), fix(a)), end=" ")
                    l1 = Arc(l.c, l.r, fix(prev), fix(a), l.index)
                    newSeg.append(l1)
                    i += 1
                    prev = a
                # dprt("(%5.1f, %5.1f)" % (fix(prev), fix(a1)))
                l1 = Arc(l.c, l.r, fix(prev), fix(a1), l.index)
            else:               # counter clockwise
                if a0 < a1:
                    a0 += 360.0
                # dprt("a0 %5.1f a1 %5.1f total %5.1f ccw" % \
                #       (fix(a0), fix(a1), a0 - a1))
                prev = a = a0
                while True:
                    if a % 90 > .001:
                        a = floor(a / 90) * 90
                    else:
                        a -= 90
                    if a <= a1:
                        break
                    # dprt("(%5.1f, %5.1f)" % (fix(a), fix(prev)), end=" ")
                    l1 = Arc(l.c, l.r, fix(a), fix(prev), l.index)
                    l1.swap()
                    newSeg.append(l1)
                    i += 1
                    prev = a
                # dprt("(%5.1f, %5.1f)" % (fix(prev), fix(a1)))
                l1 = Arc(l.c, l.r, fix(a1), fix(prev), l.index)
                l1.swap()
            newSeg.append(l1)
            i += 1
        elif l.type == LINE:
            # dprt("%3d              s %9.6f, %9.6f e %9.6f, %9.6f" % \
            #       (i, l.p0[0], l.p0[1], l.p1[0], l.p1[1]))
            l1 = copy(l)
            newSeg.append(l1)
            i += 1
    dprt("\nsplitArcs out")
    for l in newSeg:
        l.prt()
    dprt()
    return(newSeg)

def combineArcs(seg):
    newSeg = []
    i = 0
    segLen = len(seg)
    k = 0
    while i < segLen:
        l = seg[i]
        # l.prt()
        # combine arcs
        if l.type == ARC:
            a1 = None
            # p0 = l.p0
            j = i
            while True:
                if j + 1 >= segLen:
                    break
                l0 = seg[j + 1]
                if (l0.type == ARC and l0.r == l.r and \
                    l0.c[0] == l.c[0] and l0.c[1] == l.c[1]):
                    # l0.prt()
                    j += 1
                    # p1 = l0.p1
                    a1 = l0.aEnd()
                else:
                    break
            if a1 is not None:
                # dprt("p0 %7.4f, %7.4f p1 %7.4f %7.4f" % \
                #       (p0[0], p0[1], p1[0], p1[1]))
                # dprt("%2d combine arc %2d %2d a0 %5.1f a1 %5.1f" % \
                #         (l.index, i, j, l.aStr(), a1))
                i = j
                if not l.swapped:
                    l0 = Arc(l.c, l.r, l.aStr(), a1)
                else:
                    l0 = Arc(l.c, l.r, a1, l.aStr())
                    l0.swap()
                # l0.prt()
                # dprt()
                l = l0
        l.index = k
        newSeg.append(l)
        i += 1
        k += 1

    dprt()
    for l in newSeg:
        l.prt()
    dprt()
    return(newSeg)

def createPath(seg, dist, outside, tabPoints=None, \
               closed=True, ref=None, addArcs=False, \
               split=True, keepIndex=False, dbg=True):
    if dbg:
        dprt("createPath")
    if split:
        newSeg = splitArcs(seg)
    else:
        newSeg = seg
    labelPoints(newSeg)

    d = abs(dist)
    if closed:                  # closed path
        curDir = pathDir(newSeg, 0.050)
        if dbg:
            dprt("curdir %s" % (oStr(curDir)))

        if cfg.climb:               #      \  outside path
            dir = CW                # ccw ^ |  / normal
        else:                       #       | ^ cutter turns cw
            dir = CCW               #  cw v |  \ climb
        			    #      /
        if not outside:             #
            if dir == CCW:          #        / inside path
                dir = CW            #  cw ^ |  / normal
            else:                   #       | ^ cutter turns cw
                dir = CCW           # ccw v |  \ climb
        			    #        \
        if curDir != dir:
            if dbg:
                dprt("reverse direction")
            newSeg = reverseSeg(newSeg)

        curDir = pathDir(newSeg, 0.100)
        if dbg:
            dprt("%s %s dir %s" % (('normal', 'climb')[cfg.climb], \
                                   ('inside', 'outside')[outside], oStr(curDir)))

        if outside:                 # outside ^    cw <-|
            if dir == CCW:          #  dir cw | dir ccw |
                d = -d              #  ccw <- |         v
        else:
            if dir == CW:
                d = -d
    else:                       # open path
        pFirst = newSeg[0].p0
        pLast = newSeg[-1].p1
        if xyDist(ref, pLast) < xyDist(ref, pFirst):
            if dbg:
                dprt("reverse direction")
            newSeg = reverseSeg(newSeg)
        l = newSeg[0]
        dir = orientation(l.p0, l.p1, ref)
        if dir == CW:
            d = -d

    if dbg:
        for l in newSeg:
            l.prt()

    intersect = True
    segPath = []
    prev = None
    if tabPoints is not None:
        segTabPoints = []
    else:
        segTabPoints = None
    for (i, l) in enumerate(newSeg):
        if dbg:
            dprt("processing %d" % (l.index))
            l.prt()
            dprt()
            l.draw()
        pMid = l.midPoint(d, dbg)
        if closed:
            cross = inside(pMid, newSeg, False)
            # if draw is not None
            #     draw.drawX(pMid, "i%d-%d" % (cross, l.index))
            if ((cross & 1) == 0) != outside:
                ePrint("creatPath - parallel line not on correct side")
                dprt("choose distance negative %d" % (cross))
                d = -d
        if l.index != INDEX_MARKER:
            l1 = l.parallel(d)
        else:
            l1 = copy(l)
        if not keepIndex:
            l1.index = i
        if prev is not None:
            # dprt("intersect %d %s and %d %s" % \
            #       (prev.index, prev.str[0], l1.index, l1.str[0]))
            if intersect:
                p = prev.intersect(l1)
        segPath.append(l1)
        if tabPoints is not None:
            for (n, p) in enumerate(tabPoints):
                dp = l.pointDistance(p)
                if dp is not None:
                    if abs(dp) < MIN_DIST:
                        p0 = l.point90(p, d)
                        dp = l1.pointDistance(p0)
                        if dbg:
                            dprt("dp %7.4f p %7.4f, %7.4f" % (dp, p[0], p[1]))
                            if draw is not None:
                                draw.drawX(p0, "T%d" % (n), True)
                        segTabPoints.append(p0)
                    else:
                        if dbg:
                            dprt("dp %7.4f p %7.4f, %7.4f" % (dp, p[0], p[1]))
        prev = l1

    if intersect and closed:
        l1 = segPath[0]
        # dprt("intersect %d and %d" % (prev.index, l1.index))
        prev.intersect(l1)

    if dbg:
        dprt("offset path")
        for l in segPath:
            l.prt()
        dprt()

    if segTabPoints is not None:
        if dbg:
            dprt("tab points")
            for (n, p) in enumerate(segTabPoints):
                dprt("%d (%7.4f %7.4f)" % (n, p[0], p[1]))
            dprt()
        segTabPoints = list(set(segTabPoints))

    if addArcs and closed:
        if dbg:
            dprt("add arcs")
        prev = None
        if closed:
            prev = segPath[-1]
        newPath = []
        for l in segPath:
            l.prt()
            if prev is not None and prev.type == LINE and l.type == LINE:
                arc = lineLineArc(segPath, prev, l, cfg.endMillSize / 2.0, dir)
                if arc is not None:
                    newPath.append(arc)
            newPath.append(l)
            prev = l
            if dbg:
                dprt()
    else:
        newPath = segPath

    prev = None
    if closed:
        prev = newPath[-1]
    p1 = None
    for (i, l) in enumerate(newPath):
        l.prt()
        if p1 is not None:
            l.updateP0(p1)
            p1 = None
        elif prev is not None and l.type == ARC and l.index == -1:
            prev.updateP1(l.p0)
            p1 = l.p1
        if not keepIndex:
            l.index = i
        prev = l

    if dbg:
        for l in newPath:
            l.draw()
            labelP(l.p0, "%s %d" % (l.str[0].upper(), l.index))
        dprt()
    return(newPath, segTabPoints)

def labelPoints(seg):
    if draw is None:
        return
    for (i, l) in enumerate(seg):
        (x, y) = l.p0
        t = 'l'
        if l.type == ARC:
            t = 'a'
        draw.text('%s%d' % (t, l.index), (x + .010, y + .010), .010)

def labelP(p, txt):
    if draw is None:
        return
    (x, y) = p
    # cfg.draw.text('%s' % (txt), (x + .010, y + .010), .025)
    draw.text('%s' % (txt), (x, y), .010)

def printPoint(name, point):
    dprt("%s x %6.4f y %6.4f" % (name, point[0], point[1]))

# def segDirection(seg):
#     dprt("segDirection")
#     prev = seg[-1]
#     dir = None
#     outsideDir = None
#     dbg = False
#     for l in seg:
#         l.prt()
#         curDir = None
#         if l.type == ARC:
#             if dbg and draw is not None:
#                 draw.move(l.c)
#                 draw.line((l.c[0], l.c[1] + 1))
#             c = inside(l.c, seg, dbg)
#             dprt("c %d" % (c))
#             s = l.swapped
#             curDir = (CW, CCW)[s]
#             dirStr = "a %s" % (oStr(curDir))
#         else:
#             if prev.type == LINE or prev.type == ARC:
#                 val = orientation(prev.p0, l.p0, l.p1)
#                 if val != 0:
#                     curDir = val
#                 dirStr = "l %s" % (oStr(val))
#         md = 0.005
#         m0 = l.midPoint(md)
#         m1 = l.midPoint(-md)
#         c0 = inside(m0, seg)
#         c1 = inside(m1, seg)
#         dprt("%5s c0 %d c1 %d m0 %7.4f, %7.4f m1 %7.4f, %7.4f" % \
#              (dirStr, c0, c1, m0[0], m0[1], m1[0], m1[1]))

#         if curDir is not None:
#             if outsideDir is None and (c0 == 0 or c1 == 0):
#                 outsideDir = curDir
#             if dir is None:
#                 dir = curDir
#             else:
#                 if curDir != BOTH and curDir != dir:
#                     dir = BOTH
#         prev = l
#         dprt()
#     dprt("dir %s outsideDir %s\n" % \
#           (('', 'CW', 'CCW', 'BOTH')[dir], oStr(outsideDir)))
#     return((dir, outsideDir))

# def center(seg):
#     index = findMinX(seg)[0]
#     o0 = pathDir(seg)
#     n = 0
#     xSum = 0
#     ySum = 0
#     prev = seg[index - 1]
#     segLen = len(seg)
#     for i in range(segLen):
#         l = seg[index]
#         # prev.prt()
#         # l.prt()
#         o1 = orientation(prev.p0, l.p0, l.p1)
#         if o1 == o0:
#             (x, y) = l.p0
#             xSum += x
#             ySum += y
#             n += 1
#             prev = l
#         #     dprt("%3d %3d %d x %7.4f y %7.4f xSum %7.1f ySum %7.1f" % \
#         #           (i, n, o1, x, y, xSum, ySum))
#         # else:
#         #     dprt("%3d     %d x %7.4f y %7.4f" % (i, o1, l.p0[0], l.p0[1]))
#         index += 1
#         if index >= segLen:
#             index = 0
#     x = xSum / n
#     y = ySum / n
#     # dprt("center n %d x %7.4f y %7.4f" % (n, x, y))
#     # dprt()
#     return((x, y))

# def findMaxY(seg):
#     dprt("findMaxY")
#     maxY = 0
#     index = None
#     for (i, l) in enumerate(seg):
#         (x, y) = l.p0
#         dprt("%2d %2d x %7.4f y %7.4f" % (i, l.index, x, y))
#         if y > maxY:
#             cross = inside(l.midPoint(0.005), seg, True)
#             if cross == 0:
#                 maxY = y
#                 index = i
#             else:
#                 cross = inside(l.midPoint(-0.005), seg, True)
#                 if cross == 0:
#                     maxY = y
#                     index = i
#     dflush()
#     if index is None:
#         return((0, 0))
#     dprt("index %d maxY %7.4f" % (index, maxY))
#     dprt()
#     return((index, maxY))

# def removeArcs(seg):
#     # dprt("removeArcs")
#     newSeg = []
#     i = 0
#     for l in seg:
#         # l.prt()
#         if l.type == ARC:
#             (i0, i1) = l.c
#             r = l.r
#             a0 = degrees(calcAngle(l.c, l.p0))
#             a1 = degrees(calcAngle(l.c, l.p1))
#             inc = 360 / 100
#             prev = l.p0
#             # dprt("a0 %5.1f a1 %5.1f" % (a0, a1))
#             if not l.swapped:   # clockwise
#                 if a1 < a0:
#                     a1 += 360.0
#                 dir = 'cw '
#             else:               # counter clockwise
#                 if a0 == 0.0:
#                     a0 += 360.0
#                 dir = 'ccw'
#             delta = a1 - a0
#             steps = int(ceil(abs(delta) / inc))
#             inc = delta / steps
#             # dprt("%s delta %5.1f steps %d inc %6.3f" % \
#             #       (dir, delta, steps, inc))
#             j = 0
#             while j < steps:
#                 a0 += inc
#                 x = r * cos(radians(a0)) + i0
#                 y = r * sin(radians(a0)) + i1
#                 # dprt("%3d %3d a0 %5.1f s %9.6f, %9.6f e %9.6f, %9.6f" % \
#                 #       (i, j, a0, prev[0], prev[1], x, y))
#                 p = (x, y)
#                 l1 = Line(prev, p)
#                 l1.index = i
#                 # l1.draw()
#                 newSeg.append(l1)
#                 prev = p
#                 j += 1
#                 i += 1
#         elif l.type == LINE:
#             # dprt("%3d              s %9.6f, %9.6f e %9.6f, %9.6f" % \
#             #       (i, l.p0[0], l.p0[1], l.p1[0], l.p1[1]))
#             # l.draw()
#             l1 = copy(l)
#             l1.index = i
#             newSeg.append(l1)
#             i += 1
#     # dprt()
#     # labelPoints(newSeg)
#     # segDirection(newSeg)
#     return(newSeg)
