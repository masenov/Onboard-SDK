import serial
from serial_tools import Serial_Tools
from tools import *

from scope_commander import Scope_Commander

class MachineMeter(object):
    def __init__(self):        
        """Serial and other"""
        self.model = ""
        self.device_connected = False
        self.ser = None

        self.s_t = Serial_Tools(self.ser) # Tool to help issuing without waiting.
        self.s_t.show_messages = False
        
        scom = Scope_Commander(self.ser)

        """TRACE AND DUMP SETTINGS"""
        self.trace_size = 512 # Captured trace size in samples.
        self.extra_trace = 16 # ADC warmup junk
        self.whole_trace = self.trace_size + self.extra_trace
        self.d_dec = 16
        self.d_size = (self.trace_size / self.d_dec) * 2 # Dump size in bytes
        self.ex_size = (self.extra_trace / self.d_dec) * 2 # Extra samples for ADC warmup in bytes
        self.whole_dump = ((self.trace_size + self.extra_trace) / self.d_dec) * 2
        self.div = float(self.d_size)
        
        """ STATE. IT'S HERE """
        self.state = self.s_find_device

        self.data = {}
        self.data['ranges'] = {
            "BS0005":(-5.28, 8.11), # <1% error
            "BS0010":(-4.84, 10.8) # Not sure on this one!
        }

        """ Measurement data """
        self.data['ch'] = {}
        self.data['ch']['a'] = {
            'raw_avg':  0,
            'clip':     {'top':False, 'bot':False},
            'ana':      0.0,
            'display':  0.0,
            'ready':    {'data':False, 'display':False},
            'ena':      False,
            'was_ena':  False,
            'text_out': ""
        }

        """ Mult """
        self.data['mult'] = {'values':[1,2,5,10]}
        self.data['ch']['a']['mult_index'] = 0

        """ Logic """
        self.data['logic'] = {
            'step':     0.100,
            'rounding': 3,
            'min':      -6.000,
            'max':      6.000
        }
        self.data['ch']['a']['logic'] = {'top':1.5,'bot':0.0,'ena':False,'val':0}
        
        """ OTHER """
        self.data['ch']['a']['zero'] = 0.00

        self.data['diff'] = {
            'ena': False,
            'zero':0.00,
            'display':0.00,
            'text_out':""
        }

        self.data['frame_toggle'] = 0

        """ Interpolation for Enhanced """
        self.data['enhanced'] = {
            'ena': False,
            'frame': {'count': 0, 'max': 24}
        }
        self.data['ch']['a']['interp'] = {
            'queue': [0,0,0,0,0,0,0,0,0],
            'value': 0.0
        }

        self.data['device'] = {
            'model':None,
            'connected':False
        }
        
        self.data['mode'] = {
            'single':True,
            'dual':False,
            'diff':False,
            'logic':False
        }

        self.data['ch']['b'] = {}
        copy_dict(self.data['ch']['a'], self.data['ch']['b'])
        self.ch = self.data['ch']
        self.a = self.data['ch']['a']
        self.b = self.data['ch']['b']
        self.diff = self.data['diff']
        
        # Start the engine.... In the key of a.
        self.force_ch('a', True)
        
        self.range_in_use = self.data['ranges']['BS0005']
        

    """ API Functions """
    def step_limit(self, ch, top_bot, inc):
        if self.ch[ch]['logic']['ena']:
            lim = self.ch[ch]['logic']
            lim[top_bot] = round(lim[top_bot] + inc, 1)
            if lim[top_bot] < self.data["logic"]['min']:
                lim[top_bot] = self.data["logic"]['min']
            elif lim[top_bot] > self.data["logic"]['max']:
                lim[top_bot] = self.data["logic"]['max']

    def toggle_limits(self, ch):
        self.ch[ch]['logic']['ena'] = not self.ch[ch]['logic']['ena']

    def step_mult(self, ch, inc):
        if self.ch[ch]['ena']:
            ch = self.ch[ch]
            ch['mult_index'] += inc
            if ch['mult_index'] < 0:
                ch['mult_index'] = 0
            elif ch['mult_index'] >= len(self.data['mult']['values']):
                ch['mult_index'] = len(self.data['mult']['values']) - 1

    def toggle_ch(self, ch):
        self.ch[ch]['ena'] = not self.ch[ch]['ena']

    def force_ch(self, ch, state):
        self.ch[ch]['ena'] = state

    def zero_ch(self, ch):
        if self.ch[ch]['ena']:
            if self.data['diff']['ena'] and ch == 'a':
                self.data['diff']['zero'] = self.ch[ch]['display'] + self.data['diff']['zero']
            else:
                self.ch[ch]['zero'] = self.ch[ch]['display'] + self.ch[ch]['zero']

    def toggle_diff(self):
        self.data['diff']['ena'] = not self.data['diff']['ena']

    def force_diff(self, state):
        self.data['diff']['ena'] = state

    def toggle_sound(self):
        self.sound_enabled = not self.sound_enabled

    def toggle_enhanced(self):
        self.data['enhanced']['ena'] = not self.data['enhanced']['ena']

    def force_enhanced(self, state):
        self.data['enhanced']['ena'] = state

    """ STATES """

    def s_find_device(self):
        self.ser = self.s_t.find_device()
        if self.ser != None:
            self.data['device']['connected'] = True
            self.state = self.s_check_model
        else:
            if self.device_connected:
                self.data['device']['connected'] = False
            self.state = self.s_find_device

    def s_check_model(self):
        self.ser.flushInput() #Try to get anything in the buffer.
        self.s_t.clear_waiting() #Force the counter to reset.
        self.s_t.issue_wait("?")
        self.data['device']['model'] = (self.ser.read(20)[1:7])
        print self.data['device']['model'] + " Connected."

        self.dirty = True
        if self.data['device']['model'] in self.data['ranges']:
            self.state = self.s_setup_bs
        else:
            self.state = self.s_check_model

    def s_setup_bs(self):
        """ Put the BS into a workable state """
        si = self.s_t.issue
        siw = self.s_t.issue_wait
        self.range_in_use = self.data['ranges'][self.data['device']['model']]
        siw("!")
        si(
            "[1c]@[%s]sn[%s]s" % l_endian_hexify(self.whole_dump / 2) # Dump size
            + "[1e]@[06]s[21]@[12]s" # Dump, trace mode = filter, macro
            + "[08]@[00]sn[00]sn[00]s" # Spock address
            + "[16]@[01]sn[00]s" # Iterations = 1
            + "[26]@[%s]sn[%s]s" % l_endian_hexify(16) # Pre trig cap
            + "[2a]@[%s]sn[%s]s" % l_endian_hexify(self.whole_trace) # Post trig cap
            + "[30]@[00]s" # Dump channel
            + "[31]@[04]s" # Buffer mode = macro
            + "[37]@[01]s" # Analogue channel enable
            + "[2c]@[00]sn[0a]s" # Time out (REALLY IMPORTANT)
            + "[2e]@[90]sn[01]s" # Clock ticks
            + "[14]@[01]sn[00]s" # Clock scale
            ### Filter mode ###
            + "[18]@[10]sn[00]s" # Dump send = 16
            + "[1a]@[00]sn[00]s" # Skip = 0
            ### Range ###
            + "[66]@[ff]sn[ff]s" # High
            + "[64]@[00]sn[00]s" # Low
        )
        self.ser.flushInput()

        siw("U")
        siw(">")
        
        self.state = self.s_change_to_chop

    def s_change_to_chop(self):
        self.ser.flushInput()
        self.s_t.clear_waiting()
        self.s_t.issue(
            "[1e]@[06]s" # Set dump mode stays as filter
            "[21]@[13]s" # Set trace mode (macro chop)
            "[31]@[05]s" # Buffer mode
            "[37]@[03]s" # Ana ch enable
        )
        self.s_t.issue_wait(">")
        self.s_t.issue("U")

        self.state = self.s_pre_idle

    def s_pre_idle(self):
        self.s_t.clear_waiting()
        self.ser.flushInput()
        self.state = self.s_idle

    def s_idle(self): # Idle
        self.s_t.issue_wait("?")
        self.ser.flushInput()
        if self.a['ena'] or self.b['ena']:
            self.state = self.s_init_a_b_req_chop

    """ Dual chop """
    def s_init_a_b_req_chop(self):
        self.s_t.clear_waiting()
        self.ser.flushInput()
        self.s_t.issue_wait(">")
        self.s_t.issue("[37]@[03]sD")
        self.state = self.s_a_dump_chop

    def s_a_dump_chop(self):
        self.s_t.clear_waiting()
        self.ser.read(33) # Get rid of unused timing junk
        self.s_t.issue_wait(">")
        self.s_t.issue("[30]@[00]sA") # Dump chA

        if self.a['ena'] or self.b['ena']:
            self.state = self.s_a_proc_b_dump_chop
        else:
            self.state = self.s_pre_idle

    def s_a_proc_b_dump_chop(self):
        self.s_t.clear_waiting()
        if self.ch['a']['ena']:
            self.ser.read(self.ex_size)
            dump = convert_12bit_bin_dump(self.ser.read(self.d_size))
            self.a['ana'] = self.derive_voltage(dump)
            self.a['clip']['top'], self.a['clip']['bot'] = self.check_clipping(dump)
            self.a['ready']['data'] = True
        else:
            self.ser.read(self.d_size + self.ex_size) # Read off dump as junk.
            self.b['ready']['data'] = False
        self.s_t.issue_wait(">")
        self.s_t.issue("[30]@[01]sA") # Dump chB

        self.state = self.s_b_proc_a_b_req_chop

    def s_b_proc_a_b_req_chop(self):
        self.s_t.clear_waiting()
        if self.b['ena']:
            self.ser.read(self.ex_size)
            dump = convert_12bit_bin_dump(self.ser.read(self.d_size))
            self.b['ana'] = self.derive_voltage(dump)
            self.b['clip']['top'], self.b['clip']['bot'] = self.check_clipping(dump)
            self.b['ready']['data'] = True
        else:
            self.ser.read(self.d_size + self.ex_size) # Read off dump as junk.
        self.a['ready']['data'] = False
        self.s_t.issue_wait(">")
        self.s_t.issue("[37]@[03]sD") # Request both channels.

        self.state = self.s_a_dump_chop

    """ Utility functions """
    def volt_interp(self, ls, new_v):
        ls.pop(0)
        ls.append(new_v)
        return round((sum(ls) / len(ls)), 4)
        
    def derive_voltage(self, dump):
        avg = sum(dump) / len(dump)
        # Map 16 bit range to voltage range
        return to_range(avg, (-32768, 32767), self.range_in_use)
        
    def check_clipping(self, dump):
        clip_top, clip_bot = False, False
        if (max(dump) > (32767 - 72)): # Clipping top WHY 72?!?!?!
            clip_top = True
            
        if (min(dump) < (-32768 + 32)): # Clipping bottom
            clip_bot = True
            
        return (clip_top, clip_bot)

    def update(self):
        """ Do state! """
        try:
            self.state()
        except serial.SerialException:
            print "Device disconected | Error: SE"
            self.state = self.s_find_device
        except serial.SerialTimeoutException:
            print "Device disconected | Error: STE"
            self.state = self.s_find_device

        a = self.a
        b = self.b
        a_ready = a['ready']
        b_ready = b['ready']
        a_interp = a['interp']
        b_interp = b['interp']
        diff = self.diff
        enhanced_frame = self.data['enhanced']['frame']
        
        """ Data post-process """
        if self.data['device']['connected']:
            for ch, ch_ready in (a, a_ready), (b, b_ready):
                if ch['ena'] and ch_ready['data']:
                    ch['ana'] = round((ch['ana'] - ch['zero']), 6) # Zero
                    ch['display'] = ch['ana'] * self.data['mult']['values'][ch['mult_index']] # Apply multiplier
                    if ch['logic']['ena']:
                        if ch['display'] >= ch['logic']['top']:
                            log = 1
                        elif ch['display'] <= ch['logic']['bot']:
                            log = 2
                        else:
                            log = 0
                    else:
                        log = 0
                    ch['logic']['val'] = log
                
            """ INTERP MODE """
            if self.data['enhanced']['ena']:
                for ch, ch_interp in (a, a_interp), (b, b_interp):
                    if ch['ena'] and ch['ready']['data']:
                        ch_interp['value'] = self.volt_interp(ch_interp['queue'], ch['display'])
                        ch['display'] = ch_interp['value']

            """ DIFF MODE """
            if diff['ena']:
                a['display'] = (a['ana'] - b['ana']) - diff['zero']

            """ SLOW DOWN INTERP """
            if self.data['enhanced']['ena']:
                for ch, count in (a, 0), (b, 12):
                    if ch['ena'] and enhanced_frame['count'] == count:
                        ch['ready']['display'] = True
                
                enhanced_frame['count'] += 1
                if enhanced_frame['count'] >= enhanced_frame['max']-1:
                    enhanced_frame['count'] = 0

            else:
                a_ready['display'] = True
                b_ready['display'] = True

            if self.data['enhanced']['ena']: # Check interp, set rounding
                round_to = "4"
            else:
                round_to = "3"
                
            """ Set the text """ # This should really be done by the widget
            reduce_to = "%." + round_to + "f" # Max length of voltage is 8 chars
            for ch, ch_ready in (a, a_ready), (b, b_ready):
                if ch['ena'] and ch_ready['display']:
                    ch['text_out'] = (reduce_to % ch['display'] + "v").rjust(8)
                    ch_ready['display'] = False
