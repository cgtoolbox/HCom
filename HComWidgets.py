import os
import datetime
import time

import PySide.QtGui as QtGui
import PySide.QtCore as QtCore

import HComUtils

HCOM_VERSION = "0.5.0"

ICONPATH = os.path.dirname(__file__) + "\\HCom_Icons\\"
HISTORY_PATH = os.path.dirname(__file__) + "\\HCom_History"
RECEIVED_FILES_PATH = os.path.dirname(__file__) + "\\HCom_Received_Files"

class UiUpdaterThread(QtCore.QThread):
    
    # Type of UI changement
    update_ui_signal = QtCore.Signal(str)
    
    # Header, Message, tabTarget
    append_message_signal = QtCore.Signal(str, str, str)
    
    # sender, dataType, dataDict, tabTarget
    input_data_signal = QtCore.Signal(str, str, object, str)
    
    def __init__(self):
        QtCore.QThread.__init__(self)
        
        self.data = None
        self.messageData = None
        self.forceStop = False
        self.inputData = None
        
    def run(self):
        
        while 1:
            time.sleep(0.1)
            
            if self.forceStop:
                break
            
            if self.data:
                self.update_ui_signal.emit(self.data)
                time.sleep(0.1)
                self.data = None
                
            if self.messageData:
                self.append_message_signal.emit(str(self.messageData[0]), str(self.messageData[1]), str(self.messageData[2]))
                time.sleep(0.1)
                self.messageData = None
                
            if self.inputData:
                self.input_data_signal.emit(self.inputData[0], self.inputData[1], self.inputData[2], self.inputData[3])
                time.sleep(0.1)
                self.inputData = None
                

