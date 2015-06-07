import sys
import rpyc
import copy
from rpyc.utils.server import ThreadedServer


class HCom_Server(rpyc.Service):
    
    '''
        Main server, CLIENTS is a dict of clients registered on the server
    '''
    CLIENTS = {}
    CLIENTS_TYPE = {}
    
    def on_disconnect(self):
        '''
            Remove the client when is disconnected from the registred dict
        '''
        clientDisconnected = ""
        clientDisconnected_type = "None"
        for k in self.CLIENTS.keys():
            try:
                if self.CLIENTS[k] == self._conn:
                    clientDisconnected = k
                    break
            except:
                continue
        
        
        if clientDisconnected:
            del(self.CLIENTS[clientDisconnected])
            clientDisconnected_type = self.CLIENTS_TYPE[clientDisconnected]
            del(self.CLIENTS_TYPE[clientDisconnected])
            sys.stdout.write("=> HCOM_INFO: Client " + str(clientDisconnected) + " left the server !\n")
        
            # Send update to clients
            for k in self.CLIENTS.keys():
                if k ==  clientDisconnected: continue
                self.CLIENTS[k].root.exposed_sendIDUpdate(clientDisconnected, "left", clientDisconnected_type)

    def exposed_registerClient(self, clientID, clientType):
        '''
            Save the given client ( from _conn ) to the CLIENTS dict, using the client ID as key 
        '''
        if not clientID in self.CLIENTS.keys():
            self.CLIENTS[clientID] = self._conn
            self.CLIENTS_TYPE[clientID] = clientType
            sys.stdout.write("=> HCOM_INFO: Client " + str(clientID) + " registered !\n")
            
            # Send update to clients
            for k in self.CLIENTS.keys():
                self.CLIENTS[k].root.exposed_sendIDUpdate(clientID, "join", clientType)
            
            print("=> HCOM_INFO: Registered clients: " + str(self.CLIENTS.keys()).replace("[", "").replace("]", ""))
                
            return True
        else:
            return False

    def exposed_removeClient(self, clientID):
        '''
            Remove client from server registered clients.
        '''
        if clientID in self.CLIENTS.keys():
            del(self.CLIENTS[clientID])
            del(self.CLIENTS_TYPE[clientID])
            sys.stdout.write("=> HCOM_INFO: Client " + str(clientID) + " removed from server !\n")
            sys.stdout.write("=> HCOM_INFO: Registered clients: " + str(self.CLIENTS.keys()).replace("[", "").replace("]", ""))
    
    def exposed_getClient(self, clientID):
        '''
            return given client.
        '''
        if not clientID in self.CLIENTS.keys():
            return None
        
        return self.CLIENTS[clientID]
    
    def exposed_getClientType(self, clientID):
        
        if not clientID in self.CLIENTS_TYPE.keys():
            return None
        
        return self.CLIENTS_TYPE[clientID]
    
    def exposed_getAllClientTypes(self):
        
        return self.CLIENTS_TYPE
    
    def exposed_getAllClients(self):
        '''
            return all clients registered on the server.
        '''
        return self.CLIENTS
    
    def exposed_getAllCientInfos(self):
        return [self.CLIENTS, self.CLIENTS_TYPE]

    def exposed_sendDataToClient(self, clientID, dataType, sender, data, tabTarget):
        '''
            Invoke the 'catchData' of the client(s) from the given ID(s).
        '''
        
        c_data = copy.copy(data)
        
        notReached = []
        if not isinstance(clientID, list):
            clientID = [clientID,]
        
        if 'OPEN_CHAT_ROOM' in clientID or tabTarget == 'OPEN_CHAT_ROOM':
            
            for k in self.CLIENTS.keys():
                if k == sender:
                    continue
                self.CLIENTS[k].root.exposed_catchData(dataType, sender, c_data, tabTarget, [None, None])
        else:
            for client in clientID:
                if not client in self.CLIENTS.keys():
                    notReached.append(client)
                    continue
                self.CLIENTS[client].root.exposed_catchData(dataType, sender, c_data, tabTarget, self.CLIENTS_TYPE[client])
            
            if not notReached:
                return True
            else:
                return notReached

                
if __name__ == "__main__":
    
    print("LAUNCHING HCOM SERVER ...")
    print("SERVER VERSION: 1.0")

    t = ThreadedServer(HCom_Server, port = 5000, protocol_config={"allow_public_attrs" : True, "allow_pickle" : True})
    t.start()