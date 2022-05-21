import sys
import os
import struct
import ndspy.rom
import ndspy.fnt
import ndspy.color
import ndspy.graphics2D
#import ndspy.extras.textureEncoding
import threading
from enum import Enum 
from enum import IntEnum

from PyQt5 import Qt, QtCore, QtGui, QtWidgets
from ndspy import Processor
from PIL import Image

class NodeTypes(Enum):
    rom = 1
    filesystem = 2
    directory = 3
    arm9directory = 4
    arm7directory = 5
    main9 = 6
    main7 = 7
    overlay9 = 8
    overlay7 = 9
    file = 10

class NodeData(IntEnum):
    nodeType = 0
    size = 1
    path = 3
    fileID = 4
    ramAddress = 5
    compressedSize = 6
    folderFirstID = 7 
    romName = 8
    ramSize = 9
    nodeName = 10
    overlayID = 11

class FilesystemEditorWidget(QtWidgets.QWidget):

    def __init__(self, parent):
        super(FilesystemEditorWidget, self).__init__(parent)
        
        self.romEdited = False
        self.ROM = None
        self.currentNode = None
        self.arm7File = None
        self.arm9File = None
        self.overlays7 = None
        self.overlays9 = None

        self.overlays9Thread = threading.Thread(target=self.LoadOverlay9Files)
        self.overlays7Thread = threading.Thread(target=self.LoadOverlay7Files)
        self.main9Thread = threading.Thread(target=self.LoadMain9File)
        self.main7Thread = threading.Thread(target=self.LoadMain7File)

        self.progress = QtWidgets.QStatusBar()
        self.progress.maximumHeight = 20

        self.tabs = QtWidgets.QTabWidget()
        self.tab1 = QtWidgets.QWidget()
        self.tab2 = QtWidgets.QWidget()
        self.tabs.addTab(self.tab1,'ROM Filesystem')
        self.tabs.addTab(self.tab2,'ROM Other')

        # Tab 1

        self.extractButton = QtWidgets.QPushButton('Extract...', self)
        self.extractButton.clicked.connect(self.HandleExtract)

        self.openButton = QtWidgets.QPushButton('Open...', self)

        self.renameButton = QtWidgets.QPushButton('Rename...', self)
        self.renameButton.clicked.connect(self.HandleRename)

        self.addButton = QtWidgets.QPushButton('Add...', self)
        self.addButton.clicked.connect(self.CreateAddMenu)

        self.removeButton = QtWidgets.QPushButton('Remove...', self)
        self.removeButton.clicked.connect(self.HandleRemove)

        self.replaceButton = QtWidgets.QPushButton('Replace...', self)
        self.replaceButton.clicked.connect(self.HandleReplace)

        self.selectedFileText = QtWidgets.QLabel('---------', self)
        self.selectedFileText.setFont(QtGui.QFont('Times',weight=QtGui.QFont.Bold))
        self.selectedFileDetails = QtWidgets.QLabel('---------', self)

        self.romFilesystemTreeView = QtWidgets.QTreeWidget()
        self.romFilesystemTreeView.setHeaderHidden(True)
        self.romFilesystemTreeView.setColumnCount(1)
        self.romFilesystemTreeView.setHeaderHidden(True)
        self.romFilesystemTreeView.setIndentation(16)
        self.romFilesystemTreeView.currentItemChanged.connect(self.HandleItemChange)
        self.romFilesystemTreeView.itemActivated.connect(self.HandleItemActivated)

        self.romFilesystemTreeView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.romFilesystemTreeView.customContextMenuRequested.connect(self.CreateContextMenu)

        detailsLayout = QtWidgets.QGridLayout()
        detailsLayout.addWidget(self.selectedFileText, 1, 1)
        detailsLayout.addWidget(self.selectedFileDetails, 2, 1)

        buttonsLayout = QtWidgets.QGridLayout() 
        buttonsLayout.addWidget(self.openButton, 1, 1)
        buttonsLayout.addWidget(self.extractButton, 1, 2)
        buttonsLayout.addWidget(self.replaceButton, 1, 3)
        buttonsLayout.addWidget(self.renameButton, 2, 1)
        buttonsLayout.addWidget(self.addButton, 2, 2)
        buttonsLayout.addWidget(self.removeButton, 2, 3)
        
        tab1layout = QtWidgets.QGridLayout()
        tab1layout.addWidget(self.romFilesystemTreeView, 1, 0)
        tab1layout.addLayout(detailsLayout, 2, 0)
        tab1layout.addLayout(buttonsLayout, 3, 0)
        self.tab1.setLayout(tab1layout)

        # Tab 2

        tab2Layout = QtWidgets.QGridLayout()
        iconbuttonlayout = QtWidgets.QGridLayout()
        generalinfolayout = QtWidgets.QGridLayout()

        tab2Layout.addLayout(iconbuttonlayout, 0, 1)
        tab2Layout.addLayout(generalinfolayout, 0, 2)
        
        self.bannerIconLabel = QtWidgets.QLabel(self)
        pixmapBlank = QtGui.QPixmap(64, 64)
        pixmapBlank.fill(QtGui.QColor('transparent'))
        self.bannerIconLabel.setPixmap(pixmapBlank)

        self.extractIconButton = QtWidgets.QPushButton('Extract icon...', self)
        self.extractIconButton.clicked.connect(self.HandleExtractIcon)
        self.importIconButton = QtWidgets.QPushButton('Import icon...', self)
        self.importIconButton.clicked.connect(self.HandleImportIcon)

        tab2Layout.addWidget(self.bannerIconLabel, 0, 0)
        iconbuttonlayout.addWidget(self.extractIconButton, 0, 0)
        iconbuttonlayout.addWidget(self.importIconButton, 1, 0)

        self.lJapanese = QtWidgets.QLabel('Japanese:',self)
        self.lEnglish = QtWidgets.QLabel('English:',self)
        self.lFrench = QtWidgets.QLabel('French:',self)
        self.lGerman = QtWidgets.QLabel('German:',self)
        self.lItalian = QtWidgets.QLabel('Italian:',self)
        self.lSpanish = QtWidgets.QLabel('Spanish:',self)

        self.tJapanese = QtWidgets.QTextEdit()
        self.tEnglish = QtWidgets.QTextEdit()
        self.tFrench = QtWidgets.QTextEdit()
        self.tGerman = QtWidgets.QTextEdit()
        self.tItalian = QtWidgets.QTextEdit()
        self.tSpanish = QtWidgets.QTextEdit()

        tab2Layout.addWidget(self.lJapanese, 1, 0)
        tab2Layout.addWidget(self.lEnglish, 2, 0)
        tab2Layout.addWidget(self.lFrench, 3, 0)
        tab2Layout.addWidget(self.lGerman, 4, 0)
        tab2Layout.addWidget(self.lItalian, 5, 0)
        tab2Layout.addWidget(self.lSpanish, 6, 0)

        tab2Layout.addWidget(self.tJapanese, 1, 1)
        tab2Layout.addWidget(self.tEnglish, 2, 1)
        tab2Layout.addWidget(self.tFrench, 3, 1)
        tab2Layout.addWidget(self.tGerman, 4, 1)
        tab2Layout.addWidget(self.tItalian, 5, 1)
        tab2Layout.addWidget(self.tSpanish, 6, 1)

        self.tab2.setLayout(tab2Layout)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tabs)
        layout.addWidget(self.progress)
        self.setLayout(layout)

    def SetProgressText(self, text):
        self.progress.showMessage(text)

    def LoadBannerAndTitles(self):
        (_version, _CRC16, _CRC16_2, _CRC16_3, _CRC16_4, _reserved, 
        iconBitmap, iconPalette,
        japanese, english, french, german, italian, spanish) = struct.unpack_from('<5h22s512s32s256s256s256s256s256s256s', self.ROM.iconBanner, 0)

        self.tJapanese.setText(str(japanese, 'utf-8'))
        self.tEnglish.setText(str(english, 'utf-8'))
        self.tFrench.setText(str(french, 'utf-8'))
        self.tGerman.setText(str(german, 'utf-8'))
        self.tItalian.setText(str(italian, 'utf-8'))
        self.tSpanish.setText(str(spanish, 'utf-8'))

        #colorInts = struct.unpack('<%dh' % 16, iconPalette)
        #colors = []

        #for i in range(len(iconPalette) // 2):
        #    tup = ndspy.color.unpack255(colorInts[i])

        #    if (i == 0):
        #        colors.append((tup[0], tup[1], tup[2], 0))
        #    else:
        #        colors.append((tup[0], tup[1], tup[2], 255))

        #tiles = ndspy.graphics2D.loadImageTiles(iconBitmap, 4)
        #data = ndspy.graphics2D.renderImageTiles(tiles, colors, 0, 4).convert('RGBA').tobytes('raw', 'RGBA')
        #self.bannerIcon = QtGui.QImage(data, 32, 32, QtGui.QImage.Format_RGBA8888)
        #self.bannerIconLabel.setPixmap(QtGui.QPixmap.fromImage(self.bannerIcon).scaled(64,64))


    def LoadROM(self, fileName):
        self.SetProgressText('Loading the ROM...')
        self.ROM = ndspy.rom.NintendoDSRom.fromFile(fileName)
        self.romFileName = fileName
        self.romEdited = False

        self.romFilesystemTreeView.clear()
        self.romTree = QtWidgets.QTreeWidgetItem()
        romName = self.ROM.name.decode('utf-8')
        self.romTree.setText(0, romName)
        self.romTree.setData(NodeData.nodeType, QtCore.Qt.UserRole, NodeTypes.rom)
        self.romTree.setData(NodeData.folderFirstID, QtCore.Qt.UserRole, 0)
        self.romTree.setData(NodeData.path, QtCore.Qt.UserRole, '') 
        self.romFilesystemTreeView.addTopLevelItem(self.romTree)

        root = QtWidgets.QTreeWidgetItem()
        root.setText(0, 'Filesystem')
        root.setData(NodeData.nodeType, QtCore.Qt.UserRole, NodeTypes.filesystem)
        root.setData(NodeData.folderFirstID, QtCore.Qt.UserRole, self.ROM.filenames.firstID)
        root.setData(NodeData.path, QtCore.Qt.UserRole, '') 
        self.romTree.addChild(root)

        self.ReloadCode(True, Processor.ARM9)
        self.ReloadCode(True, Processor.ARM7)
        self.ReloadCode(False, Processor.ARM9)
        self.ReloadCode(False, Processor.ARM7)

        self.LoadROMDir(self.ROM.filenames, '', root)
        self.LoadBannerAndTitles()
        self.LoadOverlays(self.romTree)
     
        self.romTree.setExpanded(True)
        self.SetProgressText('Done.')


    def ROMChanged(self):
        self.romEdited = True


    def Save(self):
        print(len(self.ROM.files))
        self.ROM.saveToFile(self.romFileName)
        self.romEdited = False


    def MakeOverlayNode(self, id, overlay, type):
        ov = QtWidgets.QTreeWidgetItem()
        ov.setText(0, 'Overlay ' + str(id))
        ov.setData(NodeData.nodeType, QtCore.Qt.UserRole, type)
        ov.setData(NodeData.overlayID, QtCore.Qt.UserRole, id)
        ov.setData(NodeData.fileID, QtCore.Qt.UserRole, overlay.fileID)
        ov.setData(NodeData.ramAddress, QtCore.Qt.UserRole, overlay.ramAddress)
        ov.setData(NodeData.compressedSize, QtCore.Qt.UserRole, overlay.compressedSize)
        ov.setData(NodeData.ramSize, QtCore.Qt.UserRole, overlay.ramSize)
        return ov


    def LoadOverlays(self, node):
        self.SetProgressText('Loading the overlays...')

        arm9OvsNode = QtWidgets.QTreeWidgetItem()
        arm9OvsNode.setText(0, 'ARM9')
        arm9OvsNode.setData(NodeData.nodeType, QtCore.Qt.UserRole, NodeTypes.arm9directory)
        arm9OvsNode.setData(NodeData.nodeName, QtCore.Qt.UserRole, 'ARM9')
        node.addChild(arm9OvsNode)
    
        arm7OvsNode = QtWidgets.QTreeWidgetItem()
        arm7OvsNode.setText(0, 'ARM7')
        arm7OvsNode.setData(NodeData.nodeType, QtCore.Qt.UserRole, NodeTypes.arm7directory)
        arm7OvsNode.setData(NodeData.nodeName, QtCore.Qt.UserRole, 'ARM7')
        node.addChild(arm7OvsNode)

        self.WaitUntilCodeLoadThreadFinished(True, Processor.ARM9)
        arm9 = QtWidgets.QTreeWidgetItem()
        arm9.setText(0, 'Main ARM9')
        arm9.setData(NodeData.nodeType, QtCore.Qt.UserRole, NodeTypes.main9)
        arm9.setData(NodeData.ramAddress, QtCore.Qt.UserRole, self.arm9File.ramAddress)
        arm9.setData(NodeData.size, QtCore.Qt.UserRole, len(self.ROM.arm9))
        
        arm9OvsNode.addChild(arm9)

        self.WaitUntilCodeLoadThreadFinished(True, Processor.ARM7)
        arm7 = QtWidgets.QTreeWidgetItem()
        arm7.setText(0, 'Main ARM7')
        arm7.setData(NodeData.nodeType, QtCore.Qt.UserRole, NodeTypes.main7)
        arm7.setData(NodeData.ramAddress, QtCore.Qt.UserRole, self.arm7File.ramAddress)
        arm7.setData(NodeData.size, QtCore.Qt.UserRole, len(self.ROM.arm7))
        arm7OvsNode.addChild(arm7)

        self.WaitUntilCodeLoadThreadFinished(False, Processor.ARM9)
        for id, overlay in self.overlays9.items():
            arm9OvsNode.addChild(self.MakeOverlayNode(id, overlay, NodeTypes.overlay9))  

        self.WaitUntilCodeLoadThreadFinished(False, Processor.ARM7)
        for id, overlay in self.overlays7.items():          
            arm7OvsNode.addChild(self.MakeOverlayNode(id, overlay, NodeTypes.overlay7)) 

    def LoadOverlay9Files(self):
        self.overlays9 = self.ROM.loadArm9Overlays()

    def LoadOverlay7Files(self):
        self.overlays7 = self.ROM.loadArm7Overlays()

    def LoadMain9File(self):
        self.arm9File = self.ROM.loadArm9()

    def LoadMain7File(self):
        self.arm7File = self.ROM.loadArm7()

    def ReloadCode(self, main, processor):
        if main:
            if processor == Processor.ARM7:
                try:
                    self.main7Thread.join()
                except RuntimeError:
                    pass
                self.main7Thread = threading.Thread(target=self.LoadMain7File)
                self.main7Thread.start()
            if processor == Processor.ARM9:
                try:
                    self.main9Thread.join()
                except RuntimeError:
                    pass
                self.main9Thread = threading.Thread(target=self.LoadMain9File)
                self.main9Thread.start() 
        else:
            if processor == Processor.ARM7:
                try:
                    self.overlays7Thread.join()
                except RuntimeError:
                    pass
                self.overlays7Thread = threading.Thread(target=self.LoadOverlay7Files)
                self.overlays7Thread.start()
            if processor == Processor.ARM9:
                try:
                    self.overlays7Thread.join()
                except RuntimeError:
                    pass
                self.overlays9Thread = threading.Thread(target=self.LoadOverlay9Files)
                self.overlays9Thread.start()       

    def WaitUntilCodeLoadThreadFinished(self, main, processor):     
        if main:
            if processor == Processor.ARM7:
                try:
                    self.main7Thread.join()
                except RuntimeError:
                    pass
            if processor == Processor.ARM9:
                try:
                    self.main9Thread.join()
                except RuntimeError:
                    pass
        else:
            if processor == Processor.ARM7:
                try:
                    self.overlays7Thread.join()
                except RuntimeError:
                    pass
            if processor == Processor.ARM9:
                try:
                    self.overlays9Thread.join()
                except RuntimeError:
                    pass

    def ReloadCodeBasedOnNodeType(self, nodetype):
        if nodetype == NodeTypes.overlay7:
            self.ReloadCode(False, Processor.ARM7)
        elif nodetype == NodeTypes.overlay9:
            self.ReloadCode(False, Processor.ARM9)
        elif nodetype == NodeTypes.main7:
            self.ReloadCode(True, Processor.ARM7)
        elif nodetype == NodeTypes.main9:
            self.ReloadCode(True, Processor.ARM9)
        elif nodetype == NodeTypes.arm7directory:
            self.ReloadCode(True, Processor.ARM7)
            self.ReloadCode(False, Processor.ARM7) 
        elif nodetype == NodeTypes.arm9directory:
            self.ReloadCode(True, Processor.ARM9)
            self.ReloadCode(False, Processor.ARM9)
        elif nodetype == NodeTypes.rom:
            self.ReloadCode(True, Processor.ARM7)
            self.ReloadCode(True, Processor.ARM9)
            self.ReloadCode(False, Processor.ARM7)
            self.ReloadCode(False, Processor.ARM9)

    def WaitForReloadExecutionFinishBasedOnNodeType(self, nodetype):
        if nodetype == NodeTypes.overlay7:
            self.WaitUntilCodeLoadThreadFinished(False, Processor.ARM7)
        elif nodetype == NodeTypes.overlay9:
            self.WaitUntilCodeLoadThreadFinished(False, Processor.ARM9)
        elif nodetype == NodeTypes.main7:
            self.WaitUntilCodeLoadThreadFinished(True, Processor.ARM7)
        elif nodetype == NodeTypes.main9:
            self.WaitUntilCodeLoadThreadFinished(True, Processor.ARM9)
        elif nodetype == NodeTypes.arm7directory:
            self.WaitUntilCodeLoadThreadFinished(True, Processor.ARM7)
            self.WaitUntilCodeLoadThreadFinished(False, Processor.ARM7) 
        elif nodetype == NodeTypes.arm9directory:
            self.WaitUntilCodeLoadThreadFinished(True, Processor.ARM9)
            self.WaitUntilCodeLoadThreadFinished(False, Processor.ARM9)
        elif nodetype == NodeTypes.rom:
            self.WaitUntilCodeLoadThreadFinished(True, Processor.ARM7)
            self.WaitUntilCodeLoadThreadFinished(True, Processor.ARM9)
            self.WaitUntilCodeLoadThreadFinished(False, Processor.ARM7)
            self.WaitUntilCodeLoadThreadFinished(False, Processor.ARM9)   

    def LoadROMDir(self, folder, path, node):
        for i, fileName in enumerate(folder.files):

            self.SetProgressText('Found file: ' + fileName)

            fileNode = QtWidgets.QTreeWidgetItem()
            fileNode.setText(0, fileName)
            fileNode.setData(NodeData.nodeType, QtCore.Qt.UserRole, NodeTypes.file)
            fileNode.setData(NodeData.fileID, QtCore.Qt.UserRole, i + folder.firstID) 
            fileNode.setData(NodeData.path, QtCore.Qt.UserRole, path) 
            node.addChild(fileNode)

        for i, (folderName, childFolder) in enumerate(folder.folders):

            self.SetProgressText('Found folder: ' + folderName)

            folderNode = QtWidgets.QTreeWidgetItem()
            folderNode.setText(0, folderName)
            folderNode.setData(NodeData.nodeType, QtCore.Qt.UserRole, NodeTypes.directory)
            folderNode.setData(NodeData.folderFirstID, QtCore.Qt.UserRole, childFolder.firstID)
            folderNode.setData(NodeData.path, QtCore.Qt.UserRole, path) 
            node.addChild(folderNode)

            self.LoadROMDir(childFolder, path + '/' + folderName, folderNode)


    def ExtractFolder(self, folder, dirPath):
        for fileName in folder.files:
            self.SetProgressText('Extracting ' + fileName)
            data = self.ROM.files[folder.idOf(fileName)]

            with open(os.path.join(dirPath, fileName), 'wb') as f:
                f.write(data)

        for (folderName, childFolder) in folder.folders:
            self.SetProgressText('Extracting ' + folderName)
            path = os.path.join(dirPath, folderName)
            if not os.path.isdir(path):
                os.mkdir(path)

            self.ExtractFolder(childFolder, path)


    def ReplaceFolder(self, folder, dirPath):
        for fileName in folder.files:
            self.SetProgressText('Replacing ' + fileName)
            fpath = os.path.join(dirPath, fileName)

            if os.path.isfile(fpath):
                with open(fpath, 'rb') as f:
                    fileData = f.read()                   
                    self.ROM.files[folder.idOf(fileName)] = fileData

        for folderName, childFolder in folder.folders:
            self.SetProgressText('Replacing ' + folderName)
            path = os.path.join(dirPath, folderName)
            self.ReplaceFolder(childFolder, path)


    def ExtractCodeFolder(self, processor, path):
        if processor == Processor.ARM7:
            ovs = self.overlays7
            m = self.ROM.arm7
        else:
            ovs = self.overlays9
            m = self.ROM.arm9      

        procStr = str(int(processor))

        self.SetProgressText('Extracting main' + procStr)
        with open(os.path.join(path, 'ARM' + procStr + '.bin'), 'wb') as f:
            f.write(m)                 

        for i, ov in ovs.items():
            fileName = 'Overlay' + procStr + '_' + str(i)
            self.SetProgressText('Extracting ' + fileName)

            with open(os.path.join(path, fileName), 'wb') as f:
                f.write(ov.data)     


    def ReplaceCodeFolder(self, processor, path):
        if processor == Processor.ARM7:
            ovs = self.overlays7
        else:
            ovs = self.overlays9 

        procStr = str(int(processor))
        mainPath = os.path.join(path, 'ARM' + procStr + '.bin')

        if os.path.isfile(mainPath):
            self.SetProgressText('Replacing main' + procStr)
            with open(mainPath, 'rb') as f:
                fileData = f.read()     

                if processor == Processor.ARM7:
                    self.ROM.arm7 = fileData
                else:
                    self.ROM.arm9 = fileData

        for i, ov in ovs.items():     
            fileName = 'Overlay' + procStr + '_' + str(i)
            overlayPath = os.path.join(path, fileName)

            if os.path.isfile(overlayPath):
                self.SetProgressText('Replacing ' + fileName)
                with open(overlayPath, 'rb') as f:
                    fileData = f.read()                   
                    self.ROM.files[ov.fileID] = fileData

    def ChangeFolderFirstIDsHigherThanBy(self, folder, startID, amount):
        if (folder.firstID > startID):
            folder.firstID += amount

        for _folderName, childFolder in folder.folders:
            self.ChangeFolderFirstIDsHigherThanBy(childFolder, startID, amount)         


    def ChangeOverlayFileIDsHigherThanByAndDelete(self, startID, amount):
        idsToDelete = []

        self.WaitUntilCodeLoadThreadFinished(False, Processor.ARM7)
        for i, ov in self.overlays7.items():
            if ov.fileID == startID:
                idsToDelete.append(i)

        for Id in idsToDelete:
            del self.overlays7[Id]   

        for i, ov in self.overlays7.items():
            if ov.fileID > startID:
                ov.fileID += amount     

        idsToDelete.clear()
        self.WaitUntilCodeLoadThreadFinished(False, Processor.ARM9)
        
        for i, ov in self.overlays9.items():
            if ov.fileID == startID:
                idsToDelete.append(i) 

        for Id in idsToDelete:
            del self.overlays9[Id]      

        for i, ov in self.overlays9.items():
            if ov.fileID > startID:
                ov.fileID += amount

        self.ROM.arm7OverlayTable = ndspy.code.saveOverlayTable(self.overlays7)
        self.ROM.arm9OverlayTable = ndspy.code.saveOverlayTable(self.overlays9)

        self.ReloadCode(False, Processor.ARM7)
        self.ReloadCode(False, Processor.ARM9)


    def ChangeOverlayFileIDsHigherThanBy(self, startID, amount):

        self.WaitUntilCodeLoadThreadFinished(False, Processor.ARM7)
        for _i, ov in self.overlays7.items():
            if ov.fileID > startID:
                ov.fileID += amount     

        self.WaitUntilCodeLoadThreadFinished(False, Processor.ARM9)
        for _i, ov in self.overlays9.items():
            if ov.fileID > startID:
                ov.fileID += amount

        self.ROM.arm7OverlayTable = ndspy.code.saveOverlayTable(self.overlays7)
        self.ROM.arm9OverlayTable = ndspy.code.saveOverlayTable(self.overlays9)

        self.ReloadCode(False, Processor.ARM7)
        self.ReloadCode(False, Processor.ARM9)


    def UpdateNodeFileIDs(self, startID, amount, node):
        count = node.childCount()

        for i in range (0, count):
            nodeType = node.child(i).data(NodeData.nodeType, QtCore.Qt.UserRole) 

            if nodeType in {NodeTypes.file, NodeTypes.overlay7, NodeTypes.overlay9}:
                fId = node.child(i).data(NodeData.fileID, QtCore.Qt.UserRole) 
                if fId > startID:
                    node.child(i).setData(NodeData.fileID, QtCore.Qt.UserRole, fId + amount)

            elif nodeType == NodeTypes.directory:
                fId = node.child(i).data(NodeData.folderFirstID, QtCore.Qt.UserRole) 
                if fId > startID:
                    node.child(i).setData(NodeData.folderFirstID, QtCore.Qt.UserRole, fId + amount)

            self.UpdateNodeFileIDs(startID, amount, node.child(i))

    def UpdateOverlayNodes(self, node, startid):
        count = node.childCount()

        for i in range (1, count):

            oldOvId = node.child(i).data(NodeData.overlayID, QtCore.Qt.UserRole)
            if (oldOvId > startid):
                node.child(i).setText(0, 'Overlay ' + str(oldOvId + 1))
                node.child(i).setData(NodeData.overlayID, QtCore.Qt.UserRole, oldOvId + 1)


    def GetNumberOfFilesInFolder(self, folder):
        num = len(folder.files)
        for _folderName, folder in folder.folders:
            num += self.GetNumberOfFilesInFolder(folder)
        return num


    def FixNodesAfterRename(self, node, parentPath, newFolderName):
        count = node.childCount()

        for i in range (0, count):
            childNode = node.child(i)
            newData = parentPath + '/' + newFolderName
            childNode.setData(NodeData.path, QtCore.Qt.UserRole, newData)

            nodeType = childNode.data(NodeData.nodeType, QtCore.Qt.UserRole) 

            if nodeType == NodeTypes.directory:
                childFolderName = childNode.text(0)
                self.FixNodesAfterRename(childNode, newData, childFolderName)

    def HandleExtract(self):
        if self.currentNode == None:
            return

        nodeType = self.currentNode.data(NodeData.nodeType, QtCore.Qt.UserRole)

        if nodeType not in {NodeTypes.directory, NodeTypes.arm7directory, NodeTypes.arm9directory, NodeTypes.rom, NodeTypes.filesystem}:
            fileName = QtWidgets.QFileDialog.getSaveFileName(self, 
                                                            'Pick a location to save the file...', 
                                                            '', 
                                                            'All Files(*)')[0]    
            if fileName == '': return
            else:     
                self.WaitForReloadExecutionFinishBasedOnNodeType(nodeType)

                if nodeType in {NodeTypes.file, NodeTypes.overlay7, NodeTypes.overlay9}:
                    fileid = self.currentNode.data(NodeData.fileID, QtCore.Qt.UserRole)
                    data = self.ROM.files[fileid]
                elif nodeType == NodeTypes.main9:
                    data = self.arm9
                elif nodeType == NodeTypes.main7:
                    data = self.arm7        

                with open(fileName, 'wb') as f:
                    f.write(data)
        
        else:
            dirName = QtWidgets.QFileDialog.getExistingDirectory(self, 
                                                                'Select a directory to save these files...',
                                                                '',
                                                                QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks)

            if dirName == '': return
            else:
                self.WaitForReloadExecutionFinishBasedOnNodeType(nodeType)

                if not os.path.isdir(dirName):
                    os.mkdir(dirName)  

                folderName = self.currentNode.text(0)
                extractPath = os.path.join(dirName, folderName)

                if not os.path.isdir(extractPath):
                    os.mkdir(extractPath)

                if nodeType in {NodeTypes.directory, NodeTypes.filesystem}:
                    path = self.currentNode.data(NodeData.path, QtCore.Qt.UserRole)

                    if nodeType == NodeTypes.filesystem:
                        folderToExtract = self.ROM.filenames
                    else:
                        folderToExtract = self.ROM.filenames.subfolder(folderName) if path == '' else self.ROM.filenames.subfolder(path + '/' + folderName)

                    self.ExtractFolder(folderToExtract, extractPath)

                elif nodeType == NodeTypes.arm7directory:
                    self.ExtractCodeFolder(Processor.ARM7, extractPath) 

                elif nodeType == NodeTypes.arm9directory:
                    self.ExtractCodeFolder(Processor.ARM9, extractPath)  

                elif nodeType == NodeTypes.rom:
                    romPath = os.path.join(extractPath, 'Filesystem Root')
                    if not os.path.isdir(romPath):
                        os.mkdir(romPath)
                    self.ExtractFolder(self.ROM.filenames, romPath)

                    romPath = os.path.join(extractPath, 'ARM7')
                    if not os.path.isdir(romPath):
                        os.mkdir(romPath)
                    self.ExtractCodeFolder(Processor.ARM7, romPath)   

                    romPath = os.path.join(extractPath, 'ARM9')
                    if not os.path.isdir(romPath):
                        os.mkdir(romPath)
                    self.ExtractCodeFolder(Processor.ARM9, romPath) 

        self.SetProgressText('Done.')


    def HandleReplace(self):
        if self.currentNode == None:
            return

        nodeType = self.currentNode.data(NodeData.nodeType, QtCore.Qt.UserRole)
        
        if nodeType not in {NodeTypes.directory, NodeTypes.arm7directory, NodeTypes.arm9directory, NodeTypes.rom, NodeTypes.filesystem}:
            fileName = QtWidgets.QFileDialog.getOpenFileName(self, 
                                                            'Choose a file...', 
                                                            '', 
                                                            'All Files(*)')[0]  
            if fileName == '': return
            else:     
                fileData = None

                with open(fileName, 'rb') as f:
                    fileData = f.read()        

                self.WaitForReloadExecutionFinishBasedOnNodeType(nodeType)            

                if nodeType in {NodeTypes.file, NodeTypes.overlay7, NodeTypes.overlay9}:
                    fileid = self.currentNode.data(NodeData.fileID, QtCore.Qt.UserRole)
                    self.ROM.files[fileid] = fileData
                    self.HandleItemChange(self.currentNode, None)

                elif nodeType == NodeTypes.main9:
                    self.ROM.arm9 = fileData

                elif nodeType == NodeTypes.main7:
                    self.ROM.arm7 = fileData              

                self.ROMChanged()
        else:
            dirName = QtWidgets.QFileDialog.getExistingDirectory(self, 
                                                                'Select a directory...',
                                                                '',
                                                                QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks)  
            if dirName == '': return
            else:        
                self.WaitForReloadExecutionFinishBasedOnNodeType(nodeType)  

                if nodeType in {NodeTypes.directory, NodeTypes.filesystem}:
                    folderName = self.currentNode.text(0)
                    path = self.currentNode.data(NodeData.path, QtCore.Qt.UserRole)

                    if nodeType == NodeTypes.filesystem:
                        folderToExtract = self.ROM.filenames
                    else:
                        folderToExtract = self.ROM.filenames.subfolder(folderName) if path == '' else self.ROM.filenames.subfolder(path + '/' + folderName)

                    self.ReplaceFolder(folderToExtract, dirName)

                elif nodeType == NodeTypes.arm7directory:
                    self.ReplaceCodeFolder(Processor.ARM7, dirName)

                elif nodeType == NodeTypes.arm9directory:
                    self.ReplaceCodeFolder(Processor.ARM9, dirName)  

                elif nodeType == NodeTypes.rom:
                    self.ReplaceFolder(self.ROM.filenames, os.path.join(dirName, 'Filesystem Root'))   
                    self.ReplaceCodeFolder(Processor.ARM7, os.path.join(dirName, 'ARM7'))   
                    self.ReplaceCodeFolder(Processor.ARM9, os.path.join(dirName, 'ARM9')) 

                self.ROMChanged()

        self.ReloadCodeBasedOnNodeType(nodeType)              
        self.SetProgressText('Done.')            

                    
    def HandleRename(self):
        if self.currentNode == None:
            return

        nodeType = self.currentNode.data(NodeData.nodeType, QtCore.Qt.UserRole)  

        if nodeType in {NodeTypes.directory, NodeTypes.file}:
  
            name = self.currentNode.text(0)
            newName, ok = QtWidgets.QInputDialog.getText(self, '', 'Enter a new name for this ' + 'file' if nodeType == NodeTypes.file else 'folder' + ':')
            
            if ok:
                parentFolderPath = self.currentNode.data(NodeData.path, QtCore.Qt.UserRole)
                parentFolder = self.ROM.filenames if parentFolderPath == '' else self.ROM.filenames.subfolder(parentFolderPath)

                if (nodeType == NodeTypes.file):
                    for fn in parentFolder.files:
                        if newName == fn:
                            QtWidgets.QMessageBox.information(self, 'Error', 'A file with this name already exists in this folder.')
                            return

                    for i, fn in enumerate(parentFolder.files):
                        if name == fn:
                            parentFolder.files[i] = newName
                            break
                else:
                    for dn in parentFolder.folders:
                        if newName == dn:
                            QtWidgets.QMessageBox.information(self, 'Error', 'A folder with this name already exists in this folder.')
                            return

                    for i, (folderName, childFolder) in enumerate(parentFolder.folders):
                        if name == folderName:
                            parentFolder.folders[i] = (newName, childFolder)
                            break

                    self.FixNodesAfterRename(self.currentNode, parentFolderPath, newName)

                self.currentNode.setText(0, newName)
                self.ROMChanged()
            else:
                return
        else:
            QtWidgets.QMessageBox.information(self, 'Error', 'These cannot be renamed.')

    def HandleRemove(self):
        if self.currentNode is None:
            return

        nodeType = self.currentNode.data(NodeData.nodeType, QtCore.Qt.UserRole)

        fileNumber = 0
        fileId = 0
        
        if nodeType in {NodeTypes.file, NodeTypes.overlay7, NodeTypes.overlay9}:
            fileName = self.currentNode.text(0)
            fileId = self.currentNode.data(NodeData.fileID, QtCore.Qt.UserRole)

            if nodeType == NodeTypes.file:
                parentFolderPath = self.currentNode.data(NodeData.path, QtCore.Qt.UserRole)
                parentFolder = self.ROM.filenames if parentFolderPath == '' else self.ROM.filenames.subfolder(parentFolderPath)

                for fn in parentFolder.files:
                    if fn == fileName:
                        parentFolder.files.remove(fn)
                        break
            del self.ROM.files[fileId]
            fileNumber = 1

        elif nodeType in {NodeTypes.directory, NodeTypes.filesystem}:
            folderName = self.currentNode.text(0)
            parentFolderPath = self.currentNode.data(NodeData.path, QtCore.Qt.UserRole)
            parentFolder = self.ROM.filenames if parentFolderPath == '' else self.ROM.filenames.subfolder(parentFolderPath)

            if nodeType == NodeTypes.filesystem:
                folderToRemove = self.ROM.filenames
            else:
                folderToRemove = self.ROM.filenames.subfolder(folderName) if parentFolderPath == '' else self.ROM.filenames.subfolder(parentFolderPath + '/' + folderName)

            fileNumber = self.GetNumberOfFilesInFolder(folderToRemove)
            fileId = folderToRemove.firstID

            del self.ROM.files[fileId : fileId + fileNumber]

            if nodeType != NodeTypes.filesystem:
                del parentFolder.folders[ndspy.indexInNamedList(parentFolder.folders, folderName)]
            else:
                parentFolder.folders.clear()
                parentFolder.files.clear()
        else:
            QtWidgets.QMessageBox.information(self, 'Error', 'This cannot be deleted...')

        if nodeType in {NodeTypes.directory, NodeTypes.filesystem, NodeTypes.file, NodeTypes.overlay7, NodeTypes.overlay9}:
            self.SetProgressText('Correcting folders...')
            self.ChangeFolderFirstIDsHigherThanBy(self.ROM.filenames, fileId, -1 * fileNumber)

            self.SetProgressText('Correcting overlays...')
            self.ChangeOverlayFileIDsHigherThanByAndDelete(fileId, -1 * fileNumber)

            self.UpdateNodeFileIDs(fileId, -1 * fileNumber, self.romTree)
            
            if nodeType != NodeTypes.filesystem:
                self.currentNode.parent().removeChild(self.currentNode)
            else:
                count = self.currentNode.childCount()
                for _i in range (count):
                    self.currentNode.removeChild(self.currentNode.child(0))

            self.ROMChanged()
            self.SetProgressText('Done.') 


    def HandleAddFile(self):
        if self.currentNode is None:
            return

        nodeType = self.currentNode.data(NodeData.nodeType, QtCore.Qt.UserRole)

        if nodeType not in {NodeTypes.file, NodeTypes.overlay7, NodeTypes.overlay9, NodeTypes.main7, NodeTypes.main9,
                            NodeTypes.arm7directory, NodeTypes.arm9directory, NodeTypes.directory, NodeTypes.filesystem}:
            QtWidgets.QMessageBox.information(self, 'Error', 'You cannot add files here...')
            return

        fileId = 0
        ovId = 0
        folder = None

        if nodeType in {NodeTypes.file, NodeTypes.directory, NodeTypes.filesystem}:
            newName, ok = QtWidgets.QInputDialog.getText(self, '', 'Enter a new name for the new file:')

            if not ok:
                return

            fileName = self.currentNode.text(0)
            fileId = self.currentNode.data(NodeData.fileID, QtCore.Qt.UserRole)

            if nodeType == NodeTypes.file:
                parentFolderPath = self.currentNode.data(NodeData.path, QtCore.Qt.UserRole)
                folder = self.ROM.filenames if parentFolderPath == '' else self.ROM.filenames.subfolder(parentFolderPath)

                for fn in folder.files:
                    if newName == fn:
                        QtWidgets.QMessageBox.information(self, 'Error', 'A file with this name already exists in this folder.')
                        return

                for i, fn in enumerate(folder.files):
                    if fn == fileName:
                        folder.files.insert(i + 1, newName)
                        self.ROM.files.insert(fileId + 1, b'')
                        break
            else:
                parentFolderPath = self.currentNode.data(NodeData.path, QtCore.Qt.UserRole)

                if nodeType == nodeType.filesystem:
                    folder = self.ROM.filenames
                else:
                    folder = self.ROM.filenames.subfolder(self.currentNode.text(0)) if parentFolderPath == '' else self.ROM.filenames.subfolder(parentFolderPath + '/' + self.currentNode.text(0))

                for fn in folder.files:
                    if newName == fn:
                        QtWidgets.QMessageBox.information(self, 'Error', 'A file with this name already exists in this folder.')
                        return

                fileId = len(folder.files) + folder.firstID - 1

                if (len(folder.files) == 0):
                    newfolder = True

                folder.files.insert(len(folder.files), newName)
                self.ROM.files.insert(fileId + 1, b'')


        if nodeType in {NodeTypes.main7, NodeTypes.overlay7, NodeTypes.arm7directory}:
            fileId = len(self.ROM.files)

            if nodeType == NodeTypes.main7:
                ovId = -1
            elif nodeType == NodeTypes.overlay7:
                ovId = self.currentNode.data(NodeData.overlayID, QtCore.Qt.UserRole)
            else:
                ovId = len(self.overlays7) - 1

            newoverlays7 = {}
            for key, overlay in self.overlays7.items():
                if (key > ovId):
                    newoverlays7[key + 1] = overlay
                else:
                    newoverlays7[key] = overlay

            self.overlays7 = newoverlays7

            self.ROM.files.insert(fileId, b'')
            self.overlays7[ovId + 1] = ndspy.code.Overlay(b'', 0, 0, 0, 0, 0, fileId, 0, 0)

        if nodeType in {NodeTypes.main9, NodeTypes.overlay9, NodeTypes.arm9directory}:
            fileId = len(self.ROM.files)

            if nodeType == NodeTypes.main9:
                ovId = -1
            elif nodeType == NodeTypes.overlay9:
                ovId = self.currentNode.data(NodeData.overlayID, QtCore.Qt.UserRole)
            else:
                ovId = len(self.overlays9) - 1

            newoverlays9 = {}
            for key, overlay in self.overlays9.items():
                if (key > ovId):
                    newoverlays9[key + 1] = overlay
                else:
                    newoverlays9[key] = overlay

            self.overlays9 = newoverlays9

            self.ROM.files.insert(fileId, [])
            self.overlays9[ovId + 1] = ndspy.code.Overlay(b'', 0, 0, 0, 0, 0, fileId, 0, 0) 

        oldId = 0

        if (folder is not None):
            oldId = folder.firstID

        self.SetProgressText('Correcting folders...')
        self.ChangeFolderFirstIDsHigherThanBy(self.ROM.filenames, fileId, 1)

        self.SetProgressText('Correcting overlays...')
        self.ChangeOverlayFileIDsHigherThanBy(fileId, 1)

        self.UpdateNodeFileIDs(fileId, 1, self.romTree)

        if (folder is not None):
            folder.firstID = oldId

        if nodeType in {NodeTypes.file, NodeTypes.filesystem, NodeTypes.directory}:
            fileNode = QtWidgets.QTreeWidgetItem()
            fileNode.setText(0, newName)
            fileNode.setData(NodeData.nodeType, QtCore.Qt.UserRole, NodeTypes.file)
            fileNode.setData(NodeData.fileID, QtCore.Qt.UserRole, fileId + 1)  

            if nodeType == NodeTypes.file:
                parentNodeType = self.currentNode.data(0, QtCore.Qt.UserRole)

                if parentNodeType == NodeTypes.filesystem:
                    fileNode.setData(NodeData.path, QtCore.Qt.UserRole, '')
                else:
                    fileNode.setData(NodeData.path, QtCore.Qt.UserRole, parentFolderPath + '/' + self.currentNode.parent().text(0))
                    
                self.currentNode.parent().insertChild(self.currentNode.parent().indexOfChild(self.currentNode) + 1, fileNode)
            else:
                if (nodeType == NodeTypes.filesystem):
                    fileNode.setData(NodeData.path, QtCore.Qt.UserRole, '')
                else:
                    fileNode.setData(NodeData.path, QtCore.Qt.UserRole, parentFolderPath + '/' + self.currentNode.text(0))

                self.currentNode.addChild(fileNode)         

        if nodeType in {NodeTypes.overlay9, NodeTypes.arm9directory, NodeTypes.overlay7, NodeTypes.arm7directory, NodeTypes.main9, NodeTypes.main7}:
            if nodeType in {NodeTypes.overlay9, NodeTypes.arm9directory, NodeTypes.main9}:
                ovNode = self.MakeOverlayNode(ovId + 1, self.overlays9[ovId + 1], NodeTypes.overlay9)
            if nodeType in {NodeTypes.overlay7, NodeTypes.arm7directory, NodeTypes.main7}:
                ovNode = self.MakeOverlayNode(ovId + 1, self.overlays7[ovId + 1], NodeTypes.overlay7)

            if nodeType in {NodeTypes.overlay7, NodeTypes.overlay9, NodeTypes.main9, NodeTypes.main7}:
                self.UpdateOverlayNodes(self.currentNode.parent(), ovId)
                self.currentNode.parent().insertChild(self.currentNode.parent().indexOfChild(self.currentNode) + 1, ovNode)  
            else:
                self.currentNode.addChild(ovNode)      

        self.ROMChanged()
        self.SetProgressText('Done.') 


    def HandleAddFolder(self):
        if self.currentNode is None:
            return

        nodeType = self.currentNode.data(NodeData.nodeType, QtCore.Qt.UserRole)

        if nodeType not in {NodeTypes.file, NodeTypes.directory, NodeTypes.filesystem}:
            QtWidgets.QMessageBox.information(self, 'Error', 'You cannot add folders here...')
            return

        newName, ok = QtWidgets.QInputDialog.getText(self, '', 'Enter a new name for the new folder:')

        if not ok:
            return

        if nodeType == NodeTypes.file:
            parentFolderPath = self.currentNode.data(NodeData.path, QtCore.Qt.UserRole)
            parentFolder = self.ROM.filenames if parentFolderPath == '' else self.ROM.filenames.subfolder(parentFolderPath)

            for fn in parentFolder.folders:
                if newName == fn:
                    QtWidgets.QMessageBox.information(self, 'Error', 'A folder with this name already exists in this folder.')
                    return

            firstIDOfAddedFolder = len(self.ROM.files)
            parentFolder.folders.append((newName, ndspy.fnt.Folder([], [], firstIDOfAddedFolder)))   

            parentNodeType = self.currentNode.data(0, QtCore.Qt.UserRole)
        
            folderNode = QtWidgets.QTreeWidgetItem()
            folderNode.setText(0, newName)
            folderNode.setData(NodeData.nodeType, QtCore.Qt.UserRole, NodeTypes.directory)
            folderNode.setData(NodeData.folderFirstID, QtCore.Qt.UserRole, firstIDOfAddedFolder)

            if parentNodeType == NodeTypes.filesystem:
                folderNode.setData(NodeData.path, QtCore.Qt.UserRole, '')
            else:
                folderNode.setData(NodeData.path, QtCore.Qt.UserRole, parentFolderPath + '/' + self.currentNode.parent().text(0))

            self.currentNode.parent().addChild(folderNode)

        else:
            parentFolderPath = self.currentNode.data(NodeData.path, QtCore.Qt.UserRole)

            if nodeType == nodeType.filesystem:
                folder = self.ROM.filenames
            else:
                folder = self.ROM.filenames.subfolder(self.currentNode.text(0)) if parentFolderPath == '' else self.ROM.filenames.subfolder(parentFolderPath + '/' + self.currentNode.text(0))

            for fn in folder.folders:
                if newName == fn:
                    QtWidgets.QMessageBox.information(self, 'Error', 'A folder with this name already exists in this folder.')
                    return

            firstIDOfAddedFolder = len(self.ROM.files)
            folder.folders.append((newName, ndspy.fnt.Folder([], [], firstIDOfAddedFolder))) 

            folderNode = QtWidgets.QTreeWidgetItem()
            folderNode.setText(0, newName)
            folderNode.setData(NodeData.nodeType, QtCore.Qt.UserRole, NodeTypes.directory)
            folderNode.setData(NodeData.folderFirstID, QtCore.Qt.UserRole, firstIDOfAddedFolder)

            if (nodeType == NodeTypes.filesystem):
                folderNode.setData(NodeData.path, QtCore.Qt.UserRole, '')
            else:
                folderNode.setData(NodeData.path, QtCore.Qt.UserRole, parentFolderPath + '/' + self.currentNode.text(0))

            self.currentNode.addChild(folderNode)


    def HandleExtractIcon(self):
        if self.ROM is None:    
            return
        else:
            fileName = QtWidgets.QFileDialog.getSaveFileName(self, 
                                                            'Pick a location to save the file...', 
                                                            '', 
                                                            'Portable Network Graphics (*.png);;All Files(*)')[0]

            if fileName == '': return
            else:
                self.bannerIcon.save(fileName, 'PNG', 100)


    def HandleImportIcon(self):
        if self.ROM is None:
            return 
        else:    
            fileName = QtWidgets.QFileDialog.getOpenFileName(self, 
                                                            'Choose a file...', 
                                                            '', 
                                                            'Portable Network Graphics (*.png)')[0]
            if fileName == '': return
            else:
                image = Image.open(fileName)
                tex, _none, _pal = ndspy.extras.textureEncoding.encodeImage_Paletted_4BPP(image)

                outdata = bytearray()
                for y in range(4):
                    for x in range(4):
                        for row in range(8):
                            offs = (y * 8 + row) * 16 + x * 4
                            outdata.extend(tex[offs : offs + 4])

                print (str(len(outdata)))
                return


    def HandleItemChange(self, current, previous):

        self.currentNode = current 

        if current is None:
            self.selectedFileText.setText('---------')
            self.selectedFileDetails.setText('---------')      
            return    

        nodeType = current.data(0, QtCore.Qt.UserRole) 

        if nodeType == NodeTypes.file:
            fileName = current.text(0)
            fileId = current.data(NodeData.fileID, QtCore.Qt.UserRole)

            self.selectedFileText.setText('Selected file: ' + fileName)        
            currentFile = self.ROM.files[fileId]
            self.selectedFileDetails.setText('File ID: ' + str(fileId) + ', File size: ' + str(len(currentFile)) + ' bytes.')

        if nodeType in {NodeTypes.directory, NodeTypes.arm7directory, NodeTypes.arm9directory, NodeTypes.rom, NodeTypes.filesystem}:
            self.selectedFileText.setText('Selected folder: ' + current.text(0))
            self.selectedFileDetails.setText('---------')

        if nodeType in {NodeTypes.overlay7, NodeTypes.overlay9}:
            id = current.data(NodeData.overlayID, QtCore.Qt.UserRole)
            fileId = current.data(NodeData.fileID, QtCore.Qt.UserRole)
            ramAddress = current.data(NodeData.ramAddress, QtCore.Qt.UserRole)

            self.selectedFileText.setText('Selected file: Overlay ' + str(id))        
            self.selectedFileDetails.setText('Overlay File ID: ' + str(fileId) + 
                                            ' File size: ' + str(len(self.ROM.files[fileId])) + ' bytes.' +
                                            ' RAM Address: ' + hex(ramAddress))

        if nodeType in {NodeTypes.main7, NodeTypes.main9}:
            ramAddress = current.data(NodeData.ramAddress, QtCore.Qt.UserRole)
            size = current.data(NodeData.size, QtCore.Qt.UserRole)

            self.selectedFileText.setText('Selected file: ' + current.text(0))        
            self.selectedFileDetails.setText('RAM Address: ' + hex(ramAddress) + ', File size: ' + str(size) + ' bytes.')

    def CreateContextMenu(self, location):
        if self.romFilesystemTreeView is None:
            return

        if self.currentNode is None:
            return

        nodeType = self.currentNode.data(0, QtCore.Qt.UserRole)

        contextMenu = QtWidgets.QMenu()
        openAction = QtWidgets.QAction('&Open...', self)

        extractAction = QtWidgets.QAction('&Extract...', self)
        extractAction.triggered.connect(self.HandleExtract)

        renameAction = QtWidgets.QAction('&Rename...', self)
        renameAction.triggered.connect(self.HandleRename)

        replaceAction = QtWidgets.QAction('&Replace...', self)
        replaceAction.triggered.connect(self.HandleReplace)
        
        addFileActionF = QtWidgets.QAction('&Add file...', self)
        addFileActionF.triggered.connect(self.HandleAddFile)

        addFolderActionF = QtWidgets.QAction('&Add folder...', self)
        addFolderActionF.triggered.connect(self.HandleAddFolder)

        removeActionF = QtWidgets.QAction('&Remove...', self)
        removeActionF.triggered.connect(self.HandleRemove)

        if nodeType not in {NodeTypes.directory, NodeTypes.arm7directory, NodeTypes.arm9directory, NodeTypes.rom}:
            contextMenu.addAction(openAction)

        if nodeType not in {NodeTypes.rom}:
            contextMenu.addAction(addFileActionF)

        if nodeType in {NodeTypes.file, NodeTypes.directory, NodeTypes.filesystem}:
            contextMenu.addAction(addFolderActionF)

        if nodeType not in {NodeTypes.main7, NodeTypes.main9, NodeTypes.arm7directory, NodeTypes.arm9directory, NodeTypes.rom}:
            contextMenu.addAction(removeActionF)

        contextMenu.addAction(extractAction)
        contextMenu.addAction(replaceAction)

        if nodeType in {NodeTypes.file, NodeTypes.directory}:
            contextMenu.addAction(renameAction)

        contextMenu.exec(self.romFilesystemTreeView.mapToGlobal(location))

    def CreateAddMenu(self):
        if self.romFilesystemTreeView is None:
            return

        if self.currentNode is None:
            return

        nodeType = self.currentNode.data(0, QtCore.Qt.UserRole)

        if nodeType not in {NodeTypes.file, NodeTypes.directory, NodeTypes.filesystem}:
            self.HandleAddFile()
        else:
            addMenu = QtWidgets.QMenu()

            addFileAction = QtWidgets.QAction('&Add file...', self)
            addFileAction.triggered.connect(self.HandleAddFile)

            addFolderAction = QtWidgets.QAction('&Add folder...', self)
            addFolderAction.triggered.connect(self.HandleAddFolder)

            addMenu.addAction(addFileAction)
            addMenu.addAction(addFolderAction)
            addMenu.exec(self.addButton.mapToGlobal(QtCore.QPoint(0,self.addButton.frameGeometry().height())))


    def HandleItemActivated(self, item, column):
        return