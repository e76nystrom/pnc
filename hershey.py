#!/cygdrive/c/DevSoftware/Python/Python36-32/Python.exe

from __future__ import print_function

from math import atan2, cos, degrees, hypot, pi, radians, sin

from dbgprt import dprt, dprtSet, ePrint

# The structure is bascially as follows: each character consists of a
# number 1->4000 (not all used) in column 0:4, the number of vertices in
# columns 5:7, the left hand position in column 8, the right hand
# position in column 9, and finally the vertices in single character
# pairs. All coordinates are given relative to the ascii value of
# 'R'. If the coordinate value is " R" that indicates a pen up
# operation.

# As an example consider the 8th symbol

# 0123456789
#     8  9MWOMOV RUMUV ROQUQ

# It has 9 coordinate pairs (this includes the left and right position).
# The left position is 'M' - 'R' = -5
# The right position is 'W' - 'R' = 5
# The first coordinate is "OM" = (-3,-5)
# The second coordinate is "OV" = (-3,4)
# Raise the pen " R"
# Move to "UM" = (3,-5)
# Draw to "UV" = (3,4)
# Raise the pen " R"
# Move to "OQ" = (-3,-1)
# Draw to "UQ" = (3,-1)
# Drawing this out on a piece of paper will reveal it represents an 'H'.

class Font():
    def __init__(self, m, d, fontFile):
        self.letter = []
        self.min = 99
        self.max = -99
        self.height = 0.0
        self.scale = 0.0
        self.dbg = False
        if self.dbg:
            dprtSet(True)
        self.readFont(fontFile)
        self.m = m
        self.d = d
        self.zOffset = 0.0

    def readFont(self, fontFile):
        inp = open(fontFile, 'rb')
        c = ord(' ')
        while True:
            minVal = 99
            maxVal = -99
            val = inp.read(5)
            if len(val) == 0:
                break
            index = int(val.decode())
            val = inp.read(3)
            length = int(val.decode())
            l = ord(inp.read(1)) - ord('R')
            r = ord(inp.read(1)) - ord('R')
            chArray = []
            move = True
            for i in range(0, length - 1):
                while True:
                    x = inp.read(1)
                    if ord(x) >= ord(' '):
                        break
                y = inp.read(1)
                if ord(x) == ord(' ') and ord(y) == ord('R'):
                    move = True
                else:
                    x = ord(x) - ord('R')
                    y = ord(y) - ord('R')
                    if y > maxVal:
                        maxVal = y
                    if y < minVal:
                        minVal = y
                    chArray.append([x + abs(l), y, move])
                    move = False
            self.letter.append(Letter(r, l, chArray))
            val = inp.read(1)
            if ord(val) != 10:
                ePrint("error")
            if self.dbg:
                dprt("%3d '%1c' length %2d index %4d len %2d l %3d r %3d "\
                     "max %3d min %3d" % \
                     (c, c, length, index, len(chArray), l, r, maxVal, minVal))
                j = 0
                for i, (x, y, move) in enumerate(chArray):
                    dprt("(%2d %3d %3d %5s)" % (i, x, y, move), end=" ")
                    j += 1
                    if j & 3 == 0:
                        dprt()
                if j & 3 != 0:
                    dprt()
                c += 1
            if maxVal > self.max:
                self.max = maxVal
            if minVal < self.min:
                self.min = minVal

    def setHeight(self, h):
        self.height = h
        self.scale = h / (self.max - self.min)
        # dprt("scale %7.3f" % (self.scale))

    def offset(self):
        yOffset = -self.min
        ySize = self.max - self.min
        for l in self.letter:
            l.offset(yOffset, ySize)

    def setZOffset(self, zOffset):
        self.zOffset = zOffset

    def width(self, string):
        width = 0
        for b in list(string):
            letter = self.letter[ord(b) - ord(' ')]
            width += letter.width()
        return(self.scale * width)

    def left(self, string):
        left = 0
        for b in list(string):
            letter = self.letter[ord(b) - ord(' ')]
            left += letter.l
        return(self.scale * left)
    
    def mill(self, pt, string, xDir=True, center=False):
        (x, y) = pt
        if center:
            w = self.width(string) / 2.0
            if xDir:
                x -= w
            else:
                y -= w
        for b in list(string):
            letter = self.letter[ord(b) - ord(' ')]
            letter.mill(self, (x, y), xDir, b)
            if xDir:
                x += letter.width() * self.scale
            else:
                y += letter.width() * self.scale

    def millOnArc(self, pt, angle, string, center=False):
        # dprt("angle %7.3f" % (angle))
        a = radians(angle)
        (x0, y0) = pt
        if center:
            w = self.width(string) / 2.0
            x0 -= w * cos(pi + a)
            y0 -= w * sin(pi + a)
        cosA = cos(a)
        sinA = sin(a)
        scale = self.scale
        for b in list(string):
            letter = self.letter[ord(b) - ord(' ')]
            letter.millOnArc(self, (x0, y0), a)
            w = letter.width() * scale
            x0 -= w * cosA
            y0 -= w * sinA
            
    def millOnCylinder(self, pt, angle, radius, string, xDir, center=False):
        a0 = angle
        if center:
            w = self.width(string) / 2.0
            if xDir:
                a0 += degrees(atan2(w, radius))
            else:
                a0 -= degrees(atan2(w, radius))
        self.m.retract()
        self.m.write("g0 a%7.4f\n" % (a0))
        for b in list(string):
            letter = self.letter[ord(b) - ord(' ')]
            letter.millOnCylinder(self, pt, a0, radius, xDir)
            if xDir:
                a0 -= degrees(atan2(letter.width() * self.scale, radius))
            else:
                a0 += degrees(atan2(letter.width() * self.scale, radius))
            self.m.retract()
            self.m.write("g0 a%7.4f\n" % (a0))

