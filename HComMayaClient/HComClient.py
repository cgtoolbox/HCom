import rpyc
import sys
import getpass
import os

import maya.cmds as cmds
import maya.utils as mUtils
from HComMayaClient import HComWidgets

RECEIVED_FILES = os.path.dirname(__file__)  + "\\HCom_Received_Files\\"

from PySide import QtGui

import threading

pysidePath = os.environ["PYTHONHOME"] + r"lib\site-packages-forced"
if not pysidePath in sys.path:
    sys.path.append(pysidePath)

from _globals import MayaGlobals

import HComMayaUi
import HComUtils

global server_conn
server_conn = None

global server_id
server_id = None

global bgsrv
bgsrv = None

# Decorator tor send new data to client
# into a new thread
def threaded_sendata(func):
    
    def wrapper(*args, **kwargs):
        t = threading.Thread(target=func, args=args, kwargs=kwargs)
        t.start()
    
    return wrapper

class HCom_ClientService(rpyc.Service):
    '''
        This is the client service called to fetch data from server.
    '''
    
    def on_disconnect(self):
        server_is_disconnected()
    
    def exposed_catchData(self, dataType, sender, data, tabTarget, clientType):
        
        HComMayaUi.receiveData(sender, data, dataType, tabTarget, clientType)
        
    def exposed_sendIDUpdate(self, ID, action, clientType):

        HComMayaUi.receiveIDUpdate(ID, action, clientType)


def connectToServer(ID=None, clientType="NONE"):
    '''
        Try to connect to the server and launch the BG thread service
    '''
    
    if not ID:
        ID = getpass.getuser()
    
    global server_conn
    global bgsrv
    
    try:
        server_conn = rpyc.connect(HComUtils.readIni()["SERVER"].replace(" ",""), int(str(HComUtils.readIni()["PORT"]).replace(" ","")), service=HCom_ClientService, config={"allow_pickle":True})
    except Exception as e:
        print("ERROR: Can not connect to server: " + str(e))
        return False, False
    else:
        if ID in server_conn.root.getAllClients().keys():
            ask = QtGui.QMessageBox()
            ask.setText("User ID already registered on the server")
            ask.setIcon(QtGui.QMessageBox.Critical)
            ask.exec_()
            server_conn.close()
            return False
        
        MayaGlobals.HCOMCLIENT = [server_conn, ID]
        
    global server_id
    server_id = ID
    
    bgsrv = rpyc.BgServingThread(server_conn)
    result = server_conn.root.registerClient(ID, clientType)
    
    if result:
        return ID
    else:
        return False

def _sendData(target_clientID, sender, data, datatype, tabTarget):
    '''
        Send data the to target client, could be message, otl or settings.
    '''
    
    global server_conn
        
    if not server_conn:
        print("ERROR: Client is not connected.")
        return False
    
    try:
        setDataAsync = rpyc.async(server_conn.root.sendDataToClient)
        result = setDataAsync(target_clientID, datatype, sender, data, tabTarget)
        return result
    except AttributeError:
        return False
        print("ERROR: client " + target_clientID + " not found.")

@threaded_sendata  
def sendMessage(target_clientID, sender, message, tabTarget):
    
    result = _sendData(target_clientID, sender, message, "msg", tabTarget)
    return result

def sendAlembic(target_clientID, sender, tabTarget):
    
    result = mUtils.executeInMainThreadWithResult(_exportAlembic)
    if not result:
        return False
    
    fileName = result[0]
    filePath = result[1]
    frameRange = result[2]
    
    with open(filePath, 'rb') as f:
        data = f.read()
        
    outData = {}
    outData["TYPE"] = "alembic_cache"
    outData["NAME"] = fileName
    outData["FRAME_RANGE"] = frameRange
    outData["DATA"] = data
    
    try:   
        os.remove(filePath)
    except:
        pass
    
    result = _sendData(target_clientID, sender, outData, "alembic", tabTarget)
    
    return result

def sendSettings(target_clientID, sender, tabTarget):
    return
 
def sendOtl(target_clientID, sender, tabTarget):
    return

def sendBgeo(target_clientID, sender, tabTarget, isObj=False):
    return

