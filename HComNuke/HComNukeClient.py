import rpyc
import sys
import getpass
import os
import random
import tempfile

import nuke


from PySide import QtGui

import threading

from _globals import NukeGlobals
import HComNukeUtils
import HComNukeUi

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
        
        HComNukeUi.receiveData(sender, data, dataType, tabTarget, clientType)
        
    def exposed_sendIDUpdate(self, ID, action, clientType):
        
        HComNukeUi.receiveIDUpdate(ID, action, clientType)


def connectToServer(ID=None, clientType="NONE"):
    '''
        Try to connect to the server and launch the BG thread service
    '''
    
    if not ID:
        ID = getpass.getuser()
    
    global server_conn
    global bgsrv
    
    try:
        server_conn = rpyc.connect(HComNukeUtils.readIni()["SERVER"].replace(" ",""), int(str(HComNukeUtils.readIni()["PORT"]).replace(" ","")), service=HCom_ClientService, config={"allow_pickle":True})
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
        
        NukeGlobals.HCOMCLIENT = [server_conn, ID]
        
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

def sendNodeOuput(target_clientID, sender, tabTarget):
    
    fileType = HComNukeUtils.readIni()["OUTPUT_IMAGE_FORMAT"]
    
    try:
        selectedNode = nuke.selectedNode()
    except ValueError:
        return False
    
    curFrame = int(nuke.knob("frame"))
    tmpfilePath = tempfile.gettempdir() + "\\hcom_tmp_" + ''.join([random.choice("abcdef0123456789") for n in xrange(5)]) + "." + fileType
    tmpWriterName = "tmp_writer_" + ''.join([random.choice("abcdef0123456789") for n in xrange(5)])
    
    result = nuke.executeInMainThreadWithResult(_createWriter, args=(tmpWriterName, tmpfilePath, selectedNode, curFrame))
    
    if not result:
        return False
    
    with open(tmpfilePath, 'rb') as f:
        data = f.read()
        
    outImdageData = {}
    outImdageData["IMAGE_NAME"] = os.path.basename(selectedNode.name()) + "." + fileType
    outImdageData["BINARY_DATA"] = data
    
    try:   
        os.remove(tmpfilePath)
    except:
        pass
    
    w = nuke.toNode(tmpWriterName)
    if w:
        nuke.delete(w)
    
    result = _sendData(target_clientID, sender, outImdageData, "pic", tabTarget)
    
    return result

def _createWriter(name, filePath, selectedNode, curFrame):
    
    n = nuke.createNode('Write', inpanel=False)
    n.setName(name)
    n["file"].setValue(filePath.replace("\\", "/"))
    n.setInput(0, selectedNode)
    
    try:
        nuke.execute(name, curFrame, curFrame, 1)
    except RuntimeError as e:
        print str(e)
        return False
    
    return True

def sendSettings(target_clientID, sender, tabTarget):
    return
 

def sendObjMesh(target_clientID, sender, tabTarget, alembic=False, frames=[0,0]):
    
    try:
        selectedNode = nuke.selectedNode()
    except ValueError:
        return False
    
    meshOut = {}
    
    geoType = ".obj"
    if alembic:
        geoType = ".abc"
    
    curFrame = int(nuke.knob("frame"))
    tmpfilePath = tempfile.gettempdir() + "\\hcom_tmp_" + ''.join([random.choice("abcdef0123456789") for n in xrange(5)]) + geoType
    tmpWriterName = "tmp_geoWriter_" + ''.join([random.choice("abcdef0123456789") for n in xrange(5)])
    
    result = nuke.executeInMainThreadWithResult(_createObjWriter, args=(tmpWriterName, tmpfilePath, selectedNode, curFrame, alembic, frames))
    
    if not result:
        return False
    
    
    with open(tmpfilePath, 'rb') as f:
        data = f.read()
        
    
    try:   
        os.remove(tmpfilePath)
    except:
        pass
    
    meshOut["MESH_TYPE"] = geoType
    meshOut["MESH_NAME"] = selectedNode.name()
    meshOut["MESH_DATA"] = data
    
    w = nuke.toNode(tmpWriterName)
    if w:
        nuke.delete(w)
    
    outType = "mesh"
    if alembic:
        outType = "alembic"
        meshOut["NAME"]= selectedNode.name()
        meshOut["FRAME_RANGE"] = frames
        meshOut["DATA"]= data
        
    result = _sendData(target_clientID, sender, meshOut, outType, tabTarget)
    
    return result

def _createObjWriter(tmpWriterName, tmpfilePath, selectedNode, curFrame, alembic, frames):
    
    w = nuke.createNode('WriteGeo', inpanel=False)
    w.setName(tmpWriterName)
    w["file"].setValue(tmpfilePath.replace("\\", "/"))
    w.setInput(0, selectedNode)
    
    try:
        
        if alembic:
            w["use_limit"].setValue(True)
            w["first"].setValue(int(frames[0]))
            w["last"].setValue(int(frames[1]))
            w["file_type"].setValue(1)
            nuke.execute(tmpWriterName, int(frames[0]), int(frames[1]), 1)
        else:
            w["file_type"].setValue(3)
            nuke.execute(tmpWriterName, curFrame, curFrame, 1)
            
    except RuntimeError as e:
        
        print str(e)
        return False
    
    return True


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
    NukeGlobals.MAIN_UI.updateUiThread.data = {"ACTION":"server_disconnect", "ID":None, "CLIENT_TYPE":None}
    
    
def server_is_disconnected():
    disconnect()