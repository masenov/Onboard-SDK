import pygame
from pygame.locals import *

from dynamic_widget import Dynamic_Widget

class Button(Dynamic_Widget):
    def __init__(self, cfg):
        Dynamic_Widget.__init__(self, cfg)
        self.cache_type = "button"
        
        self.proto_pos = cfg['globals']['proto_pos']['button']
        
        # Purely for the name 'Button'
