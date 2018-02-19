'''Base class for widgets'''
import copy
from numbers import Number
import pygame
from pygame.locals import *


class Widget(object):
    def __init__(self, cfg):
        self.name = ""
        self.cfg = cfg

        self.enabled = True
        #outline
        self.pos = [0,0]
        self.rect = [0,0,0,0]
        self.m_perc = [0,0] # Mouse percentage
        self.output = [0,0] # Filtered m_perc by widget
        
        #Other
        self.text_surf = None
        self.text_surf_x = 0
        self.text_surf_y = 0

        self.font_size = 16
        self.label_font_size = 12
        self.font = None
        self.text_font = None
        self.label_font = None

        self.text_colours = {
        "default": [220,220,200],
        "on"     : [200,210,190],
        "off"    : [40,40,40]
        }

        self.text_colour = cfg['globals']['colours']['default_light']

        self.set_font()
        self.text = ""
        #actions for all widgets
        self.click_action = []
        self.hover_action = []
        self.unhover_action = []
        self.scroll_up_action = []
        self.scroll_down_action = []
        self.lmb_held_action = []
        self.key_bind = None # Just a number.
        self.group = None

        #Internal data and model data hook
        self.refs = { #Path is the full path up to the needed value-key, ref is the value-key.
                        # 'data':{'path':None,'ref':None,'copy':None}, 
                        # 'ena':{'path':None,'ref':None,'copy':None}, 
                        # 'dis':{'path':None, 'ref':None, 'copy':None},
                        # 'redraw':{'path':None,'ref':None,'copy':None}
                    }

        self.dirty = True
        self.hidden = False
        self.overlap = False
        self.layer = None
        self.force_data = False
        
        self.alterable = True
        
        self.state = None
        
        self.held = False
        
        """ These all assume the text's colour """
        self.prefix = ""
        self.suffix = ""
        self.label = None
        self.rounding = 0
        self.rjust = 0
        
        self.label_surf = None
        self.label_surf_pos = [0,0]
        
    def refresh(self):
        self.refresh_text()
        
    def link_refs_to_functions(self):
        """ Link handle functions to refs;
        Makes it easier/faster to call in updates
        """
        refs = self.refs
        for ref in refs.keys():
            fn_str = "handle_" + ref
            if fn_str in dir(self):
                exec("refs[ref]['function'] = self." + fn_str)
        
    def set_pos(self, pos):
        self.pos = pos
    
    def set_rel_pos(self, pos, rel):
        nr = [pos[0] - rel[0], pos[1] - rel[1]]
        new_pos = [self.pos[0] + nr[0], self.pos[1] + nr[1]]
        self.set_pos(new_pos)
        
    def get_rel_pos(self, pos):
        return [pos[0] - self.pos[0], pos[1] - self.pos[1]]
    
    def get_rel_percentage(self, pos):
        r_pos = self.get_rel_pos(pos)
        x = (float(r_pos[0]) / self.rect[2]) * 100
        y = (float(r_pos[1]) / self.rect[3]) * 100
        return [x,y]
        
    def set_rect(self, rect):
        self.rect = rect
        
    def shift_rect(self, shift):
        self.rect = [shift[0], shift[1], self.rect[2], self.rect[3]]
        self.dirty = True #Mark as dirty to make sure it gets rerendered.

    def get_pos_rect(self):
        return [self.pos[0], self.pos[1], self.rect[2], self.rect[3]]

    def on_click(self, m_pos=[0,0]):
        if self.alterable and self.enabled:
            return self.click_action
    
    """ TEST LMB FUNCS """
    
    def on_lmb_down(self, m_pos=[0,0]):
        pass
    
    def on_lmb_held(self, m_pos=[0,0]):
        if self.alterable and self.enabled:
            return self.lmb_held_action
        
    def on_lmb_up(self, m_pos=[0,0]):
        pass
    
    """ END """

    def on_hover(self, m_pos=[0,0]):
        pass

    def on_unhover(self):
        pass
        
    def set_state(self, state):
        pass

    def on_scroll_up(self, m_pos=[0,0]):
        if self.alterable and self.enabled:
            return self.scroll_up_action
    
    def on_scroll_down(self, m_pos=[0,0]):
        if self.alterable and self.enabled:
            return self.scroll_down_action
    
    def on_drag(self):
        return self

    def set_text(self, text):
        col = self.text_colour
        if self.rounding and text:
            text = round(float(text), self.rounding)
        if self.rjust and text:
            text = str(text).rjust(self.rjust)
        self.text = self.prefix + str(text) + self.suffix
        self.text_surf = self.text_font.render(self.text, 1, col)
        self.align_text()
        self.dirty = True
        
    def set_label(self, label):
        col = self.text_colour
        self.label_surf = self.label_font.render(self.label, 1, col)
        self.align_label()
        self.dirty = True
        
    def refresh_text(self):
        self.set_font()
        self.set_text(self.text)
        self.set_label(self.label)
        
    def set_text_col(self, colour):
        self.text_col = colour
        self.refresh_text()
        
    def set_font(self):
        if self.font is not None:
            self.text_font = pygame.font.Font(self.font, self.font_size)
            self.label_font = pygame.font.Font(self.font, self.label_font_size)
        else:
            cfg_font = self.cfg['globals']['fonts']['standard']
            self.text_font = pygame.font.Font(cfg_font, self.font_size)
            self.label_font = pygame.font.Font(cfg_font, self.label_font_size)
        self.dirty = True
        
    def align_text(self):
        if self.text_surf:
            self.text_surf_x = (self.rect[2] - self.text_surf.get_width()) / 2
            self.text_surf_y = (self.rect[3] - self.text_surf.get_height()) / 2
            self.dirty = True
            
    def align_label(self):
        if self.label_surf:
            self.label_surf_pos[0] = (self.rect[2] - self.label_surf.get_width()) / 2
            self.label_surf_pos[1] = 3 # Turn into percentage
            self.dirty = True
                    
    def update(self):
        refs = self.refs
        for ref_key in refs.keys():
            ref = refs[ref_key]
            kd = ref['path'][ref['ref']]
            if isinstance(kd, Number):
                if self.force_data or kd != ref['copy']:
                    if 'function' in ref.keys():
                        ref['function'](kd)
                    else:
                        self.handle_wild_ref(ref_key, kd)
                    ref['copy'] = kd
            elif self.force_data or kd is not ref['copy']:
                if 'function' in ref.keys():
                    ref['function'](kd)
                else:
                    self.handle_wild_ref(ref_key, kd)
                ref['copy'] = kd

    def handle_on(self, val):
        self.set_state(val)

    def handle_off(self, val):
        self.set_state(val, True)

    def handle_enable(self, val):
        self.enabled = val

    def handle_disable(self, val):
        self.enabled = not val

    def handle_data(self, val):
        self.set_text(val)

    def handle_redraw(self, val):
        self.dirty = True
        
    def handle_hide(self, val):
        self.hidden = val
        self.dirty = True
        
    def handle_unhide(self, val):
        self.hidden = not val
        self.dirty = True

    def handle_wild_ref(self, key, ref):
        pass
