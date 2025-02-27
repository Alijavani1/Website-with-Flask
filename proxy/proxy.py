import select
import socket
import threading
from scapy.all import *
from scapy.layers.http import HTTP, HTTPRequest
from scapy.all import IP, TCP


def http_packet_callback(packet):
    # Check if the packet has an HTTP layer
    if packet.haslayer(HTTPRequest):
        # Extract HTTP request details
        http_layer = packet[HTTPRequest]
        print(f"HTTP Method: {http_layer.Method.decode('utf-8')}")
        print(f"Host: {http_layer.Host.decode('utf-8')}")
        print(f"Path: {http_layer.Path.decode('utf-8')}")
        print(f"User-Agent: {http_layer.User_Agent.decode('utf-8')}")


def threaded(fn):
    def wrapper(*args, **kwargs):
        _thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        _thread.start()
        return _thread

    return wrapper


class TCPBridge(object):

    def __init__(self, host, port, dst_host, dst_port):
        self.host = host
        self.port = port
        self.dst_host = dst_host
        self.dst_port = dst_port

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.settimeout(1)
        self.server.bind((self.host, self.port))
        self.stop = False

    @threaded
    def tunnel(self, sock: socket.socket, sock2: socket.socket, chunk_size=1024):
        try:
            while not self.stop:
                """this line is for raising exception when connection is broken"""
                sock.getpeername() and sock2.getpeername()
                r, w, x = select.select([sock, sock2], [], [], 1000)
                if sock in r:
                    data = sock.recv(chunk_size)
                    if len(data) == 0:
                        break
                    packet = IP(data)
                    if packet.haslayer(TCP):
                        tcp_layer = packet.getlayer(TCP)
                        # Change source IP to current machine IP
                        packet[IP].src = "192.168.217.130"
                        # Recompute the checksums
                        del packet[IP].chksum
                        del packet[TCP].chksum
                        data = bytes(packet)
                    sock2.sendall(data)

                if sock2 in r:
                    data = sock2.recv(chunk_size)
                    if len(data) == 0:
                        break
                    packet = IP(data)
                    if packet.haslayer(TCP):
                        tcp_layer = packet.getlayer(TCP)
                        # Change source IP to current machine IP
                        packet[IP].src = self.host
                        # Recompute the checksums
                        del packet[IP].chksum
                        del packet[TCP].chksum
                        data = bytes(packet)
                    sock.sendall(data)
        except:
            pass
        try:
            sock2.close()
        except:
            pass
        try:
            sock.close()
        except:
            pass

    def run(self) -> None:
        self.server.listen()

        while not self.stop:
            try:
                (sock, addr) = self.server.accept()
                if sock is None:
                    continue
                client_socket = socket.socket(
                    socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((self.dst_host, self.dst_port))
                self.tunnel(sock, client_socket)
            except KeyboardInterrupt:
                self.stop = True
            except TimeoutError as exp:
                pass
            except Exception as exp:
                print("Exception:", exp)


if __name__ == "__main__":
    # TODO:change destonation ip
    tcp_bridge = TCPBridge("0.0.0.0", 8888, "192.168.217.128", 8000)
    tcp_bridge.run()