class Letter():
    def __init__(self, r, l, chArray):
        self.r = r
        self.l = l
        self.chArray = chArray

    def width(self):
        return(self.r - self.l)

    def offset(self, yOffset, ySize):
        for s in self.chArray:
            y = s[1]
            s[1] = ySize - (y + yOffset)

    def mill(self, font, pt, xDir=True, letter=""):
        scale = font.scale
        m = font.m
        (x, y) = pt
        m.move(pt, comment=letter)
        for (xRel, yRel, move) in self.chArray:
            # dprt("%3d %3d %5s" % (xRel, yRel, move))
            if xDir:
                x0 = x + xRel * scale
                y0 = y + yRel * scale
            else:
                x0 = x + yRel * scale
                y0 = y + xRel * scale
            p = (x0, y0)
            if move:
                m.retract()
                m.move(p)
                m.zDepth(font.zOffset)
            else:
                m.cut(p)
        m.retract()

    def millOnArc(self, font, pt, angle):
        scale = font.scale
        m = font.m
        (xC, yC) = pt
        for (x, y, move) in self.chArray:
            theta = atan2(y, x) + angle
            r = hypot(x, y)
            x0 = xC + scale * r * cos(theta)
            y0 = yC + scale * r * sin(theta)
            p0 = (x0, y0)
            if move:
                m.retract()
                m.move(p0)
                m.zDepth(font.zOffset)
            else:
                m.cut(p0)

    def millOnCylinder(self, font, pt, angle, radius, xDir):
        scale = font.scale
        m = font.m
        d = font.d
        (xP, yP) = pt
        for (x, y, move) in self.chArray:
            if xDir:
                x0 = xP + x * scale
                y0 = yP + y * scale
                xA = radians(angle) * radius
                yA = 0.0
            else:
                x0 = xP + y * scale
                y0 = yP - x * scale
                xA = 0.0
                yA = radians(angle) * radius
            p0 = (x0, y0)
            pA = (xA + x0, yA + y0)
            if move:
                m.retract()
                m.move(p0)
                m.zDepth(font.zOffset)
                if d is not None:
                    d.move(pA)
            else:
                m.cut(p0, draw=False)
                if d is not None:
                    d.line(pA)
                
if __name__ == '__main__':
    f = Font(None, None, "rowmans.jhf")
    f.mill(0, 0, "test")
