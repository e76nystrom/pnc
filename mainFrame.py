import os
import wx
from wx.lib.splitter import MultiSplitterWindow
import cairo
import wx.lib.wxcairo as wxcairo
from math import radians, pi
from geometry import (ARC, LINE, Line, xyDist)
from orientation import (O_CENTER, O_LOWER_LEFT, O_LOWER_RIGHT, O_MAX, O_POINT,
                         O_UPPER_LEFT, O_UPPER_RIGHT)
from orientation import (REF_OVERALL, REF_MATERIAL, REF_FIXTURE)
from geometry import Point as Pt

def fieldList(panel, sizer, fields, col=1):
    total = len(fields)
    offset = (total + 1) // 2
    for i in range(total):
        if col == 1:
            field = fields[i]
        else:
            j = i // 2
            if (i & 1) != 0:
                j += offset
            field = fields[j]
        (label, index) = field[:2]
        if label.startswith('b'):
            addCheckBox(panel, sizer, label[1:], index)
        elif label.startswith('c'):
            action = field[3]
            addComboBox(panel, sizer, label[1:], index, action)
        elif label.startswith('w'):
            addField(panel, sizer, label[1:], index, (80, -1))
        else:
            addField(panel, sizer, label, index)

def addFieldText(panel, sizer, label, key, fmt=None, keyText=None):
    if fmt is not None:
        panel.formatList.append((key, fmt))

    # cfg = panel.mf.cfg
    txt = None
    if len(label) != 0:
        txt = wx.StaticText(panel, -1, label)
        sizer.Add(txt, flag=wx.ALL|wx.ALIGN_RIGHT|\
                  wx.ALIGN_CENTER_VERTICAL, border=2)
        # if keyText is not None:
        #     cfg.initInfo(keyText, txt)

    tc = wx.TextCtrl(panel, -1, "", size=(panel.width, -1), \
                     style=wx.TE_PROCESS_ENTER)
    tc.Bind(wx.EVT_TEXT_ENTER, panel.OnEnter)
    sizer.Add(tc, flag=wx.ALL, border=2)
    # cfg.initInfo(key, tc)
    return tc, txt

def addField(panel, sizer, label, index, fmt=None, size=None):
    if size is None:
        size = (panel.width, -1)
    if fmt is not None:
        panel.formatList.append((index, fmt))
    if label is not None:
        txt = wx.StaticText(panel, -1, label)
        sizer.Add(txt, flag=wx.ALL|wx.ALIGN_RIGHT|\
                  wx.ALIGN_CENTER_VERTICAL, border=2)

    tc = wx.TextCtrl(panel, -1, "", size=size, \
                     style=wx.TE_PROCESS_ENTER)
    tc.Bind(wx.EVT_TEXT_ENTER, panel.OnEnter)
    sizer.Add(tc, flag=wx.ALL, border=2)

    # cfg = panel.mf.cfg
    # if cfg.info[index] is not None:
    #     val = cfg.getInfo(index)
    #     tc.SetValue(val)
    # cfg.initInfo(index, tc)
    return tc

def addCheckBox(panel, sizer, label, index, action=None, box=False):
    txt = wx.StaticText(panel, -1, label)
    if box:
        sizerH = wx.BoxSizer(wx.HORIZONTAL)
        sizerH.Add(txt, flag=wx.ALL|\
                   wx.ALIGN_CENTER_VERTICAL, border=2)
    else:
        sizerH = sizer
        sizerH.Add(txt, flag=wx.ALL|wx.ALIGN_RIGHT|\
                   wx.ALIGN_CENTER_VERTICAL, border=2)
    cb = wx.CheckBox(panel, -1, style=wx.ALIGN_LEFT)
    if action is not None:
        panel.Bind(wx.EVT_CHECKBOX, action, cb)
    sizerH.Add(cb, flag=wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=2)

    # cfg = panel.mf.cfg
    # if cfg.info[index] is not None:
    #     val = cfg.getInfo(index)
    #     cb.SetValue(val == 'True')
    # cfg.initInfo(index, cb)
    if box:
        sizer.Add(sizerH, flag=wx.ALIGN_RIGHT)
    return cb

