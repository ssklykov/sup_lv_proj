# -*- coding: utf-8 -*-
"""
Test transfer of an image through threaded multiple UDP ports launched by this script and LV code.

This script should reveal performance and capability to send an image through four independent ports.
Byte strings, that are sent through threaded ports, are decoded to image chunks in a dedicated thread.

@author: ssklykov
"""
# %% Imports
import socket
import time
from threading import Thread
import numpy as np

# %% Parameters
host = 'localhost'
port_py_main = 5005  # number of the first ports of that will be opened
port_py = 5010  # number of the first ports of that will be opened
port_LV = 5100
st_n_bytes = 1024


# %% Independent UDP server as a thread
class independentImgPort(Thread):
    """
    Implement socket on individual thread launched by this class (subclass of Thread class with overriden
                                                                  methods __init__ and run).
    """
    host = ''
    portN = 0
    sock = None
    received_str = ''
    received_img_chunk = []
    nRowsReceive = 0
    nRowsLast = 0
    nDispatchedChunks = 0
    chunk_max_size = 0

    def __init__(self, host, port_number: int, nRowsReceive: int, nRowsLast: int, nDispatchedChunks: int,
                 chunk_max_size: int, img_width: int):
        self.host = host
        self.portN = port_number
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.nRowsReceive = nRowsReceive
        self.nRowsLast = nRowsLast
        self.nDispatchedChunks = nDispatchedChunks
        self.chunk_max_size = chunk_max_size
        self.img_width = img_width
        Thread.__init__(self)
        # print("Port", self.portN, "initialized")  # for debugging
        # print(self.sock, "- check socket object created")  # for debugging

    def run(self):
        # print("Attempt to initialize port", self.portN)  # for debugging
        sock = self.sock
        try:
            sock.bind((self.host, self.portN))
            if self.nRowsLast == 0:
                self.received_img_chunk = np.zeros((self.nRowsReceive*self.nDispatchedChunks, self.img_width),
                                                   dtype="uint16")  # container for chunk initialization
            elif self.nRowsLast > 0:
                self.received_img_chunk = np.zeros((self.nRowsReceive*(self.nDispatchedChunks - 1) + self.nRowsLast,
                                                    self.img_width), dtype="uint16")
            sock.settimeout(1.2)
            # time.sleep(0.005)
            # print("Port", self.portN, "opened")  # for debugging
            # Transfer chunk by chunk
            for i in range(self.nDispatchedChunks):
                (raw_chunk, address) = sock.recvfrom(self.chunk_max_size)
                raw_chunk = (str(raw_chunk, encoding='utf-8'))  # Converting byte string to normal one
                # print("Received:", raw_chunk)  # for debugging
                string_chunk = raw_chunk.split()  # split to numbers using standard whitespace as a separator
                # Case below - for normal port (not last one)
                if self.nRowsLast == 0:  # Last transfer - not equal number of string
                    for j in range(self.nRowsReceive):
                        # Saving raw string as several rows in image
                        self.received_img_chunk[i*self.nRowsReceive + j, :] = np.uint16(
                            string_chunk[self.img_width*j:self.img_width*(j+1)])
                # Case below - for last port
                else:
                    # Exceptional case - transfer last rows from images (remained)
                    if (i == (self.nDispatchedChunks - 1)):
                        for j in range(self.nRowsLast):
                            self.received_img_chunk[i*self.nRowsReceive + j, :] = np.uint16(
                                string_chunk[self.img_width*j:self.img_width*(j+1)])
                    # Common case - transfer rows before remained ones (as a tail)
                    else:
                        for j in range(self.nRowsReceive):
                            # Saving raw string as several rows in image
                            self.received_img_chunk[i*self.nRowsReceive + j, :] = np.uint16(
                                string_chunk[self.img_width*j:self.img_width*(j+1)])

            # sendingString = "port " + str(self.portN) + " received"
            # sendingString = sendingString.encode()  # to utf-8
            # sock.sendto(sendingString, address)
            # time.sleep(0.005)
        finally:
            sock.close()


