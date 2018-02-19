import pygame
from pygame.locals import *


from widget import Widget

class Image_Box(Widget):
    def __init__(self, cfg):
        Widget.__init__(self, cfg)
        self.mode = "single"

        self.is_alpha = False

        self.base_path = ""
        self.images = {}
        self.surfaces = {}
        self.init_image = None
        
        self.img_surf = None
        self.rect = None
        self.scale = 1
        self.size = None
        
        self.new_rect = None

    def refresh(self):
        self.load_images()
        if self.scale != 1 or self.size:
            self.scale_images()

        if self.init_image:
            self.img_surf = self.surfaces[self.init_image]
        else:
            self.img_surf = self.surfaces[self.surfaces.keys()[0]] # default to whatever.

        if self.rect is None:
            self.rect = self.img_surf.get_rect()

    def load_images(self): # Destroys the paths, and loads images into RAM instead.
        for img in self.images.keys():
            self.surfaces[img] = pygame.image.load(self.base_path + self.images[img])
            if self.is_alpha:
                self.surfaces[img].convert_alpha()

    def scale_images(self):
        for img in self.surfaces.keys():
            img_size = self.surfaces[img].get_rect()[2:]
            if self.size and self.size != [0,0]:
                if self.size[0] == 0:
                    # 1 is the relevant one
                    div = float(img_size[1]) / float(self.size[1])
                    img_scaled_size = [int(img_size[0] / div), self.size[1]]
                elif self.size[1] == 0:
                    # 0 is the guy
                    div = float(img_size[0]) / float(self.size[0])
                    img_scaled_size = [self.size[0], int(img_size[1] / div)]
                else:
                    img_scaled_size = self.size  
            else:
                img_scaled_size = (int(img_size[0] * self.scale), int(img_size[1] * self.scale))
                
            self.surfaces[img] = pygame.transform.smoothscale(self.surfaces[img], img_scaled_size)

    def img_from_path(self, path):
        self.img_surf = pygame.image.load(path)
        self.dirty = True

    def set_image(self, img_num):
        self.img_surf = pygame.image.load(Image_Man.ex_imgs[img_num]).convert_alpha()

    def on_render(self, screen):
        screen.blit(self.img_surf, self.pos)

    def handle_data(self, val):
        if self.mode == "multi":
            if val in self.surfaces.keys():
                self.img_surf = self.surfaces[val]
                self.dirty = True
