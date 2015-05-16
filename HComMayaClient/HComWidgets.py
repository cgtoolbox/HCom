import os
import datetime
import time
import webbrowser

import PySide.QtGui as QtGui
import PySide.QtCore as QtCore

import HComUtils
import HComClient

HCOM_VERSION = "0.7.0"

ICONPATH = os.path.dirname(__file__) + "\\HCom_Icons\\"
HISTORY_PATH = os.path.dirname(__file__) + "\\HCom_History"
RECEIVED_FILES_PATH = os.path.dirname(__file__) + "\\HCom_Received_Files"

###########################################
# THREADS
###########################################
class RecieveDataThread(QtCore.QThread):
    '''
        Thread used to update message box when a client is writing a data.
    '''
    dataRecieved_signal = QtCore.Signal(object)
    
    def __init__(self):
        QtCore.QThread.__init__(self)
        
        self.dataDict = None
        self._sender = None
        self.settings = None

    def run(self):
        
        result = self.workFonc(self.dataDict, self.sender, self.settings)
        self.dataRecieved_signal.emit(result)
    
    def workFonc(self, *args, **kwargs):
        return
    
class SendingDataThread(QtCore.QThread):
    '''
        Thread used to update the progress bar when a client is sending a data to the server.
    '''
    dataSent_signal = QtCore.Signal(int)
    
    def __init__(self):
        
        QtCore.QThread.__init__(self)
        self.target_clientID = None
        self.sender = None
        self.tabTarget = None
        self.imagePath = None
        
    def run(self):
        
        if self.imagePath:
            result = self.workFunc(self.target_clientID, self.sender, self.tabTarget, self.imagePath)
        else:
            result = self.workFunc(self.target_clientID, self.sender, self.tabTarget)
        
        if result:
            self.dataSent_signal.emit(1)
        else:
            self.dataSent_signal.emit(0)
            
    def workFunc(self, *args, **kwargs):
        pass

class UiUpdaterThread(QtCore.QThread):
    '''
       Thread used for all update made on main UI
       This include appening a message, receiving confirmation
       Change icons states 
    '''
    # Type of UI changement
    update_ui_signal = QtCore.Signal(object)
    
    # Header, Message, tabTarget
    append_message_signal = QtCore.Signal(object)
    
    # sender, dataType, dataDict, tabTarget
    input_data_signal = QtCore.Signal(object)
    
    # Send a data received update
    data_received_update = QtCore.Signal(object)
    
    def __init__(self):
        QtCore.QThread.__init__(self)
        
        self.data = {}
        self.messageData = {}
        self.forceStop = False
        self.inputData = {}
        self.dataReceivedUpdate = False
        
    def run(self):
        
        while 1:
            time.sleep(0.1)
            
            if self.forceStop:
                break
            
            if len(self.data.keys()) > 0:
                self.update_ui_signal.emit(self.data)
                self.data = {}
                
            if len(self.messageData.keys()) > 0:
                self.append_message_signal.emit(self.messageData)
                self.messageData = {}
                
            if len(self.inputData.keys()) > 0:
                self.input_data_signal.emit(self.inputData)
                self.inputData = {}
                
            if self.dataReceivedUpdate:
                self.data_received_update.emit(self.dataReceivedUpdate)
                self.dataReceivedUpdate = False

###########################################
# WIDGETS
###########################################