class UserChatTabWidget(QtGui.QWidget):
    
    def __init__(self, target, openChatRoom=False, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)
        
        self.mainUI = parent
        self.connected = self.mainUI.connected
        
        if openChatRoom:
            self.tabTargetID = target
        else:
            self.tabTargetID = self.mainUI.ID
        
        self.targetLabel = str(target).replace("[", "").replace("]", "")
        if not isinstance(target, list):
            target = [target]
        self.target = target
        
        self.widgetList = []
        
        self.centralLayout = QtGui.QVBoxLayout()
        self.centralLayout.setSpacing(10)
        
        # target ( placeholder )
        self.targetLayout = QtGui.QHBoxLayout()
        self.targetLayout.setSpacing(5)
        
        if not openChatRoom:
            
            self.closeBtn = QtGui.QPushButton()
            self.closeBtn.setObjectName("closebtn")
            self.closeBtn.setStyleSheet('''QPushButton#closebtn{ background-color: rgba(0,0,0,0); border: none; }''')
            self.closeBtn.setFixedSize(QtCore.QSize(20,20))
            self.closeBtn.setIcon(QtGui.QIcon(ICONPATH + "close.png"))
            self.closeBtn.setIconSize(QtCore.QSize(16,16))
            self.closeBtn.clicked.connect(lambda: self.mainUI._removeUserTab(self.targetLabel))
            self.targetLayout.addWidget(self.closeBtn)
            
            self.targetLbl = QtGui.QLabel("Target: " + str(self.target).replace("[", "").replace("]", ""))
            self.targetLbl.setDisabled(not self.connected)
            self.targetLayout.addWidget(self.targetLbl)
            
            self.widgetList.append(self.targetLbl)
        
        self.centralLayout.addItem(self.targetLayout)
        
        # Message widget
        ###############################################################
        self.messageScrollArea = QtGui.QScrollArea()
        self.messageScrollArea.setWidgetResizable(True)
        
        self.messageContent = QtGui.QWidget()
        self.messageScrollArea.setWidget(self.messageContent)
        
        self.messageOutLayout = QtGui.QVBoxLayout()
        self.messageOutLayout.setSpacing(2)
        self.messageOutLayout.setAlignment(QtCore.Qt.AlignTop)
        self.messageOutLayout.setSizeConstraint(QtGui.QLayout.SetMinAndMaxSize)
        
        self.messageContent.setLayout(self.messageOutLayout)
        
        self.centralLayout.addWidget(self.messageScrollArea)
        
        self.messageLayout = QtGui.QHBoxLayout()
        
        self.messageLayout.setSpacing(5)
        self.messageLine = QtGui.QLineEdit()
        self.messageLine.setDisabled(not self.connected)
        self.messageLine.returnPressed.connect(lambda: self.mainUI._sendMessage(self.target, str(self.messageLine.text().encode('latin-1')), self, self.tabTargetID))
        self.messageLayout.addWidget(self.messageLine)
        self.widgetList.append(self.messageLine)
        
        self.messageSendBtn = QtGui.QPushButton("Send Message")
        self.messageSendBtn.clicked.connect(lambda: self.mainUI._sendMessage(self.target, str(self.messageLine.text().encode('latin-1')), self, self.tabTargetID))
        self.messageSendBtn.setDisabled(not self.connected)
        self.messageLayout.addWidget(self.messageSendBtn)
        self.widgetList.append(self.messageSendBtn)
        
        self.centralLayout.addItem(self.messageLayout)
        
        # Send data buttons
        self.actionButtonLayout = QtGui.QHBoxLayout()
        self.actionButtonLayout.setSpacing(5)
        
        sendLbl = "Send:"
        if openChatRoom:
            sendLbl = "Send to all users:"
        sendLblW = QtGui.QLabel(sendLbl)
        
        self.actionButtonLayout.addWidget(sendLblW)
        
        self.sendotlBtn = QtGui.QPushButton("")
        self.sendotlBtn.setToolTip("Send houdini node or digital asset")
        self.sendotlBtn.setIconSize(QtCore.QSize(30,30))
        self.sendotlBtn.setFixedSize(40,40)
        self.sendotlBtn.setIcon(QtGui.QIcon(ICONPATH + "digitalasset.png"))
        self.sendotlBtn.clicked.connect(lambda: self.mainUI._sendOtl(self.target, self.tabTargetID, self))
        self.sendotlBtn.setDisabled(not self.connected)
        self.actionButtonLayout.addWidget(self.sendotlBtn)
        self.widgetList.append(self.sendotlBtn)
        
        self.sendSettingsBtn = QtGui.QPushButton("")
        self.sendSettingsBtn.setToolTip("Send houdini node or digital asset settings")
        self.sendSettingsBtn.setIconSize(QtCore.QSize(30,30))
        self.sendSettingsBtn.setFixedSize(40,40)
        self.sendSettingsBtn.setIcon(QtGui.QIcon(ICONPATH + "digitalasset_settings.png"))
        self.sendSettingsBtn.clicked.connect(lambda: self.mainUI._sendSettings(self.target, self.tabTargetID, self))
        self.sendSettingsBtn.setDisabled(not self.connected)
        self.actionButtonLayout.addWidget(self.sendSettingsBtn)
        self.widgetList.append(self.sendSettingsBtn)
        
        self.sendBgeoBtn = QtGui.QPushButton("")
        self.sendBgeoBtn.setToolTip("Send bgeo mesh")
        self.sendBgeoBtn.setIconSize(QtCore.QSize(30,30))
        self.sendBgeoBtn.setFixedSize(40,40)
        self.sendBgeoBtn.setIcon(QtGui.QIcon(ICONPATH + "bgeo.png"))
        self.sendBgeoBtn.setDisabled(not self.connected)
        self.sendBgeoBtn.clicked.connect(lambda: self.mainUI._sendBgeo(self.target, self.tabTargetID, self))
        self.actionButtonLayout.addWidget(self.sendBgeoBtn)
        self.widgetList.append(self.sendBgeoBtn)
        
        self.sendObjBtn = QtGui.QPushButton("")
        self.sendObjBtn.setToolTip("Send obj mesh")
        self.sendObjBtn.setIconSize(QtCore.QSize(30,30))
        self.sendObjBtn.setFixedSize(40,40)
        self.sendObjBtn.setIcon(QtGui.QIcon(ICONPATH + "obj.png"))
        self.sendObjBtn.setDisabled(not self.connected)
        self.sendObjBtn.clicked.connect(lambda: self.mainUI._sendObjMesh(self.target, self.tabTargetID, self))
        self.actionButtonLayout.addWidget(self.sendObjBtn)
        self.widgetList.append(self.sendObjBtn)
        
        self.sendPictureBtn = QtGui.QPushButton("")
        self.sendPictureBtn.setToolTip("Send picture file")
        self.sendPictureBtn.setIconSize(QtCore.QSize(30,30))
        self.sendPictureBtn.setFixedSize(40,40)
        self.sendPictureBtn.setIcon(QtGui.QIcon(ICONPATH + "picture.png"))
        self.sendPictureBtn.setDisabled(not self.connected)
        self.sendPictureBtn.clicked.connect(lambda: self.mainUI._sendPic(self.target, self.tabTargetID, self))
        self.actionButtonLayout.addWidget(self.sendPictureBtn)
        self.widgetList.append(self.sendPictureBtn)
        
        self.actionButtonLayout.setAlignment(QtCore.Qt.AlignLeft)
        self.centralLayout.addItem(self.actionButtonLayout)
        
        self.setLayout(self.centralLayout)
        
    def appendMessage(self, header, message, fromMyself=False):
        
        if header:
            now = datetime.datetime.now()
            timeStamp = "{1}:{2} {0}:".format(header, str(now.hour).zfill(2), str(now.minute).zfill(2))
        
            if fromMyself:
                timeStamp = HComUtils.coloredString(timeStamp, "70738c", italic=True)
                
        else:
            timeStamp = ""
            
        msbBox = MessageBox(timeStamp, message, fromMyself)
        self.messageOutLayout.addWidget(msbBox)
        
    def appendInputBox(self, sender, dataType, data):
        
        now = datetime.datetime.now()
        timeStamp = "{1}:{2} {0}:".format(sender, str(now.hour).zfill(2), str(now.minute).zfill(2))
        
        message = "{0} wants to send you ".format(sender)
        
        if dataType == "otl":
            message += "a node.\n  => type: {0}, Name: {1}".format(data["OTL_TYPE"], data["OTL_NAME"])
            
        elif dataType == "mesh":
            message += "a mesh.\n  => type: {0}".format(data["MESH_TYPE"])
            
        elif dataType == "settings":
            message += "a node settings.\n  => type: {0}".format(data["OTL_TYPE"])
            
        elif dataType == "pic":
            message += "an image file.\n  => name: {0}".format(data["IMAGE_NAME"])
        
        data = [dataType, data]
        
        msbBox = MessageBox(timeStamp, message, data=data, isInputData=True, mainUi=self.mainUI, sender=sender)
        self.messageOutLayout.addWidget(msbBox)
        
    def disableTab(self, toggle):
        
        for w in self.widgetList:
            w.setDisabled(toggle)

