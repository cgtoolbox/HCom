import getpass
import time
import datetime
import socket
import os
import threading

from nukescripts import panels
import nuke

import PySide.QtGui as QtGui
import PySide.QtCore as QtCore

import HComNukeClient

import HComNukeWidgets
reload(HComNukeWidgets)
import HComNukeUtils
reload(HComNukeUtils)

from _globals import NukeGlobals

ICONPATH = os.path.dirname(__file__) + "\\HCom_Icons\\"

class HComNukeMainView(QtGui.QWidget):
    
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)
        
        self.CLIENT_TYPE = [HComNukeUtils.CLIENT_TYPE.NUKE, "Nuke " + nuke.NUKE_VERSION_STRING]
        self.setWindowFlags(QtCore.Qt.Window)
        
        self.updateUiThread = HComNukeWidgets.UiUpdaterThread()
        self.updateUiThread.update_ui_signal.connect(self._updateUi)
        self.updateUiThread.append_message_signal.connect(self._appendMessageToTab)
        self.updateUiThread.input_data_signal.connect(self._getInputData)
        self.updateUiThread.data_received_update.connect(self._dataReveivedUpdate)
        self.updateUiThread.start()
        
        self.connected = False
        if NukeGlobals.HCOM_TABS != {}:
            self.USER_TABS = NukeGlobals.HCOM_TABS
        else:
            self.USER_TABS = {}
        
        if not self.connected:
            self.hcc = False
            self.ID = ""
        else:
            self.hcc = NukeGlobals.HCOMCLIENT[0]
            self.ID = NukeGlobals.HCOMCLIENT[1]
        
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
        
        if NukeGlobals.CUR_ID:
            defaultName = NukeGlobals.CUR_ID
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
        
        self.userListWidget = HComNukeWidgets.UserListDockWidget(self.hcc, self.ID, self)
        self.userListWidget.session_ID = self.ID
        self.userListWidget.userListW.session_ID = self.ID
        self.userListLayout.addWidget(self.userListWidget)
        
        self.userListLayout.setSizeConstraint(QtGui.QLayout.SetMinimumSize)
        
        self.userListWidget.setLayout(self.userListLayout)
        self.splitter.addWidget(self.userListWidget)
    
    def __init_centralWidget(self):
        
        self.centralTabWidget = QtGui.QTabWidget()
        self.centralTabWidget.currentChanged.connect(self._updateTabIcon)
        
        if NukeGlobals.HCOM_TABS != {}:
            if "OPEN_CHAT_ROOM" in NukeGlobals.HCOM_TABS.keys():
                tab = NukeGlobals.HCOM_TABS["OPEN_CHAT_ROOM"]
                self.USER_TABS["OPEN_CHAT_ROOM"] = tab
                self.openChatRoom = tab
                self.centralTabWidget.addTab(self.openChatRoom, "Open Chat Room")
                
            for k in NukeGlobals.HCOM_TABS.keys():
                if k == "OPEN_CHAT_ROOM": continue
                tab = NukeGlobals.HCOM_TABS[k]
                self.centralTabWidget.addTab(tab, k)
        else:
            self.openChatRoom = HComNukeWidgets.UserChatTabWidget("OPEN_CHAT_ROOM", clientType="None", openChatRoom=True, parent=self)
            self.centralTabWidget.addTab(self.openChatRoom, "Open Chat Room")
            self.USER_TABS["OPEN_CHAT_ROOM"] = self.openChatRoom
            NukeGlobals.HCOM_TABS["OPEN_CHAT_ROOM"] = self.openChatRoom
        
        self.splitter.addWidget(self.centralTabWidget)

    def _getInputData(self, in_data):
        '''
            Fetch data from client and add confirmation widget to the chat
        '''
        
        sender = in_data["SENDER"]
        dataType = in_data["DATA_TYPE"]
        data = in_data["DATA"]
        tabTarget = in_data["TAB_TARGET"]
        
        if not tabTarget in self.USER_TABS.keys():
            return False
        
        curTab = self.centralTabWidget.currentWidget()
        
        if self.USER_TABS[tabTarget] != curTab:
            targetTabIdx = self.centralTabWidget.indexOf(self.USER_TABS[tabTarget])
            self.centralTabWidget.tabBar().setTabIcon(targetTabIdx, QtGui.QIcon(ICONPATH + "unreadmsg.png"))
            
            settings = HComNukeUtils.readIni()
            if "PLAY_SOUND" in settings.keys():
                if settings["PLAY_SOUND"]:
                    s = QtGui.QSound(ICONPATH + "gnm.wav")
                    s.play()
            
        self.USER_TABS[tabTarget].appendInputBox(sender, dataType, data)
        

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
            
            settings = HComNukeUtils.readIni()
            if "PLAY_SOUND" in settings.keys():
                if settings["PLAY_SOUND"]:
                    s = QtGui.QSound(ICONPATH + "gnm.wav")
                    s.play()
            
        self.USER_TABS[tabTarget].appendMessage(sender, message)
        
        NukeGlobals.HCOM_TABS = self.USER_TABS
        
    def _sendMessage(self, targets, message, tab, tabTarget):
        
        if not message:
            return
        
        settings = HComNukeUtils.readIni()
        
        if targets:
            result = HComNukeClient.sendMessage(targets, self.ID, message, tabTarget)
        
            if isinstance(result, list):
                
                for i in result:
                    tab.outMessage.append("Error: User '{0}' not found.\n".format(i))
                
        now = datetime.datetime.now()
        timeStamp = str(self.ID) + ":" + str(now.hour).zfill(2) + ":" + str(now.minute).zfill(2) + ":"
        
        tab.appendMessage(self.ID, str(tab.messageLine.toPlainText().encode('latin-1')) + "\n", fromMyself=True)
        
        if settings["SAVE_HISTORY"]:
            for t in targets:
                HComNukeUtils.writeHistory(t, timeStamp, str(tab.messageLine.toPlainText().encode('latin-1')))
        
        tab.messageLine.clear()
        
    def _sendOtl(self, targets, tabTarget, tab):
        
        if tab.tabTargetID == "OPEN_CHAT_ROOM":
            tab = self.openChatRoom
            
        now = datetime.datetime.now()
        msg = str(now.hour).zfill(2)  + ":" + str(now.minute).zfill(2) + " Sending Node ..."

        tab.appendDataSendBox(msg, targets, self.ID, tabTarget, HComNukeClient.sendOtl)
        
    def _sendOuputNode(self, targets, tabTarget, tab):
        
        try:
            n = nuke.selectedNode()
            if not n.channels():
                nuke.message('Selected node has not valid channels, nothing to write.')
                return
            
        except ValueError:
            nuke.message('Nothing selected')
            return
        
        if tab.tabTargetID == "OPEN_CHAT_ROOM":
            tab = self.openChatRoom
            
        now = datetime.datetime.now()
        msg = str(now.hour).zfill(2)  + ":" + str(now.minute).zfill(2) + " Sending Selected Node's Output ..."

        tab.appendDataSendBox(msg, targets, self.ID, tabTarget, HComNukeClient.sendNodeOuput)
        
    def _sendSettings(self, targets, tabTarget, tab):
        
        if tab.tabTargetID == "OPEN_CHAT_ROOM":
            tab = self.openChatRoom
            
        now = datetime.datetime.now()
        msg = str(now.hour).zfill(2)  + ":" + str(now.minute).zfill(2) + " Sending Node Settings ..."

        tab.appendDataSendBox(msg, targets, self.ID, tabTarget, HComNukeClient.sendSettings)

    def _sendObjMesh(self, targets, tabTarget, tab, alembic=False, frames=[0,0]):
        
        validNodes = ['Sphere', 'Cylinder', 'Cube', 'MergeGeo', 'ReadGeo2', 'WriteGeo', 'Card2',
                      'Scene', 'TransformGeo', 'CrosstalkGeo', 'DisplaceGeo', 'EditGeo', 'GeoSelect',
                      'LookupGeo', 'LogGeo', 'Normals', 'ProcGeo', 'RadialDistort', 'Trilinear', 'UVProject']
        
        try:
            n = nuke.selectedNode()
            if not n.Class() in validNodes:
                if alembic:
                    msg = 'Selected node is not supported by HCom for alembic export, node supported:\n\n   - Cameras\n'
                else:
                    msg = 'Selected node is not supported by HCom for .obj export, node supported:\n\n'
                for n in validNodes:
                    msg += "  - " + n + "\n"
                nuke.message(msg)
                return
            
        except ValueError:
            nuke.message('Nothing selected')
            return
        
        if alembic:
            frameUi = HComNukeWidgets.FrameRangeSelection(start=nuke.root().firstFrame(),
                                                          end=nuke.root().lastFrame())
            frameUi.exec_()
            
            if not frameUi.VALID:
                return False
            
            else:
                frames = frameUi.frameRange
        
        if tab.tabTargetID == "OPEN_CHAT_ROOM":
            tab = self.openChatRoom
            
        now = datetime.datetime.now()
        msg = str(now.hour).zfill(2)  + ":" + str(now.minute).zfill(2) + " Sending obj file ..."

        tab.appendDataSendBox(msg, targets, self.ID, tabTarget, HComNukeClient.sendObjMesh, alembic=alembic, frames=frames) 
        
    def _sendAlembicMesh(self, targets, tabTarget, tab):
        
        self._sendObjMesh(targets, tabTarget, tab, alembic=True)
        
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

        tab.appendDataSendBox(msg, targets, self.ID, tabTarget, HComNukeClient.sendPic, imagePath = imageFile )
        
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
            tab = HComNukeWidgets.UserChatTabWidget(str(target_ID), clientType=clientType,  parent=self)
            self.USER_TABS[target_ID] = tab
            
            self.centralTabWidget.addTab(tab, str(target_ID))
            
            if fromUserList:
                self.centralTabWidget.setCurrentWidget(tab)
                
        NukeGlobals.HCOM_TABS = self.USER_TABS

    def _removeUserTab(self, ID):
        
        if ID in self.USER_TABS.keys():
            self.USER_TABS[ID].close()
            self.USER_TABS[ID].deleteLater()
            del(self.USER_TABS[ID])
            NukeGlobals.HCOM_TABS = self.USER_TABS
           
    def _connectToHCom(self):
        
        self.CLIENT_TYPE = [HComNukeUtils.CLIENT_TYPE.NUKE, "Nuke " + nuke.NUKE_VERSION_STRING]
        
        ID = str(self.ID_line.text())
        NukeGlobals.CUR_ID = ID
        result = HComNukeClient.connectToServer(ID=ID, clientType=self.CLIENT_TYPE)
        
        if not result:
            return False
        
        self.ID = ID
        
        if result == (False, False):
            ask = QtGui.QMessageBox(parent=self)
            ask.setText("Error: HCom server can't be reached !")
            ask.setIcon(QtGui.QMessageBox.Critical)
            ask.exec_()
            return False
        
        if not NukeGlobals.HCOMCLIENT:
            ask = QtGui.QMessageBox(parent=self)
            ask.setText("Error: HCom server can't be reached !")
            ask.setIcon(QtGui.QMessageBox.Critical)
            ask.exec_()
            return False
        else:
            self._switchConnection(True)
            
    def _switchConnection(self, connected, serverDisconnect=False):
        
        if connected:
            
            if not serverDisconnect:
                self.userListWidget.userListW.outuserInfo.clear()
            
            self.hcc = NukeGlobals.HCOMCLIENT[0]
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
            
            if HComNukeClient.bgsrv:
                try:
                    HComNukeClient.bgsrv.stop()
                except:
                    pass
            if HComNukeClient.server_conn:
                try:
                    HComNukeClient.server_conn.close()
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
            if NukeGlobals.HCOMCLIENT:
                NukeGlobals.HCOMCLIENT = None
    
    def _showSettings(self):
        
        settings = HComNukeWidgets.SettingsWindow(parent=self)
        settings.exec_()
        
    def _rdnname(self):
        if str(self.ID_line.text()) == "2501":
            self.ID_line.setText(HComNukeUtils.rdnname())
            