class UserChatTabWidget(QtGui.QWidget):
    '''
        Widget appended to the main tab widget when a user double click
        on a user name or when a user receive a message from a user
    '''
    
    def __init__(self, target, clientType, openChatRoom=False, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)
        
        self.mainUI = parent
        self.connected = self.mainUI.connected
        self.clientType = clientType
        
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
            
        self.clearTabBtn = QtGui.QPushButton("")
        self.clearTabBtn.clicked.connect(self.clearTab)
        self.clearTabBtn.setStyleSheet('''QPushButton#closebtn{ background-color: rgba(0,0,0,0); border: none; }''')
        self.clearTabBtn.setFlat(True)
        self.clearTabBtn.setToolTip("Clear messages")
        self.clearTabBtn.setFixedSize(QtCore.QSize(32,32))
        self.clearTabBtn.setIcon(QtGui.QIcon(ICONPATH + "clearmsg.png"))
        self.targetLayout.addWidget(self.clearTabBtn)
        
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
        
        self.targetLayout.setAlignment(QtCore.Qt.AlignLeft)
        
        self.centralLayout.addItem(self.targetLayout)
        
        # Message widget
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
        self.messageLine = InputMessageBox(self)
        self.messageLine.setMaximumHeight(50)
        self.messageLine.setDisabled(not self.connected)
        self.messageLayout.addWidget(self.messageLine)
        self.widgetList.append(self.messageLine)
        
        self.messageSendBtn = QtGui.QPushButton("Send Message")
        self.messageSendBtn.clicked.connect(lambda: self.mainUI._sendMessage(self.target, str(self.messageLine.toPlainText().encode('latin-1')), self, self.tabTargetID))
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
        
        self.sendObjBtn = QtGui.QPushButton("")
        self.sendObjBtn.setToolTip("Send obj mesh")
        self.sendObjBtn.setIconSize(QtCore.QSize(32,32))
        self.sendObjBtn.setFixedSize(40,40)
        self.sendObjBtn.setIcon(QtGui.QIcon(ICONPATH + "obj.png"))
        self.sendObjBtn.setDisabled(not self.connected)
        self.sendObjBtn.clicked.connect(lambda: self.mainUI._sendObjMesh(self.target, self.tabTargetID, self))
        self.actionButtonLayout.addWidget(self.sendObjBtn)
        self.widgetList.append(self.sendObjBtn)
        
        self.sendAlembicBtn = QtGui.QPushButton("")
        self.sendAlembicBtn.setToolTip("Send alembic cache")
        self.sendAlembicBtn.setIconSize(QtCore.QSize(32,32))
        self.sendAlembicBtn.setFixedSize(40,40)
        self.sendAlembicBtn.setIcon(QtGui.QIcon(ICONPATH + "alembic.png"))
        self.sendAlembicBtn.setDisabled(not self.connected)
        self.sendAlembicBtn.clicked.connect(lambda: self.mainUI._sendAlembic(self.target, self.tabTargetID, self))
        self.actionButtonLayout.addWidget(self.sendAlembicBtn)
        self.widgetList.append(self.sendAlembicBtn)
        
        self.sendPictureBtn = QtGui.QPushButton("")
        self.sendPictureBtn.setToolTip("Send picture file")
        self.sendPictureBtn.setIconSize(QtCore.QSize(32,32))
        self.sendPictureBtn.setFixedSize(40,40)
        self.sendPictureBtn.setIcon(QtGui.QIcon(ICONPATH + "picture.png"))
        self.sendPictureBtn.setDisabled(not self.connected)
        self.sendPictureBtn.clicked.connect(lambda: self.mainUI._sendPic(self.target, self.tabTargetID, self))
        self.actionButtonLayout.addWidget(self.sendPictureBtn)
        self.widgetList.append(self.sendPictureBtn)
        
        self.actionButtonLayout.setAlignment(QtCore.Qt.AlignLeft)
        self.centralLayout.addItem(self.actionButtonLayout)
        
        self.setLayout(self.centralLayout)
        
    def clearTab(self):
        
        nmsg = self.messageOutLayout.count()
        if nmsg == 0: return
        widgets = []
        for i in range(nmsg):
            w = self.messageOutLayout.itemAt(i)
            widgets.append(w.widget())
            
        for w in widgets:
            w.setParent(None)
            w.deleteLater()
        
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
        self.messageOutLayout.update()
        
        self.messageScrollArea.ensureWidgetVisible(self.messageOutLayout.widget())
        
    def appendInputBox(self, _sender, dataType, data):
        
        now = datetime.datetime.now()
        
        timeStamp = str(_sender) + ":" + str(now.hour).zfill(2) + ":" + str(now.minute).zfill(2) + ":"
        message = str(_sender) + " wants to send you "
        
        if dataType == "otl":
            message += "a node.\n  => type: " + str(data["OTL_TYPE"]) + ", Name: " + str(data["OTL_NAME"])
            
        elif dataType == "mesh":
            message += "a mesh.\n  => type: " + str(data["MESH_TYPE"])
            
        elif dataType == "settings":
            message += "a node settings.\n  => type: " + str(data["OTL_TYPE"])
            
        elif dataType == "pic":
            message += "an image file.\n  => name: "+ str(data["IMAGE_NAME"])
        
        elif dataType == "alembic":
            message += "an alembic cache file.\n  => name: " + str(data["NAME"])
        
        data = [dataType, data]
        
        msbBox = MessageBox(timeStamp, message, data=data, isInputData=True, mainUi=self.mainUI, _sender=_sender)
        self.messageOutLayout.addWidget(msbBox)
        
    def appendDataSendBox(self, msg, targets, _sender, tabTarget, workFunc, imagePath=None):
        
        box = SendingDataMessageBox(msg, targets, _sender, tabTarget, workFunc, imagePath=imagePath, parent=self)
        self.messageOutLayout.addWidget(box)
        box.workerThread.start()
        
    def disableTab(self, toggle):
        
        for w in self.widgetList:
            w.setDisabled(toggle)

