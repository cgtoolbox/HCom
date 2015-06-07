import os
import time
import hou
import subprocess
import random
import threading

HISTORY_FOLDER = os.path.dirname(__file__) + "\\HCom_History\\"
ICONPATH = os.path.dirname(__file__) + "\\HCom_Icons\\"

def readIni():
    
    iniValues = {}
    
    ini = os.path.dirname(__file__) + "\\HCom.ini"
    with open(ini, 'r') as f:
        for i in f.readlines():
            if i.startswith("#"):
                continue
            elif i == "\n":
                continue
            else:
                data = i.split("=")
                
                val = data[1].replace("\n", "")
                if val.isdigit() and "." in val:
                    val = float(val)
                elif val.isdigit() and not "." in val:
                    val = int(val)
                elif val.lower() == "true":
                    val = True
                elif val.lower() == "false":
                    val = False
                else:
                    val = str(val)
                
                iniValues[data[0]] = val
                
    return iniValues

def writeIni(settings):
    ini = os.path.dirname(__file__) + "\\HCom.ini"
    with open(ini, 'w') as f:
        
        f.write("#HCom info file\n")
        
        for k in settings.keys():
            f.write(k + "=" + str(settings[k]) + "\n")

def getAllLib(node):
    '''
        Fetch all library path of sub otls and selected otl.
        returns a dict {lib_file:binary_data}
    '''
    
    libFound = False
    libData = []
    libNameList = []
                
    # All sub children nodes
    allChildrens = list(node.allSubChildren())
    allChildrens.append(node)
    
    for childrenNode in allChildrens:
        
        nodeDefinition = childrenNode.type().definition()
        if not nodeDefinition:
            continue
        
        libPath = nodeDefinition.libraryFilePath()
        libName = os.path.basename(libPath)
        
        if libName in libNameList:
            continue
        
        # Skip built-in otl
        if libPath.startswith(hou.expandString("$HH")):
            continue
        
        if not os.path.exists(libPath):
            continue
        
        binaryData = ""
        with open(libPath, 'rb') as f:
            binaryData = f.read()
        
        libData.append([libName, binaryData])
        libNameList.append(libName)
        libFound = True
    
    if libFound:
        return libData
    return False

def writeHistory(sender, timeStamp, data):
    
    historyFile = HISTORY_FOLDER + sender.lower() + "_history.txt"
    with open(historyFile, 'a') as f:
        f.write(timeStamp + "\n")
        f.write("  " + str(data) + "\n")      

def coloredString(string, hexColor=None, rgb=None, italic=False, bold=False):
        
    in_italic_tag = ""
    out_italic_tag = ""
    if italic:
        in_italic_tag = "<i>"
        out_italic_tag = "</i>"
        
    in_bold_tag = ""
    out_bold_tag = ""
    if bold:
        in_bold_tag = "<b>"
        out_bold_tag = "</b>"
    
    if not hexColor and not rgb:
        return "<FONT>{0}{1}{2}{3}{4}</FONT>".format(in_italic_tag, in_bold_tag, string, out_bold_tag, out_italic_tag)
    
    if hexColor:
        if hexColor.startswith("#"):
            hexColor = hexColor.replace("#", "")
        return "<FONT COLOR=#{5}>{0}{1}{2}{3}{4}</FONT>".format(in_italic_tag, in_bold_tag, string, out_bold_tag, out_italic_tag, hexColor)
    else:
        return "<FONT COLOR=rgb({5},{6},{7})>{0}{1}{2}{3}{4}</FONT>".format(in_italic_tag, in_bold_tag, string, out_bold_tag, out_italic_tag, rgb[0], rgb[1], rgb[2])
    
def incrementFile(filePath):
    
    if not os.path.exists(filePath):
        return filePath
    
    baseName = os.path.basename(filePath)
    name = baseName.split(".")[0]
    fileType = baseName.split(".")[1]
    dirName = os.path.dirname(filePath)
    
    fileInc = dirName + os.sep + name + "_1." + fileType
    i = 2
    while os.path.exists(fileInc):
        fileInc = dirName + os.sep + name + "_" + str(i) + "." + fileType
    
    return fileInc

