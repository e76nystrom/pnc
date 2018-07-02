from __future__ import print_function
import os
from dbgprt import dprt
from time import strftime, localtime
from geometry import MIN_DIST

class Mill():
    def __init__(self, cfg, outFile, draw=True):
        self.cfg = cfg
        self.outFile = None
        self.spindleActive = False
        self.speed = 0
        self.tool = None
        if outFile is not None:
            self.init(outFile, draw)

    def init(self, outFile, draw=True):
        cfg = self.cfg
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
            self.out = out = open(outFile, 'w')

            out.write("(%s created %s)\n" % \
                      (outFile, strftime("%m-%d-%Y %H:%M:%S", localtime())))

            if cfg.variables:
                out.write("#%s = %s	(depth)\n" % (cfg.depthVar, cfg.depth))
                out.write("#%s = %s	(retract between holes)\n" % \
                          (cfg.retractVar, cfg.retract))
                out.write("#%s = %s	(safe z)\n" % \
                          (cfg.safeZVar, cfg.safeZ))
                out.write("#%s = %s	(top)\n" % (cfgtopVar, cfg.top))
            else:
                out.write("(%7.4f	depth)\n" % (cfg.depth))
                out.write("(%7.4f	retract between holes)\n" % \
                          (cfg.retract))
                out.write("(%7.4f	safe z)\n" % (cfg.safeZ))
                out.write("(%7.4f	top)\n" % (cfg.top))
            out.write("\ng90		(absolute coordinates)\n")
            out.write("g20		(inch units)\n")
            out.write("g61		(exact path mode)\n")
            out.write("g%d		(coordinate system)\n" % \
                      (cfg.coordinate))
            self.setFeed(cfg.feed)
            if cfg.tool is not None:
                self.toolChange(cfg.tool, cfg.toolComment)
            self.safeZ()
            if cfg.homePause:
                self.move((cfg.xInitial, cfg.yInitial))
                self.pause()
            out.write("\n")
        else:
            self.toolChange(cfg.tool, cfg.toolComment)

    def write(self, str):
        self.out.write(str)
        if self.cfg.printGCode:
            dprt(str.rstrip('\n'))

    def pause(self):
        self.out.write("m0 (pause)\n")

    def toolChange(self, tool, toolComment=""):
        if tool != self.tool:
            self.tool = tool
            self.setSpeed(0)
            self.lastZ = 999    # set to invalid z
            self.out.write("\nG30 (Go to preset G30 location)\n")
            if len(toolComment) != 0:
                toolComment = " (" + toolComment + ")"
            self.out.write("T %d M6 G43 H %d%s\n\n" % \
                           (tool, tool, toolComment))
            self.safeZ()
            self.setSpeed(self.speed)

    def setArcCW(self, cw):
        self.cw = not cw
        self.arcCmd = ('g3', 'g2')[cw]

    def setSpeed(self, speed):
        out = self.out
        cfg = self.cfg
        if speed != 0:
            if speed != self.speed:
                self.speed = speed
                out.write("s %0.0f		(set spindle speed)\n" % \
                          (speed))
            if not self.spindleActive:
                self.spindleActive = True
                out.write("m3		(start spindle)\n")
                if cfg.delay != 0:
                    out.write("g4 p %0.1f	" \
                              "(wait for spindle to start)\n" % \
                              (cfg.delay))
        else:
            if self.spindleActive:
                self.spindleActive = False
                self.speed = 0
                out.write("m5	(stop spindle)\n")
                if cfg.delay != 0:
                    out.write("g4 p %0.1f	" \
                              "(wait for spindle to stop)\n" % \
                              (cfg.delay))

    def setFeed(self, newFeed):
        if newFeed != self.curFeed:
            self.curFeed = newFeed
            self.out.write("f %s		(set feed rate)\n" % (newFeed))

    def move(self, end, comment=""):
        if self.draw is not None:
            self.draw.move(end)
        (xEnd, yEnd) = end
        if len(comment) != 0:
            comment = "\t(%s)" % (comment)
        self.write("g0 x%7.4f y%7.4f%s\n" % (xEnd, yEnd, comment))
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

    def retract(self, fast=True):
        cfg = self.cfg
        retractZ = cfg.top + cfg.retract
        if abs(retractZ - self.lastZ) > MIN_DIST:
            self.lastZ = retractZ
            if cfg.variables:
                z = "[#%s + #%s]" % (cfg.topVar, cfg.retractVar)
            else:
                z = "%0.4f" % (cfg.top + cfg.retract)
                if fast:
                    self.write("g0 z %s (retract)\n" % (z))
                else:
                    self.write("g1 z %s f %1.1f(retract)\n" % (z, self.zFeed))

    def safeZ(self):
        cfg = self.cfg
        safeZ = cfg.top + cfg.safeZ
        if abs(safeZ - self.lastZ) > MIN_DIST:
            self.lastZ = safeZ
            if cfg.variables:
                z = "[#%s + #%s]" % (cfg.topVar, cfg.safeZVar)
            else:
                z = "%0.4f" % (cfg.top + cfg.safeZ)
            self.write("g0 z %s (safe z)\n" % (z))

    def parkZ(self):
        cfg = self.cfg
        parkZ = cfg.top + cfg.zPark
        if abs(parkZ - self.lastZ) > MIN_DIST:
            self.lastZ = parkZ
            if cfg.variables:
                z = "[#%s + #%s]" % (cfg.topVar, cfg.parkZVar)
            else:
                z = "%0.4f" % (parkZ)
            self.write("g0 z %s (park z)\n" % (z))
        
    def zTop(self, comment=""):
        cfg = self.cfg
        if abs(cfg.top - self.lastZ) > MIN_DIST:
            self.lastZ = cfg.top
            if cfg.variables:
                z = "[#%s]" % (cfg.topVar)
            else:
                z = "%0.4f" % (cfg.top)
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
                z = "%0.4f" % (zDepth)
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
                z = "%0.4f" % (zDepth)
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
        out = self.out
        cfg = self.cfg
        str = " (%s)" % comment if comment is not None else ""
            
        out.write("g0 x%7.4f y%7.4f\n" % end)
        out.write("g38.2 z%6.4f f%0.1f%s\n" % (cfg.probeDepth, feed, str))
        out.write("g0 z%6.4f\n\n" % (cfg.retract))
        self.last = end

    def probeSetZ(self, feed=1.0, z=0.00):
        out = self.out
        out.write("g38.2 z%6.4f f%0.1f\n" % (self.cfg.probeDepth, feed))
        out.write("g10 L20 P0 z%7.4f (set z)\n" % (z))
        self.curFeed = feed
        self.retract()

    def close(self):
        out = self.out
        if out is not None:
            if self.spindleActive:
                self.spindleActive = False
                self.speed = 0
                out.write("m5	(stop spindle)\n")
            self.parkZ()
            self.move((self.cfg.xPark, self.cfg.yPark))
            out.write("m2\n")
            out.close()
            self.out = None
            self.outFile = None
