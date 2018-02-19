import glob
import os
import json
import pprint
from machines import *

class Config(object):
    def __init__(self):
        self.cfg = {"globals":{},"modes":{}}
        self.cfg["globals"] = {
            "default_title":"BitScope PiLab",
            "colours":{},
            "fonts":{},
            "fullscreen":False,
            "frame_rate":50,
            "depth":32,
            "widget_sheet":None,
            "widget_rects":{},
            "machines":{},
            "fast_widgets":False,
            "loading":{"image":"./image/loading.png", "spin_speed":1.5},
            "output_dir":"./output/",
            "cache_dir":"./cache/" # ./cache/mode/layout/widgetname.png
        }

        self.cfg["globals"]["colours"] = {
            "cha" :[255,255,50],
            "chb" :[60,255,60],
            "on"  :[210,215,190],
            "off" :[60,60,60],
            "diff":[90,220,255],
            "default":[200,200,215],
            "default_dark":[150,150,155],
            "default_darker":[100,100,105],
            "default_light":[250,250,255],
            "red" :[255,0,0],
            "orange":[255,140,0],
            "green":[0,255,0],
            "blue":[0,0,255],
            "purple":[255,0,255],
            "pink":[255,180,210],
            "yellow":[255,255,0],
            "aqua":[0,255,255],
            "white":[255,255,255],
            "brown":[150,100,50]
        }

        self.cfg["globals"]["fonts"] = {
            "standard":"./font/VeraBd.ttf",
            "mono":"./font/VeraMoBd.ttf"
        }

        self.cfg["globals"]["widget_sheet"] = "Graphics/sheet_states_new.png"

        self.cfg["globals"]["widget_rects"] = {
            "tiny"    : [0,0,32,32],
            "sml_h"   : [0,32,48,48],
            "sml"     : [0,80,64,32],
            "std"     : [0,112,96,32],
            "big"     : [0,144,128,64],
            "huge"    : [0,0,256,128],
            "sml_disp": [0,208,128,64],
            "big_disp": [0,272,384,96],
            "huge_disp":[0,0,768,192],
            "led_t"   : [0,464,8,8],
            "led_s"   : [0,0,12,12],
            "led"     : [0,472,16,16],
            "led_data": [0,488,48,24],
            "led_link": [0,512,48,24],
            "led_big" : [0,544,48,48],
            "led_huge": [0,0,64,64]
        }
        self.cfg["globals"]["proto_pos"] = {
            "button":[0,0],
            "small_button":[0,30],
            "panel":[0,42],
            "small_panel":[0,72],
            "led":[0,84],
            "small_led":[0,114]
        } # Squared graphics get to have much smaller slice sizes.
        
        self.cfg["globals"]["default_refs"] = [
            "data",
            "enable",
            "disable",
            "redraw",
            "on",
            "off",
            "colour"
        ]

        self.cfg["globals"]["machines"] = {
            "machine_xy_plot":MachineXYPlot,
            "machine_lobby":MachineLobby,
            "machine_logic":MachineLogic,
            "machine_meter":MachineMeter,
            "machine_scope":MachineScope,
            "machine_sound":MachineSound,
            "machine_test":MachineTest,
            "machine_ttafe":MachineTTAFE,
            "machine_verify":MachineVerify,
            "machine_simple_meter":MachineSimpleMeter,
            "machine_tuner":MachineTuner,
            "machine_triggered_logic":MachineTriggeredLogic
        }

        

        self.cfg["modes"] = {}
        self.load_config_files("./config")
        self.convert_colours(self.cfg)
        self.convert_colour(self.cfg)
        self.convert_rects(self.cfg)
        self.convert_sizes(self.cfg)
        self.convert_fonts(self.cfg)


    def load_config_files(self, directory):
        # Get all the JSON files from the current directory
        cfgs = glob.glob(directory + "/*.json")
        cfgs.sort()
        # Append them all to the config tree
        for f in cfgs:
            f = open(f, 'r')
            j = json.loads(f.read())
            self.update_branch(j['cfg'], self.cfg)
        # Find all folders in the current dir
        for newdir in os.walk(directory):
            if newdir[0] != directory:
                self.load_config_files(newdir[0])
                
    def update_branch(self, fi, cfg):
        for key in fi.keys():
            if key in cfg.keys():
                if isinstance(cfg[key], dict) and isinstance(fi[key], dict): # If both are dicts, step in.
                    self.update_branch(fi[key], cfg[key])
                elif not isinstance(cfg[key], dict) and not isinstance(fi[key], dict):
                    # Otherwise, check that they're both not dicts and update.
                    cfg[key] = fi[key]
            elif isinstance(fi[key], dict):
                cfg[key] = {} # If it's not in the config tree but is a dict in the file; make it a dict...
                self.update_branch(fi[key], cfg[key]) # And step into it!
            else:
                cfg[key] = fi[key] # If it's not in the cfg tree and not meant to be a dict; assign it.

    def convert_colours(self, cfg): # Convert tokens
        for k in cfg.keys():
            if (k == "cols"
                or "colours" in k
                and isinstance(cfg[k], dict)):
                for c in cfg[k]:
                    if not isinstance(cfg[k][c], list):
                        cfg[k][c] = self.cfg["globals"]["colours"][cfg[k][c]]
            elif isinstance(cfg[k], dict):
                self.convert_colours(cfg[k])
                
    def convert_colour(self, cfg): # Converts single colours.
        for k in cfg.keys():
            if ("colour" in k
                and not ("colours" in k)
                and isinstance(cfg[k], basestring)
                and not ("default_colour" in k)):
                cfg[k] = self.cfg['globals']['colours'][cfg[k]]
            elif k == "refs":
                pass
            elif isinstance(cfg[k], dict):
                self.convert_colour(cfg[k])
                
    def convert_rects(self, cfg):
        for k in cfg.keys():
            if k == "rect" and not isinstance(cfg[k], list):
                cfg[k] = self.cfg["globals"]["widget_rects"][cfg[k]]
            elif isinstance(cfg[k], dict):
                self.convert_rects(cfg[k])
                
    def convert_sizes(self, cfg):
        for k in cfg.keys():
            if k == "size" and not isinstance(cfg[k], list):
                cfg[k] = self.cfg['globals']['widget_rects'][cfg[k]][2:]
            elif isinstance(cfg[k], dict):
                self.convert_sizes(cfg[k])

    def convert_fonts(self, cfg):
        for k in cfg.keys():
            if k == "font":
                cfg[k] = self.cfg["globals"]["fonts"][cfg[k]]
            elif isinstance(cfg[k], dict):
                self.convert_fonts(cfg[k])
                
    def delete_widgets(self, cfg):
        for k in cfg.keys():
            if k == "delete_widgets":
                for w in cfg[k]:
                    del cfg['layout'][w]
            elif isinstance(cfg[k], dict):
                self.delete_widgets(cfg[k])
                                    
    def include_widgets(self):
        for k in cfg.keys():
            if k == "include_widgets":
                for w in cfg['layout'].keys():
                    if w not in cfg[k]:
                        del cfg['layout'][w]
            elif isinstance(cfg[k], dict):
                self.include_widgets(cfg[k])
