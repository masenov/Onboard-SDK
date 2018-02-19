import serial
from serial_tools import Serial_Tools
from tools import *


class Scope_Commander(object):
    def __init__(self, ser):
        self.ser = ser
        self.st = Serial_Tools(self.ser)
        
        """ Dict of all the BS's state.
        This way, if it disconnects, we know exactly how to set it up.
        This is assuming the BS was setup entirely through this...
        """
        self.registers = {
        
        }
        
    def l_endian_hexify(self, dec, bytes = 2):
        hd = bytes * 2
        b = hex(dec) #turn into hex
        b = b[2:] #take the 0x off
        b = ("0" * (hd - len(b)) + b) #Append needed "0"s
        ls = []
        if len(b) > hd:
            print dec, "too big for the", bytes,"byte(s) requested."
        else:
            for byte in range(hd, 0, -2):
                ls.append(b[byte-2:byte])
            return ls
