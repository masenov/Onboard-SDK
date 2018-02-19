import pygame
from pygame.locals import *
import numbers
import numpy

from widget import Widget

from tools import *

class Logic_Display(Widget):
    def __init__(self, cfg):
        Widget.__init__(self, cfg)
        
        self.size = [0,0]
        
        self.trace_surf = None
        self.trace_surf_size = None
        
        # Scaling and position
        self.position = 0 # Where the trace starts within the ba
        self.range = None # Where it ends within relative pos (set in refresh)
        self.frequency = 100
        
        # Background colour
        self.colour = [0,0,0]
        # Trace dict
        self.traces = {}
        
        # Grid spacing, because why not?
        self.grid_spacing = None # If 0, no grid, otherwise; percentage
        self.grid_list = [] # Only verticals, so this is just x pos's
        self.grid_labels = []
        self.grid_label_font = None
        
        self.gutter = 0
        
        self.need_parse = False
        
    def refresh(self):
        """ Called by the manufacturer (view) directly after
        embedding all the data from the config. """
        self.make_grid_label_font()
        self.confirm_gutters()
        self.make_surface()
        self.rect = [0, 0] + self.size
        self.correct_trace_info()
        self.range = self.trace_surf_size[1]
        self.compute_grid()
    
    def refresh_bytearray(self, val):
        if val:
            ref = self.refs['data']['path'][self.refs['data']['ref']]
            self.parse_bytearray(ref)
            self.dirty = True
    
    def make_surface(self):
        self.surface = pygame.Surface(self.size, 0, self.cfg['globals']['depth'])
        self.surface = self.surface.convert()
        # Subsurface for drawing the traces and such to
        s_rect = self.surface.get_rect()
        g = self.gutter
        g_l, g_r, g_t, g_b = g['left'], g['right'], g['top'], g['bottom']
        rect_pos = [s_rect[0] + g_l, s_rect[1] + g_t]
        rect_size = [s_rect[2] - (g_l + g_r), s_rect[3] - (g_t + g_b)]
        new_rect = rect_pos + rect_size
        self.trace_surf = self.surface.subsurface(new_rect)
        self.trace_surf_size = new_rect[2:]
        
    def make_grid_label_font(self):
        cfg_font = self.cfg['globals']['fonts']['standard']
        self.grid_label_font = pygame.font.Font(cfg_font, 9)
        
    def correct_trace_info(self):
        """ Turns any y offsets that are percentages into
        real numbers. Also initialises 2 important lists
        incase they don't exist or aren't lists for some reason. """
        y_size = self.trace_surf_size[1]
        for trace in self.traces.keys():
            t = self.traces[trace]
            if isinstance(t['y_offset'], basestring):
                if t['y_offset'].endswith('%'):
                    p_pos = t['y_offset'].find('%')
                    p = float(t['y_offset'][:p_pos])
                    t['y_offset'] = y_size * p/100
            t['line'] = []
            t['rects'] = []
    
    def confirm_gutters(self):
        """ Makes sure gutters are well/properly defined """
        if isinstance(self.gutter, dict):
            if 'other' not in self.gutter.keys():
                self.gutter['other'] = 0
            for g in ['left', 'right', 'top', 'bottom']:
                if g not in self.gutter.keys():
                    self.gutter[g] = self.gutter['other']
        elif isinstance(self.gutter, numbers.Number):
            g = self.gutter
            self.gutter = {'left':g, 'right':g, 'top':g, 'bottom':g}
            
    def compute_grid(self):
        """ Takes the grid spacing (as a percentage)
        and generates a list of x positions """
        if self.grid_spacing:
            if isinstance(self.grid_spacing, basestring):
                self.grid_spacing = str(self.grid_spacing).translate(None, "%")
            self.grid_spacing = float(self.grid_spacing)
            # Now we definitely have a percentage
            grid_pix = self.trace_surf_size[0] / self.grid_spacing
            self.grid_list.extend(float_range(grid_pix, self.trace_surf_size[0], grid_pix))
            
    def make_grid_labels(self):
        """ This takes position, range and frequency
        and labels each grid line with a time signature
        """
        freq = self.frequency * 1000
        # The first line is the time sig of that pos
        start_seconds = float(self.position) / freq
        end_seconds = float(self.position + self.range) / freq
        # The other lines are offsets from the first
        ts_x = self.trace_surf_size[0]
        g_fractions = [g / ts_x for g in self.grid_list]
        g_seconds = [(self.position + (self.range * frac)) / freq for frac in g_fractions]
        self.grid_labels = [start_seconds] + g_seconds + [end_seconds]
        
    def parse_bytearray(self, ba):
        # If sparse, do sparse
        if ba:
            if self.range < self.trace_surf_size[0]:
                self.sparse_parse(ba)
            else:
                self.dense_parse(ba)
                
    def sparse_parse(self, ba):
        """ Figures out where and how to draw all the logic
        channels when the number of samples per pixel > 1
        """
        end = int(self.position + self.range)
        y_size = self.trace_surf_size[1]
        x_inc = float(self.trace_surf_size[0]) / self.range # Zoom has to be derived from the start and end pos
        for trace in self.traces.keys():
            local_x = 0.0
            bit_val = self.traces[trace]['bit']
            y_offset = self.traces[trace]['y_offset']
            y_scale = self.traces[trace]['y_scale']
            line = self.traces[trace]['line'] = []
            l_append = line.append
            # Put in the first point from pos-1
            y = y_size - ((y_scale * ((ba[self.position-1] & bit_val) > 0)) + y_offset)
            l_append([-x_inc, y])
            point = [0.0,y]
            # Gather the rest of the line
            for b in xrange(self.position, end):
                try:
                    if ba[b-1] == ba[b]:
                        point[0] += x_inc
                    elif ba[b-1] != ba[b]:
                        point[0] += x_inc
                        l_append(tuple(point))
                        point[1] = y_size - ((y_scale * ((ba[b] & bit_val) > 0)) + y_offset)
                        l_append(tuple(point))
                except (IndexError):
                    break
            # Put in the last point
            y = y_size - ((y_scale * ((ba[end-1] & bit_val) > 0)) + y_offset)
            l_append([point[0] + x_inc, y])
            
    def dense_parse(self, ba, subsample = 1):
        """ This function works out how best to display the data from the samples
        that lie within each pixel column.
        If 1 or more samples fits inside a pixel, this mode is used.
        If the samples belonging to a a single pixel column are alternating,
        that column is recorded as a rectangle.
        If the next pixel is the same, that same rectangle is extended to the current column.
        This cuts down on the amount of rendering pygame has to do.
        """
        view_x = self.trace_surf_size[0]
        ba_start = self.position
        ba_end = int(ba_start + self.range)
        block_test = []
        block_test_append = block_test.append
        y_size = self.trace_surf_size[1]
        traces = self.traces
        
        """ Get block info """
        # Build linspace array and append last sample pos at the end
        size_array = numpy.linspace(ba_start, ba_end, self.trace_surf_size[0], endpoint=False)
        size_array = numpy.append(size_array, [ba_end]).astype('uint')
        # Iterate over whole array, less the last element, as we will not account for that
        fc = 0
        for block in xrange(len(size_array) - 1):
            and_test = 255
            or_test = 0
            for byte in xrange(size_array[block], size_array[block + 1]):
                and_test &= ba[byte]
                or_test |= ba[byte]
                
            block_test_append((and_test, or_test))
            
        """ Build traces! """
        for trace in traces.keys():
            t = traces[trace]
            bit_val = t['bit']
            
            """ Visual stuff... Maybe move to the
            render function, so it matches rects """
            y_offset = t['y_offset']
            y_scale = t['y_scale']
            
            line_list = t['line'] = []
            rect_list = t['rects'] = []
            
            line_append = line_list.append
            rect_append = rect_list.append
            
            point = [0, y_size - y_offset]
            rect = [-1, -1]
            
            current_block = 0
            prev_block = 1
            
            for block in xrange(-1, len(block_test) - 1):
                at = (block_test[block][0] & bit_val) > 0
                ot = (block_test[block][1] & bit_val) > 0
                current_block = at + ot
                
                if current_block == 1:
                    if prev_block == 1:
                        # Extend the rect
                        rect[1] = block + 1
                    else:
                        # Append
                        if (rect[1] - rect[0]) > 1:
                            rect_append(tuple(rect))
                        # Restart
                        rect = [block, block + 1]
                elif prev_block == current_block:
                    # Extend last point
                    point[0] = block
                elif prev_block == 1:
                    # Extend and append the last point
                    point[0] = block - 1 # Why minus 1?!
                    line_append(tuple(point))
                    # Raise and append new point
                    if not current_block:
                        point[1] = y_size - (y_scale + y_offset)
                        line_append(tuple(point))
                    # Adjust point to current block and append
                    point[1] = y_size - (((current_block > 0) * y_scale) + y_offset)
                    line_append(tuple(point))
                else:
                    point[0] = block
                    line_append(tuple(point))
                    point[1] = y_size - (((current_block > 0) * y_scale) + y_offset)
                    line_append(tuple(point))
                    
                prev_block = current_block
            
            line_append(tuple(point))
            point = (ba_end, y_size - y_offset)
            line_append(tuple(point))
            if (rect[1] - rect[0]) > 0:
                rect_append(tuple(rect))
            
    def handle_data(self, val):
        # self.parse_bytearray(val)
        self.dirty = True
            
    def handle_data_refresh(self, val):
        if val:
            self.need_parse = True
            
    def handle_position(self, val):
        self.position = val
        self.need_parse = True
            
    def handle_range(self, val):
        self.range = val
        self.need_parse = True
        
    def handle_frequency(self, val):
        self.frequency = val
        self.make_grid_labels()
        self.dirty = True
        
    def render_labels(self):
        f_rend = self.grid_label_font.render
        y_pos = self.trace_surf.get_rect()[3] + self.gutter['top']
        labels = self.grid_labels
        gutter = self.gutter
        # Render first
        surf = f_rend(str(labels[0]) + "s", 1, [60,90,60])
        self.surface.blit(surf, [gutter['left'], y_pos])
        # Then last
        surf = f_rend(str(labels[len(labels)-1]) + "s", 1, [60,90,60])
        x = self.size[0] - surf.get_rect()[2] - gutter['right']
        self.surface.blit(surf, [x, y_pos])
        # Then the rest
        ts_size_x = self.trace_surf_size[0]
        labels = labels[1:len(labels)-1] # Remove first and last
        for l in range(len(labels)):
            surf = f_rend(str(labels[l] * 1000) + "ms", 1, [60,60,60])
            x = (self.grid_list[l] + self.gutter['left']) - (surf.get_rect()[2] * 0.5)
            self.surface.blit(surf, [x, y_pos])
            
    def update(self):
        # Do the normal update
        super(Logic_Display, self).update()
        # Now do own logic
        if self.need_parse:
            self.make_grid_labels()
            self.refresh_bytearray(True)
            self.need_parse = False
        
    def on_render(self, screen):
        fill = self.surface.fill
        trace_fill = self.trace_surf.fill
        draw_lines = pygame.draw.lines
        surf_size_x = self.trace_surf_size[0]
        surf_size_y = self.trace_surf_size[1]
        
        self.render_labels()
        # Draw border around trace surface
        pygame.draw.rect(self.trace_surf, [50,50,50], self.trace_surf.get_rect(), 1)
        # Draw verticals
        for v_line in self.grid_list:
            trace_fill([50,50,50], [v_line, 0, 1, self.trace_surf_size[1]])
        
        for trace in self.traces.keys():
            t = self.traces[trace]
            if t['line']:
                draw_lines(self.trace_surf, t['colour'], False, t['line'], 1)
            if self.range >= surf_size_x and t['rects']:
                for rect in t['rects']:
                    x_size = rect[1] - rect[0]
                    y_size = t['y_scale']
                    y_pos = surf_size_y - (t['y_scale'] + t['y_offset'])
                    trace_fill(t['colour'], [rect[0], y_pos, x_size, y_size + 1])
                
        screen.blit(self.surface, self.pos) # This includes the subsurface
        self.surface.fill([0,0,0])
