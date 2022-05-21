import sys
import FilesystemEditorWidget

from PyQt5 import Qt, QtCore, QtGui, QtWidgets
from PIL import Image

class MainNDSPYWindow(QtWidgets.QMainWindow):

    def CreateMenuBar(self):

        self.statusBar()
        mainMenu = self.menuBar()

        fileMenu = mainMenu.addMenu('&File')
      
        openAction = QtWidgets.QAction('&Open...', self)
        openAction.triggered.connect(self.HandleOpenROM)

        saveAction = QtWidgets.QAction('&Save', self)
        saveAction.triggered.connect(self.HandleSave)
        
        saveAsAction = QtWidgets.QAction('&Save as...', self)
        saveAsAction.triggered.connect(self.HandleSaveAs)
        
        exitAction = QtWidgets.QAction('&Exit', self)
        exitAction.triggered.connect(self.HandleCloseApplication)

        fileMenu.addAction(openAction)
        fileMenu.addAction(saveAction)
        fileMenu.addAction(saveAsAction)
        fileMenu.addAction(exitAction)
        
        aboutMenu = mainMenu.addMenu('&Help')
        
        aboutAction = QtWidgets.QAction('&About', self)
        aboutAction.triggered.connect(self.HandleAbout)      
        
        
        aboutMenu.addAction(aboutAction)

    def __init__(self):
        super(MainNDSPYWindow, self).__init__()
        self.setGeometry(50, 50, 800, 600)
        self.setWindowTitle('ndspy-gui')

        self.CreateMenuBar()
        self.CreateEditor()

    def CreateEditor(self):
        self.romEditor = FilesystemEditorWidget.FilesystemEditorWidget(self)
        self.setCentralWidget(self.romEditor)

    def HandleCloseApplication(self):
        if self.UnsavedChanges():
            sys.exit()

    def HandleSave(self):
        self.romEditor.Save()
        
    def HandleAbout(self):
        print('fuck')
        QtWidgets.QMessageBox.information(self, 'About', 'NDSPY-Gui 0.1 by Skawo.')

    def HandleSaveAs(self):
        fileName = QtWidgets.QFileDialog.getOpenFileName(self, 
                                                        'Choose a file name...', 
                                                        '', 
                                                        'Nintendo DS ROMs (*.nds;*.srl);;All Files(*)')[0]

        if fileName == '': return
        else:     
            self.romEditor.romFileName = fileName
            self.romEditor.Save()

    def HandleOpenROM(self):
        if self.UnsavedChanges():
            fileName = QtWidgets.QFileDialog.getOpenFileName(self, 
                                                            'Choose a file...', 
                                                            '', 
                                                            'Nintendo DS ROMs (*.nds;*.srl);;All Files(*)')[0]
            if fileName == '': return
            else:     
                self.romEditor.LoadROM(fileName)

    def UnsavedChanges(self):
        if self.romEditor.romEdited:
            Reply = QtWidgets.QMessageBox.question(self, 
                                                  'Unsaved changes', 
                                                  'You have unsaved changes. Would you like to save this ROM first?', 
                                                  QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel)

            if Reply == QtWidgets.QMessageBox.Yes:
                self.romEditor.Save()
                return True
            elif Reply == QtWidgets.QMessageBox.Cancel:
                return False      
            else:
                return True
        else:
            return True

def main():
    global app, mainwindow
    
    app = QtWidgets.QApplication([])
    
    mainwindow = MainNDSPYWindow()
    mainwindow.show()
    app.exec_()

if __name__ == '__main__':
    main()
