from __future__ import print_function
from sys import stderr, stdout

DBG = False
dbgFile = ""
dbg = None

def ePrint(str):
    dprt(str)
    dflush()
    if not DBG or dbg != None:
        print(str, file=stderr)
    
def dprt(str="", end='\n'):
    global DBG, dbg
    if DBG:
        if dbg == None:
            print(str, end=end)
        else:
            try:
                dbg.write(str)
                dbg.write('\n')
            except IOError:
                dbg = None
                print("debug file write error", file=stderr)
                
def dflush():
    global DBG, dbg, dbgFile
    if DBG:
        if dbg == None:
            stdout.flush()
        else:
            try:
                dbg.flush()
            except IOError:
                dbg = None
                print("debug file flush error", file=stderr)

def dprtSet(dbgFlag=None, dFile=None):
    global DBG, dbg, dbgFile
    if dbgFlag != None:
        DBG = dbgFlag
    if dFile != None:
        if dbg != None and dbgFile != dFile:
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
    if dbg != None:
        dbg.close()
        dbg = None
        