class UserListDockWidget(QtGui.QWidget):
    
    def __init__(self, hcc, session_ID, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)
        
        self.hcc = hcc
        self.session_ID = session_ID
        
        self.mainUI = parent
        
        self.setObjectName("cw")
        mainLayout = QtGui.QVBoxLayout()
        mainLayout.setSpacing(5)
        
        self.setWindowTitle("User Connected:")
        
        self.userListW = UserListWidget(self.session_ID, mainUI = self.mainUI, parent=self)
        
        if self.hcc:
            try:
                users = self.hcc.root.getAllClients().keys()
            except  EOFError:
                pass
            else:
                for k in users:
                    self.userListW._addUser(k)
            
        mainLayout.addItem(self.userListW)
        
        folderButtonsLayout = QtGui.QHBoxLayout()
        folderButtonsLayout.setSpacing(10)
        
        self.openReveicedFolder = QtGui.QPushButton()
        self.openReveicedFolder.setToolTip("Open 'HCom My Received files' folder")
        self.openReveicedFolder.setFixedSize(QtCore.QSize(38,38))
        self.openReveicedFolder.setIconSize(QtCore.QSize(32,32))
        self.openReveicedFolder.setIcon(QtGui.QIcon(ICONPATH + "folder.png"))
        self.openReveicedFolder.clicked.connect(self._openReceivedFilesFolder)
        folderButtonsLayout.addWidget(self.openReveicedFolder)
        
        self.openHistoryBtn = QtGui.QPushButton()
        self.openHistoryBtn.setToolTip("Open history folder")
        self.openHistoryBtn.setFixedSize(QtCore.QSize(38,38))
        self.openHistoryBtn.setIconSize(QtCore.QSize(32,32))
        self.openHistoryBtn.setIcon(QtGui.QIcon(ICONPATH + "folder_hist.png"))
        self.openHistoryBtn.clicked.connect(self._openHistoryFolder)
        folderButtonsLayout.addWidget(self.openHistoryBtn)
        
        self.openHelp = QtGui.QPushButton()
        self.openHelp.setToolTip("Open help")
        self.openHelp.setFixedSize(QtCore.QSize(38,38))
        self.openHelp.setIconSize(QtCore.QSize(32,32))
        self.openHelp.setIcon(QtGui.QIcon(ICONPATH + "help.png"))
        self.openHelp.clicked.connect(self._showHelp)
        folderButtonsLayout.addWidget(self.openHelp)
        
        folderButtonsLayout.setAlignment(QtCore.Qt.AlignHCenter)
        mainLayout.addItem(folderButtonsLayout)
        
        self.setLayout(mainLayout)
        
    def _updateUserList(self, ID, action):
        
        if action == "join":
            self.userListW._addUser(ID)
        elif action == "left":
            self.userListW._removeUser(ID)
            
    def _openHistoryFolder(self):
        if os.path.exists(HISTORY_PATH):
            os.startfile(HISTORY_PATH)
        else:
            print("ERROR: History folder not found.")
            
    def _showHelp(self):
        
        helpWin = HelpWindow(self)
        helpWin.exec_()
    
    def _openReceivedFilesFolder(self):
        if os.path.exists(RECEIVED_FILES_PATH):
            os.startfile(RECEIVED_FILES_PATH)
        else:
            print("ERROR: Received files folder not found.")
        
