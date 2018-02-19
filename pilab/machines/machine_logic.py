import os
import serial
import numpy
from serial_tools import Serial_Tools
from tools import *
import time
import random
import sigrok_session

class MachineLogic(object):
    def __init__(self, name, cfg):
        self.name = name
        self.cfg = cfg
        self.mode_cfg = cfg['modes'][name]
        """Serial Setup"""
        self.ser = None
        self.s_t = Serial_Tools(self.ser)
        self.s_t.show_messages = False
        self.command = ""

        self.state = self.s_find_device

        self.position = 0
        self.max = 10000000

        """Data exposed through API"""
        self.data = {
            "device":{"connected":False, "model":None},
            "accepted_models":["BS0005", "BS0010"],
            "status":"stopped",
            "streaming":False,
            "stream_mode":0, # Analogue A, or logic
            "trace":[],
            "ba":bytearray(1024*1024*10),
            "ba":bytearray(100000),
            "ba_pos":0,
            "ba_range":1000,
            "data_ready":False,
            "deep_scan":False,
            "range_high":200000,
            "range_low":100,
            "ba_zoom":(0,0),
            "frequency":100, # khz
            "interval":0, # us
            "file_mode":0
        }
        self.data['ba_zoom'] = (0, len(self.data['ba']))
        self.data['interval'] = int(freq_to_ns(self.data['frequency']) / 1000)

    """API Functions"""
    def start_capture(self):
        self.command += "T"
        self.state = self.s_capture
        
    def pause_capture(self):
        self.command += "."
        self.state = self.s_idle
        self.data['ba_zoom'] = (0,len(self.data['ba']))
        
    def stop_capture(self):
        self.command += "."
        self.state = self.s_idle
        self.data['ba_zoom'] = (0,len(self.data['ba']))
        
    def stop_start(self):
        status = self.data['status']
        if self.state == self.s_idle or self.state == self.s_capture:
            if status == "stopped":
                self.data['data_ready'] = False
                self.data['status'] = "capturing"
                self.data['streaming'] = True
                # self.state = self.start_capture
                self.start_capture()
            elif status == "paused":
                self.data['data_ready'] = False
                self.data['status'] = "capturing"
                self.data['streaming'] = True
                # self.state = self.start_capture
                self.start_capture()
            elif status == "capturing":
                self.data['data_ready'] = True
                self.data['status'] = "stopped"
                self.data['streaming'] = False
                # self.state = self.stop_capture
                self.stop_capture()
        
    def set_sample_frequency(self, freq):
        self.data['frequency'] = freq
        self.data['interval'] = int(freq_to_ns(freq))
        self.command = ("[2e]@[%s]sn[%s]s" % l_endian_hexify(self.data['interval'] / 25))
        self.data['interval'] /= 1000 # Convert to us
        
    def inc_sample_frequency(self, inc):
        freq = self.data['frequency']
        freq = int(inc_125_pattern(freq, inc))
        if (1 <= freq <= 500): # If the value is okay
            self.set_sample_frequency(freq) # Set it!
            
    def clear_data(self):
        self.data['ba'] = bytearray(100000)
        self.data['ba_zoom'] = (0, len(self.data['ba']))
        self.data['ba_range'] = 1000
        self.data['ba_pos'] = 0
        self.data['data_ready'] = 100 # To ensure redraw no matter true or false
        self.position = 0
        
    def check_position(self, pos):
        ba_range = self.data['ba_range']
        ba_len = len(self.data['ba'])
        if (pos + ba_range) > ba_len:
            return int(ba_len - ba_range)
        elif pos < 0:
            return 0
        else:
            return int(pos)
        
    def inc_ba_pos(self, inc):
        self.data['ba_pos'] += int(inc)
        self.data['ba_pos'] = self.check_position(self.data['ba_pos'])
        
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
                 
    def zoom_ba(self):
        sd = self.data
        zoom = sd['ba_pos'], sd['ba_pos'] + sd['ba_range']
        if zoom[1] - zoom[0] >= 1000:
            sd['ba_zoom'] = zoom
        
    def reset_zoom_ba(self):
        sd = self.data
        sd['ba_zoom'] = 0, len(sd['ba'])
    
    def do_deep_scan(self):
        self.data['deep_scan'] = not self.data['deep_scan']
        
    def inc_file_format(self, inc):
        last_mode = 3
        new_mode = self.data['file_mode'] + inc
        if new_mode > last_mode:
            new_mode = 0
        elif new_mode < 0:
            new_mode = last_mode
        self.data['file_mode'] = new_mode
        
    def dump_to_file(self):
        file_name = time.strftime("%Y-%m-%d_%H:%M:%S")
        mode = self.data['file_mode']
        extension = "txt"
        replace_chars = []
        
        if mode == 0: # Raw
            file_name = "bin_" + file_name
            to_write = self.data['ba'][:self.position]
        elif mode == 1: # CSV decimal
            file_name = "dec_" + file_name
            to_write = str([int(b) for b in self.data['ba'][:self.position]])
            replace_chars = ["[", "]"]
        elif mode == 2: # CSV hex
            file_name = "hex_" + file_name
            to_write = str([hex(b)[2:] for b in self.data['ba'][:self.position]])
            replace_chars = ["'", "[", "]"]
        elif mode == 3: # Sigrok session
            file_name = "sr_" + file_name
            extension = "sr"
            data = self.data['ba'][:self.position]
            sr = sigrok_session.SigrokSession()
            sr.set_rate(self.data['frequency'] * 1000)
            sr.set_data(data)
            to_write = sr.get_session_file().getvalue()
                   
        for ch in replace_chars:
            to_write = to_write.replace(ch, "")
        
        directory = os.path.dirname(self.cfg['globals']['output_dir'])
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        with open(directory + "/" + file_name + '.' + extension, 'wb') as out:
            out.write(to_write)
            
    def toggle_stream_mode(self):
        sm = self.data['stream_mode']
        if sm == 0:
            self.set_stream_mode(1)
        elif sm == 1:
            self.set_stream_mode(0)
        
    def set_stream_mode(self, mode):
        self.data['stream_mode'] = mode
        if mode == 1:
            self.command = "[37]@[01]sn[00]s>"
        elif mode == 0:
            self.command = "[37]@[00]sn[ff]s>"
        
    """States"""
    def s_find_device(self):
        self.data['streaming'] = False
        self.data['status'] = "stopped"
        self.ser = self.s_t.find_device()
        if self.ser != None:
            self.data['device']['connected'] = True
            self.state = self.s_check_model
        else:
            if self.data['device']['connected']:
                self.data['device']['connected'] = False
            self.state = self.s_find_device

    def s_check_model(self):
        self.ser.read(10000) #Try to get anything in the buffer.
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
        self.command = "" # Clear command buffer
        siw("!") # Reset
        si(
            "[21]@[02]s" # Trace mode (change to logic!)
            "[14]@[01]sn[00]s" # Clock scale
            # "[74]@[00]s" # Logic pins to inputs
        )
        self.set_stream_mode(self.data['stream_mode'])
        mch_cfg = self.mode_cfg['machine_cfg']
        high, low = to_span(mch_cfg['offset'], mch_cfg['range'])
        si("[66]@[%s]sn[%s]s" % l_endian_hexify(high))
        si("[64]@[%s]sn[%s]s" % l_endian_hexify(low))
        intervals = int(freq_to_ns(self.data['frequency']) / 25)
        si("[2e]@[%s]sn[%s]s" % l_endian_hexify(intervals)) # Clock ticks
        siw("U")
        siw(">")
        self.state = self.s_idle
        
    def s_idle(self):
        self.s_t.issue_wait("?")
        self.ser.flushInput()
        if self.command and self.ser:
            self.s_t.issue_wait(self.command)
            self.command = ""
        
    def s_capture(self):
        if self.command and self.ser:
            self.s_t.issue_wait(self.command)
            self.command = ""
        in_count = self.ser.inWaiting()
        if in_count:
            new_ba = self.ser.read(in_count)
            self.alter_bytearray(new_ba)
            if self.position >= self.max:
                self.stop_start()
            

    """Data Processing Functions"""
    def alter_bytearray(self, new_data):
        # No for-loop version
        self.data['ba'][self.position:self.position + len(new_data)] = new_data
        self.position += len(new_data)
            
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
        except IOError:
            print "Some other IO fault"
            self.state = self.s_find_device
