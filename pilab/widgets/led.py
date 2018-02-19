import pygame
from pygame.locals import *

from dynamic_widget import Dynamic_Widget

class LED(Dynamic_Widget):
    def __init__(self, cfg):
        Dynamic_Widget.__init__(self, cfg)
        self.cache_type = "led"
        
        self.alterable = False
        
        self.proto_pos = cfg['globals']['proto_pos']['led']
        self.alt_proto_pos = cfg['globals']['proto_pos']['small_led']
        
        self.colours['true'] = cfg['globals']['colours']['green']
        self.colours['false'] = cfg['globals']['colours']['red']
        
        self.reversed = False
        
        
    def handle_data(self, val): # This is a hack.
        if isinstance(val, bool) and self.reversed:
            val = not val
        self.handle_colour(val)
        
    def on_render(self, screen):
        screen.blit(self.widget_surface, self.pos, self.rect)
        # If, for any reason, an LED needs text, just delete this function.
