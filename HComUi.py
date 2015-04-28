import hou
import getpass
import time
import datetime
import socket
import os
import subprocess

import PySide.QtGui as QtGui
import PySide.QtCore as QtCore

import HComClient
import HComWidgets
reload(HComWidgets)
import HComUtils

global HComMainUi
HComMainUi = None

ICONPATH = os.path.dirname(__file__) + "\\HCom_Icons\\"
RECEIVED_FILES = os.path.dirname(__file__) + "\\HCom_Received_Files\\"

class HComMainView(QtGui.QFrame):
    
    def __init__(self, connected):
        QtGui.QFrame.__init__(self)
        
        self.updateUiThread = HComWidgets.UiUpdaterThread()
        self.updateUiThread.update_ui_signal.connect(self._updateUi)
        self.updateUiThread.append_message_signal.connect(self._appendMessageToTab)
        self.updateUiThread.input_data_signal.connect(self._getInputData)
        self.updateUiThread.start()
        
        self.connected = connected
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
        self.centralTabWidget.currentChanged.connect(self._updateTabIcon)
        
        self.openChatRoom = HComWidgets.UserChatTabWidget("OPEN_CHAT_ROOM", openChatRoom=True, parent=self)
        self.centralTabWidget.addTab(self.openChatRoom, "Open Chat Room")
        self.USER_TABS["OPEN_CHAT_ROOM"] = self.openChatRoom
        
        self.splitter.addWidget(self.centralTabWidget)

    def _getInputData(self, sender, dataType, data, tarbTarget):
        '''
            Fetch data from client and add confirmation widget to the chat
        '''
        
        if not tarbTarget in self.USER_TABS.keys():
            return False
        
        curTab = self.centralTabWidget.currentWidget()
        curTabIdx = self.centralTabWidget.currentIndex()       
        
        if self.USER_TABS[tarbTarget] != curTab:
            targetTabIdx = self.centralTabWidget.indexOf(self.USER_TABS[tarbTarget])
            self.centralTabWidget.tabBar().setTabIcon(targetTabIdx, QtGui.QIcon(ICONPATH + "unreadmsg.png"))
            
        self.USER_TABS[tarbTarget].appendInputBox(sender, dataType, data)
        

    def _updateUi(self, data):
        '''
            This methode is triggered by the update UI thread from HComWidget
        '''
        data = data.split(";")
        action = data[0]
        ID = data[1]
        
        now = datetime.datetime.now()
        
        if action == "server_disconnect":
            self._switchConnection(False)
            
        elif action == "join":
            if ID != self.ID:
                self.userListWidget._updateUserList(ID, action)
                IDLabel = "<FONT COLOR=#4b5488><i>{1}:{2} {0} join</i></FONT>".format(ID, str(now.hour).zfill(2), str(now.minute).zfill(2))
                self.userListWidget.userListW.outuserInfo.append(IDLabel)
        
        elif action == "left":
            if ID != self.ID:
                self.userListWidget._updateUserList(ID, action)
                IDLabel = "<FONT COLOR=#4b5488><i>{1}:{2} {0} left</i></FONT>".format(ID, str(now.hour).zfill(2), str(now.minute).zfill(2))
                self.userListWidget.userListW.outuserInfo.append(IDLabel)
                
        elif action == "add_tab":
            self._addUserTab(ID)
            
        elif action == "append_msg":
            _appendMessageToTab(ID)
            
    def _updateTabIcon(self, idx):
        
        self.centralTabWidget.tabBar().setTabIcon(idx, QtGui.QIcon(""))
            
    def _appendMessageToTab(self, tarbTarget, messageHeader, message):
        
        if not tarbTarget in self.USER_TABS.keys():
            return False
        
        curTab = self.centralTabWidget.currentWidget()
        curTabIdx = self.centralTabWidget.currentIndex()       
        
        if self.USER_TABS[tarbTarget] != curTab:
            targetTabIdx = self.centralTabWidget.indexOf(self.USER_TABS[tarbTarget])
            self.centralTabWidget.tabBar().setTabIcon(targetTabIdx, QtGui.QIcon(ICONPATH + "unreadmsg.png"))
            
        self.USER_TABS[tarbTarget].appendMessage(messageHeader, message)
        
    def _sendMessage(self, targets, message, tab, tabTarget):
        
        if not message:
            return
        
        settings = HComUtils.readIni()
        
        result = HComClient.sendMessage(targets, self.ID, message, tabTarget)
        
        if isinstance(result, list):
            
            for i in result:
                tab.outMessage.append("Error: User '{0}' not found.\n".format(i))
                
        now = datetime.datetime.now()
        
        timeStamp = "{1}:{2} {0}:".format(self.ID, str(now.hour).zfill(2), str(now.minute).zfill(2))
        timeStamp = HComUtils.coloredString(timeStamp, "70738c", italic=True)
        
        tab.appendMessage(self.ID, "   {0}\n".format(str(tab.messageLine.text().encode('latin-1'))), fromMyself=True)
        
        if settings["SAVE_HISTORY"]:
            for t in targets:
                HComUtils.writeHistory(t, timeStamp, str(tab.messageLine.text().encode('latin-1')))
        
        tab.messageLine.clear()
        
    def _sendOtl(self, targets, tabTarget):
        
        HComClient.sendOtl(targets, self.ID, tabTarget)
        
    def _sendSettings(self, targets, tabTarget):
        
        HComClient.sendSettings(targets, self.ID, tabTarget)
        
    def _sendBgeo(self, targets, tabTarget):
        
        HComClient.sendBgeo(targets, self.ID, tabTarget)
        
    def _sendObjMesh(self, targets, tabTarget):
        
        HComClient.sendObjMesh(targets, self.ID, tabTarget)
        
    def _sendPic(self, targets, tabTarget):
        
        imageFile = QtGui.QFileDialog.getOpenFileName(self, "Pick a picture file", filter="Images (*.png *.tga *.tif *.bmp *.r32z *.u8z *.xpm *.jpg)")
        
        if not imageFile:
            return
        
        HComClient.sendPic(targets, self.ID, tabTarget, str(imageFile[0]))
        
    def _addUserTab(self, target_ID, fromUserList=False):
        '''
            Add a new user tab for private conversation
            Must be sent from updaterUiThread
        '''
        
        if self.ID == target_ID:
            return
        
        if target_ID in self.USER_TABS.keys():
            self.centralTabWidget.setCurrentWidget(self.USER_TABS[target_ID])
            
        else:
            tab = HComWidgets.UserChatTabWidget(str(target_ID), parent=self)
            self.USER_TABS[target_ID] = tab
            
            self.centralTabWidget.addTab(tab, str(target_ID))
            
            if fromUserList:
                self.centralTabWidget.setCurrentWidget(tab)

    def _removeUserTab(self, ID):
        
        if ID in self.USER_TABS.keys():
            self.USER_TABS[ID].close()
            self.USER_TABS[ID].deleteLater()
            del(self.USER_TABS[ID])
           
    def _connectToHCom(self):
        
        ID = str(self.ID_line.text())
        hou.session.HCOM_CUR_ID = ID
        result = HComClient.connectToServer(ID)
        
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
            
            for user in self.hcc.root.getAllClients().keys():
                self.userListWidget._updateUserList(user, "join")
            
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
def receiveData(sender, data, dataType, tabTarget):
    
    settings = HComUtils.readIni()
    
    # Send a text message
    if dataType == "msg":
        
        if tabTarget == "" or tabTarget == "OPEN_CHAT_ROOM":
            HComMainUi.updateUiThread.messageData = ["OPEN_CHAT_ROOM",
                                                     sender,
                                                     "   {0}\n".format(data)]
        else:
            sendAddTabToThread(tabTarget)
            HComMainUi.updateUiThread.messageData = [str(tabTarget),
                                             sender,
                                             "   {0}\n".format(data)]
            
        if settings["SAVE_HISTORY"]:
            now = datetime.datetime.now()
            timeStamp = "{1}:{2} {0}:".format(sender, str(now.hour).zfill(2), str(now.minute).zfill(2))
            HComUtils.writeHistory(sender, timeStamp, data)
    
    # Send a setting of parms for the given node selection type
    elif dataType == "settings":
        sendAddTabToThread(tabTarget)
        HComMainUi.updateUiThread.inputData = [sender, "settings", data, tabTarget]
    
    # Send an otl or a node
    elif dataType == "otl":
        sendAddTabToThread(tabTarget)
        HComMainUi.updateUiThread.inputData = [sender, "otl", data, tabTarget]
            
    # Bgeo mesh
    elif dataType == "mesh":
        sendAddTabToThread(tabTarget)
        HComMainUi.updateUiThread.inputData = [sender, "mesh", data, tabTarget]
 
    # Pictures
    elif dataType == "pic":
        sendAddTabToThread(tabTarget)
        HComMainUi.updateUiThread.inputData = [sender, "pic", data, tabTarget]
        
def sendAddTabToThread(tabTarget):

    # Create a new tab if target tab is not found
    if not tabTarget in HComMainUi.USER_TABS.keys():
        HComMainUi.updateUiThread.data = "add_tab;{0}".format(tabTarget)
        
        while not tabTarget in HComMainUi.USER_TABS.keys():
                time.sleep(0.1)
        
def receiveIDUpdate(ID, action):
    
    if action == "left":
        HComMainUi.updateUiThread.data = "left;{0}".format(ID)
        
    elif action == "join":
        HComMainUi.updateUiThread.data = "join;{0}".format(ID)
    