class HComLauncherPanelWidget(QtGui.QWidget):
    
    def __init__(self):
        QtGui.QWidget.__init__(self)
        
        self.mainLayout = QtGui.QVBoxLayout()
        uiwidget = HComNukeMainView()
        NukeGlobals.MAIN_UI = uiwidget
        self.mainLayout.addWidget(uiwidget)
        
        self.setLayout(self.mainLayout)

def main():
    
    if not nuke.getPaneFor('HCom-guillaumej'):
    
        pane = nuke.getPaneFor('Properties.1')
        panels.registerWidgetAsPanel( __name__ + '.HComLauncherPanelWidget', 'HCom', 'HCom-guillaumej', create=True).addToPane(pane)
        
        t = threading.Thread(target=checkForHCom)
        t.start()
        
    else:
        nuke.message('HCom already opened')
        
def checkForHCom():
    '''
        This is used to check if HCom Panel has been closed.
        If Yes, disconnect the client from the server ( it acts like a "close panel callback" )
    '''
    while 1:
        
        if nuke.getPaneFor('HCom-guillaumej'):
            continue
        
        if HComNukeClient.bgsrv:
            try:
                HComNukeClient.bgsrv.stop()
            except:
                pass
            
        if HComNukeClient.server_conn:
            try:
                HComNukeClient.server_conn.close()
            except:
                pass
            
        NukeGlobals.HCOMCLIENT = None
        NukeGlobals.MAIN_UI = None
        break
    
        time.sleep(1)

