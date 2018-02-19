import pygame
from pygame.locals import *

from widget import Widget


class Drawing_Surface(Widget):
    def __init__(self, cfg):
        Widget.__init__(self, cfg)

        self.size = [0,0]
        self.surface = None
        self.line_col = cfg['globals']['colours']['cha']
        self.mode = "line" # line, lines, rectangle are valid

        self.scale = {"x":1.0, "y":1.0}
        self.offset = {"x":0.0, "y":0.0}
        self.start = {"x":0, "y":0}
        
        # Pluralities for multiple traces
        self.offsets = {}
        self.scales = {}
        self.line_cols = {}
        self.sources = {}
        
        self.slots = {"colour":False, "offset":False, "order":[]}
        self.slots['colours'] = [
            [255,255,0],
            [0,255,0],
            [255,0,0],
            [0,0,255],
            [255,0,255],
            [0,255,255],
            [255,255,255],
            [128,128,255]
        ]
        
        self.alpha = 255
        
        self.markers = {}

    def make_surface(self):
        # self.surface = pygame.Surface(self.size, pygame.SRCALPHA, 32)
        # self.surface = self.surface.convert_alpha()
        self.surface = pygame.Surface(self.size, 0, 24)
        self.surface = self.surface.convert()

    def refresh(self):
        self.make_surface()
        self.rect = [0,0, self.size[0], self.size[1]]
        self.check_trace_info()
        
    def draw_rect(self, rect):
        pygame.draw.rect(self.surface, [0,255,0], rect)

    #Draw one line
    def draw_line(self, line, col):
        if line:
            pygame.draw.lines(self.surface, col, False, line, 1)

    def draw_lines(self, line_ls):
        for iii in range(0, len(line_ls), 1):
            pygame.draw.aalines(self.surface, self.line_col, False, line_ls[iii], 1)

    def draw_trace(self, trace, source=None):
        y_size = self.size[1]
        new_trace = []
        if source is not None:
            offset = self.offsets[source]
            scale = self.scales[source]
            colour = self.line_cols[source]
        else:
            offset = self.offset
            scale = self.scale
            colour = self.line_col
        
        x_local = 0.0
        for t in trace:
            if x_local <= self.size[0]:
                new_trace.append((x_local + offset['x'], y_size - ((t * scale['y']) + offset['y'])))
                x_local += self.scale['x']
            else:
                break
        if trace:
            self.draw_line(new_trace, colour)
            
    def draw_logic(self, trace, source=None):
        y_size = self.size[1]
        new_trace = []
        if source is not None:
            offset = self.offsets[source]
            scale = self.scales[source]
            colour = self.line_cols[source]
        else:
            offset = self.offset
            scale = self.scale
            colour = self.line_col
        
        x_local = 0.0
        for iii in range(len(trace)):
            if x_local <= self.size[0] + self.scale['x']:
                if trace[iii] != trace[iii-1]:
                    x_local -= self.scale['x']
                new_trace.append((x_local + offset['x'], y_size - ((trace[iii] * scale['y']) + offset['y'])))
                x_local += self.scale['x']
            else:
                break
        if trace:
            self.draw_line(new_trace, colour)
        
    def on_render(self, screen):
        y_size = self.size[1]
        if self.mode == "trace":
            draw = self.draw_trace
        elif self.mode == "logic":
            draw = self.draw_logic
        else:
            draw = self.draw_trace
            
        if self.slots['order']:
            for s in self.slots['order']:
                tr = self.sources[s]['trace']
                draw(tr, s)
        else:
            for s in self.sources.keys():
                draw(self.sources[s]['trace'])
                
        # Draw markers
        if self.markers:
            for m in self.markers.keys():
                # Get colour
                m_col = self.markers[m]['colour']
                # Do offsets and scaling
                level = y_size - ((self.markers[m]['level'] + self.offset['y']) * self.scale['y'])
                line = [[0, level], [self.size[0], level]]
                pygame.draw.lines(self.surface, m_col, False, line, 1)
        screen.blit(self.surface, self.pos)
        pygame.draw.rect(self.surface, [0,0,0,100], self.surface.get_rect())
        # self.surface.fill((0,0,0,self.alpha))

    def handle_data(self, val):
        if self.mode == "line":
            self.draw_line(val, self.line_col)
        elif self.mode == "lines":
            self.draw_lines(val)
        elif self.mode == "rect" or self.mode == "rectangle":
            self.draw_rect(val)
        elif self.mode == "trace":
            self.draw_trace(val)
        elif self.mode == "logic":
            self.draw_logic(val)
        
    def handle_wild_ref(self, key, val):
        if "marker" in key:
            self.markers[key]['level'] = val
        else:
            self.sources[key]['trace'] = val
        self.dirty = True

    def check_trace_info(self):
        for r in self.refs.keys():
            c1 = r != "data"
            c2 = r != "ena"
            c3 = r != "dis"
            c4 = r != "redraw"
            if c1 and c2 and c3 and c4:
                if r not in self.offsets.keys():
                    if self.slots['offset'] and r in self.slots['order']:
                        pos = self.slots['order'].index(r)
                        self.offsets[r] = {}
                        self.offsets[r]['y'] = (pos * self.offset['y']) + self.start['y']
                        self.offsets[r]['x'] = (pos * self.offset['x']) + self.start['x']
                    else:
                        self.offsets[r] = self.offset
                if r not in self.scales.keys():
                    self.scales[r] = self.scale
                if r not in self.line_cols.keys():
                    if self.slots['colour'] and r in self.slots['order']:
                        pos = self.slots['order'].index(r)
                        if pos < len(self.slots['colours']):
                            self.line_cols[r] = self.slots['colours'][pos]
                        else:
                            self.line_cols[r] = self.line_col
                    else:
                        self.line_cols[r] = self.line_col
                        
                self.sources[r] = {"trace":[]}
                    