class UserListWidget(QtGui.QVBoxLayout):
    
    def __init__(self, session_ID, mainUI=None, parent=None):
        
        QtGui.QVBoxLayout.__init__(self)
        self.setSpacing(5)
        self.session_ID = session_ID
        
        self.mainUi = mainUI
        
        self.ITEM_IDS = []
        
        splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        splitter.setStyleSheet(''' QSplitter::handle:vertical{height: 2px;}''')
        
        # user connected list
        self.userList = QtGui.QListWidget(parent=parent)
        self.userList.itemDoubleClicked.connect(self._selItem)
        splitter.addWidget(self.userList)
        
        # user connection and deconnection infos
        self.outuserInfo = QtGui.QTextEdit(parent=parent)
        self.outuserInfo.setReadOnly(True)
        splitter.addWidget(self.outuserInfo)
        
        splitter.setSizes([400,50])
        
        self.addWidget(splitter)
        
    def _selItem(self):
        
        idSelected = self.userList.currentItem().text()
        if not "(me)" in idSelected:
            self.mainUi._addUserTab(str(idSelected), fromUserList=True)
        
    def _addUser(self, ID):
               
        IDtoAdd = ID
        if ID == self.session_ID:
            IDtoAdd = "(me) " + ID
        
        if ID not in self.ITEM_IDS:
            self.ITEM_IDS.append(IDtoAdd)
        self.userList.addItem(IDtoAdd)

    def _removeUser(self, ID):
        
        if ID in self.ITEM_IDS:
            itemIndex = self.ITEM_IDS.index(ID)
            it = self.userList.takeItem(itemIndex)
            qIndex = self.userList.indexFromItem(it)
            model = self.userList.model()
            model.removeRow(qIndex.row())
            self.ITEM_IDS.remove(ID)
    
    def clearUserList(self):
        self.userList.clear()
        
class HelpWindow(QtGui.QDialog):
    
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent=parent)
        
        mainLayout = QtGui.QVBoxLayout()
        mainLayout.setSpacing(10)
        
        self.versionString = QtGui.QLabel("HCom Version {0}".format(HCOM_VERSION))
        mainLayout.addWidget(self.versionString)

        self.closeButton = QtGui.QPushButton("Close")
        self.closeButton.clicked.connect(self.close)
        mainLayout.addWidget(self.closeButton)
        
        self.setLayout(mainLayout)

class SettingsWindow(QtGui.QDialog):
    
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent=parent)
        
        initValues = HComUtils.readIni()
        
        self.SETTINGS = initValues
        
        self.setWindowTitle("HCom Settings")
        self.setWindowIcon(QtGui.QIcon(ICONPATH + "\\settings.png"))
        
        settingsLayout = QtGui.QVBoxLayout()
        settingsLayout.setSpacing(10)
        
        settingsLayout.addWidget(QtGui.QLabel("HCom version: {0}".format(HCOM_VERSION)))
        
        serverAdresslayout = QtGui.QHBoxLayout()
        serverAdresslayout.setSpacing(10)
        serverAdresslayout.addWidget(QtGui.QLabel("Server Adress:"))
        self.serverAdress = QtGui.QLineEdit(str(initValues["SERVER"]))
        serverAdresslayout.addWidget(self.serverAdress)
        settingsLayout.addItem(serverAdresslayout)
        
        serverPortlayout = QtGui.QHBoxLayout()
        serverPortlayout.setSpacing(10)
        serverPortlayout.addWidget(QtGui.QLabel("Server Port:"))
        self.serverPort = QtGui.QLineEdit(str(initValues["PORT"]))
        serverPortlayout.addWidget(self.serverPort)
        settingsLayout.addItem(serverPortlayout)
        
        self.switchToManualMode = QtGui.QCheckBox("Auto Switch To Manual Update")
        self.switchToManualMode.setChecked(initValues["SWITCH_TO_MANUAL_UPDATE"])
        settingsLayout.addWidget(self.switchToManualMode)
        
        self.showOpenChatRoom = QtGui.QCheckBox("Show Open Chat Room")
        self.showOpenChatRoom.setChecked(initValues["SHOW_OPEN_CHAT"])
        settingsLayout.addWidget(self.showOpenChatRoom)
        
        self.saveHistory = QtGui.QCheckBox("Save Conversation history")
        self.saveHistory.setChecked(initValues["SAVE_HISTORY"])
        settingsLayout.addWidget(self.saveHistory)
        
        buttonsLayout = QtGui.QHBoxLayout()
        buttonsLayout.setSpacing(10)
        
        self.validBtn = QtGui.QPushButton("Valid")
        self.validBtn.clicked.connect(self.validSettings)
        buttonsLayout.addWidget(self.validBtn)
        
        self.cancelBtn = QtGui.QPushButton("Cancel")
        self.cancelBtn.clicked.connect(self.cancelSettings)
        buttonsLayout.addWidget(self.cancelBtn)
        
        settingsLayout.addItem(buttonsLayout)
        
        settingsLayout.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(settingsLayout)
    
    def validSettings(self):
        
        self.SETTINGS["SERVER"] = str(self.serverAdress.text())
        self.SETTINGS["PORT"] = str(self.serverPort.text())
        self.SETTINGS["SWITCH_TO_MANUAL_UPDATE"] = str(self.switchToManualMode.isChecked())
        self.SETTINGS["SHOW_OPEN_CHAT"] = str(self.showOpenChatRoom.isChecked())
        
        HComUtils.writeIni(self.SETTINGS)
        self.close()
    
    def cancelSettings(self):
        self.close()

