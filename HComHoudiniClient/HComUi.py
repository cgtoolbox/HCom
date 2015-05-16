import hou
import getpass
import time
import datetime
import socket
import os

import PySide.QtGui as QtGui
import PySide.QtCore as QtCore

import HComClient
import HComUtils
reload(HComUtils)
import HComWidgets
reload(HComWidgets)

if not hasattr(hou.session, "HCOM_TABS"):
    hou.session.HCOM_TABS = {}

global HComMainUi
HComMainUi = None

ICONPATH = os.path.dirname(__file__) + "\\HCom_Icons\\"
RECEIVED_FILES = os.path.dirname(__file__)  + "\\HCom_Received_Files\\"

class HComMainView(QtGui.QFrame):
    
    def __init__(self, connected):
        QtGui.QFrame.__init__(self)
        
        self.CLIENT_TYPE = [HComUtils.CLIENT_TYPE.HOUDINI,
                            hou.applicationName() + " " + hou.applicationVersionString()]
        
        self.updateUiThread = HComWidgets.UiUpdaterThread()
        self.updateUiThread.update_ui_signal.connect(self._updateUi)
        self.updateUiThread.append_message_signal.connect(self._appendMessageToTab)
        self.updateUiThread.input_data_signal.connect(self._getInputData)
        self.updateUiThread.data_received_update.connect(self._dataReveivedUpdate)
        self.updateUiThread.start()
        
        self.connected = connected
        if hou.session.HCOM_TABS != {}:
            self.USER_TABS = hou.session.HCOM_TABS
        else:
            self.USER_TABS = {}
        
        if not self.connected:
            self.hcc = False
            self.ID = ""
        else:
            self.hcc = hou.session.HCOMCLIENT[0]
            self.ID = hou.session.HCOMCLIENT[1]
        
        self.mainLayout = QtGui.QVBoxLayout()
        self.mainLayout.setSpacing(10)
        
        self.splitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        self.centralLayout = QtGui.QVBoxLayout()
        self.centralWidget = QtGui.QWidget()
        
        self.__init_header()
        self.__init_userList()
        self.__init_centralWidget()
        
        # Set Layout
        self.splitter.setSizes([100,500])
        self.splitter.setStyleSheet('''QSplitter::handle:vertical{height: 2px}''')
        self.mainLayout.addWidget(self.splitter)

        self.setLayout(self.mainLayout)
    

    def __init_header(self):
        
        # Init Title
        self.titleLayout = QtGui.QHBoxLayout()
        self.titleLayout.setSpacing(10)
        
        self.iconLbl = QtGui.QLabel()
        self.iconLbl.setFixedHeight(42)
        self.iconLbl.setFixedWidth(42)
        self.iconLbl.setPixmap(QtGui.QPixmap(ICONPATH + "hcom.png"))
        self.titleLayout.addWidget(self.iconLbl)
        
        self.ID_lbl = QtGui.QLabel("Enter Name:")
        self.ID_lbl.setDisabled(self.connected)
        self.titleLayout.addWidget(self.ID_lbl)
        
        if hasattr(hou.session, "HCOM_CUR_ID"):
            defaultName = hou.session.HCOM_CUR_ID
        else:
            defaultName = getpass.getuser().replace(".", "_") + "_" + socket.gethostname().split("-")[0]
        
        self.ID_line = QtGui.QLineEdit(defaultName)
        self.ID_line.setDisabled(self.connected)
        self.ID_line.returnPressed.connect(self._rdnname)
        self.titleLayout.addWidget(self.ID_line)
        
        self.title = QtGui.QLabel("")
        
        if self.connected:
            self.title.setText("Connected")
        else:
            self.title.setText("Not Connected")
        
        self.titleLayout.addWidget(self.title)
        
        self.connectBtn = QtGui.QPushButton("")
        self.connectBtn.setToolTip("Connect to HCom")
        self.connectBtn.setIcon(QtGui.QIcon(ICONPATH + "connect.png"))
        self.connectBtn.setIconSize(QtCore.QSize(32,32))
        self.connectBtn.setFixedSize(QtCore.QSize(40,40))
        self.connectBtn.setVisible(not self.connected)
        self.connectBtn.clicked.connect(self._connectToHCom)
        self.titleLayout.addWidget(self.connectBtn)
        
        self.disconnectBtn = QtGui.QPushButton("")
        self.disconnectBtn.setToolTip("Disconnect HCom")
        self.disconnectBtn.setIcon(QtGui.QIcon(ICONPATH + "disconnect.png"))
        self.disconnectBtn.setIconSize(QtCore.QSize(32,32))
        self.disconnectBtn.setFixedSize(QtCore.QSize(40,40))
        self.disconnectBtn.setVisible(self.connected)
        self.disconnectBtn.clicked.connect(lambda: self._switchConnection(False))
        self.titleLayout.addWidget(self.disconnectBtn)
        
        # Settings button
        self.settingsBtn = QtGui.QPushButton("")
        self.settingsBtn.setToolTip("Settings")
        self.settingsBtn.setFixedSize(40,40)
        self.settingsBtn.setIcon(QtGui.QIcon(ICONPATH + "\\settings.png"))
        self.settingsBtn.setIconSize(QtCore.QSize(36,36))
        self.settingsBtn.clicked.connect(self._showSettings)
        self.titleLayout.addWidget(self.settingsBtn)
        
        self.mainLayout.addItem(self.titleLayout)
    
    def __init_userList(self):
        
        self.userListLayout = QtGui.QHBoxLayout()
        self.userListWidget = QtGui.QWidget()
        
        self.userListWidget = HComWidgets.UserListDockWidget(self.hcc, self.ID, self)
        self.userListWidget.session_ID = self.ID
        self.userListWidget.userListW.session_ID = self.ID
        self.userListLayout.addWidget(self.userListWidget)
        
        self.userListLayout.setSizeConstraint(QtGui.QLayout.SetMinimumSize)
        
        self.userListWidget.setLayout(self.userListLayout)
        self.splitter.addWidget(self.userListWidget)
    
    def __init_centralWidget(self):
        
        self.centralTabWidget = QtGui.QTabWidget()
        self.centralTabWidget.setStyleSheet('''QTabWidget{background-color:red;}''')
        self.centralTabWidget.currentChanged.connect(self._updateTabIcon)
        
        if hou.session.HCOM_TABS != {}:
            if "OPEN_CHAT_ROOM" in hou.session.HCOM_TABS.keys():
                tab = hou.session.HCOM_TABS["OPEN_CHAT_ROOM"]
                self.USER_TABS["OPEN_CHAT_ROOM"] = tab
                self.openChatRoom = tab
                self.centralTabWidget.addTab(self.openChatRoom, "Open Chat Room")
                
            for k in hou.session.HCOM_TABS.keys():
                if k == "OPEN_CHAT_ROOM": continue
                tab = hou.session.HCOM_TABS[k]
                self.centralTabWidget.addTab(tab, k)
        else:
            self.openChatRoom = HComWidgets.UserChatTabWidget("OPEN_CHAT_ROOM", clientType="None", openChatRoom=True, parent=self)
            self.centralTabWidget.addTab(self.openChatRoom, "Open Chat Room")
            self.USER_TABS["OPEN_CHAT_ROOM"] = self.openChatRoom
            hou.session.HCOM_TABS["OPEN_CHAT_ROOM"] = self.openChatRoom
        
        self.splitter.addWidget(self.centralTabWidget)

    def _getInputData(self, in_data):
        '''
            Fetch data from client and add confirmation widget to the chat
        '''
        
        _sender = in_data["SENDER"]
        dataType = in_data["DATA_TYPE"]
        data = in_data["DATA"]
        tabTarget = in_data["TAB_TARGET"]
        
        if not tabTarget in self.USER_TABS.keys():
            return False
        
        curTab = self.centralTabWidget.currentWidget()
        
        if self.USER_TABS[tabTarget] != curTab:
            targetTabIdx = self.centralTabWidget.indexOf(self.USER_TABS[tabTarget])
            self.centralTabWidget.tabBar().setTabIcon(targetTabIdx, QtGui.QIcon(ICONPATH + "unreadmsg.png"))
            
            settings = HComUtils.readIni()
            if "PLAY_SOUND" in settings.keys():
                if settings["PLAY_SOUND"]:
                    s = QtGui.QSound(ICONPATH + "gnm.wav")
                    s.play()
            
        self.USER_TABS[tabTarget].appendInputBox(_sender, dataType, data)
        

    def _updateUi(self, data):
        '''
            This methode is triggered by the update UI thread from HComWidget
        '''
        
        action = data["ACTION"]
        ID = data["ID"]
        clientType = data["CLIENT_TYPE"]
        
        now = datetime.datetime.now()
        
        if action == "server_disconnect":
            self._switchConnection(False)
            
        elif action == "join":
            if ID != self.ID:
                self.userListWidget._updateUserList(ID, action, clientType)
                IDLabel = "<FONT COLOR=#4b5488><i>{1}:{2} {0} join</i></FONT>".format(ID, str(now.hour).zfill(2), str(now.minute).zfill(2))
                self.userListWidget.userListW.outuserInfo.append(IDLabel)
        
        elif action == "left":
            if ID != self.ID:
                self.userListWidget._updateUserList(ID, action, clientType)
                IDLabel = "<FONT COLOR=#4b5488><i>{1}:{2} {0} left</i></FONT>".format(ID, str(now.hour).zfill(2), str(now.minute).zfill(2))
                self.userListWidget.userListW.outuserInfo.append(IDLabel)
                self._removeUserTab(ID)
                
        elif action == "add_tab":
            self._addUserTab(ID, clientType)
            

    def _dataReveivedUpdate(self, data):
        
        self._appendMessageToTab(data)
            
    def _updateTabIcon(self, idx):
        
        self.centralTabWidget.tabBar().setTabIcon(idx, QtGui.QIcon(""))
            
    def _appendMessageToTab(self, data):
        
        tabTarget = data["TAB_TARGET"]
        sender = data["SENDER"]
        message = data["MESSAGE"]

        if not tabTarget in self.USER_TABS.keys():
            return False
        
        curTab = self.centralTabWidget.currentWidget()   
        
        if self.USER_TABS[tabTarget] != curTab:
            targetTabIdx = self.centralTabWidget.indexOf(self.USER_TABS[tabTarget])
            self.centralTabWidget.tabBar().setTabIcon(targetTabIdx, QtGui.QIcon(ICONPATH + "unreadmsg.png"))
            
            settings = HComUtils.readIni()
            if "PLAY_SOUND" in settings.keys():
                if settings["PLAY_SOUND"]:
                    s = QtGui.QSound(ICONPATH + "gnm.wav")
                    s.play()
            
        self.USER_TABS[tabTarget].appendMessage(sender, message)
        
        hou.session.HCOM_TABS = self.USER_TABS
        
    def _sendMessage(self, targets, message, tab, tabTarget):
        
        if not message:
            return
        
        settings = HComUtils.readIni()
        
        if targets:
            result = HComClient.sendMessage(targets, self.ID, message, tabTarget)
        
            if isinstance(result, list):
                
                for i in result:
                    tab.outMessage.append("Error: User '{0}' not found.\n".format(i))
                
        now = datetime.datetime.now()
        timeStamp = "{1}:{2} {0}:".format(self.ID, str(now.hour).zfill(2), str(now.minute).zfill(2))
        
        tab.appendMessage(self.ID, "{0}\n".format(str(tab.messageLine.toPlainText().encode('latin-1'))), fromMyself=True)
        
        if settings["SAVE_HISTORY"]:
            for t in targets:
                HComUtils.writeHistory(t, timeStamp, str(tab.messageLine.toPlainText().encode('latin-1')))
        
        tab.messageLine.clear()
        
    def _sendOtl(self, targets, tabTarget, tab, tabClientType):
        
        if tab.tabTargetID == "OPEN_CHAT_ROOM":
            tab = self.openChatRoom
            
        now = datetime.datetime.now()
        msg = str(now.hour).zfill(2)  + ":" + str(now.minute).zfill(2) + " Sending Node ..."

        tab.appendDataSendBox(msg, targets, self.ID, tabTarget, HComClient.sendOtl, tabClientType=tabClientType)
        
    def _sendSettings(self, targets, tabTarget, tab):
        
        if tab.tabTargetID == "OPEN_CHAT_ROOM":
            tab = self.openChatRoom
            
        now = datetime.datetime.now()
        msg = str(now.hour).zfill(2)  + ":" + str(now.minute).zfill(2) + " Sending Node Settings ..."

        tab.appendDataSendBox(msg, targets, self.ID, tabTarget, HComClient.sendSettings)
                
    def _sendBgeo(self, targets, tabTarget, tab):
        
        if tab.tabTargetID == "OPEN_CHAT_ROOM":
            tab = self.openChatRoom
            
        now = datetime.datetime.now()
        msg = str(now.hour).zfill(2)  + ":" + str(now.minute).zfill(2) + " Sending bgeo file ..."

        tab.appendDataSendBox(msg, targets, self.ID, tabTarget, HComClient.sendBgeo)
        
    def _sendObjMesh(self, targets, tabTarget, tab):
        
        if tab.tabTargetID == "OPEN_CHAT_ROOM":
            tab = self.openChatRoom
            
        now = datetime.datetime.now()
        msg = str(now.hour).zfill(2)  + ":" + str(now.minute).zfill(2) + " Sending obj file ..."

        tab.appendDataSendBox(msg, targets, self.ID, tabTarget, HComClient.sendObjMesh)
        
    def _sendAlembic(self, targets, tabTarget, tab):
        
        if tab.tabTargetID == "OPEN_CHAT_ROOM":
            tab = self.openChatRoom
            
        now = datetime.datetime.now()
        msg = str(now.hour).zfill(2)  + ":" + str(now.minute).zfill(2) + " Sending Alembic cache ..."

        tab.appendDataSendBox(msg, targets, self.ID, tabTarget, HComClient.sendAlembic)
        
    def _sendPic(self, targets, tabTarget, tab):
        
        if tab.tabTargetID == "OPEN_CHAT_ROOM":
            tab = self.openChatRoom
        
        imageFile = QtGui.QFileDialog.getOpenFileName(self, "Pick a picture file", filter="Images (*.png *.tga *.tif *.bmp *.r32z *.u8z *.xpm *.jpg)")
        
        if not imageFile:
            return
        
        imageFile = str(imageFile[0])
        
        if not os.path.exists(imageFile):
            return False
        
        now = datetime.datetime.now()
        msg = str(now.hour).zfill(2)  + ":" + str(now.minute).zfill(2) + " Sending picture file ..."

        tab.appendDataSendBox(msg, targets, self.ID, tabTarget, HComClient.sendPic, imagePath = imageFile )
        
    def _addUserTab(self, target_ID, clientType, fromUserList=False):
        '''
            Add a new user tab for private conversation
            Must be sent from updaterUiThread
        '''
        
        if self.ID == target_ID:
            return
        
        if target_ID in self.USER_TABS.keys():
            self.centralTabWidget.setCurrentWidget(self.USER_TABS[target_ID])
            
        else:
            tab = HComWidgets.UserChatTabWidget(str(target_ID), clientType=clientType,  parent=self)
            self.USER_TABS[target_ID] = tab
            
            self.centralTabWidget.addTab(tab, str(target_ID))
            
            if fromUserList:
                self.centralTabWidget.setCurrentWidget(tab)
                
        hou.session.HCOM_TABS = self.USER_TABS

    def _removeUserTab(self, ID):
        
        if ID in self.USER_TABS.keys():
            self.USER_TABS[ID].close()
            self.USER_TABS[ID].deleteLater()
            del(self.USER_TABS[ID])
            hou.session.HCOM_TABS = self.USER_TABS
           
    def _connectToHCom(self):
        
        ID = str(self.ID_line.text())
        hou.session.HCOM_CUR_ID = ID
        result = HComClient.connectToServer(ID=ID, clientType=self.CLIENT_TYPE)
        
        if not result:
            return False
        
        self.ID = ID
        
        if result == (False, False):
            hou.ui.displayMessage("Error: HCom server can't be reached !", severity=hou.severityType.Error)
            return False
        
        try:
            hou.session.HCOMCLIENT
        except AttributeError:
            hou.ui.displayMessage("Error: HCom server can't be reached !", severity=hou.severityType.Error)
            print("ERROR: can not connect to server.")
        else:
            self._switchConnection(True)
            
    def _switchConnection(self, connected, serverDisconnect=False):
        
        if connected:
            
            if not serverDisconnect:
                self.userListWidget.userListW.outuserInfo.clear()
            
            self.hcc = hou.session.HCOMCLIENT[0]
            self.connected = True
            
            self.userListWidget.session_ID = self.ID
            self.userListWidget.userListW.session_ID = self.ID
            
            self.ID_lbl.setDisabled(True)
            self.ID_line.setDisabled(True)
            self.connectBtn.setVisible(False)
            self.disconnectBtn.setVisible(True)
            
            self.openChatRoom.disableTab(False)
            
            self.userListWidget.userListW.clearUserList()
            
            allClients, allClientTypes = self.hcc.root.getAllCientInfos()
            for user in allClients.keys():
                clientType = allClientTypes[user]
                self.userListWidget._updateUserList(user, "join", clientType)
            
            self.title.setText("Connected")
            
        else:
            
            if not serverDisconnect:
                self.userListWidget.userListW.outuserInfo.clear()
            
            if HComClient.bgsrv:
                try:
                    HComClient.bgsrv.stop()
                except:
                    pass
            if HComClient.server_conn:
                try:
                    HComClient.server_conn.close()
                except:
                    pass
            
            self.ID_lbl.setDisabled(False)
            self.ID_line.setDisabled(False)
            self.connectBtn.setVisible(True)
            self.disconnectBtn.setVisible(False)
            
            self.openChatRoom.disableTab(True)
            
            self.userListWidget.userListW.clearUserList()
            self.title.setText("Not Connected")
            
            self.connected = False
            if hasattr(hou.session, "HCOMCLIENT"):
                del(hou.session.HCOMCLIENT)
    
    def _showSettings(self):
        
        settings = HComWidgets.SettingsWindow(parent=self)
        settings.exec_()
        
    def _rdnname(self):
        if str(self.ID_line.text()) == "2501":
            self.ID_line.setText(HComUtils.rdnname())
    