class UserListDockWidget(QtGui.QWidget):
    '''
        Widget use as container for the user list and user connection infos
    '''
    def __init__(self, hcc, session_ID, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)
        
        self.hcc = hcc
        self.session_ID = session_ID
        
        self.mainUI = parent
        
        self.setObjectName("cw")
        mainLayout = QtGui.QVBoxLayout()
        mainLayout.setSpacing(5)
        
        self.setWindowTitle("User Connected:")
        
        self.userListW = UserListWidget(self.session_ID, clientType=self.mainUI.CLIENT_TYPE, mainUI=self.mainUI, parent=self)
        
        if self.hcc:
            try:
                users = self.hcc.root.getAllClients().keys()
                usersType = self.hcc.root.getAllClientTypes()
            except  EOFError:
                pass
            else:
                for k in users:
                    self.userListW._addUser(k, usersType[k])
            
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
        
    def _updateUserList(self, ID, action, clientType):
        
        if action == "join":
            self.userListW._addUser(ID, clientType)
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
    '''
        User list connected, used only in UserListDockWidget
    '''
    def __init__(self, session_ID, clientType="None", mainUI=None, parent=None):
        
        QtGui.QVBoxLayout.__init__(self)
        self.setSpacing(5)
        self.session_ID = session_ID
        self.clientType = clientType
        
        self.mainUi = mainUI
        
        self.ITEM_IDS = []
        
        splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        splitter.setStyleSheet(''' QSplitter::handle:vertical{height: 2px;}''')
        
        # user connected list
        self.userList = QtGui.QListWidget(parent=parent)
        self.userList.setSpacing(2)
        self.userList.itemDoubleClicked.connect(self._selItem)
        splitter.addWidget(self.userList)
        
        # user connection and deconnection infos
        self.outuserInfo = QtGui.QTextEdit(parent=parent)
        self.outuserInfo.setReadOnly(True)
        splitter.addWidget(self.outuserInfo)
        
        splitter.setSizes([400,50])
        
        self.addWidget(splitter)
        
    def _selItem(self):
        
        curItem = self.userList.currentItem()
        idSelected = curItem.text()
        if not "(me)" in idSelected:
            self.mainUi._addUserTab(str(idSelected), curItem.clientType, fromUserList=True)
        
    def _addUser(self, ID, clientType):
               
        IDtoAdd = ID
        
        if ID == self.session_ID:
            IDtoAdd = "(me) " + ID
        
        userObj = UserItem(IDtoAdd, clientType)
        
        if ID not in self.ITEM_IDS:
            self.ITEM_IDS.append(IDtoAdd)

        self.userList.addItem(userObj)

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
        
class UserItem(QtGui.QListWidgetItem):
    
    def __init__(self, text, clientType=[None,None]):
        QtGui.QListWidgetItem.__init__(self)
        
        self.ID = text
        self.clientType = clientType
        self.setIcon(QtGui.QIcon(ICONPATH + str(self.clientType[0]).lower() + ".png"))
        self.setToolTip(str(self.clientType[-1]))
        self.setText(text)


class HelpWindow(QtGui.QDialog):
    '''
        help / infos window
    '''
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent=parent)
        
        mainLayout = QtGui.QVBoxLayout()
        mainLayout.setSpacing(10)
        
        self.versionString = QtGui.QLabel("HCom Version {0}".format(HCOM_VERSION))
        mainLayout.addWidget(self.versionString)
        
        self.onlineHelpBtn = QtGui.QPushButton("Online Help")
        self.onlineHelpBtn.clicked.connect(self.openOnlineHelp)
        mainLayout.addWidget(self.onlineHelpBtn)

        self.closeButton = QtGui.QPushButton("Close")
        self.closeButton.clicked.connect(self.close)
        mainLayout.addWidget(self.closeButton)
        
        self.setLayout(mainLayout)
        
    def openOnlineHelp(self):
        webbrowser.open('http://guillaumejobst.blogspot.fr/p/hcom.html')

