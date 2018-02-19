import pygame
from pygame.locals import *

from numpy import *
from tools import *
import thread

from widget import Widget

class Mini_Map(Widget):
    
    """The Mini_Map widget is designed to display an entire bytearray
    in a small space.
    """
    
    def __init__(self, cfg):
        Widget.__init__(self, cfg)
        
        self.size = [0,0]
        
        self.bg_surface = None
        self.trace_surface = None
        
        self.dirty_traces = True
        
        # Positional 
        self.position = 0
        self.range = 1000.0
        self.zoom_range = (0,0)
        # Bg colour
        self.colour = [0,0,0]
        
        # Traces dict
        self.traces = {}
        
        # Viewrect
        self.view_colour = [0,255,0]
        
        # Parsing check
        self.currently_parsing = False
        self.progress = 0
        
    def refresh(self):
        cfg_g = self.cfg['globals']
        Surface = pygame.Surface
        self.surface = Surface(self.size, 0, cfg_g['depth']).convert()
        self.trace_surface = Surface(self.size, 0, cfg_g['depth']).convert()
        self.trace_surface.set_colorkey([0,0,0])
        self.rect = [0,0] + self.size
        self.correct_trace_info()
        
    def correct_trace_info(self):
        y_size = self.size[1]
        for trace in self.traces.keys():
            t = self.traces[trace]
            if isinstance(t['y_offset'], basestring):
                if t['y_offset'].endswith('%'):
                    p_pos = t['y_offset'].find('%')
                    p = float(t['y_offset'][:p_pos])
                    t['y_offset'] = y_size * p/100
            t['alts'] = []
            t['rects'] = []

    def parse_bytearray(self, ba, subsample = 1):
        """
        Similar to the dense_parse function in Logic_Display.
        It converts whichever portion of the bytearray the map is
        looking at into a
        """
        if ba and not self.currently_parsing:
            self.currently_parsing = True
            
            traces = self.traces
            x_size, y_size = self.size
            
            view_start = int(self.zoom_range[0])
            view_end = int(self.zoom_range[1])
            
            block_size = int(round(to_range(1,[0,x_size],[view_start,view_end]), 0)) - view_start
            block_test = []
            block_test_append = block_test.append
            
            """ Get block info for whole byte """
            for block in xrange(view_start, view_end, block_size):
                and_test = 255
                or_test = 0
                try:
                    for byte in xrange(block, block + block_size, subsample):
                        and_test &= ba[byte]
                        or_test |= ba[byte]
                except(IndexError):
                    pass # Who cares?! Keep going!
                block_test_append((and_test, or_test))
                self.progress += 1
                self.dirty = True
                
            """ Build traces """
            for trace in traces.keys():
                t = traces[trace]
                bit_val = t['bit']
                full_rect = [0,0]
                rect_list = t['rects'] = []
                rect_list_append = rect_list.append
                alt_rect = [0,0]
                alt_list = t['alts'] = []
                alt_list_append = alt_list.append
                
                current_block = 0
                prev_block = 2
                
                for block in xrange(len(block_test)):
                    at = (block_test[block][0] & bit_val) > 0
                    ot = (block_test[block][1] & bit_val) > 0
                    current_block = at + ot # Store both just incase
                    
                    if current_block == 1:
                        if prev_block == 1:
                            # Extend alt rect
                            alt_rect[1] = block + 1
                        else:
                            # Append alt rect and start again
                            alt_list_append(tuple(alt_rect))
                            alt_rect[0] = block
                            alt_rect[1] = block + 1
                            
                    elif current_block == 2:
                        if prev_block == 2:
                            # Extend full rect
                            full_rect[1] = block + 1
                        else:
                            # Append full rect and start again
                            rect_list_append(tuple(full_rect))
                            full_rect[0] = block
                            full_rect[1] = block + 1
                            
                    prev_block = current_block
                    self.dirty_traces, self.dirty  = True, True
                            
                rect_list_append(tuple(full_rect))
                alt_list_append(tuple(alt_rect))
                self.dirty_traces, self.dirty  = True, True
            self.currently_parsing = False
            self.progress = 0

    
    def handle_data(self, val):
        # self.parse_bytearray(val)
        # The BA barely object pretty much never changes.
        # Parsing here only makes it parse a blank array
        # when the view is loading
        self.dirty = True
    
    def handle_data_refresh(self, val):
        if val:
            ref = self.refs['data']['path'][self.refs['data']['ref']]
            thread.start_new_thread(self.parse_bytearray, (ref,103))
            self.dirty = True
            
    def handle_deep_scan(self, val):
        ref = self.refs['data']['copy']
        thread.start_new_thread(self.parse_bytearray, (ref,1))
        self.dirty = True
        
    def handle_zoom(self, val):
        """ This takes a range tuple and fits that range onto the minimap"""
        self.zoom_range = val
        self.parse_bytearray(self.refs['data']['copy'], 103)
    
    """
    All these two functions do is change the size and position
    of the view rectangle
    """
    def handle_position(self, val):
        self.position = val
        self.dirty = True
    
    def handle_range(self, val):
        self.range = val
        self.dirty = True
        
    def draw_data(self):
        """ This simply draws the gathered
        rectangles to a separate surface """
        pg_draw_rect = pygame.draw.rect
        surface_x, surface_y = self.size
        fill = self.trace_surface.fill
        # Wipe the surface clean before drawing!
        fill(self.colour, self.trace_surface.get_rect())
            
        for trace in self.traces.keys():
            t = self.traces[trace]
            y = t['y_scale']
            y_offset = surface_y - t['y_offset']
            # Draw 0 lines
            fill([30,30,30],[0,y_offset, surface_x, 1])
            if t['alts']:
                for rect in t['alts']: # Draw alternating blocks
                    x_size = rect[1] - rect[0]
                    fill(t['colour'], [rect[0], y_offset-y, x_size, y])
                    
            if t['rects']: # Draw blocks that were only on
                for alt in t['rects']:
                    x_size = alt[1] - alt[0]
                    fill(t['colour'], [alt[0], y_offset-y, x_size, 1])
                    
        self.dirty_traces = False
        
    
    def on_render(self, screen):
        pg_draw_rect = pygame.draw.rect
        surface_y = self.size[1]
        fill = self.surface.fill
        if self.progress:
            fill([50,50,50], [0,0,self.progress,surface_y])
            
        if self.dirty_traces:
            self.draw_data()
        
        # Blit the trace surface onto main
        self.surface.blit(self.trace_surface, [0,0])
        
        view_range = self.zoom_range
        start = to_range(self.position, view_range, [0,self.size[0]])
        width = to_range(self.range + self.position, view_range, [0,self.size[0]])
        width -= start
               
        view_rect = [start, 0, width, surface_y]
        pg_draw_rect(self.surface, self.view_colour, view_rect, 1)
        screen.blit(self.surface, self.pos)
        pygame.draw.rect(self.surface, [0,0,0], self.surface.get_rect())
