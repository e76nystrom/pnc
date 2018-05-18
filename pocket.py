from __future__ import print_function
import pyclipper
from dbgprt import dprtSet, dprt, dflush
from geometry import Arc, Line, xyDist
from geometry import LINE, CCW, CW, MIN_DIST, MAX_VALUE

SCALE = 10000.0

class pocket():
    def __init__(self, cfg):
        self.cfg = cfg
        print("test loaded")
        self.stepOver = 0.85
        self.cmds = \
        ( \
          ('pocket', self.pocket), \
          ('stepover', self.setStepOver), \
          # ('', self.), \
        )
        dprtSet(True)

    def setStepOver(self, args):
        self.stepOver = float(args[1]) / 100.0

    def pocket(self, args):
        layer = args[1]
        cfg = self.cfg
        dir = CCW
        if cfg.dir is not None and cfg.dir == 'CW':
            dir = CW
        stepOver = cfg.endMillSize * self.stepOver
        cfg.ncInit()
        segments = cfg.dxfInput.getPath(layer)
        pco = pyclipper.PyclipperOffset()
        mp = cfg.getMillPath()
        for seg in segments:
            pco.Clear()
            mainPath = []
            for (i, l) in enumerate(seg):
                l.draw()
                if l.type == LINE:
                    (x, y) = l.p0
                    dprt("%2d (%7.4f %7.4f)" % (i, x, y))
                    mainPath.append((int(SCALE * x), int(SCALE * y)))
            dprt()
            pco.AddPath(mainPath, pyclipper.JT_ROUND, \
                        pyclipper.ET_CLOSEDPOLYGON)
            offset = cfg.endMillSize / 2.0 + cfg.finishAllowance
            step = 0
            offsetPaths = []
            while True:
                result = pco.Execute(-int(offset * SCALE))
                dprt("%2d offset %7.4f results %d" % (step, offset, len(result)))
                if len(result) == 0:
                    break
                for (rNum, r) in enumerate(result):
                    (x, y) = r[-1]
                    pLast = (float(x) / SCALE, float(y) / SCALE)
                    path = []
                    for (i, (x, y)) in enumerate(r):
                        x = float(x) / SCALE
                        y = float(y) / SCALE
                        dprt("%3d (%7.4f %7.4f)" % (i, x, y))
                        p = (x, y)
                        l = Line(pLast, p, i)
                        txt = "s %d r %d i %d" % (step, rNum, i)
                        l.label(txt)
                        path.append(l)
                        pLast = p
                    dprt()
                    for l in path:
                        l.prt()
                    dprt()

                    for (oNum, oPath) in enumerate(offsetPaths):
                        lEnd = oPath[-1]
                        pEnd = lEnd.p1
                        minDist = MAX_VALUE
                        index = None
                        for (i, l) in enumerate(path):
                            dist = xyDist(pEnd, l.p0)
                            if dist < minDist:
                                minDist = dist
                                index = i
                        xDist = abs(pEnd[0] - path[index].p0[0])
                        yDist = abs(pEnd[1] - path[index].p0[1])
                        dprt("step %2d rNum %d oNum %d len %3d index %3d "\
                             "minDist %7.4f xDist %7.4f yDist %7.4f" % \
                             (step, rNum, oNum, len(path), index, minDist, \
                              xDist, yDist))
                        if (abs(xDist - stepOver) <= MIN_DIST) or \
                           (abs(yDist - stepOver) <= MIN_DIST):
                            path = path[index:] + path[:index]
                            oPath.append(Line(pEnd, path[0].p0))
                            oPath += path
                            path = None
                            break
                    if path is not None:
                        offsetPaths.append(path)
                offset += stepOver
                step += 1
                if step == 6:
                    break
            for path in offsetPaths:
                mp.millPath(path, closed=False)