class SettingsWindow(QtGui.QDialog):
    '''
        The setting and options window
    '''
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

        self.saveHistory = QtGui.QCheckBox("Save Conversation history")
        self.saveHistory.setChecked(bool(initValues["SAVE_HISTORY"]))
        settingsLayout.addWidget(self.saveHistory)
        
        self.playSounds = QtGui.QCheckBox("Play Sounds")
        self.playSounds.setChecked(bool(initValues["PLAY_SOUND"]))
        settingsLayout.addWidget(self.playSounds)
        
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
        self.SETTINGS["PLAY_SOUND"] = str(self.playSounds.isChecked())
        
        HComUtils.writeIni(self.SETTINGS)
        self.close()
    
    def cancelSettings(self):
        self.close()


class SendingDataMessageBox(QtGui.QWidget):
    '''
        Widget added to the current tab when data are being sent by a user
    '''
    def __init__(self, msg, target_clientID, _sender, tabTarget, workFunc, imagePath=None, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)
        
        self.workerThread = SendingDataThread()
        self.workerThread.workFunc = workFunc
        self.workerThread.target_clientID = target_clientID
        self.workerThread.tabTarget = tabTarget
        self.workerThread.sender = _sender
        self.workerThread.imagePath = imagePath
        self.workerThread.dataSent_signal.connect(self.dataSent)
        
        layout= QtGui.QVBoxLayout()
        layout.setSpacing(5)
        
        self.msg = QtGui.QLabel(msg)
        layout.addWidget(self.msg)
        
        self.progressBar = QtGui.QProgressBar()
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(0)
        self.progressBar.setFixedHeight(4)
        self.progressBar.setTextVisible(False)
        layout.addWidget(self.progressBar)
        
        self.setLayout(layout)
        
    def dataSent(self, result):
        
        if result:
            mod = " sent !"
        else:
            mod = " cancelled !"
        
        tmp = str(self.msg.text()).replace("Sending ", "") + mod
        
        self.msg.setText(tmp)
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(1)
        self.progressBar.setValue(1)
        if result:
            self.progressBar.setStyleSheet('''QProgressBar::chunk{background:green;}''')
        else:
            self.progressBar.setStyleSheet('''QProgressBar::chunk{background:red;}''')
            
class MessageBox(QtGui.QWidget):
    '''
        Widget added to the current tab when a user is receiving data from another client
    '''
    def __init__(self, header, message, fromMyself=False, mainUi=None, data=False, isInputData=False, _sender=""):
        QtGui.QWidget.__init__(self)
        
        if data:
            self.dataType = data[0]
            self.dataDict = data[1]
        else:
            self.dataType = ""
            self.dataDict = {}
            
        self._sender = _sender
        self.mainUi = mainUi
        
        self.workThread = RecieveDataThread()
        self.workThread.dataRecieved_signal.connect(self.endJob)
        self.workThread.dataDict = self.dataDict
        self.workThread._sender = self._sender
        
        self.setObjectName("msgw")
        
        self.mainLayout = QtGui.QVBoxLayout()
        self.mainLayout.setSpacing(5)
        
        if not isInputData:
            if header:
                self.headerMsg = QtGui.QLabel(header)
                self.mainLayout.addWidget(self.headerMsg)
            
        self.msg = QtGui.QLabel(message)
        self.msg.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        if fromMyself:
            self.msg.setStyleSheet('''QLabel{background-color:rgba(128,128,128,0); border:None}''')
        else:
            self.msg.setStyleSheet('''QLabel{background-color:rgba(100,110,140,0); border:None}''')

        
        self.mainLayout.addWidget(self.msg)
        
        if isInputData:
            
            self.activityBar = QtGui.QProgressBar()
            self.activityBar.setMinimum(0)
            self.activityBar.setVisible(False)
            self.activityBar.setFixedHeight(4)
            
            self.buttonLayout = QtGui.QHBoxLayout()
            self.buttonLayout.setSpacing(5)
            
            self.mainLayout.addWidget(self.activityBar)
            
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
            
        self.setLayout(self.mainLayout)
        
    def cancelInput(self):
        
        self.dataDict = None
        
        self.acceptBtn.setDisabled(True)
        self.cancelBtn.setDisabled(True)
        
        HComClient.sendDataReceivedInfo(self.sender, self.mainUi.ID, [False, self.dataType], self.mainUi.ID)
        
    def acceptInput(self):
        
        settings = HComUtils.readIni()
        self.activityBar.setMaximum(0)
        self.activityBar.setTextVisible(False)
        self.activityBar.setVisible(True)
        
        self.workThread.settings = settings

        # Send an otl or a node
        if self.dataType == "otl":
            
            self.workThread.workFonc = HComUtils.createOtl
            self.workThread.start()
                
        # Bgeo mesh
        elif self.dataType == "mesh":
            
            self.workThread.workFonc = HComUtils.createMesh
            self.workThread.start()
     
        # Pictures
        elif self.dataType == "pic":
            
            self.workThread.workFonc = HComUtils.createPic
            self.workThread.start()
            
        # Alembic
        elif self.dataType == "alembic":
            
            self.workThread.workFonc = HComUtils.createAlembic
            self.workThread.start()
            
        self.acceptBtn.setDisabled(True)
        self.cancelBtn.setDisabled(True)
            
        
    def endJob(self, result=None):
        
        if result:
            self.activityBar.setStyleSheet('''QProgressBar::chunk{background:green;}''')
        else:
            self.activityBar.setStyleSheet('''QProgressBar::chunk{background:red;}''')
                
        HComClient.sendDataReceivedInfo(self.sender, self.mainUi.ID, [True, self.dataType], self.mainUi.ID)
        self.activityBar.setMaximum(1)
        self.activityBar.setValue(1)
        self.activityBar.setStyleSheet('''QProgressBar::chunk{background:green;}''')
        self.dataDict = None
        

