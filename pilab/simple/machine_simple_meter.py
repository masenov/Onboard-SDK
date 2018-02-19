import serial
from serial_tools import Serial_Tools
from tools import *
    
import serial
from serial_tools import Serial_Tools
from tools import *

class MachineSimpleMeter(object):
    def __init__(self):
        """ Serial """
        self.ser = None
        self.s_t = Serial_Tools(self.ser)
        self.s_t.show_messages = False
        
        """ Trace and dump settings """
        self.trace_size = 512 # Size in samples (2 bytes)
        self.extra_trace = 16
        self.whole_trace = self.trace_size + self.extra_trace
        
        self.dump_compression = 16 # The BitScope will compress 16 samples to 1
        self.dump_size = (self.trace_size / self.dump_compression) * 2 # Size in bytes
        self.extra_dump = (self.extra_trace / self.dump_compression) * 2
        self.whole_dump = (self.whole_trace / self.dump_compression) * 2

        """ API Data """
        self.data = {
            "device": {"connected":False, "model":None},
            "accepted_models": ["BS0005", "BS0010"],
            "dump":[],
            "voltage": 0.0,
            "voltage_text":"",
            "dump_ready":False,
            "channel": "a",
            "ch_a_zero": 0.0,
            "ch_b_zero": 0.0,
        }
        self.data['ranges'] = {
            "BS0005":(-5.28, 8.11), # <1% error
            "BS0010":(-4.84, 10.8) # Not sure on this one!
        }
        self.command = ""
        
        self.state = self.s_find_device
        self.range_in_use = None

    """ API Functions """
    def zero_current_channel(self):
        ch_zero_string = "ch_" + self.data['channel'] + "_zero"
        self.data[ch_zero_string] += self.data['voltage']
        
    def change_channel(self):
        if self.data['channel'] == 'a':
            self.data['channel'] = 'b'
            num = 2
        else:
            self.data['channel'] = 'a'
            num = 1
            
        self.s_t.issue("[30]@[0" + str(num - 1) + "]s")
        self.s_t.issue("[37]@[0" + str(num) + "]s")
        self.s_t.issue_wait(">")
        
    """ Helpers """
    def ch_char_to_number(self, ch):
        return (1 if ch == 'a' else 2)
        
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
        d = self.data
        si = self.s_t.issue
        siw = self.s_t.issue_wait
        leh = l_endian_hexify
        ch_num = self.ch_char_to_number(d['channel'])
        self.range_in_use = self.data['ranges'][self.data['device']['model']]
        siw("!")
        si(
              "[1c]@[%s]sn[%s]s" % leh(self.whole_dump / 2) # Dump size (samples)
            + "[2a]@[%s]sn[%s]s" % leh(self.whole_trace) # Post trig (samples)
            + "[26]@[%s]sn[%s]s" % leh(self.extra_trace) # Pre trig (samples)
            + "[1e]@[06]s[21]@[12]s" # Dump/Trace = Filter/Macro
            + "[16]@[01]sn[00]s" # Iterations = 1
            + "[31]@[04]s" # Buffer mode = macro
            + "[08]@[00]sn[00]sn[00]s" # Spock address = 0
            + "[30]@[0" + str(ch_num - 1) + "]s" # Dump channel
            + "[37]@[0" + str(ch_num) + "]s" # Analogue channel enable
            + "[2c]@[00]sn[0a]s" # Time out = 10
            + "[2e]@[90]sn[01]s" # Clock ticks = 400
            + "[14]@[01]sn[00]s" # Clock scale = 1
            # Filter mode
            + "[18]@[10]sn[00]s" # Dump send = 16
            + "[1a]@[00]sn[00]s" # Skip = 0
            # Range
            + "[66]@[ff]sn[ff]s" # High
            + "[64]@[00]sn[00]s" # Low
        )
        siw(">")
        siw("U")
        self.state = self.s_idle
        
    def s_idle(self):
        self.s_t.clear_waiting()
        self.s_t.issue_wait("?")
        self.ser.flushInput()
        
        self.state = self.s_init_req
        
    def s_init_req(self):
        self.s_t.clear_waiting()
        self.ser.flushInput()
        self.s_t.issue_wait(">")
        self.s_t.issue("D") # Trace selected channel
        
        self.state = self.s_dump
        
    def s_dump(self):
        self.s_t.clear_waiting()
        self.ser.read(33) # Dispose of the trace's aux information
        self.s_t.issue_wait(">")
        self.s_t.issue("A") # Dump selected channel
        self.data['dump_ready'] = False
        
        self.state = self.s_process_and_req
        
    def s_process_and_req(self):
        self.s_t.clear_waiting()
        self.ser.read(self.extra_dump)
        self.data['dump'] = convert_12bit_bin_dump(self.ser.read(self.dump_size))
        self.data['dump_ready'] = True
        
        self.s_t.issue_wait(">")
        self.s_t.issue("D")
        
        self.state = self.s_dump

    """ Data Processing Functions """
    def derive_voltage(self):
        d = self.data
        avg = sum(d['dump']) / len(d['dump'])
        # Map 16 bit range to voltage range
        d['voltage'] = to_range(avg, (-32768, 32767), self.range_in_use)
        d['voltage'] -= d['ch_' + d['channel'] + '_zero']
        
    def set_voltage_text(self): # Move this stuff to view somehow!
        d = self.data
        reduce_to = "%." + '3' + "f" # Max length of voltage is 8 chars
        d['voltage_text'] = (reduce_to % d['voltage'] + "v").rjust(8)
        
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
            
        if self.data['dump_ready']:
            self.derive_voltage()
            self.set_voltage_text()
