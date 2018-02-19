#View
import json

import pygame
from pygame.locals import *

from widget_imports import *

class View(object):
    def __init__(self, name, mode):
        self.name = name

        #Widgets
        self.widgets = []
        self.action_widgets = []
        self.widget_d = {} # Widgets without z values
        self.widget_z = {} # With z values
        self.widgets_dict = {} # All widgets
        self.current_widget = None
        self.last_widget = None
        self.dirty = True
        self.mode = mode
        self.mch = mode.machine

        self.background = None
        self.back_surf = None

        self.overlappers = {}
        
        self.key_binds = {}
        
        self.widget_key_binds = {}
        
        self.widget_groups = {}

        cfg_mode = self.mode.cfg["modes"][self.mode.name]
        if "mode_widgets" in cfg_mode:
            self.widgets_from_config(cfg_mode["mode_widgets"])
            self.cull_not_included_widgets()
        if "views" in cfg_mode:
            self.widgets_from_config(cfg_mode["views"][self.name]["layout"])
            if "background" in cfg_mode['views'][self.name].keys():
                self.load_background(cfg_mode["views"][self.name]['background'])
        self.delete_widgets()
        self.build_widget_list()
        self.append_overlappers()
        self.append_layers()
        self.bind_widget_keys()
        self.build_groups()
        
        self.data_update() # Initial data update.

    def data_update(self):
        for w in self.widgets:
            w.update()

    """Generic view functions"""
    def derive_widget_from_pos(self, m_pos):
        top_widget = None
        widget_pos = []
        widget_rect = []
        for widget in self.widgets:
            if not widget.hidden:
                widget_pos = widget.pos
                widget_rect = widget.rect
                if ((m_pos[0] > widget_pos[0]) and (m_pos[0] < (widget_pos[0] + widget_rect[2]))):#x
                    if ((m_pos[1] > widget_pos[1]) and (m_pos[1] < (widget_pos[1] + widget_rect[3]))): #y
                        top_widget = widget
                        widget.m_perc = widget.get_rel_percentage(m_pos)
        return top_widget

    def on_click(self, m_pos):
        if self.current_widget != None:
            self.mode.handle_action(self.current_widget.on_click(m_pos))

    def on_hover(self, m_pos):
        if self.current_widget != None and self.current_widget != self.last_widget:
            self.mode.handle_action(self.current_widget.on_hover(m_pos))
            self.last_widget = self.current_widget

    def on_scroll_up(self, m_pos):
        if self.current_widget != None:
            self.mode.handle_action(self.current_widget.on_scroll_up(m_pos))

    def on_scroll_down(self, m_pos):
        if self.current_widget != None:
            self.mode.handle_action(self.current_widget.on_scroll_down(m_pos))

    def on_drag(self, m_pos, btn_pos, mode="single"):
        """ This is actually for dragging the widgets around,
        not for UI interaction """
        if self.current_widget != None:
            if mode == "single":
                self.current_widget.on_drag().set_rel_pos(m_pos, btn_pos)
            elif mode == "group":
                widget_found = False
                wg = self.widget_groups
                for group in wg.keys():
                    if self.current_widget.name in wg[group].keys():
                        widget_found = True
                        for widget in wg[group].values():
                            widget.set_rel_pos(m_pos, btn_pos)
                if not widget_found:
                    self.current_widget.set_rel_pos(m_pos, btn_pos)
                    
    def on_keydown(self, key):
        if key in self.widget_key_binds.keys():
            for w in self.widget_key_binds[key]:
                self.mode.handle_action(w.on_click())
                
    """ TEST LMB FUNCS """
    
    def on_lmb_down(self, m_pos):
        if self.current_widget != None:
            self.current_widget.on_lmb_down(m_pos)
            self.current_widget.held = True
    
    def on_lmb_held(self, m_pos):
        if self.current_widget != None:
            if self.current_widget.held:
                self.mode.handle_action(self.current_widget.on_lmb_held(m_pos))
        
    def on_lmb_up(self, m_pos):
        if self.current_widget != None:
            if self.current_widget.held:
                self.current_widget.on_lmb_up()
                self.mode.handle_action(self.current_widget.on_click(m_pos))
                self.current_widget.on_hover(m_pos)
                self.current_widget.held = False
    
    """ END """
    def widget_update(self, m_pos):
        new_widget = self.derive_widget_from_pos(m_pos)
        if new_widget != self.current_widget:
            if self.current_widget != None:
                self.mode.handle_action(self.current_widget.on_unhover())
                if self.current_widget.held:
                    self.current_widget.on_lmb_up(m_pos)
                    self.current_widget.held = False
            self.last_widget = self.current_widget
            self.current_widget = new_widget

    def on_render(self, screen, BB):
        rect_list = []
        if self.dirty:
            if self.back_surf != None: #If mode has BG, render it.
                screen.blit(self.back_surf, [0,0]) #Blit background
            else: #If not, fill screen.
                col = 120
                screen.fill((col,col,col))

            for w in self.widgets: #render all widgets regardless of dirtiness
                if BB:
                    w.on_render(screen) #Don't reset dirtiness.
                elif not w.hidden:
                    w.on_render(screen)
            if BB: #render AABBs
                pygame_draw_rect = pygame.draw.rect #So .draw.rect doesn't get re-evaluated
                for w in self.widgets:
                    pygame_draw_rect(screen, [255,0,0],w.get_pos_rect(),1)
                    w.dirty = True
            self.dirty = False
            rect_list.append([0,0,screen.get_size()[0], screen.get_size()[1]]) #append screen size
        else:
            d_w = []
            d_w_app = d_w.append #So .append doesn't get re-evaluated
            for w in self.widgets: #Generate list of dirty widgets
                if w.dirty:
                    d_w_app(w)
            if len(d_w) > 0: #If there are any dirty widgets, blit the background.
                if self.back_surf != None:
                    for w in d_w:
                        screen.blit(self.back_surf, w.pos, w.get_pos_rect())
                else:
                    col = 120
                    for w in d_w:
                        screen.fill((col,col,col), w.get_pos_rect())

            r_l_app = rect_list.append #So .append doesn't get re-evaluated
            for w in d_w: #render dirty widgets, and pass off rect list
                w.dirty = False
                r = None
                if not w.hidden:
                    r = w.on_render(screen)
                if r:
                    r_l_app(r)
                else:
                    r_l_app(w.get_pos_rect())

        return rect_list

    def widgets_from_config(self, cfg):
        for widget in cfg.keys():
            self.widgets_dict[widget] = None
        
        for wid in cfg.keys():
            # Build condition for z order.
            z_w = None
            for z in self.widget_z.keys():
                if wid in self.widget_z[z].keys():
                    z_w = self.widget_z[z][wid]

            #check if the widget already exists in widget_d
            if wid in self.widget_d.keys():
                nw = self.widget_d[wid]
            #Check if in overlappers
            elif wid in self.overlappers.keys():
                nw = self.overlappers[wid]
            #Check for z-bound widgets
            elif z_w is not None:
                nw = z_w

            #If neither, make a new widget
            else:
                nw = self.create_widget(cfg, wid)

            for para in cfg[wid].keys():
                #test for actions
                if (para.startswith("on")) and ((para[3:] + "_action") in nw.__dict__.keys()):
                    self.set_actions(cfg[wid], para, nw)
                #Test for data refs v2, dict style
                elif para == 'refs': 
                    self.set_refs(cfg, wid, nw)
                #test for attributes and other dicts
                elif para in nw.__dict__.keys():
                    if isinstance(nw.__dict__[para], dict):
                        self.update_dict(cfg[wid], nw.__dict__, para)
                    else:
                        nw.__dict__[para] = cfg[wid][para]

            nw.refresh() # refresh the widget!
            nw.link_refs_to_functions()
            # Add to a dict!
            if isinstance(nw.layer, int):
                if nw.layer not in self.widget_z.keys():
                    self.widget_z[nw.layer] = {}
                self.widget_z[nw.layer][wid] = nw

            elif nw.overlap or (wid in self.overlappers.keys()):
                self.overlappers[wid] = nw
            else:
                self.widget_d[wid] = nw
            # For references...
            self.widgets_dict[nw.name] = nw
            self.action_widgets.append(nw)

    def build_widget_list(self):
        for w in self.widget_d.keys():
            self.widgets.append(self.widget_d[w])

    def append_layers(self):
        sk = sorted(self.widget_z)
        for key in sk:
            for w in self.widget_z[key].keys():
                self.widgets.append(self.widget_z[key][w])

    def append_overlappers(self):
        for w in self.overlappers.keys():
            self.widgets.append(self.overlappers[w])
        self.overlappers = {}

    def create_widget(self, cfg, wid):
        nw = None
        args = ""
        if "type" in cfg[wid].keys(): #Make widget with type.
            s = "nw = " + cfg[wid]["type"] + "(self.mode.cfg)"
            exec(s)
        else: #Otherwise, default to button
            s = "nw = Button(self.mode.cfg)"
            exec(s)
        nw.name = wid
        return nw

    def get_ref_to_source(self,cfg,src):
        if not isinstance(cfg, dict):
            return src, cfg
        match = (set(cfg) & set(src)).pop()
        if isinstance(cfg[match], dict):
            return self.get_ref_to_source(cfg[match], src[match])
        else:
            if match in src.keys():
                return (src[match], cfg[match])

    def set_refs(self, cfg, wid, nw):
        for key in cfg[wid]['refs'].keys():
            if 'shared_data' in cfg[wid]['refs'][key]:
                path = self.mode.shared_data.shared_data
                ref_pair = path, cfg[wid]['refs'][key]['shared_data']
            else:
                ref_pair = self.get_ref_to_source(cfg[wid]['refs'][key], self.mch.data)
            if key not in nw.refs.keys():
                nw.refs[key] = {}
                nw.refs[key]['copy'] = None
            nw.refs[key]['path'], nw.refs[key]['ref'] = ref_pair

    def set_actions(self, cfg, para, nw):
        for act in cfg[para]:
            if act in self.mode.callbacks.keys():
                append = None
                exec("append = nw." + para[3:] + "_action.append")
                append(act)
            else:
                fn = ""
                bp = act.find("(")
                func_name = act[:bp]
                args = act[bp:]
                
                if func_name.startswith("shared_data."):
                    fn = "self." + func_name
                elif func_name in dir(self.mch):
                    fn = "self.machine." + func_name
                elif func_name in dir(self.mode):
                    fn = "self." + func_name
                elif func_name[:func_name.find('.')] in self.widgets_dict.keys():
                    widget_name = func_name[:func_name.find('.')]
                    widget_func = func_name[func_name.find('.')+1:]
                    fn = "self.current_view.widgets_dict['" + widget_name + "']." + widget_func
                if fn:
                    args = self.replace_dynamic_args(nw.name, args)
                    ref = fn + args
                    append = None
                    exec("append = nw." + para[3:] + "_action.append")
                    append(ref)
                else:
                    print "No function called " + func_name + " exists!"
                    print "Check modes ->",self.mode.name, "-> views ->", self.name, "-> layout ->", nw.name
    
    def update_dict(self, cfg, wid, srckey):
        for key in cfg[srckey].keys():
            cond1 = isinstance(cfg[srckey][key], dict)
            if key in wid[srckey]:
                cond2 = isinstance(wid[srckey][key], dict)
                if cond1 and cond2:
                    self.update_dict(cfg[srckey], wid[srckey], key)
                elif not cond1 and not cond2:
                    wid[srckey][key] = cfg[srckey][key]
            elif cond1:
                wid[srckey][key] = {}
                self.update_dict(cfg[srckey], wid[srckey], key)
            else:
                wid[srckey][key] = cfg[srckey][key]
        
    # Delete widgets from "delete_widgets" list in the view def (cfg)
    def delete_widgets(self):
        cfg = self.mode.cfg["modes"][self.mode.name]["views"][self.name]
        if "delete_widgets" in cfg.keys():
            for d in cfg["delete_widgets"]:
                if d in self.widget_d.keys():
                    del self.widget_d[d]
                elif d in self.overlappers.keys():
                    del self.overlappers[d]

    def cull_not_included_widgets(self):
        cfg = self.mode.cfg['modes'][self.mode.name]['views'][self.name]
        if 'include_widgets' in cfg.keys():
            inc = cfg['include_widgets']
            # All mode widgets are now included.
            # Now just cull the ones that aren't in the include list.
            for w in self.widget_d.keys():
                if w not in inc:
                    del self.widget_d[w]
            for w in self.overlappers.keys():
                if w not in inc:
                    del self.overlappers[w]
            for z in self.widget_z.keys():
                for w in self.widget_z[z].keys():
                    if w not in inc:
                        del self.widget_z[z][w]
                        
    def bind_widget_keys(self):
        # Check through the widget dict
        for w in self.widgets:
            kb = w.key_bind
            if kb and w.click_action:
                # Convert to digit
                if isinstance(kb, basestring) and kb.isdigit():
                    kb = int(kb)
                    
                # Check if number
                if isinstance(kb, int):
                    if kb <= 9 and kb >= 0:
                        kb = ord(str(kb)) # Convert to ascii code.
                
                elif isinstance(kb, basestring):
                    if len(kb) == 1:
                        kb = ord(kb)
                
                if kb not in self.widget_key_binds.keys():
                    # Make a list, if it doesn't exist
                    self.widget_key_binds[kb] = []
                self.widget_key_binds[kb].append(w)
                
    def load_background(self, bg):
        if bg:
            self.back_surf = pygame.image.load(bg).convert()
    
    def build_groups(self):
        for w in self.widgets:
            group = w.group
            if group is not None:
                if group not in self.widget_groups.keys():
                    self.widget_groups[group] = {}
                self.widget_groups[group][w.name] = w
                
    def replace_dynamic_args(self, w_name, args):
        # Replace all the dynamic arguments with hooks to the actual data
        w_str = "self.current_view.widgets_dict['" + w_name + "']."
        replace_with = [("m_x","m_perc[0]"), ("m_y", "m_perc[1]"),
                        ("w_x", "output[0]"), ("w_y", "output[1]")]
        for rep in replace_with:
            args = args.replace(rep[0], w_str + rep[1])
        
        return args
        
    def change_title(self):
        modecfg = self.mode.cfg['modes'][self.mode.name]
        if 'title' in modecfg.keys():
            title = modecfg['title']
        else:
            title = self.mode.cfg['globals']['default_title']
            
        if 'title' in modecfg['views'][self.name].keys():
            title += " - " + modecfg['views'][self.name]['title']
        pygame.display.set_caption(title)
            