class InputMessageBox(QtGui.QTextEdit):
    '''
        Custom message text field
    '''
    def __init__(self, parent):
        super(self.__class__, self).__init__()
        
        self.parent = parent
                    
    def keyPressEvent(self, event):
        
        mod = QtGui.QApplication.keyboardModifiers()

        if (event.key() == QtCore.Qt.Key_Enter or event.key() == QtCore.Qt.Key_Return) and mod == QtCore.Qt.ShiftModifier:
            self.append("")
        
        elif  (event.key() == QtCore.Qt.Key_Enter or event.key() == QtCore.Qt.Key_Return) and mod != QtCore.Qt.ShiftModifier:
            self.parent.mainUI._sendMessage(self.parent.target, str(self.toPlainText().encode('latin-1')), self.parent, self.parent.tabTargetID)
        
        else:
            super(self.__class__, self).keyPressEvent(event)
            
class FrameRangeSelection(QtGui.QDialog):
    
    def __init__(self, start=0, end=100, parent=None):
        QtGui.QDialog.__init__(self, parent=parent)
        
        self.frameRange = [start, end]
        self.VALID = False
    
        mainLayout = QtGui.QVBoxLayout()
        mainLayout.setSpacing(10)
        
        mainLayout.addWidget(QtGui.QLabel("Enter a frame range:"))
        
        frameLayout = QtGui.QHBoxLayout()
        frameLayout.setSpacing(10)
        
        frameLayout.addWidget(QtGui.QLabel("Start Frame:"))
        self.startValue = QtGui.QDoubleSpinBox()
        self.startValue.setMinimum(-999999.9)
        self.startValue.setMaximum(999999.9)
        self.startValue.setValue(start)
        frameLayout.addWidget(self.startValue)
        
        frameLayout.addWidget(QtGui.QLabel("End Frame:"))
        self.endValue = QtGui.QDoubleSpinBox()
        self.endValue.setMinimum(-999999.9)
        self.endValue.setMaximum(999999.9)
        self.endValue.setValue(end)
        frameLayout.addWidget(self.endValue)
        
        mainLayout.addItem(frameLayout)
        
        buttonsLayout = QtGui.QHBoxLayout()
        buttonsLayout.setSpacing(5)
        
        acceptBtn = QtGui.QPushButton("Accept")
        acceptBtn.clicked.connect(self.validFrameRange)
        buttonsLayout.addWidget(acceptBtn)
        
        closeBtn = QtGui.QPushButton("Cancel")
        closeBtn.clicked.connect(self.close)
        buttonsLayout.addWidget(closeBtn)
        
        mainLayout.addItem(buttonsLayout)
        
        self.setLayout(mainLayout)
        
    def validFrameRange(self):
        
        start = self.startValue.value()
        end = self.endValue.value()
        self.frameRange = [start, end]
        self.VALID= True
        self.close()
        
