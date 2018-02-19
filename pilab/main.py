import pygame, sys, os
import threading

sys.dont_write_bytecode = True

sys.path.insert(0, './machines/')
sys.path.insert(0, './widgets/')
sys.path.insert(0, './utilities/')

from math import *
from pygame.locals import *
import time

from config import Config

from mode import Mode

cfg = Config().cfg

pygame.init()

clock = pygame.time.Clock()

os.environ['SDL_VIDEO_WINDOW_POS'] = 'center'
pygame.display.set_caption(cfg['globals']['default_title'])

# Build screen arguments.
scr_flags = 0
if cfg['globals']['fullscreen']:
    scr_flags |= FULLSCREEN
else:
    scr_flags |= 0
screen = pygame.display.set_mode(cfg['globals']['resolution'], scr_flags, cfg['globals']['depth'])

running = True
loading = False
loading_thread = None
if cfg['globals']['current_mode'] not in cfg['modes']:
    print "No configuration for mode: ", cfg['globals']['current_mode']
    cfg['globals']['current_mode'] = 'lobby'
    

lmb_down = False

alt_ctrl = False
lmb_drag = False
rmb_drag = False
btn_pos = [0,0]

fps = cfg['globals']['frame_rate']
current_mode = None

def handle_events():
    global running
    global lmb_down
    global alt_ctrl
    global lmb_drag
    global rmb_drag
    global btn_pos

    """Get mouse pos and ask if it's hovering anything"""
    m_pos = pygame.mouse.get_pos()
    
    current_mode.current_view.widget_update(m_pos)
    
    current_mode.current_view.on_hover(m_pos)
    
    if lmb_down:
        current_mode.current_view.on_lmb_held(m_pos)

    """Main event loop"""
    mods = pygame.key.get_mods()
    if mods & pygame.KMOD_LALT and mods & pygame.KMOD_LCTRL: # Edit layout mode
        alt_ctrl = True
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                btn_pos = m_pos
                if event.button == 1:
                    lmb_drag = True
                elif event.button == 3:
                    rmb_drag = True
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    lmb_drag = False
                if event.button == 3:
                    rmb_drag = False
                    
            elif event.type == pygame.KEYDOWN:
                w = current_mode.current_view.current_widget
                if event.key == pygame.K_p:
                    print m_pos
                elif event.key == pygame.K_LEFTBRACKET:
                    print w.pos, w.name
                elif event.key and w:
                    if event.key == pygame.K_u:
                        w.pos[1] -= 1
                    elif event.key == pygame.K_j:
                        w.pos[1] += 1
                    elif event.key == pygame.K_h:
                        w.pos[0] -= 1
                    elif event.key == pygame.K_k:
                        w.pos[0] += 1
                    
        if lmb_drag or rmb_drag:
            current_mode.current_view.widget_update(btn_pos) # This stops the cursor escaping the widget.
            if lmb_drag:
                current_mode.current_view.on_drag(m_pos, btn_pos)
            elif rmb_drag:
                current_mode.current_view.on_drag(m_pos, btn_pos, "group")
            btn_pos = m_pos
            
    elif mods & pygame.KMOD_LCTRL:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F5:
                    cfg = Config().cfg
                    current_mode.reload_views(cfg)
    
    else:
        alt_ctrl = False
        lmb_drag = False # Turn drag off if the mod keys are let go
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
    
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                else:
                    current_mode.handle_key(event.key)
                    
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # LMB
                    current_mode.current_view.on_lmb_down(m_pos)
                    lmb_down = True
                elif event.button == 2: # Middle
                    pass
                elif event.button == 3: # RMB
                    pass
                elif event.button == 4: # Wheel up
                    current_mode.current_view.on_scroll_up(m_pos)
                elif event.button == 5: # Wheel down
                    current_mode.current_view.on_scroll_down(m_pos)
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and lmb_down: # LMB
                    lmb_down = False
                    current_mode.current_view.on_lmb_up(m_pos)
                    
def switch_mode(m_req):
    global current_mode
    if m_req in cfg["modes"]:
        if current_mode:
            del(current_mode.current_view) # Destroy old mode
            del(current_mode.views)
            del(current_mode)
        current_mode = Mode(m_req, cfg) # Create new mode with the name token
    else:
        print "Trying to switch to a mode which does not exist!"

def quit_prog():
    global current_mode
    del current_mode.current_view
    del current_mode.views
    del current_mode
    time.sleep(1)
    pygame.display.quit()
    pygame.quit()
    sys.exit()
    
def rot_centre(image, angle):
    """ Rotate an image while keeping its centre and size """
    orig_rect = image.get_rect()
    rot_image = pygame.transform.rotozoom(image, angle, 1)
    rot_rect = orig_rect.copy()
    rot_rect.center = rot_image.get_rect().center
    rot_image = rot_image.subsurface(rot_rect).copy()
    return rot_image

def show_loading():
    # Load image
    swirl = pygame.image.load(cfg['globals']['loading']['image'])
    spin_speed = cfg['globals']['loading']['spin_speed']
    deg = 0
    screen_rect = screen.get_rect()
    swirl_rect = swirl.get_rect()
    centre = (screen_rect[2] - swirl_rect[2]) / 2, (screen_rect[3] - swirl_rect[3]) / 2
    while loading:
        screen.fill((70,70,70))
        twirl = rot_centre(swirl, deg)
        screen.blit(twirl, centre)
        deg += spin_speed
        pygame.display.update()
    pygame.display.update()
    
def start_loading():
    global loading, loading_thread
    loading = True
    loading_thread = threading.Thread(target = show_loading)
    loading_thread.start()
    
def stop_loading():
    global loading
    loading = False
    loading_thread.join()

def main():
    pygame.key.set_repeat(500,100)
    switch_mode(cfg["globals"]["current_mode"])
    global running
    while(running == True):
        handle_events()
        
        m_req = current_mode.update() # Update and store returned value
        if m_req != None:
            if m_req == "exit":
                running = False
            else:
                start = time.clock()
                start_loading()
                try:
                    switch_mode(m_req) # Switch mode based on returned value.
                except:
                    stop_loading()
                    raise
                stop_loading()
                print time.clock() - start

        if alt_ctrl:
            current_mode.current_view.dirty = True

        rect_ls = current_mode.current_view.on_render(screen, alt_ctrl)

        pygame.display.update(rect_ls)
        clock.tick(fps)

    quit_prog()
    
# Run the thing!
main()