def main():
    
    global HComMainUi
    
    try:
        hou.session.HCOMCLIENT
    except AttributeError:
        view = HComMainView(False)
        HComMainUi = view
        return view
    else:
        view = HComMainView(True)
        HComMainUi = view
        return view

######################################################################
def receiveData(sender, data, dataType, tabTarget, senderType=[None, None]):
    
    settings = HComUtils.readIni()
    # Send a text message
    if dataType == "msg":
        
        if tabTarget == "" or tabTarget == "OPEN_CHAT_ROOM":
            HComMainUi.updateUiThread.messageData = {"TAB_TARGET":"OPEN_CHAT_ROOM", "SENDER":sender, "MESSAGE":"{0}\n".format(data)}
        else:
            sendAddTabToThread(tabTarget, senderType)
            HComMainUi.updateUiThread.messageData = {"TAB_TARGET":str(tabTarget), "SENDER":sender, "MESSAGE":"{0}\n".format(data)}
            
        if settings["SAVE_HISTORY"]:
            now = datetime.datetime.now()
            timeStamp = "{1}:{2} {0}:".format(sender, str(now.hour).zfill(2), str(now.minute).zfill(2))
            HComUtils.writeHistory(sender, timeStamp, data)
    
    # Send a setting of parms for the given node selection type
    elif dataType == "settings":
        sendAddTabToThread(tabTarget, senderType)
        HComMainUi.updateUiThread.inputData = {"SENDER":sender, "DATA_TYPE":dataType, "DATA":data, "TAB_TARGET":tabTarget, "SENDER_TYPE":senderType}
    
    # Send an otl or a node
    elif dataType == "otl":
        sendAddTabToThread(tabTarget, senderType)
        HComMainUi.updateUiThread.inputData = {"SENDER":sender, "DATA_TYPE":dataType, "DATA":data, "TAB_TARGET":tabTarget, "SENDER_TYPE":senderType}
            
    # Bgeo mesh
    elif dataType == "mesh":
        sendAddTabToThread(tabTarget, senderType)
        HComMainUi.updateUiThread.inputData = {"SENDER":sender, "DATA_TYPE":dataType, "DATA":data, "TAB_TARGET":tabTarget, "SENDER_TYPE":senderType}
 
    # Pictures
    elif dataType == "pic":
        sendAddTabToThread(tabTarget, senderType)
        HComMainUi.updateUiThread.inputData = {"SENDER":sender, "DATA_TYPE":dataType, "DATA":data, "TAB_TARGET":tabTarget, "SENDER_TYPE":senderType}

    # Alembic
    elif dataType == "alembic":
        sendAddTabToThread(tabTarget, senderType)
        HComMainUi.updateUiThread.inputData = {"SENDER":sender, "DATA_TYPE":dataType, "DATA":data, "TAB_TARGET":tabTarget, "SENDER_TYPE":senderType}
    

    # Data received
    elif dataType == "dataReceivedUpdate":
        
        now = datetime.datetime.now()
        minute = str(now.minute).zfill(2)
        hour = str(now.hour).zfill(2)
        timestamp = "{0}:{1}: ".format(hour, minute)
        
        if data[0]:
            statue = "accepted."
        else:
            statue = "declined."
        
        msg = ""
        if data[1] == "otl":
            msg = timestamp + "Houdini node " + statue
            
        elif data[1] == "settings":
            msg = timestamp + "Node Settings " + statue
            
        elif data[1] == "mesh":
            msg = timestamp + "Mesh " + statue
            
        elif data[1] == "pic":
            msg = timestamp + "Image File " + statue
            
        HComMainUi.updateUiThread.dataReceivedUpdate = {"SENDER":"", "MESSAGE":msg, "TAB_TARGET":tabTarget, "SENDER_TYPE":senderType}
        
def sendAddTabToThread(tabTarget, clientType):
    
    # Create a new tab if target tab is not found
    if not tabTarget in HComMainUi.USER_TABS.keys():
        
        HComMainUi.updateUiThread.data = {"ACTION":"add_tab", "ID":tabTarget, "CLIENT_TYPE":clientType}
        
        while not tabTarget in HComMainUi.USER_TABS.keys():
                time.sleep(0.1)
        
def receiveIDUpdate(ID, action, clientType):
    
    if action == "left":
        HComMainUi.updateUiThread.data = {"ACTION":"left", "ID":ID, "CLIENT_TYPE":clientType}
        
    elif action == "join":
        HComMainUi.updateUiThread.data = {"ACTION":"join", "ID":ID, "CLIENT_TYPE":clientType}
    