def addComboBox(panel, sizer, label, index, action, border=2,
                flag=wx.CENTER|wx.ALL):
    txt = wx.StaticText(panel, -1, label)
    sizer.Add(txt, flag=wx.ALL|wx.ALIGN_RIGHT|\
              wx.ALIGN_CENTER_VERTICAL, border=2)

    (indexList, choiceList, text) = action()
    if (indexList is not None) and (choiceList is not None):
        combo = ComboBox(panel, label, indexList, choiceList, \
                         id=-1, value=choiceList[0], choices=choiceList, \
                         style=wx.CB_READONLY)
    else:
        combo = ComboBox(panel, label, indexList, choiceList, \
                         id=-1, style=wx.CB_READONLY)
        
    combo.text = text
    # cfg = panel.mf.cfg
    # if cfg.info[index] is not None:
    #     val = cfg.getInfo(index)
    #     combo.SetValue(val)
    sizer.Add(combo, flag=flag, border=border)
    # cfg.initInfo(index, combo)
    return combo

class DialogButton(wx.Button):
    def __init__(self, dialog, *args, **kwargs):
        wx.Button.__init__(self, *args, **kwargs)
        self.dialog = dialog

def addDialogButton(panel, sizer, idx, action=None, border=5):
    btn = DialogButton(panel, panel, idx)
    if action is None:
        btn.SetDefault()
    else:
        btn.Bind(wx.EVT_BUTTON, action)
    sizer.Add(btn, 0, wx.ALL|wx.CENTER, border=border)
    return btn

class ComboBox(wx.ComboBox):
    def __init__(self, parent, label, indexList=None,  choiceList=None, \
                 *args, **kwargs):
        self.label = label
        self.indexList = indexList
        self.choiceList = choiceList
        self.text = None
        super(ComboBox, self).__init__(parent, *args, **kwargs)

    def GetValue(self):
        val = self.GetCurrentSelection()
        rtnVal = self.indexList[val]
        # if self.text is not None:
        #     print("label \"%s\" GetValue %d text \"%s\" index %d" % \
        #           (self.label, rtnVal, self.text[val], val))
        #     print("indexList", self.indexList)
        return str(rtnVal)
    
    def SetValue(self, val):
        if isinstance(val, str):
            val = int(val)
        for (n, index) in enumerate(self.indexList):
            if val == index:
                self.SetSelection(n)
                # if self.text is not None:
                #     print("label \"%s\" SetValue %d text \"%s\" index %d" % \
                #           (self.label, val, self.text[index], n))
                #     print("indexList", self.indexList)

    def SetSel(self, val):
        for (n, string) in enumerate(self.choiceList):
            if val == string.lower():
                self.SetSelection(n)

def menuItem(frame, topMenu, text, action=None):
    ctlId = wx.Window.NewControlId()
    menu = topMenu.Append(ctlId, text)
    if action is not None:
        frame.Bind(wx.EVT_MENU, action, menu)
    return ctlId

def menuSetup(frame):
    frame.openDialog = None
    fileMenu = wx.Menu()
    menuItem(frame, fileMenu, "Open", frame.onOpen)
    menuItem(frame, fileMenu, "Save")
    menuItem(frame, fileMenu, "Exit")

    menuBar = wx.MenuBar()
    menuBar.Append(fileMenu, 'File')

    frame.SetMenuBar(menuBar)

def onOpen(frame, e):
    # frame.dirName = os.getcwd()
    # dlg = wx.FileDialog(frame, "Choose a file", frame.dirName,
    #                     "", "*.dxf", wx.FD_OPEN)
    # if dlg.ShowModal() == wx.ID_OK:
    #     frame.filename = dlg.GetFilename()
    #     frame.dirname = dlg.GetDirectory()
    #     frame.path = os.path.join(frame.dirname, frame.filename)
    #     print(frame.path)
    dialog = frame.openDialog
    if dialog is None:
        frame.openDialog = dialog = OpenDialog(frame)
    dialog.Show(True)