class MessageBox(QtGui.QWidget):
    
    def __init__(self, header, message, fromMyself=False, mainUi=None, data=False, isInputData=False, sender=""):
        QtGui.QWidget.__init__(self)
        
        if data:
            self.dataType = data[0]
            self.dataDict = data[1]
        else:
            self.dataType = ""
            self.dataDict = {}
            
        self.sender = sender
        self.mainUi = mainUi
        
        self.setObjectName("msgw")
        
        self.mainLayout = QtGui.QVBoxLayout()
        self.mainLayout.setSpacing(1)
        
        if not isInputData:
            if header:
                self.headerMsg = QtGui.QLabel(header)
                self.mainLayout.addWidget(self.headerMsg)
            
        self.msg = QtGui.QTextEdit()
        if fromMyself:
            self.msg.setStyleSheet('''QTextEdit{background-color:rgba(128,128,128,0); border:None}''')
        else:
            self.msg.setStyleSheet('''QTextEdit{background-color:rgba(100,110,140,0); border:None}''')
            
        self.msg.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        
        txtDoc = QtGui.QTextDocument(message)
        self.msg.setReadOnly(True)
        self.msg.setDocument(txtDoc)
        h = self.msg.document().size().height()
        self.msg.setMinimumHeight(h+15)
        
        self.mainLayout.addWidget(self.msg)
        
        if isInputData:
            self.buttonLayout = QtGui.QHBoxLayout()
            self.buttonLayout.setSpacing(5)
            
            self.acceptBtn = QtGui.QPushButton("Accept")
            self.acceptBtn.setFixedWidth(75)
            self.acceptBtn.clicked.connect(self.acceptInput)
            self.cancelBtn = QtGui.QPushButton("Cancel")
            self.cancelBtn.setFixedWidth(75)
            self.cancelBtn.clicked.connect(self.cancelInput)
            
            self.buttonLayout.addWidget(self.acceptBtn)
            self.buttonLayout.addWidget(self.cancelBtn)
            
            self.buttonLayout.setAlignment(QtCore.Qt.AlignRight)
            
            self.mainLayout.addItem(self.buttonLayout)
            self.setFixedHeight(h+50)
            
        else:
            self.setFixedHeight(h+15)
            
        self.setLayout(self.mainLayout)
        
    def cancelInput(self):
        
        self.dataDict = None
        
        self.acceptBtn.setDisabled(True)
        self.cancelBtn.setDisabled(True)
        
    def acceptInput(self):
        
        settings = HComUtils.readIni()
        
        # Send a setting of parms for the given node selection type
        if self.dataType == "settings":
            HComUtils.setOtlSettings(self.dataDict, sender=self.sender, settings=settings)
        
        # Send an otl or a node
        elif self.dataType == "otl":
            HComUtils.createOtl(self.dataDict, sender=self.sender, settings=settings)
                
        # Bgeo mesh
        elif self.dataType == "mesh":
            HComUtils.createMesh(self.dataDict, sender=self.sender, settings=settings)
     
        # Pictures
        elif self.dataType == "pic":
            HComUtils.createPic(self.dataDict, sender=self.sender, settings=settings)
        
        self.acceptBtn.setDisabled(True)
        self.cancelBtn.setDisabled(True)