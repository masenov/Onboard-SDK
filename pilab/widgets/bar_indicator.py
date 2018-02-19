import pygame
from pygame.locals import *
from widget_imports import *


class Bar_Indicator(Widget):
    def __init__(self, cfg):
        Widget.__init__(self, cfg)
        self.size = [50,300]
        
        self.padding = 3
        
        self.colour = cfg['globals']['colours']['default_dark']
        self.indicator_colour = cfg['globals']['colours']['cha']
        self.baseline_colour = cfg['globals']['colours']['default_darker']
        
        self.ind_rect = None
        self.ranges = {"top": 0, "bot":0}
        
        self.px_range = 0
        
        self.level = 0
        self.baseline = 0
        
        self.marker_colours = {}
        self.markers = {}
        
    def refresh(self):
        # Fill ranges if they don't exist
        if "top" not in self.ranges.keys():
            self.ranges['top'] = 1
        if "bot" not in self.ranges.keys():
            self.ranges['bot'] = 1
            
        self.px_range = self.size[1] - (self.padding * 2)
        
        self.get_markers_from_refs()
        
        # Build ind rect
        self.rect = [0,0] + self.size
        width = self.size[0] - (self.padding*2)
        self.ind_rect = [0,0,width,0]
        
    def get_markers_from_refs(self):
        for r in self.refs.keys():
            if "marker" in r:
                self.markers[r] = 0.0
        
    def convert_to_pixel(self, val):
        out_r = float(self.px_range)
        in_r = self.ranges['bot'] - self.ranges['top']
        slope = float(out_r / in_r)
        output = slope * (val - self.ranges['top'])
        return output
        
    def generate_marker(self, level):
        px_z = self.convert_to_pixel(0)
        lv = self.convert_to_pixel(level)
        px_lv = px_z + (lv - px_z)
        start = [self.pos[0]] + [self.pos[1] + self.padding + px_lv]
        end = [self.pos[0] + self.size[0] - 1] + [self.pos[1] + self.padding + px_lv]
        return [start,end]
        
        
    def set_level(self, level):
        lv = self.convert_to_pixel(level) + 1
        if round(self.ind_rect[3]) != round(lv - self.convert_to_pixel(0)):
            self.ind_rect[3] = lv - (self.convert_to_pixel(0))
            self.dirty = True
            
    def set_marker_level(self, marker, level):
        self.markers[marker] = level
        self.dirty = True
        
    def handle_data(self, val):
        self.set_level(val)
        
    def handle_wild_ref(self, marker, val):
        self.set_marker_level(marker, val)
        
    def on_render(self, screen):
        dr = pygame.draw.rect
        dr_line = pygame.draw.line
        gen_m = self.generate_marker
        bl = gen_m(self.baseline)
        # Draw BG
        dr(screen, self.colour, self.pos + self.rect[2:])
        # Draw indicator
        ind_x = self.pos[0] + self.padding
        ind_y = self.pos[1] + self.padding + self.convert_to_pixel(0)
        ind_pos = [ind_x, ind_y]
        
        dr(screen, self.indicator_colour, ind_pos + self.ind_rect[2:])
        # Draw baseline
        dr_line(screen, self.baseline_colour, bl[0], bl[1])
        # Draw markers
        for m in self.markers.keys():
            try:
                col = self.marker_colours[m]
            except:
                col = [0,0,0]
            line = gen_m(self.markers[m])
            dr_line(screen, col, line[0], line[1], 1)
