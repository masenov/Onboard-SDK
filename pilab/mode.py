from view import View

class Shared_Data(object):
    
    """This class provides a modal data object that can be defined in the
    mode's configuration file.  It also provides a few standard ways
    of altering the data.  This is for when the mode or its views need
    some data that the machine isn't concerned with. Both functions
    and data for refs are accessed via "shared_data.".
    """
    
    def __init__(self, cfg):
        self.shared_data = cfg
        
    def increment(self, data, inc):
        """ A simple increment interface:
        If min/max aren't defined, it grabs them from the data store.
        If they aren't defined there, there are no limits.
        """
        sd = self.shared_data[data]
        
        minimum = sd['min']
        maximum = sd['max']
        
        sd['val'] += inc
        if sd['val'] > maximum:
            sd['val'] = maximum
        elif sd['val'] < minimum:
            sd['val'] = minimum
        
    def set_value(self, data, value):
        """ Set value(s) with no confines"""
        sd = self.shared_data
        if isinstance(sd[data], dict):
            sd[data]['val'] = value
        else:
            sd[data] = value
            
    def set_values(self, data_list, value):
        """ Set all data in the data_list to value """
        sd = self.shared_data
        for data in data_list:
            sd[data] = value

    def toggle(self, data):
        """ Toggle a bool """
        sd = self.shared_data
        sd[data] = not sd[data]
        
    def to_console(self, data):
        print self.shared_data[data]

class Mode(object):
    def __init__(self, name, cfg):
        self.name = name
        self.cfg = cfg
        if 'shared_data' in cfg['modes'][self.name].keys():
            self.shared_data = Shared_Data(cfg['modes'][self.name]['shared_data'])
        mode_mch = self.cfg["modes"][self.name]["machine"]
        try:
            self.machine = self.cfg["globals"]["machines"][mode_mch]()
        except(TypeError):
            self.machine = self.cfg["globals"]["machines"][mode_mch](name, cfg)
            
        self.callbacks = {}
        self.current_view = None
        self.views = {}

        self.create_callbacks()
        self.create_views()

        nk = self.cfg["modes"][self.name].keys()
        if "current_view" in nk:
            self.switch_view(self.cfg["modes"][self.name]["current_view"])
        else:
            self.switch_view(self.cfg["modes"][self.name]["views"].keys()[0])

        self.mode_request = None
        

    def handle_action(self, action):
        if action:
            for a in action:
                if a in self.callbacks.keys():
                    for act in self.callbacks[a]:
                        exec(act)
                else:
                    exec(a)

    def switch_view(self, view):
        """ Takes a view name (string) as defined in the mode's
            configuration tree. All of a mode's views are loaded
            up when the mode starts. Switching between views should
            be instant.
        """
        if view in self.views.keys():
            self.current_view = self.views[view]
            self.current_view.dirty = True
            self.current_view.change_title()

    def to_console(self, output):
        """ Prints text to the console. Great for
            debugging views as it can be used as an
            action function. 
        """
        if isinstance(output, list):
            for s in output:
                print str(s) + "\n"
        else:
            print output
            
    def exit(self):
        """ A short cut for "switch_mode('exit')" """
        self.mode_request = "exit"
        
    def handle_key(self, key):
        self.current_view.on_keydown(key)

    def create_callbacks(self):
        """ The view also does something very similar, but
            this function handles callback aliases which
            the view can use. 
        """
        if 'callbacks' in self.cfg['modes'][self.name].keys():
            for cb in self.cfg['modes'][self.name]['callbacks'].keys():
                self.callbacks[cb] = []
                for func in self.cfg['modes'][self.name]['callbacks'][cb]:
                    fn = ""
                    bp = func.find("(")
                    func_name = func[:bp]
                    args = func[bp:]
                    if func_name.startswith("shared_data."):
                        fn = "self." + func_name
                    elif func_name in dir(self.machine):
                        fn = "self.machine." + func_name
                    elif func_name in dir(self):
                        fn = "self." + func_name
                    if fn:
                        ref = fn + args
                        self.callbacks[cb].append(ref)
                    else:
                        print "No function called " + func_name + " exists!"
                        print "Check modes -> " + self.name + " -> callbacks"

    def create_views(self):
        """ The bulk of view creation is all in the view
            object. 
        """
        for view in self.cfg['modes'][self.name]['views'].keys():
            v = View(view, self)
            self.views[view] = v

    def switch_mode(self, mode):
        """ The mode's update function returns a mode
            request string consisting of a mode name. 
            Most of the time this is empty and ignored. 
            Most modes will return "lobby"
        """
        self.mode_request = mode
        
    def reload_views(self, cfg):
        """ Dumps all the view objects and reloads them from
            a (hopefully) new config tree.
            This should always be called after reloading the
            program's cfg object.
        """
        self.cfg = cfg
        cv = self.current_view.name
        self.current_view = None
        self.views.clear()
        self.callbacks.clear()
        self.create_callbacks()
        self.create_views()
        self.switch_view(cv)

    def update(self):
        """ Pretty obviously updates everything... """
        self.machine.update()
        self.current_view.data_update()
        return self.mode_request
