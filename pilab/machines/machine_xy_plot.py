import serial
from serial_tools import Serial_Tools
from tools import *
import time

class MachineXYPlot(object):
    def __init__(self):
        """Serial Setup"""
        self.ser = None
        self.s_t = Serial_Tools(self.ser)
        self.s_t.show_messages = False

        self.state = self.s_find_device
        
        self.trace_size = 1024
        self.extra_trace = 4
        self.whole_trace = self.trace_size + self.extra_trace
        self.dump_size = self.trace_size
        self.extra_dump = self.extra_trace
        self.whole_dump = self.dump_size + self.extra_dump

        """Data exposed through API"""
        self.data = {
            "device":{"connected":False, "model":None},
            "accepted_models":["BS0005", "BS0010"],
            "trace":[]
        }

        self.a_d, self.b_d = [], []
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
        self.ser.flushInput # Try to get anything in the buffer.
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
        si = self.s_t.issue
        siw = self.s_t.issue_wait
        si("[1c]@[%s]sn[%s]s" % (l_endian_hexify(self.whole_dump))) # Dump size
        si("[1e]@[00]s[21]@[02]s") # Dump/Trace = Filter/Macro
        si("[08]@[00]sn[00]sn[00]s") # Spock address
        si("[16]@[01]sn[00]s") # Iterations = 1
        
        si("[2a]@[%s]sn[%s]s" % (l_endian_hexify(self.whole_trace))) # Post trig cap (was 1024)
        si("[30]@[00]s") # Dump channel
        si("[31]@[01]s") # Buffer mode chop
        si("[37]@[03]s") # Analogue channel enable
        si("[26]@[%s]sn[%s]s" % (l_endian_hexify(self.whole_trace))) # Pre trig cap
        si("[2c]@[00]sn[0f]s") # Time out REALLY IMPORTANT
        si("[2e]@[28]sn[00]s") # Set clock ticks (ticks(6us steps) per sample)
        si("[14]@[01]sn[00]s") # Clock scale
        
        """TRIGGER"""
        si("[06]@[00]s") # Set trigger mask to "Don't care about anything"
        si("[05]@[00]s") # This doesn't matter because we don't care about triggers.

        """Filter mode stuff"""
        #self.issue("[18]@[10]sn[00]s") # Dump send to 16
        #self.issue("[1a]@[00]sn[00]s") # skip = 0 (sum 16, skip 0, sum 16, skip 0, ...)

        r_high, r_low = to_span(2.0,4.0)
        siw("[64]@[%s]sn[%s]s" % l_endian_hexify(r_low)) # Range low
        siw("[66]@[%s]sn[%s]s" % l_endian_hexify(r_high)) # Range high
        self.ser.read(1000)

        siw(">")
        siw("U")
        
        self.state = self.s_change_to_chop
        
    def s_change_to_chop(self):
        si = self.s_t.issue
        siw = self.s_t.issue_wait
        self.ser.read(1000)
        self.s_t.clear_waiting()
        si("[1e]@[00]s") # Set dump mode
        si("[21]@[02]s") # Set trace mode
        si("[31]@[01]s") # Buffer mode
        si("[37]@[03]s") # Ana ch enable

        siw(">")
        siw("U")

        self.state = self.s_pre_idle

    def s_pre_idle(self):
        self.s_t.clear_waiting()
        self.ser.read(1000)
        self.state = self.s_idle

    def s_idle(self): #Idle
        self.s_t.issue_wait("check")
        self.state = self.s_init_req
        
    """Dual chop"""
    def s_init_req(self):
        self.s_t.clear_waiting()
        self.ser.read(10000)
        self.s_t.issue_wait(">")
        self.s_t.issue("[37]@[03]sD")
        self.state = self.s_a_dump


    def s_a_dump(self):
        self.s_t.clear_waiting()
        self.ser.read(33)
        self.s_t.issue_wait(">")
        self.s_t.issue("[30]@[00]sA") # Dump chA

        self.state = self.s_a_proc_b_dump

    def s_a_proc_b_dump(self):
        self.s_t.clear_waiting()
        self.ser.read(self.extra_trace)
        self.a_d = self.ser.read(self.dump_size)
        self.s_t.issue_wait(">")
        self.s_t.issue("[30]@[01]sA") # Dump chA

        self.state = self.s_b_proc_a_b_req

    def s_b_proc_a_b_req(self):
        self.s_t.clear_waiting()
        self.ser.read(self.extra_trace)
        self.b_d = self.ser.read(self.dump_size)
        self.s_t.issue_wait(">")
        self.s_t.issue("[37]@[03]sD") # Req both

        self.generate_lissajous()

        self.state = self.s_a_dump

    """Data Processing Functions"""
    def generate_lissajous(self):
        a = map(ord, self.a_d)
        b = map(ord, self.b_d)
        line = []
        for i in range(0, len(a)-1):
            # line.append([(a[i])*(490/256), (b[i])*(490/256)])
            line.append([(a[i]), (b[i])])
        self.data['trace'] = line
        
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