# %% Test independent UDP spawned servers - main part of a program
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as mainServer:
    mainServer.bind((host, port_py_main))
    flag = True
    print("Python UDP Server launched")

    while flag:
        (command, address) = mainServer.recvfrom(st_n_bytes)
        command = str(command, encoding='utf-8')  # Conversion to a normal string
        if "Ping" in command:
            print(command, '- received command')
            sendingString = "Echo"
            sendingString = sendingString.encode()  # to utf-8
            mainServer.sendto(sendingString, address)

        elif "Img multiports" in command:
            print(command, '- received command')
            # sendingString = "ports" + " " + str(port_py) + " " + str(port_py+1) + " " + " will be opened"
            # sendingString = sendingString.encode()  # to utf-8
            # mainServer.sendto(sendingString, address)

            # Code for image transfer has been taken from UDP_Py_unified module!!!
            (width, address) = mainServer.recvfrom(st_n_bytes)  # Height and width could be flipped!
            (height, address) = mainServer.recvfrom(st_n_bytes)  # Height and width could be flipped!
            width = int(str(width, encoding='utf-8'))
            height = int(str(height, encoding='utf-8'))
            print("Sizes of an image [pixels]:", width, "x", height)  # debug
            img = np.zeros((height, width), dtype="uint16")  # image initialization (container)
            chunk_max_size = 110*100*8
            n_rows_tr = 11000 // width
            n_chunks = height // n_rows_tr
            n_last_transfer = height - (n_chunks * n_rows_tr)
            if n_last_transfer > 0:
                n_chunks += 1
            print("# of overall chunks:", n_chunks)
            print("# of rows for transfer:", n_rows_tr)
            print("# of rows for last transfer:", n_last_transfer)

            # Opening independent ports for receiving images
            (nPorts, address) = mainServer.recvfrom(st_n_bytes)  # Number of opened ports
            nPorts = int(str(nPorts, encoding='utf-8'))
            print("# of opening ports:", nPorts)
            nChunks_port = n_chunks // nPorts  # Calculation of chunks that will be transferred through single port
            remained_chunk = n_chunks - (nChunks_port * nPorts)
            if remained_chunk > 0:  # Calculation of chunks that will be transferred through last opened port
                nChunks_last = remained_chunk + nChunks_port
            else:
                nChunks_last = nChunks_port
            print("# of chunks for regular transfer:", nChunks_port)
            print("# of chunks for last transfer:", nChunks_last)
            # Construction of ports
            ports = []
            for i in range(nPorts):
                if i < (nPorts - 1):
                    ports.append(independentImgPort(host, port_py + i, n_rows_tr, 0, nChunks_port,
                                                    chunk_max_size, width))
                else:
                    ports.append(independentImgPort(host, port_py + i, n_rows_tr, n_last_transfer, nChunks_last,
                                                    chunk_max_size, width))
            # Ports opening (starting)
            for port in ports:
                port.start()
            # Force this script to wait all ports finishing their work
            for port in ports:
                port.join()
            m = 0
            for port in ports:
                # print("Received per port:")
                # print(port.received_img_chunk)
                n_rows = np.size(port.received_img_chunk, 0)
                # print("Rows:", n_rows)
                for i in range(n_rows):
                    img[m, :] = port.received_img_chunk[i, :]
                    m += 1
            # print("Transferred image:")
            # print(img)
            print("Image transfer through multiports finished")
            sendingString = "Image transferred".encode()
            mainServer.sendto(sendingString, address)

        elif "QUIT" in command:
            print(command, '- received command')
            # Do the quiting action with a delay
            sendingString = "Quit performed".encode()
            mainServer.sendto(sendingString, address)
            time.sleep(0.15)  # A delay for preventing of closing connection automatically by Python (causing errors)
            flag = False
            break


# %% For correctly representation of an image - it should be performed after quiting of image transfer
# For testing if the transfer of an image perfromed correctly
try:
    if np.size(img, axis=0) > 0:
        from skimage import io
        from skimage.util import img_as_ubyte
        import matplotlib.pyplot as plt
        if np.max(img) < 256:
            img = np.uint8(img)
        img_show = img_as_ubyte(img)
        plt.figure("Transferred image")
        io.imshow(img_show)
except NameError:
    print("No image transferred")