def createAlembic(data, sender="", settings=None):
    
    hou.setUpdateMode(hou.updateMode.Manual)
    
    fileName = data["NAME"]
    filePath = fetchMyReceivedFilesFolder() + os.sep + fileName
    filePath = incrementFile(filePath)
    
    with open(filePath, 'wb') as f:
        f.write(data["DATA"])
    
    geo = hou.node("/obj").createNode("geo", run_init_scripts=False)
    geo.setName("Alembic_container_from_" + sender, unique_name=True)
    geo.appendComment("Alembic_container_from_" + sender)
    
    alembicNode = geo.createNode("alembic")
    alembicNode.parm("fileName").set(filePath)
    
    return True

def createOtl(data, sender="", settings=None):
    
    nodeName = data["OTL_NAME"]
    parentType = data["OTL_PARENT_TYPE"]
    subOtlLibs = data["OTL_ALL_LIBS"]
    
    # Switch houdini to manual update according to settings
    if settings["SWITCH_TO_MANUAL_UPDATE"]:
        hou.setUpdateMode(hou.updateMode.Manual)
    
    # Check otl libs
    if subOtlLibs:
        
        allLoadedFiles = [os.path.basename(n) for n in hou.hda.loadedFiles()]
        
        for e in subOtlLibs:
            libName = e[0]
            libData = e[1]
            
            if libName in allLoadedFiles:
                continue
            
            otlLibToInstall = fetchMyReceivedFilesFolder() + os.sep + libName
            
            with open(otlLibToInstall, 'wb') as f:
                f.write(libData)
            
            hou.hda.installFile(otlLibToInstall)
    
    comment = " Node sent by {0} ({1})".format(str(sender), time.ctime())
    pyCode = data["PY_CODE"].split("\n")
    
    outPyCode = ""
    houNodeFound = False
    for c in pyCode:
        
        # Change code to create a geo container for sop node
        if parentType == "geo":
            if c.replace(" ", "").startswith("hou_parent") and not houNodeFound:
                houNodeFound = True
                outPyCode += c + "\n"
                outPyCode += "hou_parent = hou.node('/obj').createNode('geo', run_init_scripts=False)\n"
                outPyCode += "hou_parent.setName('{0}_container_' + '_from_{1}', unique_name=True)\n".format(nodeName, str(sender))
                outPyCode += "hou_parent.appendComment('HCom:')\n"
                outPyCode += "hou_parent.appendComment('{0}')\n".format(comment)
            else:
                outPyCode += c + "\n"
        
        # Change parent to shopnet for shop nodes       
        elif parentType == "shop":
            if c.replace(" ", "").startswith("hou_parent") and not houNodeFound:
                houNodeFound = True
                outPyCode += c + "\n"
                outPyCode += "container = hou.node('/obj').createNode('geo', run_init_scripts=False)\n"
                outPyCode += "container.setName('{0}_container_' + '_from_{1}', unique_name=True)\n".format(nodeName, str(sender))
                outPyCode += "container.appendComment('HCom:')\n"
                outPyCode += "container.appendComment('{0}')\n".format(comment)
                outPyCode += "hou_parent = container.createNode('shopnet', run_init_scripts=False)\n"
            else:
                outPyCode += c + "\n"
                
        # Change parent to dopnet for dop nodes       
        elif parentType == "dop":
            if c.replace(" ", "").startswith("hou_parent") and not houNodeFound:
                houNodeFound = True
                outPyCode += c + "\n"
                outPyCode += "container = hou.node('/obj').createNode('geo', run_init_scripts=False)\n"
                outPyCode += "container.setName('{0}_container_' + '_from_{1}', unique_name=True)\n".format(nodeName, str(sender))
                outPyCode += "container.appendComment('HCom:')\n"
                outPyCode += "container.appendComment('{0}')\n".format(comment)
                outPyCode += "hou_parent = container.createNode('dopnet', run_init_scripts=False)\n"
            else:
                outPyCode += c + "\n"
                
        # Change parent to copnet for cop nodes       
        elif parentType == "cop":
            if c.replace(" ", "").startswith("hou_parent") and not houNodeFound:
                houNodeFound = True
                outPyCode += c + "\n"
                outPyCode += "container = hou.node('/obj').createNode('geo', run_init_scripts=False)\n"
                outPyCode += "container.setName('{0}_container_' + '_from_{1}', unique_name=True)\n".format(nodeName, str(sender))
                outPyCode += "container.appendComment('HCom:')\n"
                outPyCode += "container.appendComment('{0}')\n".format(comment)
                outPyCode += "hou_parent = container.createNode('cop2net', run_init_scripts=False)\n"
            else:
                outPyCode += c + "\n"
                
        # Change parent to ropnet for rop nodes       
        elif parentType == "rop":
            if c.replace(" ", "").startswith("hou_parent") and not houNodeFound:
                houNodeFound = True
                outPyCode += c + "\n"
                outPyCode += "container = hou.node('/obj').createNode('geo', run_init_scripts=False)\n"
                outPyCode += "container.setName('{0}_container_' + '_from_{1}', unique_name=True)\n".format(nodeName, str(sender))
                outPyCode += "container.appendComment('HCom:')\n"
                outPyCode += "container.appendComment('{0}')\n".format(comment)
                outPyCode += "hou_parent = container.createNode('ropnet', run_init_scripts=False)\n"
            else:
                outPyCode += c + "\n"
        
        # Change code to change node name
        elif parentType == "obj":
            if c.startswith("hou_node") and not houNodeFound:
                houNodeFound = True
                outPyCode += c + "\n"                   
                outPyCode += "hou_node.setName('{0}' + '_from_{1}', unique_name=True)\n".format(nodeName, str(sender))
                outPyCode += "hou_node.appendComment('HCom:')\n"
                outPyCode += "hou_node.appendComment('{0}')\n".format(comment)
            else:
                outPyCode += c + "\n"
                
        # Change parent to vopsop for vex nodes       
        elif "vop" in parentType:
            
            parentTypeContainer = parentType.split(";")[1]
            parentClass = parentType.split(";")[2]
            
            # is a sop vop network
            if parentClass == "sop":
                if c.replace(" ", "").startswith("hou_parent") and not houNodeFound:
                    houNodeFound = True
                    outPyCode += c + "\n"
                    outPyCode += "container = hou.node('/obj').createNode('geo', run_init_scripts=False)\n"
                    outPyCode += "container.setName('{0}_container_' + '_from_{1}', unique_name=True)\n".format(nodeName, str(sender))
                    outPyCode += "container.appendComment('HCom:')\n"
                    outPyCode += "container.appendComment('{0}')\n".format(comment)
                    outPyCode += "hou_parent = container.createNode('{0}', run_init_scripts=False)\n".format(parentTypeContainer)
                else:
                    outPyCode += c + "\n"
            
            # it's a material network      
            elif parentClass == "material":
                if c.replace(" ", "").startswith("hou_parent") and not houNodeFound:
                    houNodeFound = True
                    outPyCode += c + "\n"
                    outPyCode += "container = hou.node('/obj').createNode('geo', run_init_scripts=False)\n"
                    outPyCode += "container.setName('{0}_container_' + '_from_{1}', unique_name=True)\n".format(nodeName, str(sender))
                    outPyCode += "container.appendComment('HCom:')\n"
                    outPyCode += "container.appendComment('{0}')\n".format(comment)
                    outPyCode += "shopnet = container.createNode('shopnet', run_init_scripts=False)\n"
                    outPyCode += "hou_parent = shopnet.createNode('{0}', run_init_scripts=False)\n".format(parentTypeContainer)
                else:
                    outPyCode += c + "\n"
                    
            # it's a cop network      
            elif parentClass == "cop":
                if c.replace(" ", "").startswith("hou_parent") and not houNodeFound:
                    houNodeFound = True
                    outPyCode += c + "\n"
                    outPyCode += "container = hou.node('/obj').createNode('geo', run_init_scripts=False)\n"
                    outPyCode += "container.setName('{0}_container_' + '_from_{1}', unique_name=True)\n".format(nodeName, str(sender))
                    outPyCode += "container.appendComment('HCom:')\n"
                    outPyCode += "container.appendComment('{0}')\n".format(comment)
                    outPyCode += "copnet = container.createNode('cop2net', run_init_scripts=False)\n"
                    outPyCode += "hou_parent = copnet.createNode('{0}', run_init_scripts=False)\n".format(parentTypeContainer)
                else:
                    outPyCode += c + "\n"
    try:
        
        exec(outPyCode)
    except Exception as e:
        print("ERROR: exec pyCode " + str(e))
        
