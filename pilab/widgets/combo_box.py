import pygame
from pygame.locals import *

from widget import Widget


class Combo_Box(Widget):
    def __init__(self, cfg):
        Widget.__init__(self, cfg)

        self.items = []
        self.item_label = None
        self.current_item = 2
        self.expanded = False
        self.was_expanded = False
        self.collapsing = False

        self.rect = [0,0,90,20]
        self.collapsed_rect = self.rect
        self.expanded_rect = [0,0,90,20]
        self.selected_rect = self.rect

        self.box_colour = [220,220,200]

        self.font_size = 12
        self.myfont = pygame.font.Font("./font/VeraBd.ttf", self.font_size)
        self.text_colour = [120,120,120]


    def add_item(self, text):
        self.items.append(text)
        self.expanded_rect[3] += 20

    def on_click(self, m_pos):
        if self.expanded == False:
            self.expand()

        elif self.expanded == True:
            #Figure out which item it's pointing at.
            #Set current item to whatever it is.
            #Return the onclick
            self.collapse()

    def on_hover(self, m_pos):
        pass

    def on_unhover(self):
        pass

    def expand(self):
        self.expanded = True
        #Generate all the text
        self.rect = self.expanded_rect
        self.dirty = True

    def collapse(self):
        self.expanded = False
        self.was_expanded = True
        self.rect = self.collapsed_rect
        self.dirty = True

    def on_render(self, rm):
        if not self.was_expanded and not self.collapsing:
            pygame.draw.rect(rm.screen, self.box_colour, self.get_pos_rect()) #Draw col rect
            if self.expanded == True:
                for i in range(0,len(self.items)-1):
                    temp_label = self.myfont.render(self.items[i], 1, self.text_colour)
                    rm.screen.blit(temp_label, (self.pos[0]+5, self.pos[1]+(i*20)+22))
            else:
                temp_label = self.myfont.render(self.items[self.current_item], 1, self.text_colour)
                rm.screen.blit(temp_label, (self.pos[0]+5, self.pos[1]+2))
        elif self.was_expanded:
            pygame.draw.rect(rm.screen, self.box_colour, self.get_pos_rect()) #Draw col rect
            self.rect = self.expanded_rect #Switch to exp rect
            self.was_expanded = False
            self.collapsing = True
            self.dirty = True
        elif self.collapsing:
            self.rect = self.collapsed_rect #Switch to collapsed
            pygame.draw.rect(rm.screen, self.box_colour, self.get_pos_rect()) #Draw col rect
            self.collapsing = False
            self.dirty = True


"""
If the cb was expanded in the previous frame, 
the cb must keep its expanded rect until the next frame.
During the next frame it must revert back to the collapsed rect.
"""


