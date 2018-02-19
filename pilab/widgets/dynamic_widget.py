import pygame
from pygame.locals import *
import os.path

from widget import Widget

from colour import *

class Dynamic_Widget(Widget):
    def __init__(self, cfg):
        Widget.__init__(self, cfg)
        self.toggle_state = True
        
        self.cache_type = "dynamic"
        
        self.colour = None
        self.colours = {"default":cfg['globals']['colours']['default']}
        self.default_colour = None

        self.size = [0,0] # Minimum size is c_size * 2

        self.img_proto = pygame.image.load("./image/proto.png")
        self.proto_pos = cfg['globals']['proto_pos']['button']
        self.alt_proto_pos = cfg['globals']['proto_pos']['small_button']
        self.img_proto.convert_alpha()
        self.internal_surface = None
        self.widget_surface = None
        self.surfaces = {}
        
        self.surf_flags = SRCALPHA
        self.special_flags = BLEND_RGBA_MULT
        
        self.strings = {"default":"Default"}
        
        self.alterable = True

        self.c_size = 10
        self.alt_c_size = 4
        
        """ STATES """
        self.clicked, self.hovered, self.idle = 0, 1, 2
        self.held_down = 3

    def refresh(self):
        self.setup_performance()
        # Check sizes
        # If both too small for standard c_size
        if self.size[0] < self.c_size*2 or self.size[1] < self.c_size*2:
            # Change proto positions and tile size.
            self.proto_pos = self.alt_proto_pos
            self.c_size = self.alt_c_size
        # If they're still to small
        if self.size[0] < self.c_size * 2:
            self.size[0] = self.c_size * 2
        if self.size[1] < self.c_size * 2:
            self.size[1] = self.c_size * 2
            
        if self.colour is None:
            self.colour = self.cfg['globals']['colours']['default']
            
        self.internal_surface = pygame.Surface(self.size, flags=self.surf_flags)
        self.internal_surface.convert_alpha()
        self.internal_surface.fill((0,0,0,0))
        
        self.widget_surface = pygame.Surface([self.size[0]*4, self.size[1]], flags=self.surf_flags)
        self.widget_surface.convert_alpha()
        self.widget_surface.fill((0,0,0,0))
        
        """ Image creating, caching and loading """
        # Set up colour from colour param
        if self.colour is not None:
            self.colours['default'] = self.colour
            
        # Make path to cached image
        cache_dir = self.cfg['globals']['cache_dir']
        cache_path = "%s%s_%s%s" % (cache_dir, self.get_cache_string_stub(), "base", ".png")
        # Ensure the directory's existence
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        # Load or generate
        if not os.path.isfile(cache_path):
            self.generate_graphic()
            pygame.image.save(self.internal_surface, cache_path)
        else:
            self.internal_surface = pygame.image.load(cache_path)
            
        # Now for colours/states
        # First try to load them, appending those that didn't to a list
        did_not_load = []
        for col in self.colours.keys():
            col_val = self.colours[col]
            cache_path = "%s%s_%s%s" % (cache_dir, self.get_cache_string_stub(), str(col_val), ".png")
            if os.path.isfile(cache_path):
                self.surfaces[col] = pygame.image.load(cache_path)
            else:
                did_not_load.append(col)
        # Generate any missing ones    
        self.generate_colour_surfaces()
        # Cache newly generated ones
        for col in did_not_load:
            col_val = self.colours[col]
            cache_path = "%s%s_%s%s" % (cache_dir, self.get_cache_string_stub(), str(col_val), ".png")
            pygame.image.save(self.surfaces[col], cache_path)
        
        # Set surface to default_colour param
        if self.default_colour is not None:
            if self.default_colour in self.colours.keys():
                self.widget_surface = self.surfaces[self.default_colour]
        else:
            self.widget_surface = self.surfaces["default"]
            
        """Almost there"""
        
        self.rect = [0,0] + self.size
        self.refresh_text()
    
    def get_cache_string_stub(self):
        return self.cache_type + "_" + str(self.size)
        
    def generate_colour_surfaces(self):
        # For each colour defined in the config
        for col in self.colours.keys():
            # Make a new surface in surfaces if not already there
            if col not in self.surfaces.keys():
                self.surfaces[col] = self.widget_surface.copy()
                self.generate_state_graphics(self.colours[col], self.surfaces[col])
            
    def generate_state_graphics(self, colour, surface):
        cols = self.generate_state_colours(colour)
        for iii in (0,1,2,3):
            pos = [self.size[0]*iii, 0]
            surface.blit(self.internal_surface, pos)
            self.colour_graphic(surface, pos, cols[iii])
            
    def colour_graphic(self, surface, pos, colour):
        if self.colour is not None:
            temp_s = surface.copy()
            arr = pygame.surfarray.pixels3d(temp_s)
            arr[:,:,:] = colour # Colour the surface [x,y,colour_index]
            del arr # Unlocks the surface
            surface.blit(temp_s, pos, pos + self.size, special_flags=self.special_flags)

    def generate_graphic(self):
        cs = self.c_size
        s = self.size
        do_scale = pygame.transform.smoothscale # Reallllllly?
        p_x = self.proto_pos[0]
        p_y = self.proto_pos[1]
        p_x_cs = p_x + cs*2
        p_y_cs = p_y + cs*2
        
        """Corners"""
        corners = {"tl":{}, "tr":{}, "bl":{}, "br":{}}
        # The rects are the position and size of the corners on the prototype image
        corners['tl']['rect'] = [p_x, p_y, cs, cs]
        corners['tr']['rect'] = [p_x_cs, p_y, cs, cs]
        corners['bl']['rect'] = [p_x, p_y_cs, cs, cs]
        corners['br']['rect'] = [p_x_cs, p_y_cs, cs, cs]
        # The pos's are the corner positions on the new surfaces.
        corners['tl']['pos'] = [0, 0]
        corners['tr']['pos'] = [s[0]-cs, 0]
        corners['bl']['pos'] = [0, s[1]-cs]
        corners['br']['pos'] = [s[0]-cs, s[1]-cs]
        for corner in corners.keys():
            self.internal_surface.blit(self.img_proto, corners[corner]['pos'], corners[corner]['rect'])
            
        """Sides"""
        sides = {"v":{}, "h":{}}
        sides['v']['mid'] = {'left':{}, 'right':{}}
        sides['v']['mid']['left']['rect'] = [0, cs+p_y, cs, cs]
        sides['v']['mid']['left']['pos'] = (0, cs)
        sides['v']['mid']['right']['rect'] = [cs*2, cs+p_y, cs, cs]
        sides['v']['mid']['right']['pos'] = ((s[0] - cs), cs)
        sides['v']['scale'] = s[1] - (cs * 2)
        sides['v']['scale_rect'] = [cs, sides['v']['scale']]
        
        sides['h']['mid'] = {'top':{}, 'bottom':{}}
        sides['h']['mid']['top']['rect'] = [cs, p_y, cs, cs]
        sides['h']['mid']['top']['pos'] = (cs, 0)
        sides['h']['mid']['bottom']['rect'] = [cs, p_y_cs, cs, cs]
        sides['h']['mid']['bottom']['pos'] = (cs, (s[1] - cs))
        sides['h']['scale'] = s[0] - (cs * 2)
        sides['h']['scale_rect'] = [sides['h']['scale'], cs]
        
        for d in sides.keys():
            for side in sides[d]['mid'].keys():
                ld = sides[d]['mid'][side]
                # Create a surface to contain the slice
                slice_s = pygame.Surface((cs,cs))
                # Blit the slice to the slice surface
                slice_s.blit(self.img_proto, (0,0), ld['rect'])
                # Scale the surface
                scaled_s = do_scale(slice_s, sides[d]['scale_rect'])
                # Blit the scaled surface to the internal surface
                self.internal_surface.blit(scaled_s, ld['pos'])
                
        """Middle!"""
        m_rect = [cs+p_x,cs+p_y, sides['h']['scale'], sides['v']['scale']]
        m_slice = pygame.Surface((cs,cs))
        m_slice.blit(self.img_proto, (0,0), (cs+p_x,cs+p_y,cs,cs))
        m_scaled = do_scale(m_slice, m_rect[2:])
        self.internal_surface.blit(m_scaled, (cs,cs))
            
    def generate_state_colours(self, colour):
        cols = [None] * 4
        f1 = 0.9
        f2 = 0.6
        cols[0] = list(colour)
        cols[1] = list(colour)
        cols[2] = list(colour)
        cols[3] = list(colour)
        
        cols[1] = HSV_alter("mult", cols[1], "s", 0.8)
        cols[1] = HSV_alter("mult", cols[1], "v", 0.8)
        
        cols[2] = HSV_alter("mult", cols[2], "s", 0.4)
        cols[2] = HSV_alter("mult", cols[2], "v", 0.4)
        
        cols[3] = HSV_alter("mult", cols[3], "s", 0.85)
        cols[3] = HSV_alter("mult", cols[3], "v", 0.75)
        
        # Check for over 255s
        for col in cols:
            for component in range(len(col)):
                if col[component] > 255:
                    col[component] = 255 
                elif col[component] < 0:
                    col[component] = 0
        return cols
            
    def on_click(self, m_pos=[0,0]):
        if self.alterable and self.enabled:
            self.state = self.clicked
        if self.enabled:
            if self.click_action != None:
                return self.click_action
            else:
                print "Action Error: " + str(self.click_action)
                
    """ TEST LMB STUFF"""
    def on_lmb_down(self, m_pos=[0,0]):
        pass
        
    def on_lmb_held(self, m_pos=[0,0]):
        if self.alterable and self.enabled:
            if self.state != self.held_down:
                self.state = self.held_down
                self.shift_rect([self.rect[2] * 2, self.rect[1]])
            return self.lmb_held_action
        
    def on_lmb_up(self, m_pos=[0,0]):
        if self.alterable and self.enabled:
            self.state = self.idle
            self.shift_rect([self.rect[2] * 0, self.rect[1]])
            
    """ END """
        
    def on_hover(self, m_pos=[0,0]):
        if self.alterable and self.enabled:
            if self.state != self.hovered:
                self.state = self.hovered
                self.shift_rect([self.rect[2] * 1,self.rect[1]])
        if self.hover_action != None:
            return self.hover_action

    def on_unhover(self):
        if self.alterable and self.enabled:
            self.state = self.idle
            if self.toggle_state == True:
                self.shift_rect([self.rect[2] * 0,self.rect[1]])
            elif self.toggle_state == False:
                self.shift_rect([self.rect[2] * 3,self.rect[1]])
            if self.unhover_action != None and self.hidden != True:
                return self.unhover_action
                
    def handle_colour(self, val):
        val = str(val).lower()
        if val in self.surfaces.keys():
            self.widget_surface = self.surfaces[val]
        else:
            self.widget_surface = self.surfaces['default']
        self.dirty = True
        
    def handle_text(self, val):
        val = str(val).lower()
        if val in self.strings.keys():
            self.set_text(self.strings[val])
        else:
            self.set_text(val + " err")
        
    def handle_enable(self, val):
        self.enabled = val
        shift = 2 * (not val)
        self.shift_rect([self.rect[2] * shift, self.rect[1]])
        
    def handle_disable(self, val):
        self.enabled = not val
        shift = 2 * val
        self.shift_rect([self.rect[2] * shift, self.rect[1]])
        
    def handle_on(self, val):
        self.toggle_state = val
        shift = 3 * (not val)
        self.shift_rect([self.rect[2] * shift, self.rect[1]])
        
    def handle_off(self, val):
        self.toggle_state = not val
        shift = 3 * val
        self.shift_rect([self.rect[2] * shift, self.rect[1]])
        
    def handle_text_colour(self, val):
        val = str(val).lower() # WHAT IS THIS!? It does nothing!
        
    def check_colour_keys(self): # Doesn't work.
        for col in self.colours.keys():
            print type(col)
            if isinstance(col, basestring):
                if col.lower() == "true":
                    self.colours[True] = self.colours[col]
                    del self.colours[col]
                elif col.lower() == "false":
                    self.colours[False] = self.colours[col]
                    del self.colours[col]
                    
    def get_colour_from_key(self, key, colours):
        colour = None
        if isinstance(key, list) or isinstance(key, tuple):
            colour = key # Key is the colour!... Maybe.
        elif key in colours.keys():
            colour = colours[key]               
        elif key in self.cfg['globals']['colours'].keys():
            colour = self.cfg['globals']['colours'][key]
        else:
            colour = self.cfg['globals']['colours']['default']
            
        return colour
        
    def setup_performance(self):
        if self.cfg['globals']['fast_widgets']:
            self.img_proto.convert()
            # self.proto_pos = self.alt_proto_pos
            self.surf_flags = 0
            self.special_flags = BLEND_RGB_MULT
            # self.c_size = self.alt_c_size
            
    def on_render(self, screen):
        screen.blit(self.widget_surface, self.pos, self.rect)
        screen.blit(self.text_surf, (self.pos[0] + self.text_surf_x, self.pos[1] + self.text_surf_y))
        if self.label_surf:
            pos = (self.pos[0] + self.label_surf_pos[0],self.pos[1] + self.label_surf_pos[1])
            screen.blit(self.label_surf,pos)