def setOtlSettings(data, sender="", settings=None):
    
    nodeType = data["OTL_TYPE"]
    
    selNode = hou.ui.selectNode()
    if not selNode:
        return False
    else:
        selection = hou.node(selNode)
    
    if selection.type().name() != nodeType:
        hou.ui.displayMessage("You must select a node of type: " + nodeType)
        return
    
    parms = data["OTL_PARMS"]
    for p in parms:
        
        parm = selection.parm(p)
        if parm:
            parm.set(parms[p])
        else:
            print("Parm '{0}' not found, skipped.".format(p))

def createMesh(data, sender="", settings=None):
    
    meshType = data["MESH_TYPE"]    
    meshName = data["MESH_NAME"]
    meshData = data["MESH_DATA"]
    
    bgeoFile = fetchMyReceivedFilesFolder() + os.sep + meshName + meshType
    bgeoFile = incrementFile(bgeoFile)
    with open(bgeoFile, 'wb') as f:
        f.write(meshData)
        
    comment = " Node sent by {0} ({1})".format(str(sender), time.ctime())
    container = hou.node("/obj").createNode("geo", run_init_scripts=False)
    container.setName(meshName + "_{0}_from_".format(meshType.replace(".", "")) + sender, unique_name=True)
    container.appendComment(comment)
    
    fileNode = container.createNode("file")
    fileNode.setName(meshName + "_{0}_model".format(meshType.replace(".", "")))
    fileNode.parm("file").set(bgeoFile)
    
