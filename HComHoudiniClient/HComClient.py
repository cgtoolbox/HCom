import hou

import rpyc
import sys
import getpass
import os

import threading

pysidePath = os.environ["PYTHONHOME"] + r"lib\site-packages-forced"
if not pysidePath in sys.path:
    sys.path.append(pysidePath)

import HComUi

import HComUtils
reload(HComUtils)

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

        HComUi.receiveData(sender, data, dataType, tabTarget, clientType)
        
    def exposed_sendIDUpdate(self, ID, action, clientType):
        
        HComUi.receiveIDUpdate(ID, action, clientType)


def connectToServer(ID=None, clientType="NONE"):
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


def sendSettings(target_clientID, sender, tabTarget, tabClientType=None):
    
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

 
def sendOtl(target_clientID, sender, tabTarget, tabClientType=None):
    
    n = hou.selectedNodes()
    if not n:
        hou.ui.displayMessage("Nothing is selected")
        return False
    sel = n[0]
    
    if tabClientType[0] != HComUtils.CLIENT_TYPE.HOUDINI:
        if not sel.type().definition():
            hou.ui.displayMessage("Invalid node")
            return False
        
        else:
            if hou.expandString("$HH") in sel.type().definition().libraryFilePath():
                hou.ui.displayMessage("Invalid node")
                return False
    
    parentType = ""
    if sel.__class__ == hou.SopNode:
        parentType = "geo"
        
    elif sel.__class__ == hou.ObjNode:
        parentType = "obj"
        
    elif sel.__class__ == hou.ShopNode:
        parentType = "shop"
        
    elif sel.__class__ == hou.CopNode:
        parentType = "cop"
        
    elif sel.__class__ == hou.DopNode:
        parentType = "dop"
        
    elif sel.__class__ == hou.RopNode:
        parentType = "rop"
        
    elif sel.__class__ == hou.VopNode:
        
        parentType = "vop;"
        parentType += sel.parent().type().name() + ";"
        
        if sel.parent().__class__ == hou.SopNode:
            parentType += "sop"
            
        elif sel.parent().__class__ == hou.ShopNode:
            parentType += "material"
            
        elif sel.parent().__class__ == hou.CopNode:
            parentType += "cop"
            
        else:
            hou.ui.displayMessage("The current node type is not supported by HCom yet.")
            return False
        
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
    if result:
        return True
    else:
        return False
    
def sendAlembic(target_clientID, sender, tabTarget, tabClientType=None):
    
    selection = hou.selectedNodes()
    if not selection:
        hou.ui.displayMessage("Nothing is selected")
        return False
    
    selection = selection[0]
    if not selection.__class__ == hou.ObjNode:
        hou.ui.displayMessage("Selection must be a geo node")
        return False
    
    start = 1
    end = 100
    cancelled = False
    inputValid = False
    while not inputValid:
    
        pickFrameUI = hou.ui.readMultiInput("Enter a frame range:",
                                            ["Start Frame", "End Frame"],
                                            buttons = ["Ok", "Cancel"],
                                            initial_contents=(hou.expandString("$FSTART"), hou.expandString("$FEND")),
                                            title="Pick Frame Range",
                                            help="Must be two integers")
        if pickFrameUI[0] == 1:
            cancelled = True
            inputValid = True
        else:
            start = pickFrameUI[1][0]
            end = pickFrameUI[1][1]
            
            if not start.isdigit() or not end.isdigit():
                inputValid = False
                
            else:
                if int(start) > int(end):
                    inputValid = False
                else:
                    start = int(start)
                    end = int(end)
                    inputValid = True
                    
    if cancelled:
        return False
    
    name = selection.name()
    frames = [start, end]
    
    nodePath = selection.path()
    tmpGeo = hou.node("/obj").createNode("geo", run_init_scripts=False)
    tmpGeo.setName('alembic_tmp_exporter', unique_name=True)
    
    objectMerge = tmpGeo.createNode("object_merge")
    objectMerge.parm("objpath1").set(nodePath)
    
    alembicExport = tmpGeo.createNode("rop_alembic")
    alembicExport.parm("trange").set(1)
    alembicExport.parm("f1").deleteAllKeyframes()
    alembicExport.parm("f1").set(int(frames[0]))
    alembicExport.parm("f2").deleteAllKeyframes()
    alembicExport.parm("f2").set(int(frames[1]))
    
    alembicExport.parm("save_attributes").set(0)
    
    alembicExport.setInput(0, objectMerge)
    
    outFile = HComUtils.fetchMyReceivedFilesFolder() + os.sep + name + "_tmpCacheAlembic.abc"
    
    alembicExport.parm("filename").set(outFile)
    alembicExport.render()
    
    tmpGeo.destroy()
    
    with open(outFile, 'rb') as f:
        data = f.read()
    
    # Clean tmp file
    try:
        os.remove(outFile)
    except:
        pass
    
    outDic = {}
    outDic["NAME"] = name
    outDic["FRAME_RANGE"] = frames
    outDic["DATA"]= data
    
    result = _sendData(target_clientID, sender, outDic, "alembic", tabTarget)
    if result:
        return True
    else:
        return False


def sendBgeo(target_clientID, sender, tabTarget, isObj=False, tabClientType=None):
    
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
    if result:
        return True
    else:
        return False


def sendObjMesh(target_clientID, sender, tabTarget, tabClientType=None):
    result = sendBgeo(target_clientID, sender, tabTarget, isObj=True)
    return result


def sendPic(target_clientID, sender, tabTarget, imagePath, tabClientType=None):
    
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
    HComUi.HComMainUi.updateUiThread.data = {"ACTION":"server_disconnect", "ID":None, "CLIENT_TYPE":None}
    
    
def server_is_disconnected():
    disconnect()