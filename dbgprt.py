from __future__ import print_function

from sys import stderr, stdout

DBG = False
dbgFile = ""
dbg = None

def ePrint(string):
    dprt(string)
    dflush()
    if not DBG or dbg is not None:
        print(string, file=stderr)
    
def dprt(string="", end='\n'):
    global DBG, dbg
    if DBG:
        if dbg is None:
            print(string, end=end)
        else:
            try:
                dbg.write(string)
                dbg.write('\n')
            except IOError:
                dbg = None
                print("debug file write error", file=stderr)
                
def dflush():
    global DBG, dbg, dbgFile
    if DBG:
        if dbg is None:
            stdout.flush()
        else:
            try:
                dbg.flush()
            except IOError:
                dbg = None
                print("debug file flush error", file=stderr)

def dprtSet(dbgFlag=None, dFile=None):
    global DBG, dbg, dbgFile
    if dbgFlag is not None:
        DBG = dbgFlag
    if dFile is not None:
        if dbg is not None and dbgFile != dFile:
            dbg.close()
            dbgFile = ""
            dbg = None
        if len(dFile) != 0:
            try:
                dbg = open(dFile, 'w')
                dbgFile = dFile
            except IOError:
                dbg = None
                print("debug file %s open error" % (dFile), file=stderr)

def dclose():
    global dbg
    if dbg is not None:
        dbg.close()
        dbg = None
