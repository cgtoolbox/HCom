import hou

import rpyc
import sys
import getpass
import os

pysidePath = os.environ["PYTHONHOME"] + r"lib\site-packages-forced"
if not pysidePath in sys.path:
    sys.path.append(pysidePath)

import HComUi
import HComUtils

global server_conn
server_conn = None

global server_id
server_id = None

global bgsrv
bgsrv = None


class HCom_ClientService(rpyc.Service):
    '''
        This is the client service called to fetch data from server.
    '''
    
    def on_disconnect(self):
        server_is_disconnected()
    
    def exposed_catchData(self, dataType, sender, data, tabTarget):

        HComUi.receiveData(sender, data, dataType, tabTarget)
        
    def exposed_sendIDUpdate(self, ID, action):
        
        HComUi.receiveIDUpdate(ID, action)


def connectToServer(ID=None):
    '''
        Try to connect to the server and launch the BG thread service
    '''
    
    if not ID:
        ID = getpass.getuser()
    
    global server_conn
    global bgsrv
    
    try:
        server_conn = rpyc.connect(HComUtils.readIni()["SERVER"], int(HComUtils.readIni()["PORT"]), service=HCom_ClientService, config={"allow_pickle":True})
    except Exception as e:
        print("ERROR: Can not connect to server: " + str(e))
        return False, False
    else:
        if ID in server_conn.root.getAllClients().keys():
            hou.ui.displayMessage("User ID already registered on the server")
            server_conn.close()
            return False
        
        hou.session.HCOMCLIENT = [server_conn, ID]
        
    global server_id
    server_id = ID
    
    bgsrv = rpyc.BgServingThread(server_conn)
    result = server_conn.root.registerClient(ID)
    
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
        result = server_conn.root.sendDataToClient(target_clientID, datatype, sender, data, tabTarget)
        return result
    except AttributeError:
        return False
        print("ERROR: client {0} not found.".format(target_clientID))
        
def sendMessage(target_clientID, sender, message, tabTarget):
    
    result = _sendData(target_clientID, sender, message, "msg", tabTarget)
    return result

def sendSettings(target_clientID, sender, tabTarget):
    
    settingsData = {}
    
    n = hou.selectedNodes()
    if not n:
        hou.ui.displayMessage("Nothing is selected")
        return False
    sel = n[0]
    
    settingsData["OTL_TYPE"] = sel.type().name()
    
    parmDict = {}
    parms = sel.parms()
    for p in parms:
        parmDict[p.name()] = p.eval()
        
    settingsData["OTL_PARMS"] = parmDict
    
    result = _sendData(target_clientID, sender, settingsData, "settings", tabTarget)
    return [result, settingsData["OTL_TYPE"] + " settings"]
    
def sendOtl(target_clientID, sender, tabTarget):
    
    n = hou.selectedNodes()
    if not n:
        hou.ui.displayMessage("Nothing is selected")
        return False
    sel = n[0]
    
    parentType = ""
    if sel.__class__ == hou.SopNode:
        parentType = "geo"
    elif sel.__class__ == hou.ObjNode:
        parentType = "obj"
    else:
        hou.ui.displayMessage("The current node type is not supported by HCom yet.")
        return False
    
    otlData = {}
    otlData["OTL_PARENT_TYPE"] =  parentType
    otlData["PY_CODE"] = sel.asCode(recurse=True)
    otlData["OTL_NAME"] = sel.name()
    otlData["OTL_TYPE"] = sel.type().name()
    otlData["OTL_ALL_LIBS"] = HComUtils.getAllLib(sel)
    
    result = _sendData(target_clientID, sender, otlData, "otl", tabTarget)
    return [result, "node: " + otlData["OTL_NAME"]]
    
def sendBgeo(target_clientID, sender, tabTarget, isObj=False):
    
    n = hou.selectedNodes()
    if not n:
        hou.ui.displayMessage("Nothing is selected")
        return False
    sel = n[0]
    
    if sel.__class__ != hou.SopNode:
        hou.ui.displayMessage("Node selected is not a sop node")
        return False
    
    geo = sel.geometry()
    
    if isObj:
        if not geo.points():
            hou.ui.displayMessage("No points found on geometry")
            return False
    
    fileType = ".bgeo"
    if isObj:
        fileType = ".obj"
    
    # Dump geo on disk in a tmp file if data() not supported by houdini's version
    # If it is an obj file it must pass by saveToFile() methode
    if hasattr(geo, "data") and not isObj:
        binaryData = geo.data()
    else:
        tmpFile = hou.expandString("$HOME") + "/" + "tmphcom__" + fileType
        geo.saveToFile(tmpFile)
        binaryData = ""
        with open(tmpFile, 'rb') as f:
            binaryData = f.read()
        os.remove(tmpFile)
    
    meshData = {}
    meshData["MESH_TYPE"] = fileType
    meshData["MESH_NAME"] = sel.name()
    meshData["MESH_DATA"] = binaryData
    
    result = _sendData(target_clientID, sender, meshData, "mesh", tabTarget)
    return [result, "geometry: " + meshData["MESH_NAME"] + ", type: " + meshData["MESH_TYPE"] ]
    
def sendObjMesh(target_clientID, sender, tabTarget):
    result = sendBgeo(target_clientID, sender, tabTarget, isObj=True)
    return result
    
def sendPic(target_clientID, sender, tabTarget, imagePath):
    
    if not os.path.exists(imagePath):
        return False
    
    with open(imagePath, 'rb') as f:
        imageData = f.read()
        
    outImdageData = {}
    outImdageData["IMAGE_NAME"] = os.path.basename(imagePath)
    outImdageData["BINARY_DATA"] = imageData
    
    result = _sendData(target_clientID, sender, outImdageData, "pic", tabTarget)
    return [ result, "image file: " + outImdageData["IMAGE_NAME"]]

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
    HComUi.HComMainUi.updateUiThread.data = "server_disconnect;None"
    
    
def server_is_disconnected():
    disconnect()