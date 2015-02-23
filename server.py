import rpyc
import socket
import sys

neighbour_ip = "localhost"
print sys.argv
if len(sys.argv) == 2:
    neighbour_ip = sys.argv[1]

def getDHT():
    DHT = {}
    filename = "DHT1.txt"
    try:
        with open(filename, "r") as DHTFile:
            for line in DHTFile:
                key, value = line.partition(":")[::2]
                DHT[int(key.strip())] = int(value.strip())
        return DHT
    except IOError:
        open(filename, 'a').close()
        return DHT


def updateDHT(DHT):
    print DHT
    with open("DHT1.txt", "w") as DHTFile:
        for key in DHT:
            DHTFile.write(str(key) + " : " + str(DHT[key]) + "\n")
        DHTFile.close()


class MyService(rpyc.Service):
    rpyc.Service.DHT = getDHT()
    rpyc.Service.Max = 1000
    rpyc.Service.node_id = 0
    rpyc.Service.node_ip = socket.gethostbyname(socket.gethostname())
    rpyc.Service.neighbour_id = 100
    rpyc.Service.neighbour_ip = neighbour_ip
    rpyc.Service.conn = None
    rpyc.Service.neighbour_port = 18862
    try:
        rpyc.Service.conn = rpyc.connect(rpyc.Service.neighbour_ip, rpyc.Service.neighbour_port)
        conn = rpyc.Service.conn
        rpyc.Service.node_id, rpyc.Service.neighbour_id, rpyc.Service.DHT, rpyc.Service.neighbour_ip = rpyc.conn.root.connect()
        updateDHT(rpyc.Service.DHT)
    except socket.error:
        rpyc.Service.conn = None

    def exposed_connect(self):
        if rpyc.Service.neighbour_id > rpyc.Service.node_id:
            middle_id = (rpyc.Service.neighbour_id - rpyc.Service.node_id)/2 + rpyc.Service.node_id
        else:
            middle_id = round((1000 - rpyc.Service.node_id)/2, 0) + rpyc.Service.node_id
        top_DHT = {}
        bottom_DHT = {}
        for key in rpyc.Service.DHT:
            if key > middle_id:
                top_DHT[key] = rpyc.Service.DHT[key]
            else:
                bottom_DHT[key] = rpyc.Service.DHT[key]
        rpyc.Service.DHT = bottom_DHT
        updateDHT(rpyc.Service.DHT)
        return middle_id, rpyc.Service.neighbour_id, top_DHT, rpyc.Service.neighbour_ip

    def exposed_get_ip(self):
        return rpyc.Service.node_ip

    def exposed_get(self, key):
        if not rpyc.Service.conn:
            try:
                rpyc.Service.conn = rpyc.connect(rpyc.Service.neighbour_ip, rpyc.Service.neighbour_port)
            except socket.error:
                rpyc.Service.conn = None
        if rpyc.Service.node_id < key < rpyc.Service.neighbour_id or rpyc.Service.neighbour_id < rpyc.Service.node_id < key:
            print "get: " + key
            try:
                return rpyc.Service.DHT[key]
            except KeyError:
                return None
        else:
            if rpyc.Service.conn:
                print "get: " + key + " not found"
                return rpyc.Service.conn.root.get(key)

    def exposed_put(self, key, value):
        if not rpyc.Service.conn:
            try:
                rpyc.Service.conn = rpyc.connect(rpyc.Service.neighbour_ip, rpyc.Service.neighbour_port)
            except socket.error:
                rpyc.Service.conn = None
        if rpyc.Service.node_id < key < rpyc.Service.neighbour_id or rpyc.Service.neighbour_id < rpyc.Service.node_id < key:
            rpyc.Service.DHT[int(key)] = int(value)
            updateDHT(rpyc.Service.DHT)
            print str(key) + ":" + str(value) + " added to DHT"
            return True
        else:
            return rpyc.Service.conn.root.put(key, value)


if __name__ == "__main__":
    from rpyc.utils.server import ThreadedServer
    t = ThreadedServer(MyService, port=18861)
    t.start()