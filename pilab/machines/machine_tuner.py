import serial
from serial_tools import Serial_Tools
from tools import *
import time

class MachineTuner(object):
    def __init__(self):
        """Serial Setup"""
        self.ser = None
        self.s_t = Serial_Tools(self.ser)
        self.s_t.show_messages = False

        self.state = self.s_find_device

        """Data exposed through API"""
        self.data = {
            "device":{"connected":False, "model":None},
            "accepted_models":["BS0005", "BS0010"]
        }

    """API Functions"""

    """States"""
    def s_find_device(self):
        self.ser = self.s_t.find_device()
        if self.ser != None:
            self.data['device']['connected'] = True
            self.state = self.s_check_model
        else:
            if self.data['device']['connected']:
                self.data['device']['connected'] = False
            self.state = self.s_find_device

    def s_check_model(self):
        self.ser.flushInput() #Try to get anything in the buffer.
        self.s_t.clear_waiting() #Force the counter to reset.
        self.s_t.issue_wait("?")
        model = (self.ser.read(20)[1:7])
        self.data['device']['model'] = model
        self.dirty = True
        if model in self.data['accepted_models']:
            self.state = self.s_setup_bs
            print self.data['device']['model'] + " Connected."
        else:
            self.state = self.s_check_model

    def s_setup_bs(self):
        pass

    """Data Processing Functions"""

    """Update Functions"""

    def update(self):
        try:
            self.state()
        except serial.SerialException:
            print "Device disconnected | Error: SE"
            self.state = self.s_find_device
        except serial.SerialTimeoutException:
            print "Device disconnected | Error: STE"
            self.state = self.s_find_device