class OpenDialog(wx.Dialog):
    def __init__(self, frame):
        self.frame = frame
        self.path = None
        self.args = None
        pos = frame.GetPosition()
        wx.Dialog.__init__(self, frame, -1, "Open", pos, \
                           wx.DefaultSize, wx.DEFAULT_DIALOG_STYLE)

        self.sizerV = sizerV = wx.BoxSizer(wx.VERTICAL)
        
        btn = wx.Button(self, wx.ID_ANY, label="Open DXF")
        btn.Bind(wx.EVT_BUTTON, self.onOpenFile)
        sizerV.Add(btn, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 3)

        self.fileName = txt = wx.TextCtrl(self, wx.ID_ANY, "", \
                                          style=wx.TE_READONLY)
        sizerV.Add(txt, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 3)
        
        sizerG = wx.FlexGridSizer(cols=2, rows=0, vgap=0, hgap=0)

        # self.fields = ( \
        #     ("cReference", None, 'c', self.setupRef), \
        # )
        # fieldList(self, sizerG, self.fields)

        self.refLayer = addComboBox(self, sizerG, "Ref Layer", \
                                         None, self.setupLayers)
        self.refLayer.Bind(wx.EVT_COMBOBOX, self.onRefLayer)

        self.materialLayer = addComboBox(self, sizerG, "Material Layer", \
                                         None, self.setupLayers)
        self.materialLayer.Bind(wx.EVT_COMBOBOX, self.onMaterialLayer)

        self.comboLoc = addComboBox(self, sizerG, "Ref Loc", None, \
                                    self.setupRef)
        self.comboLoc.Bind(wx.EVT_COMBOBOX, self.onCombo)

        self.comboType = addComboBox(self, sizerG, "Ref Type", None, \
                                 self.setupRefType)
        self.comboType.Bind(wx.EVT_COMBOBOX, self.onComboType)

        sizerV.Add(sizerG, flag=wx.LEFT|wx.ALL, border=2)

        sizerH = wx.BoxSizer(wx.HORIZONTAL)

        addDialogButton(self, sizerH, wx.ID_OK, self.onDialogOk)

        addDialogButton(self, sizerH, wx.ID_CANCEL, self.onDialogCancel)

        sizerV.Add(sizerH, 0, wx.ALIGN_RIGHT)

        self.SetSizer(sizerV)
        self.sizerV.Fit(self)
        size = self.GetSize()
        x = pos.x - size.x
        if x < 0:
            x = pos.x
        self.SetPosition(wx.Point(x, pos.y))
        self.Show(True)

    def onOpenFile(self, e):
        frame = self.frame
        frame.dirName = os.getcwd()
        dlg = wx.FileDialog(frame, "Choose a file", frame.dirName,
                            "", "*.dxf", wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            frame = self.frame
            frame.filename = dlg.GetFilename()
            self.fileName.SetValue(frame.filename)
            frame.dirname = dlg.GetDirectory()
            self.path = frame.path = os.path.join(frame.dirname, frame.filename)
            print(frame.path)

            self.args = [self.path, ]
            cfg = self.frame.cfg
            cfg.orientation = int(self.comboLoc.GetValue())
            cfg.ref = int(self.comboType.GetValue())
            cfg.readDxf(self.args)
            self.setupComboLayers()
            self.frame.bitmapPanel.setup(cfg.dxfInput)

    @staticmethod
    def setupRef():
        references = \
        (
            (O_UPPER_LEFT, "Upper Left"),
            (O_LOWER_LEFT, "Lower Left"),
            (O_UPPER_RIGHT, "Upper Right"),
            (O_LOWER_RIGHT, "Lower Right"),
            (O_CENTER, "Center"),
            (O_POINT, "Point"),
        )
        choiceList = []
        indexList = []
        sel = ["" for i in range(O_MAX)]
        for (index, txt) in references:
            indexList.append(index)
            choiceList.append(txt)
        return (indexList, choiceList, "")

    def onCombo(self, e):
        orientation = e.EventObject.GetSelection()
        cfg = self.frame.cfg
        cfg.orientation = orientation
        dxfInput = cfg.dxfInput
        if dxfInput is not None:
            if self.args is not None:
                cfg.readDxf(self.args)
                self.frame.bitmapPanel.setup(dxfInput)
                print(orientation)

    @staticmethod
    def setupRefType():
        references = \
        (
            (REF_OVERALL, "Overall"),
            (REF_MATERIAL, "Material"),
            (REF_FIXTURE, "Fixture"),
        )
        choiceList = []
        indexList = []
        sel = ["" for i in range(O_MAX)]
        for (index, txt) in references:
            indexList.append(index)
            choiceList.append(txt)
        return (indexList, choiceList, "")

    def onComboType(self, e):
        ref = e.EventObject.GetSelection()
        cfg = self.frame.cfg
        cfg.ref = ref
        dxfInput = cfg.dxfInput
        if dxfInput is not None:
            if self.args is not None:
                cfg.readDxf(self.args)
                self.frame.bitmapPanel.setup(dxfInput)
                print(ref)

    def setupLayers(self):
        dxfInput = self.frame.cfg.dxfInput
        if dxfInput is not None:
            dxfLayers = dxfInput.dxfLayers
            choiceList = []
            indexList = []
            if dxfLayers is not None:
                for n, key in enumerate(sorted(dxfLayers)):
                    indexList.append(n)
                    choiceList.append(key)
                return (indexList, choiceList, "")
        return (None, None, "")

    def setupComboLayers(self):
        (indexList, choiceList, txt) = self.setupLayers()
        refCombo = self.refLayer
        refCombo.indexList = indexList
        refCombo.choiceList = choiceList
        refCombo.Set(choiceList)
        refCombo.SetSel("fixture")
        materialCombo = self.materialLayer
        materialCombo.indexList = indexList
        materialCombo.choiceList = choiceList
        materialCombo.Set(choiceList)
        materialCombo.SetSel("material")

    def onRefLayer(self, e):
        pass

    def onMaterialLayer(self, e):
        pass

    def onDialogOk(self, e):
        cfg = self.frame.cfg
        cfg.orientation = int(self.comboLoc.GetValue())
        cfg.ref = int(self.comboType.GetValue())
        if self.args is not None:
            cfg.readDxf(self.args)
            self.frame.bitmapPanel.setup(cfg.dxfInput)
        self.Show(False)

    def onDialogCancel(self, e):
        self.Show(False)

class MainFrame(wx.Frame):
    def __init__(self, parent, cfg, title):
        self.cfg = cfg
        self.dirName = None
        super(MainFrame, self).__init__(parent, title = title, \
                                        style=wx.DEFAULT_FRAME_STYLE)

        self.SetSize((400, 300))
        self.Bind(wx.EVT_CLOSE, self.onClose)
        menuSetup(self)
        self.InitUI()

    def onClose(self, event):
        self.Destroy()

    def onOpen(self, e):
        onOpen(self, e)

    def InitUI(self):
        mainPanel = wx.Panel(self)
        self.mainSizer = mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainPanel.SetSizer(mainSizer)

        splitWindow = \
            wx.SplitterWindow(mainPanel, wx.ID_ANY, \
                              style=wx.SP_3D | wx.SP_BORDER | \
                              wx.SP_LIVE_UPDATE | wx.SP_THIN_SASH)
        splitWindow.SetBackgroundColour('Light Blue')
        splitWindow.SetMinimumPaneSize(20)
        mainSizer.Add(splitWindow, 1, wx.ALL | wx.EXPAND, 0)

        leftPanel = wx.Panel(splitWindow, wx.ID_ANY)
        leftSizer = wx.BoxSizer(wx.VERTICAL)
        leftPanel.SetSizer(leftSizer)
        
        # left top

        panelSize = wx.Size(200, 200)
        
        self.leftPanel1 = leftPanel1 = wx.Panel(leftPanel, wx.ID_ANY, \
                                                style=wx.BORDER_SIMPLE)
        # leftPanel1.SetMinClientSize(panelSize)
        leftPanel1.SetBackgroundColour('Light Gray')
        leftSizer1 = wx.BoxSizer(wx.VERTICAL)
        leftPanel1.SetSizer(leftSizer1)

        txt = wx.StaticText(leftPanel1, wx.ID_ANY, "Panel 1") #, \
#                                style=wx.ALIGN_CENTER_HORIZONTAL)
        leftSizer1.Add(txt, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 2)

        leftSizer.Add(leftPanel1, wx.ALL | wx.EXPAND, 2)

        # left middle
        
        self.leftPanel2 = leftPanel2 = wx.Panel(leftPanel, wx.ID_ANY, \
                                                style=wx.BORDER_SIMPLE)
        # leftPanel2.SetMinClientSize(panelSize)
        leftSizer2 = wx.BoxSizer(wx.VERTICAL)
        leftPanel2.SetSizer(leftSizer2)

        txt = wx.StaticText(leftPanel2, wx.ID_ANY, "Panel 2", \
                                style=wx.ALIGN_CENTER_HORIZONTAL)
        leftSizer2.Add(txt, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 2)

        leftSizer.Add(leftPanel2, wx.ALL | wx.EXPAND, 2)
        
        # left bottom
        
        self.leftPanel3 = leftPanel3 = wx.Panel(leftPanel, wx.ID_ANY, \
                                                style=wx.BORDER_SIMPLE)
        # leftPanel3.SetMinClientSize(panelSize)
        leftSizer3 = wx.BoxSizer(wx.VERTICAL)
        leftPanel3.SetSizer(leftSizer3)

        txt = wx.StaticText(leftPanel3, wx.ID_ANY, "Panel 3", \
                                style=wx.ALIGN_CENTER_HORIZONTAL)
        leftSizer3.Add(txt, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 2)

        leftSizer.Add(leftPanel3, wx.ALL | wx.EXPAND, 2)

        # right
        
        self.rightPanel = rightPanel = BitmapPanel(splitWindow)
        rightSizer = wx.BoxSizer(wx.VERTICAL)
        rightPanel.SetSizer(rightSizer)
        # rightPanel.SetMinClientSize(wx.Size(800, 600))

        splitWindow.SplitVertically(leftPanel, rightPanel)

        # mainSizer.Fit(self)
        self.Layout()
                                     
    def setPanelSize(self):
        default = wx.Size(-1, -1)
        self.leftPanel1.SetMinClientSize(default)
        self.leftPanel2.SetMinClientSize(default)
        self.leftPanel3.SetMinClientSize(default)
        self.rightPanel.SetMinClientSize(default)

     # def onOpen(self, e):
    #     self.dirName = os.getcwd()
    #     dlg = wx.FileDialog(self, "Choose a file", self.dirName,
    #                         "", "*.dxf", wx.FD_OPEN)
    #     if dlg.ShowModal() == wx.ID_OK:
    #         self.filename = dlg.GetFilename()
    #         self.dirname = dlg.GetDirectory()
    #         self.path = os.path.join(self.dirname, self.filename)
    #         print(self.path)
    #         args = [self.path, ]
    #         cfg = self.cfg
    #         cfg.orientation = O_LOWER_LEFT
    #         cfg.readDxf(args)
    #         self.rightPanel.setup(cfg.dxfInput)

class MainFrame1(wx.Frame):
    # def __init__(self, *args, **kwds):
    #     kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
    #     wx.Frame.__init__(self, *args, **kwds)
    def __init__(self, parent, cfg, title):
        self.cfg = cfg
        self.dirName = None
        super(MainFrame1, self).__init__(parent, title = title, \
                                         style=wx.DEFAULT_FRAME_STYLE)

        self.SetSize((800, 600))

        menuSetup(self)

        self.mainPanel = wx.Panel(self, wx.ID_ANY)
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        self.mainPanel.SetSizer(mainSizer)

        self.splitWindow = \
            wx.SplitterWindow(self.mainPanel, wx.ID_ANY, \
                              style=wx.SP_3D | wx.SP_BORDER | \
                              wx.SP_LIVE_UPDATE | wx.SP_NOBORDER | \
                              wx.SP_THIN_SASH)
        self.splitWindow.SetBackgroundColour("Light Gray")
        self.splitWindow.SetForegroundColour(wx.Colour(255, 0, 0))
        self.splitWindow.SetMinimumPaneSize(20)
        mainSizer.Add(self.splitWindow, 1, wx.ALL | wx.EXPAND, 0)

        if False:
            self.leftPanel = wx.Panel(self.splitWindow, wx.ID_ANY)
            leftSizer = wx.BoxSizer(wx.VERTICAL)
            self.leftPanel.SetSizer(leftSizer)
        else:
            self.leftPanel = \
                MultiSplitterWindow(self.splitWindow, \
                                    style=wx.SP_LIVE_UPDATE)
            self.leftPanel.SetOrientation(wx.VERTICAL)

        # top

        self.leftPanel1 = wx.Panel(self.leftPanel, wx.ID_ANY, \
                                style=wx.BORDER_SIMPLE)
        leftSizer1 = wx.BoxSizer(wx.VERTICAL)
        self.leftPanel1.SetSizer(leftSizer1)

        label_1 = wx.StaticText(self.leftPanel1, wx.ID_ANY, "Panel 1", \
                                style=wx.ALIGN_CENTER_HORIZONTAL)
        leftSizer1.Add(label_1, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 2)

        if False:
            leftSizer.Add(self.leftPanel1, 1, wx.ALL | wx.EXPAND, 2)
        else:
            self.leftPanel.AppendWindow(self.leftPanel1)

        # middle

        self.leftPanel2 = wx.Panel(self.leftPanel, wx.ID_ANY, \
                                style=wx.BORDER_SIMPLE)
        leftSizer2 = wx.BoxSizer(wx.VERTICAL)
        self.leftPanel2.SetSizer(leftSizer2)

        label_2 = wx.StaticText(self.leftPanel2, wx.ID_ANY, "Panel 2", \
                                style=wx.ALIGN_CENTER_HORIZONTAL)
        leftSizer2.Add(label_2, 0,  wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 2)

        if False:
            leftSizer.Add(self.leftPanel2, 1, wx.ALL | wx.EXPAND, 2)
        else:
            self.leftPanel.AppendWindow(self.leftPanel2)

        # bottom

        self.leftPanel3 = wx.Panel(self.leftPanel, wx.ID_ANY, \
                                style=wx.BORDER_SIMPLE)
        leftSizer3 = wx.BoxSizer(wx.VERTICAL)
        self.leftPanel3.SetSizer(leftSizer3)
        label_3 = wx.StaticText(self.leftPanel3, wx.ID_ANY, "Panel 3", \
                                style=wx.ALIGN_CENTER_HORIZONTAL)
        leftSizer3.Add(label_3, 0,  wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 2)

        if False:
            leftSizer.Add(self.leftPanel3, 1, wx.ALL | wx.EXPAND, 2)
        else:
            self.leftPanel.AppendWindow(self.leftPanel3)

        # right

        self.rightPanel = wx.Panel(self.splitWindow, wx.ID_ANY)
        rightSizer = wx.BoxSizer(wx.VERTICAL)
        self.rightPanel.SetSizer(rightSizer)

        # bitmap panel

        # self.bitmapPanel = wx.Panel(self.rightPanel, wx.ID_ANY)
        self.bitmapPanel = BitmapPanel(self, self.rightPanel)
        rightSizer.Add(self.bitmapPanel, 100, wx.EXPAND, 0)

        statusSizer = wx.BoxSizer(wx.HORIZONTAL)
        rightSizer.Add(statusSizer, 1, wx.EXPAND, 0)

        # status label

        statusLabel = wx.StaticText(self.rightPanel, wx.ID_ANY, "Status")
        statusSizer.Add(statusLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 3)

        # status text

        self.statusText = wx.TextCtrl(self.rightPanel, wx.ID_ANY, "xx")
        self.statusText.SetMaxSize((-1, -1))
        statusSizer.Add(self.statusText, 100, wx.ALL, 3)

        self.splitWindow.SplitVertically(self.leftPanel, self.rightPanel)

        self.Layout()

    def onOpen(self, e):
        onOpen(self, e)

# class PlotFrame(wx.Frame):
#     def __init__(self, mainFrame, title, parent=None):
#         wx.Frame.__init__(self, parent=parent, title=title)
#         self.Bind(wx.EVT_CLOSE, self.onClose)
#         self.mainFrame = mainFrame
#         self.cfg = mainFrame.cfg
#         # self.Bind(wx.EVT_PAINT, self.onPaint)
#         # self.Bind(wx.EVT_LEFT_UP, self.onMouseEvent)
#         self.setPos(mainFrame)

#         # import wx.lib.colourdb as wb
#         # colorList = wb.getColourList()
#         # for c in colorList:
#         #     print(c)
#         color = wx.Colour('Dark Green')
#         print(color)

#         sizerV = wx.BoxSizer(wx.VERTICAL)
#         # self.staticBitmap = b = wx.StaticBitmap(self, style=wx.CLIP_CHILDREN)
#         self.bitmapPanel = b = BitmapPanel(self)
#         sizerV.Add(b, 1, wx.EXPAND)
        
#         self.SetSizer(sizerV)
#         self.Show()

#     def setPos(self, mainFrame):
#         mainPos = mainFrame.GetPosition()
#         mainSize = mainFrame.GetSize()
#         self.SetPosition(wx.Point(mainPos.x + mainSize.width, mainPos.y))

#     def onClose(self, event):
#         self.mainFrame.Destroy()
#         self.Destroy()

class BitmapPanel(wx.Panel):
    def __init__(self, mainFrame, parent=None):
        wx.Panel.__init__(self, parent, id=wx.ID_ANY)
        self.parent = parent
        self.mainFrame = mainFrame
        self.Bind(wx.EVT_PAINT, self.onPaint)
        self.objects = None
        self.bitmap = None
        self.selected = None
        self.endPoint = None
        self.lastEndPoint = 2
    
        self.Bind(wx.EVT_SIZE,self.onSize)

        self.Bind(wx.EVT_LEFT_UP, self.onMouseEvent)
        self.Bind(wx.EVT_MOUSEWHEEL, self.onMouseWheel)
        self.Bind(wx.EVT_MOTION, self.onMouseMotion)
        self.Bind(wx.EVT_LEFT_DOWN, self.onLeftDown)

        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.test()
        self.render()

    def onPaint(self, e):
        if self.bitmap is not None:
            print("paint")
            dc = wx.BufferedPaintDC(self)
            # dc.SetBackground(wx.Brush("white"))
            # dc.Clear()
            dc.DrawBitmap(self.bitmap, 0,0)
            self.bitmap = None

    def onSize(self, e):
        size = self.GetMinSize()
        print("size min %d %d" % (size.x, size.y))
        if self.objects is None:
            self.test()
        else:
            self.setup()

    def test(self):
        self.minX = 0
        self.minY = 0
        self.maxX = 3
        self.maxY = 4
        
        p0 = Pt(self.minX, self.minY)
        p1 = Pt(self.maxX, self.minY)
        p2 = Pt(self.maxX, self.maxY)
        p3 = Pt(self.minX, self.maxY)

        self.objects = objects = []
        objects.append(Line(p0, p1))
        objects.append(Line(p1, p2))
        objects.append(Line(p2, p3))
        objects.append(Line(p3, p0))
        self.setup()

    def setup(self, dxf=None):
        if dxf is not None:
            self.minX = dxf.xMin
            self.maxX = dxf.xMax
            self.minY = dxf.yMin
            self.maxY = dxf.yMax
            print("minX %7.3f minY %7.3f maxX %7.3f maxY %7.3f" % \
                  (self.minX, self.minY, self.maxX, self.maxY))
            self.objects = dxf.getObjects()

        self.marginX = 2
        self.marginY = 2

        self.rangeX = rangeX = self.maxX - self.minX
        self.rangeY = rangeY = self.maxY - self.minY
        print("rangeX %7.3f rangeY %7.3f" % (rangeX, rangeY))

        size = self.GetClientSize()
        print("client size", size.x, size.y)
        sizeX = size.x - 2 * self.marginX
        sizeY = size.y - 2 * self.marginY

        scaleX = sizeX / rangeX
        scaleY = sizeY / rangeY
        scale = min(scaleX, scaleY)
        self.scale = scale
        self.scaleInc = scale / 10

        self.offsetX = int((size.x - rangeX * scale) / 2 - self.minX * scale)
        self.offsetY = int((size.y + rangeY * scale) / 2 + self.minY * scale)
        self.render()

    def calcPos(self, p):
        (x, y) = p
        xOut = self.offsetX + x * self.scale
        yOut = self.offsetY - y * self.scale
        # print(x, y, xOut, yOut)
        return (xOut, yOut)

    def onMouseEvent(self, e):
         x = e.GetX()
         print(x)
         # if not self.zoom:
         #     self.zoom = True
         #     self.offset = x > self.tc.xBase
         # else:
         #     self.zoom = False
         #     self.offset = False
         # self.tc.setZoomOffset(self.zoom, self.offset)
         # self.Refresh()
         self.render()

    def onMouseWheel(self, e):
        x = e.GetX()
        y = e.GetY()
        rot = e.GetWheelRotation()
        locX = (x - self.offsetX) / self.scale
        # locX * scale = x - offsetX
        # locX * scale - x = -offsetX
        # -locX * scale + x = offsetX
        # offsetX = x - locX * scale
        locY = -(y - self.offsetY) / self.scale
        # locY / scale = -(y - offsetY)
        # locY / scale = -y + offsetY
        # locY * scale + y = offsetY
        print("x %4d y %4d locX %7.3f lecY %7.3f, rot %4d" %\
              (int(x), int(y), locX, locY, int(rot)))
        print("offsetX %3d, offsetY %3d" % (self.offsetX, self.offsetY))
        if rot > 0:
            self.scale += self.scaleInc
        else:
            if self.scale > (self.scaleInc + 5):
                self.scale -= self.scaleInc
        self.offsetX = int(x - locX * self.scale)
        self.offsetY = int(locY * self.scale + y)
        print("scale %7.2f offsetX %3d, offsetY %3d" % \
              (self.scale, self.offsetX, self.offsetY))
        self.render()

    def onLeftDown(self, e):
        self.lastX = e.GetX()
        self.lastY = e.GetY()
        print(self.lastX, self.lastY)

    def onMouseMotion(self, e):
        # if e.ButtonDown(wx.MOUSE_BTN_LEFT):
        x = e.GetX()
        y = e.GetY()
        if e.LeftIsDown():
            deltaX = x - self.lastX
            deltaY = y - self.lastY
            self.offsetX += deltaX
            self.offsetY += deltaY
            self.lastX = x
            self.lastY = y
            self.render()
            print(x, y, deltaX, deltaY)
        else:
            locX = (x - self.offsetX) / self.scale
            locY = -(y - self.offsetY) / self.scale
            status = "(%7.3f %7.3f)" % (locX, locY)

            p = Pt(locX, locY)
            if self.selected is None:
                for l in self.objects:
                    dist = l.pointDistance(p)
                    if dist is not None:
                        if abs(dist) < .1:
                            self.selected = l
                            print("found")
                            # if l.lType == LINE:
                            if True:
                                d0 = xyDist(p, l.p0)
                                d1 = xyDist(p, l.p1)
                                if d0 < d1:
                                    self.endPoint = l.p0
                                    n = 0
                                else:
                                    self.endPoint = l.p1
                                    n = 1
                                self.lastEndPoint = n
                                print("endPoint n %d %7.3f %7.3f" % \
                                      (n, self.endPoint.x, self.endPoint.y))
                            self.render()
                            break
            else:
                l = self.selected
                dist = l.pointDistance(p)
                if (dist is None) or (abs(dist) > .1):
                    self.selected = None
                    self.endPoint = None
                    self.lastEndPoint = 2
                    self.render()
                else:
                    # if l.lType == LINE:
                    if True:
                        d0 = xyDist(p, l.p0)
                        d1 = xyDist(p, l.p1)
                        # print("d0 %7.3f d1 %7.3f" % (d0, d1))
                        if d0 < d1:
                            endPoint = l.p0
                            n = 0
                        else:
                            endPoint = l.p1
                            n = 1
                        if self.lastEndPoint != n:
                            self.endPoint = endPoint
                            self.lastEndPoint = n
                            print("endPoint %d %7.3f %7.3f" % \
                                  (n, endPoint.x, endPoint.y))
                            self.render()
            if self.selected is not None:
                if self.endPoint is not None:
                    status += " pt (%7.3f %7.3f)" % \
                        (self.endPoint.x, self.endPoint.y)
                l = self.selected
                if l.lType == LINE:
                    status += " len %7.3f" % (l.length)
                elif l.lType == ARC:
                    status += " c (%7.3f %7.3f) r %7.3f" % (l.c.x, l.c.y, l.r)
            self.mainFrame.statusText.SetValue(status)

    def render(self):
        size = self.GetClientSize()
        w, h = size.x, size.y
        print(w, h)
        if w <= 0 or h <= 0:
            return

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = cairo.Context(surface)
        ctx.set_source_rgb(1, 1, 1)  # Solid color
        ctx.paint()

        ctx.set_font_size(10)
        ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, \
                             cairo.FONT_WEIGHT_NORMAL)

        ctx.set_source_rgb(0, 0, 0)  # Solid color
        line = ctx.line_to
        for l in self.objects:
            if l.lType == LINE:
                (x, y) = self.calcPos(l.p0)
                ctx.move_to(x, y)
                (x, y) = self.calcPos(l.p1)
                line(x, y)
            elif l.lType == ARC:
                # (x, y) = self.calcPos(l.p0)
                # ctx.move_to(x, y)
                (xc, yc) = self.calcPos(l.c)
                ctx.new_sub_path()
                ctx.arc(xc, yc, l.r * self.scale, \
                        radians(360 - l.a1), radians(360 - l.a0))

        ctx.set_line_width(1)
        ctx.stroke()

        if self.selected is not None:
            l = self.selected
            if l.lType == LINE:
                (x, y) = self.calcPos(l.p0)
                ctx.move_to(x, y)
                (x, y) = self.calcPos(l.p1)
                line(x, y)
            elif l.lType == ARC:
                l.prt()
                ctx.new_sub_path()
                (xc, yc) = self.calcPos(l.c)
                ctx.arc(xc, yc, l.r * self.scale, \
                        radians(360 - l.a1), radians(360 - l.a0))
                (x, y) = self.calcPos(l.c)
                ctx.move_to(x - 5, y)
                line(x + 5, y)
                ctx.move_to(x, y + 5)
                line(x, y - 5)

            if self.endPoint is not None:
                (x, y) = self.calcPos(self.endPoint)
                ctx.new_sub_path()
                ctx.arc(x, y, 5, 0, 2 * pi)
                
            ctx.set_source_rgb(1, 0, 0)  # Solid color
            ctx.set_line_width(1)
            ctx.stroke()

        ctx.move_to(self.offsetX - 5, self.offsetY + 5)
        line(self.offsetX + 5, self.offsetY - 5)

        ctx.move_to(self.offsetX - 5, self.offsetY - 5)
        line(self.offsetX + 5, self.offsetY + 5)
        ctx.set_source_rgb(0, 0, 1)  # Solid color
        ctx.set_line_width(1)
        ctx.stroke()


        ctx.set_source_rgb(1, 0, 0)  # Solid color
        ctx.move_to(2, h / 2)
        txt = "Testing cairo"
        ctx.show_text(txt)

        self.bitmap = wxcairo.BitmapFromImageSurface(surface)
        self.Refresh()
        
