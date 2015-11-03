#!/usr/bin/env python3

import errno
import functools
from tornado import ioloop
import socket
import struct
import subprocess

blockips={}
minustime=3600

class IPManager:
    def create():
        subprocess.Popen(['ipset', 'create', 'block_ip', 'hash:ip'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True

    def add(ip):
        print("Block ip :"+ip)
        subprocess.Popen(['ipset', 'add', 'block_ip', ip], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True

    def remove(ip):
        subprocess.Popen(['ipset', 'del', 'block_ip', ip], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True

class ClientIP:
    def __init__(self, ip, port):
        self.ip = ip
        self.ports = set()
        self.ports.add(port)
        self.limit = 3

    def add(self, port):
        if port not in self.ports:
            self.ports.add(port)
            if len(self.ports) == self.limit:
                IPManager.add(self.ip)
        return len(self.ports)

    def minus(self):
        if len(self.ports) == self.limit:
            IPManager.remove(self.ip)
        if len(self.ports) > 0:
            self.ports.pop()
        return len(self.ports)

def connection_ready(sock, fd, events):
    while True:
        try:
            connection, address = sock.accept()
        except socket.error as e:
            if e.args[0] not in (errno.EWOULDBLOCK, errno.EAGAIN):
                print("Socks error")
                connection.close()
                continue
        try:
            dst = connection.getsockopt(socket.SOL_IP, 80, 16)
            dst_port, dst_ip = struct.unpack("!2xH4s8x", dst)
            src_ip, src_port = connection.getpeername()
        except:
            print("Get Address Error")
            connection.close()
            break
        ip = src_ip
        port = dst_port
        global blockips
        if ip in blockips:
            blockips[ip].add(port)
        else:
            blockips[ip]=ClientIP(ip,port)
        print("Connection From: "+src_ip+" To "+str(dst_port) + " Times: " + str(len(blockips[ip].ports)))
        connection.close()
        break

def autominus(io_loop):
    global blockips
    print("Auto Minus")
    for k in blockips.keys():
        blockips[k].minus()
    blockips = { k:v for k,v in blockips.items() if (len(v.ports) > 0)}
    io_loop.call_later(minustime,autominus,io_loop)
    return True

if __name__ == '__main__':
    IPManager.create()
    sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setblocking(0)
    sock.bind(("0.0.0.0", 3100))
    sock.listen(128)
    io_loop = ioloop.IOLoop.instance()
    callback = functools.partial(connection_ready, sock)
    io_loop.add_handler(sock.fileno(), callback, io_loop.READ)
    io_loop.call_later(minustime,autominus,io_loop)
    io_loop.start()
