import pygame
from pygame.locals import *

from dynamic_widget import Dynamic_Widget

class Panel(Dynamic_Widget):
    def __init__(self, cfg):
        Dynamic_Widget.__init__(self, cfg)
        self.cache_type = "panel"
        
        self.alterable = False
        
        self.proto_pos = cfg['globals']['proto_pos']['panel']
        self.alt_proto_pos = cfg['globals']['proto_pos']['small_panel']
        self.colours['default'] = [130,160,160]
