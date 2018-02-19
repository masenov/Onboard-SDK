import serial
from serial_tools import Serial_Tools
from tools import *
import time

class MachineSound(object):
    def __init__(self):
        """Serial Setup"""
        self.ser = None
        self.s_t = Serial_Tools(self.ser)
        self.s_t.show_messages = False

        self.state = self.s_find_device
        self.base_freq = 440 # A
        self.note = 0

        """Data exposed through API"""
        self.data = {
            "device":{"connected":False, "model":None},
            "accepted_models":["BS0005", "BS0010"]
        }
        
    """ Utilities """
    def generate_frequency(self, note_id):
        # fn = f0 * (a)n
        # a = 1.05946309
        return self.base_freq * (1.05946309 ** note_id)
        
    def inc_note(self, inc):
        notes = ["A","A#","B","C","C#","D","D#","E","F","F#","G","G#"]
        self.note += inc
        # The ocatave number
        print "Note ID", self.note
        print "Note", notes[self.note % 12], int(self.note / 12) + 4
        print "Freq", self.generate_frequency(self.note)

    """API Functions"""
    def change_wf(self, val):
        if self.ser:
            self.s_t.issue_wait("[50]@[%s]sn[%s]s" % l_endian_hexify(val))
            self.s_t.issue_wait("Z")
            
    def change_wf2(self, val=0):
        freq = int(to_range(val, [0,100], [100,260]))
        if self.ser:
            self.s_t.issue_wait("[50]@[%s]sn[%s]s" % l_endian_hexify(freq))
            self.s_t.issue_wait("Z")

    """States"""
    def s_find_device(self):
        self.ser = self.s_t.find_device(self.data['accepted_models'])
        if self.ser != None:
            self.data['device']['connected'] = True
            self.state = self.s_check_model
        else:
            if self.data['device']['connected']:
                self.data['device']['connected'] = False
            self.state = self.s_find_device

    def s_check_model(self):
        self.ser.read(10000) # Try to get anything in the buffer.
        self.s_t.clear_waiting() # Force the counter to reset.
        self.s_t.issue_wait("?")
        model = (self.ser.read(20)[1:7])
        self.data['device']['model'] = model
        print self.data['device']['model'] + " Connected."

        self.dirty = True
        if model in self.data['accepted_models']:
            self.state = self.s_setup_bs
        else:
            self.state = self.s_check_model

    def s_setup_bs(self):
        """AWG"""
        self.s_t.issue_wait(
            "[7c]@[c0]s" # Kitchen sink register B! ENABLES AWG!!!
            "[86]@[00]s" # Turn the clock generator off.
        )
        self.s_t.issue_wait("U")
        self.s_t.issue_wait(
            "[46]@[00]s" # vpCmd (Command Vector)
            "[47]@[03]s" # vpMode (Operating Mode)
            "[5a]@[00]sn[80]sn[00]sn[00]s"# vpRatio (Phase Ratio)
        )
        self.s_t.issue_wait("Y")# SYNTHESIZE!
        self.s_t.issue_wait(
            "[46]@[00]s" # vpCmd (Command Vector)
            "[47]@[00]s" # vpMode (Operating Mode)
            "[4a]@[e8]sn[03]s" # vpSize (Operation size, 1000 samples)
            "[4c]@[00]sn[00]s" # vpIndex (Operation Index, table start)
            "[4e]@[00]sn[00]s" # vpAddress (Destination Address, buffer start)
            "[54]@[ff]sn[ff]s" # vpLevel (Output Level, full scale)
            "[56]@[00]sn[00]s" # vpOffset (Output Offset, zero)
            "[5a]@[93]sn[18]sn[04]sn[00]s" # vpRatio (Phase Ratio)
        )
        self.s_t.issue_wait("X") # TRANSLATE!
        self.s_t.issue_wait(
            "[48]@[f4]sn[80]s" # vpOption (control flags)
            "[50]@[af]sn[00]s" # vpClock (Sample Clock Ticks)
            "[52]@[e8]sn[03]s" # vpModulo (Table Modulo Size)
            "[5e]@[0a]sn[01]s" # vpMark (Mark Count/Phase)
            "[60]@[01]sn[00]s" # vpSpace (Space Count/Phase)
            "[78]@[00]sn[7f]s" # vrDacOutput (DAC Level)
            "[46]@[02]s" # vmCmd (Command Vector)
        )
        self.s_t.issue_wait("Z") # GENERATE!
        self.s_t.issue_wait(">")
        self.s_t.issue("U")
        self.ser.flushInput()
        
        self.state = self.s_waiting
        
    def s_waiting(self): # Connected and doing nothing really.
        self.s_t.issue_wait("?")
        self.ser.flushInput()

    """Data Processing Functions"""

    """Update Functions"""

    def update(self):
        try:
            self.state()
        except serial.SerialException:
            print "Device disconected | Error: SE"
            self.state = self.s_find_device
        except serial.SerialTimeoutException:
            print "Device disconected | Error: STE"
            self.state = self.s_find_device
