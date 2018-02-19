import pygame
from pygame.locals import *

from dynamic_widget import Dynamic_Widget

from colour import *
from tools import *

class Slider(Dynamic_Widget):
    def __init__(self, cfg):
        Dynamic_Widget.__init__(self, cfg)
        
        self.proto_pos = cfg['globals']['proto_pos']['panel']
        
        self.bg_size = [200,50]
        self.bg_colour = (110,110,110)
        
        self.slot_size = [150, 15]
        self.slot_colour = (90,90,90)
        
        self.slider_size = [40,40]
        self.slider_colour = (150,150,150)
        
        self.slider_offset = 0 # -100 ... +100
                
    def refresh(self):
        self.rect = self.pos + self.bg_size
        
    def on_lmb_held(self, m_pos=[0,0]):
        if self.alterable and self.enabled:
            half_slot_bg_diff = (self.bg_size[0] - self.slot_size[0]) * 0.5
            slot_end = self.slot_size[0] + half_slot_bg_diff
            rel_m_x = self.get_rel_pos(m_pos)[0]
            if half_slot_bg_diff <= rel_m_x <= (self.slot_size[0] + half_slot_bg_diff):
                self.slider_offset = to_range(rel_m_x, (half_slot_bg_diff, slot_end), (-100.0, 100.0))
            elif rel_m_x < half_slot_bg_diff:
                self.slider_offset = -100.0
            elif rel_m_x > slot_end:
                self.slider_offset = 100.0
            self.output[0] = to_range(self.slider_offset, (-100, 100), (0, 100))
            self.dirty = True
            
            return self.lmb_held_action
                        
    def on_lmb_up(self, m_pos=[0,0]):
        if self.alterable and self.enabled:
            self.slider_offset = 0
            self.dirty = True
                    
    def on_render(self, screen):
        # Background
        screen.fill(self.bg_colour, self.pos + self.bg_size)
        # Slot
        slot_x = self.pos[0] + ((self.bg_size[0] - self.slot_size[0]) * 0.5)
        slot_y = self.pos[1] + ((self.bg_size[1] - self.slot_size[1]) * 0.5)
        screen.fill(self.slot_colour, [slot_x, slot_y] + self.slot_size)
        # Slider
        slider_x = self.pos[0] + ((self.bg_size[0] - self.slider_size[0]) * 0.5)
        slider_y = self.pos[1] + ((self.bg_size[1] - self.slider_size[1]) * 0.5)
        slot_range_top = self.slot_size[0] - (self.slot_size[0] / 2)
        slot_range = (-slot_range_top, slot_range_top)
        screen.fill(self.slider_colour, [slider_x + to_range(self.slider_offset, (-100, 100), slot_range), slider_y] + self.slider_size)
