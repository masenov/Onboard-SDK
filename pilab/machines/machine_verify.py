import serial
from serial_tools import Serial_Tools
from tools import *
import time

class MachineVerify(object):
    def __init__(self):

        self.ser = None
        self.s_t = Serial_Tools(self.ser)
        self.s_t.show_messages = False

        self.state = self.s_find_device

        self.trace_size = 1024 #captured trace size in samples.
        self.extra_trace = 16 #ADC warmup junk
        self.whole_trace = self.trace_size + self.extra_trace
        self.d_size = self.trace_size * 2 #dump size in bytes
        self.ex_size = self.extra_trace * 2 #extra samples for ADC warmup in bytes
        self.whole_dump = (self.trace_size + self.extra_trace) * 2

        self.data = {
            "device":{"model":None, "connected":False, "tested":False, "pass":False,
            "connected_not_tested":False},
            "test":{"status":"connect", "op_count":1},
            "ch":{"a":{}, "b":{}},
            "mask_height":5000,
            "masks":{ #Lists of tuples containing mask ranges.
                "comp":[(123,190)]
            },
            "cal_points":{
                "comp":{
                    "shape":[50,205,250],
                    "top":range(191,212)
                }
            },
            "mode":"pre_test",
            "sample_offset":{
                "comp":35,
                "adc":125,
                "logic":70
            },
        }
        self.data['ranges'] = {}
        self.data['ranges']['BS0005'] = {
            1.1 :           "[64]@[56]sn[7e]sn[77]sn[82]s",
            3.5 :           "[64]@[c3]sn[6a]sn[a3]sn[95]s",
            5.2 :           "[64]@[68]sn[44]sn[ff]sn[8a]s",
            11 :            "[64]@[6a]sn[12]sn[8c]sn[ba]s",
            "better_11" :   "[64]@[6f]sn[14]sn[8c]sn[ba]s",
            "max" :         "[64]@[00]sn[00]sn[ff]sn[ff]s"
        }

        self.data['ranges']['BS0010'] = {
            0.520:          "[64]@[40]sn[65]sn[82]sn[6c]s",
            1.1 :           "[64]@[14]sn[61]sn[6f]sn[70]s",
            3.5 :           "[64]@[5c]sn[50]sn[3a]sn[81]s",
            5.2 :           "[64]@[9d]sn[44]sn[38]sn[8d]s",
            11 :            "[64]@[28]sn[1c]sn[c1]sn[b5]s",
            "max" :         "[64]@[00]sn[00]sn[ff]sn[ff]s"
        }
        self.data['range'] = 11
        self.data['templates'] = {
            "comp":([19792] * 119) + ([480] * 152) + ([19762] * 151)
        }

        self.data['results'] = {
            "comp" : False,
            "adc"  : False,
            "logic": False,
            "test" : False
        }

        self.data['ch']['a'] = {
            "trace":[],
            "display_trace":[],
            "ena":False,
            "zero": {16:10131, 8:162},
            "sos": 0,
            "sos_string":"",
            "errors":{"shape":0, "top":0},
            "pass":{"comp":False, "adc":False},
            "limits":{"comp":30, "adc":100},
            "queue":[0]*5,
            "result":0,
            "ready":False,
            "frame_count":0,
            "ready_on_frame":5
        }
        
        # Clone ch a to ch b
        self.data['ch']['b'] = {}
        copy_dict(self.data['ch']['a'], self.data['ch']['b'])
        
        # Aliases
        self.ch = self.data['ch']
        self.a = self.ch['a']
        self.b = self.ch['b']
        self.dev = self.data['device']
        self.test = self.data['test']
        
    """API funcs"""
    def capture_trace(self, ch):
        if ch == "logic":
            print self.ch[ch]['traces']['combined']
        else:
            print self.ch[ch]['display_trace']
        # self.data['templates']['trace'] = self.ch[ch]['display_trace']
        
    def switch_operation(self, op):
        self.data['mode'] = op
        self.state = self.s_operation_router

    def reset_status(self):
        d = self.data
        dev = d['device']
        res = d['results']
        dev['connected_not_tested'] = False
        dev['model'] = dev['tested'] = dev['pass'] = False
        res['comp'] = False
        self.data['test']['status'] = 'connect'
        if self.data['mode'] == "post_test":
            self.data['mode'] = "pre_test"

    """STATES"""
    def s_operation_router(self):
        op = self.data['mode']
        test = self.data['test']
        if self.data['device']['connected']:
            if op == "post_test":
                self.state = self.s_post
                test['op_count'] = 4
            elif op == "pre_test":
                self.state = self.s_idle
                if test['status'] == 'proceed':
                    test['op_count'] = 2
            elif op == "comp":
                self.state = self.s_setup_for_comp
                test['op_count'] = 3
        else:
            self.state = self.s_find_device
    
    def s_find_device(self):
        if self.data['mode'] == "post_test":
            self.reset_status()
        elif self.data['mode'] == "pre_test":
            self.data['test']['status'] = 'connect'
            self.data['test']['op_count'] = 1
        else:
            self.data['test']['status'] = 'connect'

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
        self.data['device']['model'] = (self.ser.read(20)[1:7])
        print self.data['device']['model'] + " Connected."
        self.data['test']['status'] = "proceed"

        self.dirty = True
        if self.data['device']['model'] in self.data['ranges']:
            self.state = self.s_setup_bs
        else:
            self.state = self.s_check_model

    def s_setup_bs(self):
        bc = ""
        bc+="[1c]@[%s]sn[%s]s" % l_endian_hexify(self.whole_dump / 2) #Dump size
        bc+="[1e]@[05]s[21]@[12]s" #set dump and trace
        bc+="[08]@[00]sn[00]sn[00]s" #Set spock address
        bc+="[16]@[01]sn[00]s" #Set iterations to 1
        
        bc+="[2a]@[%s]sn[%s]s" % l_endian_hexify(self.whole_trace) #post trig cap 
        bc+="[30]@[00]s" #dump channel (Doesn't do anything?)
        bc+="[31]@[04]s" #Buffer mode (to macro)
        bc+="[37]@[00]s" #Analogue channel enable
        bc+="[26]@[%s]sn[%s]s" % l_endian_hexify(16) #pre trig cap
        bc+="[2c]@[00]sn[0a]s" #Time out REALLY IMPORTANT
        bc+="[2e]@[90]sn[00]s" #Set clock ticks
        bc+="[14]@[01]sn[00]s" #clock scale
        self.s_t.issue_wait(bc)
        """TRIGGER"""
        self.s_t.issue_wait(
            "[06]@[00]s" #Set trigger mask to "Don't care about anything"
            "[05]@[00]s" #This doesn't matter because we don't care about triggers.
            "[28]@[00]sn[00]s" #pre trigger delay
            "[32]@[00]sn[00]sn[00]sn[00]s" #Edge trigger intro, then outro filter.
            "[44]@[00]sn[00]s" #dig comparitor trigger (signed)
            "[40]@[00]sn[00]sn[00]sn[00]s" #stop watch trigger (ticks)
        )
        bc = (self.data['ranges'][self.data['device']['model']][self.data['range']]) #Range entry
        bc += "U"
        self.s_t.issue_wait(bc)
        
        """WAVE FORM GENERATOR"""
        self.s_t.issue_wait(
            "[7c]@[c0]s" # Kitchen sink register B! ENABLES AWG!!!
            "[86]@[00]s"  # Turn the clock generator off.
        )
        self.s_t.issue_wait("U")
        self.s_t.issue_wait(
            "[46]@[00]s"# vpCmd (Command Vector)
            "[47]@[03]s"# vpMode (Operating Mode)
            "[5a]@[00]sn[80]sn[00]sn[00]s"# vpRatio (Phase Ratio)
        )
        self.s_t.issue_wait("Y")# SYNTHESIZE!
        self.s_t.issue_wait(
            "[46]@[00]s"# vpCmd (Command Vector)
            "[47]@[00]s"# vpMode (Operating Mode)
            "[4a]@[e8]sn[03]s"# vpSize (Operation size, 1000 samples)
            "[4c]@[00]sn[00]s"# vpIndex (Operation Index, table start)
            "[4e]@[00]sn[00]s"# vpAddress (Destination Address, buffer start)
            "[54]@[ff]sn[ff]s"# vpLevel (Output Level, full scale)
            "[56]@[00]sn[00]s"# vpOffset (Output Offset, zero)
            "[5a]@[93]sn[18]sn[04]sn[00]s"# vpRatio (Phase Ratio)
        )
        self.s_t.issue_wait("X")# TRANSLATE!
        self.s_t.issue_wait(
            "[48]@[f4]sn[80]s"# vpOption (control flags)
            "[50]@[af]sn[00]s"# vpClock (Sample Clock Ticks)
            "[52]@[e8]sn[03]s"# vpModulo (Table Modulo Size)
            "[5e]@[0a]sn[01]s"# vpMark (Mark Count/Phase)
            "[60]@[01]sn[00]s"# vpSpace (Space Count/Phase)
            "[78]@[00]sn[7f]s"# vrDacOutput (DAC Level)
            "[46]@[02]s"# vmCmd (Command Vector)
        )
        self.s_t.issue_wait("Z")# GENERATE!
        self.ser.read(10000)
        self.s_t.issue_wait(">")
        self.s_t.issue("U")
        
        self.state = self.s_operation_router

    """Idle..........."""
    def s_idle(self):
        self.s_t.issue_wait("?")
        self.ser.flushInput()

    def s_post(self):
        dev = self.data['device']
        dev['tested'] = True
        res = self.data['results']
        dev['pass'] = res['comp']
        if dev['connected'] and dev['tested']:
            if dev['pass']:
                self.data['test']['status'] = "passed"
            else:
                self.data['test']['status'] = "failed"
        
        self.state = self.s_idle

    """COMP"""
    def s_setup_for_comp(self):
        self.s_t.issue_wait(
            "[1e]@[05]s[21]@[12]s" #set dump and trace mode
            "[31]@[04]s" #Buffer mode (to macro)
            "[2e]@[90]sn[00]s" # Clock ticks
        )
        self.s_t.issue_wait(self.data['ranges']['BS0005'][11]) #Range entry
        """AWG"""
        self.s_t.issue_wait("[7c]@[c0]s") # Kitchen sink register B! ENABLES AWG!!!
        self.s_t.issue_wait("[74]@[0f]s") # Logic pins to outputs.
        self.s_t.issue_wait("[86]@[00]s") # Turn the clock generator off.
        self.s_t.issue_wait(
            "[46]@[00]s"# vpCmd (Command Vector)
            "[47]@[03]s"# vpMode (Operating Mode)
            "[5a]@[00]sn[80]sn[00]sn[00]s"# vpRatio (Phase Ratio)
        )
        self.s_t.issue_wait("Y")# SYNTHESIZE!
        self.s_t.issue_wait(
            "[47]@[00]s"# vpMode (Operating Mode)
            "[5a]@[93]sn[18]sn[04]sn[00]s"# vpRatio (Phase Ratio)
        )
        self.s_t.issue_wait("X")# TRANSLATE!
        self.s_t.issue_wait(
            "[50]@[af]sn[00]s"# vpClock (Sample Clock Ticks)
            "[46]@[02]s"# vmCmd (Command Vector)
        )
        self.s_t.issue_wait("Z")# GENERATE!
        self.s_t.issue_wait(">")
        self.s_t.issue_wait("U")
        self.ser.read(1000)
        
        self.state = self.s_init_a_req

    # Use alternating capture! 
    def s_init_a_req(self):
        self.s_t.clear_waiting()
        self.ser.read(10000)
        self.s_t.issue_wait(">")
        self.s_t.issue("[37]@[01]sD")

        self.state = self.s_a_dump

    def s_a_dump(self):
        self.s_t.clear_waiting()
        self.ser.read(33)
        self.s_t.issue_wait(">")
        self.s_t.issue("A")

        self.state = self.s_a_proc_b_req

    def s_a_proc_b_req(self):
        self.s_t.clear_waiting()
        self.ser.read(self.ex_size)
        a_dump = self.ser.read(self.d_size)
        self.a['trace'] = convert_12bit_bin_dump(a_dump)
        self.a['ready'] = True

        self.s_t.issue_wait(">")
        self.s_t.issue("[07]@[04]s[37]@[02]sD")

        self.state = self.s_b_dump

    def s_b_dump(self):
        self.s_t.clear_waiting()
        self.ser.read(33)
        self.s_t.issue_wait(">")
        self.s_t.issue("A")

        self.state = self.s_b_proc_a_req

    def s_b_proc_a_req(self):
        self.s_t.clear_waiting()
        self.ser.read(self.ex_size)
        b_dump = self.ser.read(self.d_size)
        self.b['trace'] = convert_12bit_bin_dump(b_dump)
        self.b['ready'] = True
        
        self.s_t.issue_wait(">")
        self.s_t.issue("[07]@[00]s[37]@[01]sD")

        self.state = self.s_a_dump            
        
    """Process funcs"""
    def find_trigger(self, ch):
        tr = self.ch[ch]['trace']

        if tr:
            zero = self.ch[ch]['zero'][16]

            count = 5
            for iii in range(50, len(tr)-count, 1): # 50 sample lead so we can move backwards later.
                pre_sum = 0
                post_sum = 0
                #Check previous samples are lower
                for prev in range(0,count-1,1):
                    pre_sum += tr[iii + prev]
                #Check proceeding samples are higher
                for post in range(1,count,1):
                    post_sum += tr[iii + post]

                post_avg = post_sum / (count)
                pre_avg = pre_sum / (count)

                if post_avg >= zero and pre_avg <= zero:
                    return iii

            return None
            
    def triggered_trace(self, ch):
        trigger = self.find_trigger(ch)
        if trigger is not None:
            offset = self.data['sample_offset'][self.data['mode']]
            self.ch[ch]['display_trace'] = self.ch[ch]['trace'][trigger+offset:] # offset backwards to 0
        else:
            self.ch[ch]['display_trace'] = self.ch[ch]['trace']

    def sum_of_squares(self, ch):
        temp = self.data['templates'][self.data['mode']]
        trace = self.ch[ch]['display_trace']
        error = self.ch[ch]['errors']['top']
        mask = self.data['mask_height']
        m2 = 500
        diff_sqr = 0.0
        count = 0
        if trace and (len(trace) >= len(temp)):
            for iii in range(len(temp)):
                if (temp[iii] < mask
                    and trace[iii] < mask
                    and (trace[iii-1] - trace[iii]) < m2
                    and (trace[iii+1] - trace[iii]) < m2):
                    diff_sqr += ((float(temp[iii] - error) - float(trace[iii]))**2) / 100.0
                    count += 1
            self.ch[ch]['sos_string'] = str("%.1f"%diff_sqr).rjust(5)
            if count:
                self.ch[ch]['sos'] = diff_sqr / count

    def check_error(self, ch, mode):
        temp = self.data['templates'][self.data['mode']]
        trace = self.ch[ch]['display_trace']
        temp_diff = 0
        if len(trace) > len(temp):
            for pt in self.data['cal_points'][self.data['mode']][mode]:
                temp_diff += temp[pt] - trace[pt]

            self.ch[ch]['errors'][mode] = temp_diff / len(self.data['cal_points'][self.data['mode']][mode])

    def test_error_value(self, ch):
        if abs(self.ch[ch]['errors']['shape']) >= 400:
            self.ch[ch]['pass']['comp'] = False

    def correct_error(self, ch): # Moves template wave around. Not used. :(
        temp = self.data['templates']['comp']
        err = self.ch[ch]['error']
        for iii in range(len(temp)-1):
            temp[iii] = temp[iii] - err

    def process_queue(self, ch):
        channel = self.ch[ch]
        channel['queue'].pop(0)
        channel['queue'].append(self.ch[ch]['sos'])
        if channel['frame_count'] == channel['ready_on_frame']:
            avg = sum(channel['queue']) / len(channel['queue'])
            channel['result'] = int(avg * 10) # *10 to make it pretty. No other reason.
            channel['frame_count'] = 0
        else:
            channel['frame_count'] += 1

    def check_pass(self, ch, op):
        channel = self.ch[ch]
        result = channel['result']
        limit = channel['limits'][op]
        if result <= limit:
            channel['pass'][op] = True
        else:
            channel['pass'][op] = False
        if result >= 10000:
            channel['result'] = "OVER"

    def check_operation_pass(self, op):
        d_ch = self.ch
        d_res = self.data['results']
        d_res['comp'] = d_ch['a']['pass']['comp'] and d_ch['b']['pass']['comp']
        
    """UPDATES"""
    def comp_update(self):
        if self.ch['a']['ready']:
            self.check_error('a', 'top')
            self.triggered_trace('a')
            self.sum_of_squares('a')
            self.process_queue('a')
            self.check_error('a', 'shape')
            self.check_pass('a', 'comp')
            self.test_error_value('a')
            self.ch['a']['ready'] = False

        if self.ch['b']['ready']:
            self.check_error('b', 'top')
            self.triggered_trace('b')
            self.sum_of_squares('b')
            self.process_queue('b')
            self.check_error('b', 'shape')
            self.check_pass('b', 'comp')
            self.test_error_value('b')
            self.ch['b']['ready'] = False

        self.check_operation_pass('comp')
            
    def update(self):
        if self.test['op_count'] == 2:
            self.dev['connected_not_tested'] = True
        else:
            self.dev['connected_not_tested'] = False
        
        try:
            self.state()
        except serial.SerialException:
            print "Device disconected | Error: SE"
            self.state = self.s_find_device
        except serial.SerialTimeoutException:
            print "Device disconected | Error: STE"
            self.state = self.s_find_device

        self.comp_update()