def createPic(data, sender="", settings=None):
    
    imageName = data["IMAGE_NAME"]   
    imageData = data["BINARY_DATA"]
    
    imageNameAndFile = imageName.split(".")
            
    outFile = fetchMyReceivedFilesFolder() + os.sep + imageNameAndFile[0] + "." + imageNameAndFile[1]
    outFile = incrementFile(outFile)
    
    with open(outFile, 'wb') as f:
        f.write(imageData)
    
    t = threading.Thread(target = openPicFile, args=(outFile,))
    t.start()
            
def openPicFile(picFile):
    
    try:
        subprocess.Popen(["mplay.exe", picFile])
    except Exception as e:
        print "MPLAY ERROR: " + str(e)
        try:
            subprocess.Popen(["explorer", picFile])
        except Exception as e:
            print "EXPLORER ERROR: " + str(e)
    

def fetchMyReceivedFilesFolder():
    
    p = readIni()["MY_RECEIVED_FILES"]
    if p == "DEFAULT":
        p = os.path.dirname(__file__) + "\\HCom_Received_Files"
    
    if not os.path.exists(p):
        os.makedirs(p)
    
    return p
    
def rdnname():
    names = ["Motoko", "Bato", "Kusanagi", "Frodon", "Sheldon", "Pipo", "Sam", "Gandalf", "Fitz", "Henry"]
    names += ["Leonard", "Batman", "Bobleponge", "rincewind", "carrot", "HelloWorld", "Python", "Houdini"]
    return names[random.randint(0, len(names)-1)]

class CLIENT_TYPE():
    
    NONE = "NONE"
    HOUDINI = "Houdini"
    MAYA_NO_HENGINE = "Maya_no_hengine"
    MAYA_HENGINE = "Maya_hengine"
    NUKE = "nuke"
    