######################################################################
def receiveData(sender, data, dataType, tabTarget, senderType=[None, None]):
    
    settings = HComNukeUtils.readIni()
    # Send a text message
    if dataType == "msg":
        
        if tabTarget == "" or tabTarget == "OPEN_CHAT_ROOM":
            NukeGlobals.MAIN_UI.updateUiThread.messageData = {"TAB_TARGET":"OPEN_CHAT_ROOM", "SENDER":sender, "MESSAGE":"{0}\n".format(data)}
        else:
            sendAddTabToThread(tabTarget, senderType)
            NukeGlobals.MAIN_UI.updateUiThread.messageData = {"TAB_TARGET":str(tabTarget), "SENDER":sender, "MESSAGE":"{0}\n".format(data)}
            
        if settings["SAVE_HISTORY"]:
            now = datetime.datetime.now()
            timeStamp = "{1}:{2} {0}:".format(sender, str(now.hour).zfill(2), str(now.minute).zfill(2))
            HComNukeUtils.writeHistory(sender, timeStamp, data)
    
    # Send a setting of parms for the given node selection type
    elif dataType == "settings":
        sendAddTabToThread(tabTarget, senderType)
        NukeGlobals.MAIN_UI.updateUiThread.inputData = {"SENDER":sender, "DATA_TYPE":dataType, "DATA":data, "TAB_TARGET":tabTarget, "SENDER_TYPE":senderType}
    
    # Send an otl or a node
    elif dataType == "otl":
        sendAddTabToThread(tabTarget, senderType)
        NukeGlobals.MAIN_UI.updateUiThread.inputData = {"SENDER":sender, "DATA_TYPE":dataType, "DATA":data, "TAB_TARGET":tabTarget, "SENDER_TYPE":senderType}
            
    # Bgeo mesh
    elif dataType == "mesh":
        sendAddTabToThread(tabTarget, senderType)
        NukeGlobals.MAIN_UI.updateUiThread.inputData = {"SENDER":sender, "DATA_TYPE":dataType, "DATA":data, "TAB_TARGET":tabTarget, "SENDER_TYPE":senderType}
 
    # Pictures
    elif dataType == "pic":
        sendAddTabToThread(tabTarget, senderType)
        NukeGlobals.MAIN_UI.updateUiThread.inputData = {"SENDER":sender, "DATA_TYPE":dataType, "DATA":data, "TAB_TARGET":tabTarget, "SENDER_TYPE":senderType}
        
    # Alembic
    elif dataType == "alembic":
        sendAddTabToThread(tabTarget, senderType)
        NukeGlobals.MAIN_UI.updateUiThread.inputData = {"SENDER":sender, "DATA_TYPE":dataType, "DATA":data, "TAB_TARGET":tabTarget, "SENDER_TYPE":senderType}
    
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
            
        NukeGlobals.MAIN_UI.updateUiThread.dataReceivedUpdate = {"SENDER":"", "MESSAGE":msg, "TAB_TARGET":tabTarget, "SENDER_TYPE":senderType}
        
def sendAddTabToThread(tabTarget, clientType):
    
    # Create a new tab if target tab is not found
    if not tabTarget in NukeGlobals.MAIN_UI.USER_TABS.keys():
        
        NukeGlobals.MAIN_UI.updateUiThread.data = {"ACTION":"add_tab", "ID":tabTarget, "CLIENT_TYPE":clientType}
        
        while not tabTarget in NukeGlobals.MAIN_UI.USER_TABS.keys():
                time.sleep(0.1)
        
def receiveIDUpdate(ID, action, clientType):
    
    if action == "left":
        NukeGlobals.MAIN_UI.updateUiThread.data = {"ACTION":"left", "ID":ID, "CLIENT_TYPE":clientType}
        
    elif action == "join":
        NukeGlobals.MAIN_UI.updateUiThread.data = {"ACTION":"join", "ID":ID, "CLIENT_TYPE":clientType}
    