def sendObjMesh(target_clientID, sender, tabTarget):
    
    meshOut = {}
    meshOut["MESH_TYPE"] = ".obj"
    
    meshName, objtmp = mUtils.executeInMainThreadWithResult(_exportObj)
    
    if not meshName:
        return False
    
    if not objtmp:
        return False

    with open(objtmp, 'rb') as f:
        meshOut["MESH_DATA"] = f.read()
    
    try:   
        os.remove(objtmp)
    except:
        pass
    
    meshOut["MESH_TYPE"] = ".obj"
    meshOut["MESH_NAME"] = meshName
    
    result = _sendData(target_clientID, sender, meshOut, "mesh", tabTarget)
    
    return result

def _exportAlembic():
    
    if not "AbcExport" in cmds.pluginInfo( query=True, listPlugins=True ):
        ask = QtGui.QMessageBox()
        ask.setText("Error: Alembic export plugin not loaded (AbcExport) !")
        ask.setIcon(QtGui.QMessageBox.Warning)
        ask.exec_()
        return False
    
    selection = cmds.ls(sl=True)
    if not selection:
        ask = QtGui.QMessageBox()
        ask.setText("Error: Nothing selected !")
        ask.setIcon(QtGui.QMessageBox.Warning)
        ask.exec_()
        return False
    
    name = str(selection[0]) + ".abc"
    abcFile = RECEIVED_FILES + name
    abcFile = HComUtils.incrementFile(abcFile)
    start = cmds.playbackOptions(query=True, minTime=True)
    end = cmds.playbackOptions(query=True, maxTime=True)
    
    frameRangeUi = HComWidgets.FrameRangeSelection(start=start, end=end)
    frameRangeUi.exec_()
    
    if not frameRangeUi.VALID:
        return False
    
    else:
        frames = frameRangeUi.frameRange
        print frames
    
    cmd = "-fr {0} {1} -f {2}".format(frames[0], frames[1], abcFile)
    cmds.AbcExport(sl=True, j=cmd)
    
    if os.path.exists(abcFile):
        return name, abcFile, frames
    
    return False

def _exportObj():
    
    selection = cmds.ls(sl=True)
    if not selection:
        ask = QtGui.QMessageBox()
        ask.setText("Error: Nothing selected !")
        ask.setIcon(QtGui.QMessageBox.Warning)
        ask.exec_()
        return False, False
    
    meshName = str(selection[0])
    
    objtmp = RECEIVED_FILES + meshName + "_tmp.obj"
    objtmp = HComUtils.incrementFile(objtmp)
    
    try:
        cmds.file(objtmp, force=True, type="OBJexport", es=True, shader=False, )
    except Exception as e:
        print("ERROR: " + str(e))
        return False, False
    
    return meshName, objtmp
    
    

def sendPic(target_clientID, sender, tabTarget, imagePath):
    
    with open(imagePath, 'rb') as f:
        imageData = f.read()
        
    outImdageData = {}
    outImdageData["IMAGE_NAME"] = os.path.basename(imagePath)
    outImdageData["BINARY_DATA"] = imageData
    
    result = _sendData(target_clientID, sender, outImdageData, "pic", tabTarget)
    if result:
        return True
    else:
        return False

def sendDataReceivedInfo(targetClient, sender, data, tabTarget):
    
    _sendData(targetClient, sender, data, "dataReceivedUpdate", tabTarget)


def getAllClientRegistred():
    
    global server_conn
        
    if not server_conn:
        print("ERROR: Client is not connected.")
        return False
    
    return server_conn.root.getAllClients().keys()
        
def disconnect():
    '''
        Disconect client and stop BG thread
    '''
    
    global server_conn
    global bgsrv
    global server_id
    
    if not server_conn:
        return
    try:
        bgsrv.stop()
        bgsrv = None
    except:
        pass
    
    try:
        server_conn.root.removeClient(server_id)
    except EOFError:
        pass

    try:
        server_conn.close()

    except:
        pass
    server_conn = None
    MayaGlobals.MAIN_UI.updateUiThread.data = {"ACTION":"server_disconnect", "ID":None, "CLIENT_TYPE":None}
    
    
def server_is_disconnected():
    disconnect()