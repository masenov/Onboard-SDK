import pygame
from pygame.locals import *

from widget import Widget

class Text_Box(Widget):
    def __init__(self, cfg):
        Widget.__init__(self, cfg)

        self.internal_surface = None
        self.blocks = None

        self.mode = "select" # Select or input are the options.
        self.size = [0,0]
        self.justification = "center"

        self.colour = cfg['globals']['colours']['default']

    def refresh(self):
        self.set_font()
        self.internal_surface = pygame.Surface(self.size)
        self.rect = [0,0] + self.size
        if self.blocks:
            self.select_text(self.blocks.keys()[0])
        else:
            self.set_text(self.text)

    def set_text(self, text):
        self.text = text
        self.generate_text_surface()
        self.dirty = True

    def select_text(self, block):
        if block in self.text_colours.keys():
            self.text_colour = block
        else:
            self.text_colour = "default"
        self.set_text(self.blocks[block])

    def generate_text_surface(self):
        text_col = self.text_colours[self.text_colour]
        final_lines = []

        requested_lines = self.text.splitlines()

        # Create a series of lines that will fit on the rect
        for requested_line in requested_lines:
            if self.text_font.size(requested_line)[0] > self.size[0]:
                words = requested_line.split(' ')
                # if any of our words are too long to fit, return.
                for word in words:
                    if self.text_font.size(word)[0] >= self.size[0]:
                        print "'" + word + "' is too long. Make rect wider."
                # Start a new line
                accumulated_line = ""
                for word in words:
                    test_line = accumulated_line + word + " "
                    # Build the line while the words fit.    
                    if self.text_font.size(test_line)[0] < self.size[0]:
                        accumulated_line = test_line 
                    else: 
                        final_lines.append(accumulated_line) 
                        accumulated_line = word + " " 
                final_lines.append(accumulated_line)
            else: 
                final_lines.append(requested_line) 

        # Write the text out on the surface.
        surface = self.internal_surface
        surface.fill(self.colour) 

        accumulated_height = 0 
        for line in final_lines: 
            if accumulated_height + self.text_font.size(line)[1] >= self.size[1]:
                print "One or more lines don't fit at the bottom. Make the size taller."
            if line != "":
                if line[len(line)-1] == " ":
                    line = line[:len(line)-1]
                tempsurface = self.text_font.render(line, 1, text_col)
                if self.justification == "left":
                    surface.blit(tempsurface, (0, accumulated_height))
                elif self.justification == "center":
                    surface.blit(tempsurface, ((self.size[0] - tempsurface.get_width()) / 2, accumulated_height))
                elif self.justification == "right":
                    surface.blit(tempsurface, (self.size[0] - tempsurface.get_width(), accumulated_height))
                else:
                    print "No such justification: " + str(self.justification)
            accumulated_height += self.text_font.size(line)[1]

    def handle_data(self, val):
        self.select_text(val)

    def on_render(self, screen):
        screen.blit(self.internal_surface, self.pos, self.rect)
