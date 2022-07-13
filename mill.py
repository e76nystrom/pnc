import os

from time import localtime, strftime

from dbgprt import dflush, dprt
from geometry import MIN_DIST, MIN_VALUE

class Mill():
    def __init__(self, cfg, outFile, draw=True):
        self.cfg = cfg
        self.outFile = None
        self.spindleActive = False
        self.speed = 0
        self.tool = None
        self.coordinate = None
        if outFile is not None:
            self.init(outFile, draw)

    def init(self, outFile, draw=True):
        cfg = self.cfg
        self.blank = False
        self.drawFlag = draw
        self.draw = cfg.draw if draw else None
        self.last = (0.0, 0.0)
        self.lastZ = 0.0
        self.arcCmd = 'g2'
        self.curFeed = 0.0
        self.speed = 0.0
        self.cw = False
        if cfg.zFeed == 0:
            cfg.zFeed = cfg.feed
        if self.outFile is None:
            self.outFile = outFile
            self.tool = None

            # print("%s" % (os.environ['TZ'],))
            # os.environ['TZ'] = 'America/New_York'
            # print("%s %s" % (strftime("%m-%d-%Y %H:%M:%S", localtime()), \
            #                  os.environ['TZ']))

            # self.out = out = open(outFile, 'w', newline='\n')
            self.out = open(outFile, 'w')

            timeString = "%m-%d-%Y %H:%M:%S"
            t = strftime(timeString,
                         localtime(os.path.getmtime(cfg.curInFile)))
            inFile = os.path.realpath(cfg.curInFile)
            self.write("(%s modified %s)\n" %  (inFile, t))

            self.write("(%s created %s)\n" % \
                       (outFile, strftime(timeString, localtime())))
            self.write("(orientation %s" % \
                       (cfg.orientationValues[cfg.orientation][1]))
            dxf = cfg.dxfInput
            if dxf is not None:
                x = dxf.xMax - dxf.xMin
                y = dxf.yMax - dxf.yMin
                self.write(" %s material %7.4f %7.4f" % (dxf.inFile, x, y))
                if dxf.fXMax != MIN_VALUE:
                    x = dxf.fXMax - dxf.fXMin
                    y = dxf.fYMax - dxf.fYMin
                    self.write(" fixture %7.4f %7.4f" % (x, y))
            self.write(")\n")
            if cfg.compNumber is not None:
                self.write("(component %s%s)\n" % \
                           (cfg.compNumber, cfg.compComment))

            if cfg.variables:
                self.write("#%s = %s	(depth)\n" % (cfg.depthVar, cfg.depth))
                self.write("#%s = %s	(retract between holes)\n" % \
                           (cfg.retractVar, cfg.retract))
                self.write("#%s = %s	(safe z)\n" % \
                           (cfg.safeZVar, cfg.safeZ))
                self.write("#%s = %s	(top)\n" % (cfg.topVar, cfg.top))
            else:
                self.write("(%7.4f	depth)\n" % (cfg.depth))
                self.write("(%7.4f	retract between holes)\n" % \
                           (cfg.retract))
                self.write("(%7.4f	safe z)\n" % (cfg.safeZ))
                self.write("(%7.4f	top)\n" % (cfg.top))
            self.write("\ng90		(absolute coordinates)\n")
            self.write("g20		(inch units)\n")
            self.write("g61		(exact path mode)\n")
            self.write("g%d		(coordinate system)\n" % \
                       (cfg.coordinate))
            self.coordinate = cfg.coordinate
            self.setFeed(cfg.feed)
            self.toolChange(cfg.tool, cfg.toolComment)
            self.safeZ()
            if cfg.homePause:
                self.move((cfg.xInitial, cfg.yInitial))
                self.pause()
            else:
                self.blankLine()
        else:
            self.toolChange(cfg.tool, cfg.toolComment)

    def setCoordinate(self, coordinate):
        if self.coordinate != coordinate:
            self.coordinate = coordinate
            self.write("g%d		(coordinate system)\n" % \
                       (coordinate))
            self.safeZ()
            cfg = self.cfg
            self.move((cfg.xInitial, cfg.yInitial))
            self.pause()

    def write(self, string):
        self.out.write(string)
        self.blank = False
        if self.cfg.printGCode:
            dprt(string.rstrip('\n'))
            dflush()

    def blankLine(self):
        if not self.blank:
            self.out.write("\n")
            self.blank = True

    def pause(self):
        self.write("m0 (pause)\n")
        self.blankLine()

    def toolChange(self, tool, toolComment=""):
        cfg = self.cfg
        if cfg.opNumber != None:
            self.blankLine()
            self.write("(operation %s%s)\n" % \
                       (cfg.opNumber, cfg.opComment))
            self.blankLine()
        if tool is not None and tool != self.tool:
            self.tool = tool
            self.setSpeed(0)
            self.lastZ = 999    # set to invalid z
            self.blankLine()
            self.write("(debug, current tool #<_current_tool>)\n")
            oVal = cfg.nextOVal()
            self.write("o%d if [#<_current_tool> ne %d]\n" % (oVal, tool))
            self.write("G30 z %7.4f (Go to preset G30 location)\n" %\
                       (cfg.safeZ))
            if len(toolComment) != 0:
                toolComment = " (" + toolComment + ")"
            self.write("T %d M6 G43 H %d%s\n" % \
                       (tool, tool, toolComment))
            self.write("o%d endif\n" % (oVal))
            self.blankLine()
            self.safeZ()
            self.setSpeed(self.cfg.speed)

    def setArcCW(self, cw):
        self.cw = not cw
        self.arcCmd = ('g3', 'g2')[cw]

    def setSpeed(self, speed):
        cfg = self.cfg
        if speed != 0:
            if speed != self.speed:
                self.speed = speed
                self.write("s %0.0f		(set spindle speed)\n" % \
                           (speed))
            if not self.spindleActive:
                self.spindleActive = True
                self.write("m3		(start spindle)\n")
                if cfg.delay != 0:
                    self.write("g4 p %0.1f	" \
                               "(wait for spindle to start)\n\n" % \
                               (cfg.delay))
        else:
            if self.spindleActive:
                self.spindleActive = False
                self.speed = 0
                self.write("m5	(stop spindle)\n")
                # if cfg.delay != 0:
                #     self.write("g4 p %0.1f	" \
                #                "(wait for spindle to stop)\n" % \
                #                (cfg.delay))

    def setFeed(self, newFeed):
        if newFeed != self.curFeed:
            self.curFeed = newFeed
            self.write("f %s		(set feed rate)\n" % (newFeed))

    def move(self, end, comment=""):
        if self.draw is not None:
            self.draw.move(end)
        (xEnd, yEnd) = end
        if len(comment) != 0:
            comment = "\t(%s)" % (comment)
        self.write("g0 x %7.4f y %7.4f%s\n" % (xEnd, yEnd, comment))
        self.last = end

    def moveZ(self, zEnd, comment=""):
        if abs(zEnd - self.lastZ) > MIN_DIST:
            self.lastZ = zEnd
            if len(comment) != 0:
                comment = "\t(%s)" % (comment)
            self.write("g0 z %7.4f%s\n" % (zEnd, comment))

    def plungeZ(self, zEnd, comment=""):
        if abs(zEnd - self.lastZ) > MIN_DIST:
            self.lastZ = zEnd
            self.setFeed(self.cfg.zFeed)
            if len(comment) != 0:
                comment = "\t(%s)" % (comment)
            self.write("g1 z %7.4f%s\n" % (zEnd, comment))

    def retract(self, fast=True, comment=None):
        cfg = self.cfg
        retractZ = cfg.top + cfg.retract
        if abs(retractZ - self.lastZ) > MIN_DIST:
            self.lastZ = retractZ
            if comment is None:
                comment = "(retract)"
            else:
                comment = "(retract %s)" % comment
            if cfg.variables:
                z = "[#%s + #%s]" % (cfg.topVar, cfg.retractVar)
            else:
                z = "%7.4f" % (cfg.top + cfg.retract)
            if fast:
                self.write("g0 z %s %s\n" % (z, comment))
            else:
                self.write("g1 z %s f %1.1f (retract)\n" % \
                           (z, cfg.zFeed, comment))

    def safeZ(self):
        cfg = self.cfg
        safeZ = cfg.top + cfg.safeZ
        if abs(safeZ - self.lastZ) > MIN_DIST:
            self.lastZ = safeZ
            if cfg.variables:
                z = "[#%s + #%s]" % (cfg.topVar, cfg.safeZVar)
            else:
                z = "%7.4f" % (cfg.top + cfg.safeZ)
            self.write("g0 z %s (safe z)\n" % (z))

    def parkZ(self):
        cfg = self.cfg
        parkZ = cfg.top + cfg.zPark
        if abs(parkZ - self.lastZ) > MIN_DIST:
            self.lastZ = parkZ
            if cfg.variables:
                z = "[#%s + #%s]" % (cfg.topVar, cfg.parkZVar)
            else:
                z = "%7.4f" % (parkZ)
            self.write("g0 z %s (park z)\n" % (z))
        
    def zTop(self, comment=""):
        cfg = self.cfg
        if abs(cfg.top - self.lastZ) > MIN_DIST:
            self.lastZ = cfg.top
            if cfg.variables:
                z = "[#%s]" % (cfg.topVar)
            else:
                z = "%7.4f" % (cfg.top)
            if len(comment) != 0:
                comment = "\t(top %s)" % (comment)
            else:
                comment = "\t(top)"
            self.write("g0 z %s%s\n" % (z, comment))
            
    def zDepth(self, zOffset=0.0, comment=""):
        cfg = self.cfg
        zDepth = cfg.top + cfg.depth + zOffset
        if abs(zDepth - self.lastZ) > MIN_DIST:
            self.lastZ = zDepth
            self.setFeed(cfg.zFeed)
            if cfg.variables:
                z = "[#%s + #%s + %7.4f]" % \
                    (cfg.topVar, cfg.depthVar, zOffset)
            else:
                z = "%7.4f" % (zDepth)
            if len(comment) != 0:
                comment = "\t(%s)" % (comment)
            self.write("g1 z %s%s\n" % (z, comment))

    def cut(self, end, zOffset=None, comment=None, draw=True):
        if draw and self.draw is not None:
            self.draw.line(end)
        (xEnd, yEnd) = end
        self.setFeed(self.cfg.feed)
        if zOffset is None:
            t = "g1 x %7.4f y %7.4f" % (xEnd, yEnd)
        else:
            cfg = self.cfg
            zDepth = cfg.top + zOffset
            if cfg.variables:
                z = "[#%s + %7.4f]" % \
                    (cfg.topVar, zOffset)
            else:
                z = "%7.4f" % (zDepth)
            t = "g1 x %7.4f y %7.4f z%s" % (xEnd, yEnd, z)
            self.lastZ = zDepth
        if comment is not None:
            t += " (%s)" % (comment)
        self.write(t + "\n")
        self.last = end

    def arc(self, end, center, zEnd=None, comment=None, draw=True):
        (xEnd, yEnd) = end
        (xCen, yCen) = center
        (lastX, lastY) = self.last
        if draw and self.draw is not None:
            if self.cw:
                self.draw.arc(end, center)
            else:
                self.draw.move(end)
                self.draw.arc(self.last, center)
                self.draw.move(end)
        self.setFeed(self.cfg.feed)
        if zEnd is None:
            t = "%s x %7.4f y %7.4f i %7.4f j %7.4f" % \
                (self.arcCmd, xEnd, yEnd, xCen - lastX, yCen - lastY)
        else:
            t = "%s x %7.4f y %7.4f z %7.4f i %7.4f j %7.4f" % \
                (self.arcCmd, xEnd, yEnd, zEnd, xCen - lastX, yCen - lastY)
            self.lastZ = zEnd
        if comment is not None:
            t += " (%s)" % (comment)
        self.write(t + "\n")
        self.last = end

    def probe(self, end, feed=1.0, comment=None):
        cfg = self.cfg
        string = " (%s)" % comment if comment is not None else ""
            
        self.write("g0 x%7.4f y%7.4f\n" % end)
        self.write("g38.2 z%6.4f f%0.1f%s\n" % (cfg.probeDepth, feed, string))
        self.write("g0 z%6.4f\n" % (cfg.retract))
        self.blankLine()
        self.last = end

    def probeSetZ(self, feed=1.0, z=0.00):
        self.write("g38.2 z%6.4f f%0.1f\n" % (self.cfg.probeDepth, feed))
        self.write("g10 L20 P0 z%7.4f (set z)\n" % (z))
        self.curFeed = feed
        self.retract()

    # def setCoordinate(self, val):
    #     if self.out is not None:
    #         self.write("g%d\n" % (val))

    def setX(self, coordinate, val):
        if self.out is not None:
            coordinate -= 54
            coordinate += 1
            self.write("g10 L20 P%d x%7.4f (set x)\n" % (coordinate, val))

    def setY(self, coordinate, val):
        if self.out is not None:
            coordinate -= 54
            coordinate += 1
            self.write("g10 L20 P%d y%7.4f (set y)\n" % (coordinate, val))
            
    def close(self):
        if self.out is not None:
            if self.spindleActive:
                self.spindleActive = False
                self.speed = 0
                self.write("m5	(stop spindle)\n")
            self.parkZ()
            self.move((self.cfg.xPark, self.cfg.yPark))
            self.write("m2\n")
            self.out.close()
            self.out = None
            self.outFile = None
