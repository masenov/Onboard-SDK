import serial
from serial_tools import Serial_Tools
from tools import *
import time

class MachineTriggeredLogic(object):
    def __init__(self):
        """Serial Setup"""
        self.ser = None
        self.s_t = Serial_Tools(self.ser)
        self.s_t.show_messages = False

        self.state = self.s_find_device
        
        self.buffer_size = 12288
        
        self.trace_size = 12000
        self.trace_received = 0
        
        self.trace_intro = 16
        self.trace_outro = self.trace_size
        
        self.command = ""

        """Data exposed through API"""
        self.data = {
            "device":{"connected":False, "model":None},
            "accepted_models":["BS0005", "BS0010"],
            "status":"stopped",
            "ba":bytearray(),
            "ba_pos":0,
            "ba_range":1000,
            "ba_zoom":(0,1000),
            "range_high":20000,
            "range_low":100,
            "deep_scan":False,
            "data_ready":False,
            "trigger_byte":0,
            "mask_byte":255, # Any bit marked as ? will be a "don't care" bit
            "trigger":[2,2,2,2,2,2,2,2],
            "rate":5000, # kHz (up to 5mHz on tmLogic)
            "running":False
        }

    """API Functions"""
    def inc_trigger(self, ch, inc):
        trig = self.data["trigger"]
        trig[ch] += inc
        if trig[ch] == 3:
            trig[ch] = 0
        
        self.data["trigger_byte"] = self.to_trigger_byte(trig)
        self.data["mask_byte"] = self.to_mask_byte(trig)
        tb = l_endian_hexify(self.data["trigger_byte"], 1)
        mb = l_endian_hexify(self.data["mask_byte"], 1)
        self.command += "[05]@[%s]s[06]@[%s]s" % (tb[0], mb[0]) # Trigger logic and mask
        
    def stop_start(self):
        if self.data['running']:
            self.data['running'] = False
            self.state = self.s_idle
            self.s_t.issue_wait(".")
        elif not self.data['running']:
            self.data['running'] = True
            self.state = self.s_start_capture
            
    def set_ba_pos(self, val):
        zr = self.data['ba_zoom']
        pos = to_range(val, [0,100], zr)
        pos = self.check_position(pos - self.data['ba_range'] / 2)
        self.data['ba_pos'] = int(pos)
        
    def inc_ba_range(self, inc):
        # Make some data local and get centre
        sd = self.data
        bar = sd['ba_range']
        bap = sd['ba_pos']
        old_centre = bap + (bar / 2)
        # Increment
        sd['ba_range'] = int(inc_125_pattern(bar, inc))
        # Get new, unaltered centre, and adjust the view pos
        new_centre = bap + (sd['ba_range'] / 2)
        sd['ba_pos'] -= int(new_centre - old_centre)
        # Refresh locals
        bar = sd['ba_range']
        bap = sd['ba_pos']
        # Check
        if ((bar + bap) > len(sd['ba']) or
            bar > sd['range_high'] or
            bar < sd['range_low'] or
            bap < 0):
            # Reverse
            self.inc_ba_range(-inc)
            
    """ Utilities """
    def to_trigger_byte(self, bit_ls):
        to_bit = lambda x : str(int(x > 0))
        bit_str = "".join(map(to_bit, bit_ls))
        return int(bit_str, 2)
                        
    def to_mask_byte(self, bit_ls):
        to_mask = lambda x : str(int(x == 2))
        bit_str = "".join(map(to_mask, bit_ls))
        return int(bit_str, 2)
        
    def check_position(self, pos):
        ba_range = self.data['ba_range']
        ba_len = len(self.data['ba'])
        if (pos + ba_range) > ba_len:
            return int(ba_len - ba_range)
        elif pos < 0:
            return 0
        else:
            return int(pos)
        
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
        si = self.s_t.issue
        siw = self.s_t.issue_wait
        self.command = ""
        siw("!")
        si(
            "[21]@[0e]s" # Logic trace mode
            + "[1e]@[00]s" # Dump mode
            + "[1c]@[%s]sn[%s]s" % l_endian_hexify(self.trace_size) # Dump
            + "[31]@[00]s" # Buffer mode
            + "[14]@[01]sn[00]s" # Clock scale
            + "[2a]@[%s]sn[%s]s" % l_endian_hexify(self.trace_size) # Post trig cap
            + "[30]@[80]s" # Dump channel
            + "[37]@[00]s" # Analogue chan
            + "[38]@[00]s" # Digital
            + "[18]@[00]sn[00]s" # Dump send
            + "[1a]@[00]sn[00]s" # Dump skip
        )
        ticks = int(freq_to_ns(self.data["rate"]) / 25)
        si("[2e]@[%s]sn[%s]s" % l_endian_hexify(ticks))
        # Trigger
        si(
            "[2c]@[00]sn[00]s" # Trigger timeout (NEVER!)
            "[07]@[01]s" # Trigger mode (spock opt) (hardware/rising edge)
            "[32]@[01]sn[00]sn[01]sn[00]s" # Trigger intro and outro
        )
        tb = hex(self.data["trigger_byte"])[2:]
        mb = hex(self.data["mask_byte"])[2:]
        si("[05]@[%s]s[06]@[%s]s" % (tb, mb))
        siw(">")
        siw("U")
        
        self.state = self.s_idle
    
    def s_idle(self):
        self.s_t.issue_wait("?")
        self.ser.flushInput()
        if self.command and self.ser:
            self.s_t.issue_wait(self.command)
            self.command = ""
        
    def s_start_capture(self):
        self.data['data_ready'] = False
        self.data['ba'] = bytearray()
        self.trace_received = 0
        self.s_t.clear_waiting()
        self.ser.flushInput()
        if self.command and self.ser:
            self.s_t.issue_wait(self.command)
            self.command = ""
        self.s_t.issue_wait(">")
        self.s_t.issue("D")
        self.state = self.s_await_trigger
    
    def s_await_trigger(self):
        self.s_t.clear_waiting()
        returned = self.ser.inWaiting()
        if returned >= 12:
            self.ser.read(12) # Read out the first part of the timing info
            self.state = self.s_await_complete
        else:
            self.state = self.s_await_trigger
    
    def s_await_complete(self):
        returned = self.ser.inWaiting()
        if returned >= 21: # Trace has finished!
            self.ser.read(12) # Pesky other information
            end_address = unhexify(self.ser.read(8))
            self.ser.read(1) # Last byte
            # Set up spock stuff
            start_address = ((end_address + self.buffer_size) - self.trace_size) % self.buffer_size
            self.s_t.issue("[08]@[%s]sn[%s]sn[%s]s" % l_endian_hexify(start_address, 3))
            self.s_t.issue_wait(">")
            # Dump!
            self.s_t.issue("A")
            self.state = self.s_acquire
        else:
            self.state = self.s_await_complete
        
    def s_acquire(self):
        self.s_t.clear_waiting() # Bye 'A'
        to_get = self.ser.inWaiting()
        self.trace_received += to_get
        self.data['ba'] += self.ser.read(to_get)
        if self.trace_received == self.trace_size:
            self.data['data_ready'] = True
            self.data['running'] = False
            self.data['ba_range'] = self.trace_size
            self.state = self.s_idle

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
