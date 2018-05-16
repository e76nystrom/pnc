from __future__ import print_function
import pyclipper
from copy import copy
from dbgprt import dprtSet, dprt, dflush
from geometry import Arc, Line, LINE, CCW, CW, MIN_DIST

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
            mainPath = []
            for (i, l) in enumerate(seg):
                l.draw()
                if l.type == LINE:
                    (x, y) = l.p0
                    dprt("%2d (%7.4f %7.4f)" % (i, x, y))
                    mainPath.append((int(10000 * x), int(10000 * y)))
            dprt()
            offset = cfg.endMillSize / 2.0 + cfg.finishAllowance
            step = 0
            while True:
                dprt("%2d offset %7.4f" % (step, offset))
                pco.Clear()
                pco.AddPath(mainPath, pyclipper.JT_ROUND, \
                            pyclipper.ET_CLOSEDPOLYGON)
                result = pco.Execute(-int(offset * 10000))
                if len(result) == 0:
                    break
                for r in result:
                    (x, y) = r[-1]
                    pLast = (float(x) / 10000.0, float(y) / 10000.0)
                    path = []
                    for (i, (x, y)) in enumerate(r):
                        x = float(x) / 10000.0
                        y = float(y) / 10000.0
                        dprt("%2d (%7.4f %7.4f)" % (i, x, y))
                        p = (x, y)
                        l = Line(pLast, p)
                        path.append(l)
                        pLast = p
                    dprt()
                    for l in path:
                        l.prt()
                    dprt()
                    mp.millPath(path)
                offset += stepOver
                step += 1
                
