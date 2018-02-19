# This should just contain a bunch of colour related helpers.
import math
    
def RGB_to_HSV(colour):
    r = colour[0] / 255.0
    g = colour[1] / 255.0
    b = colour[2] / 255.0
    
    c_max = max(r,g,b)
    c_min = min(r,g,b)
    
    delta = c_max - c_min
    
    # Hue
    if r == c_max:
        h = 60 * ((( g - b) / delta ) % 6)
    elif g == c_max:
        h = 60 * (((b - r) / delta) + 2)
    elif b == c_max:
        h = 60 * (((r - g) / delta) + 4)
    # Saturation
    if c_max != 0:
        s = delta / c_max
    else:
        s = 0
    # Value
    v = c_max
    s *= 100
    v *= 100
    return [h,s,v]
        
def HSV_to_RGB(colour):
    h, s, v = colour
    s /= 100
    v /= 100
    if s == 0:
        r = g = b = v
        return [r,g,b]
    c = v * s
    x = c * (1.0 - abs(((h / 60.0) % 2.0) - 1.0))
    m = v - c
    
    if 0 <= h < 60:
        r,g,b = c,x,0
    elif 60 <= h < 120:
        r,g,b = x,c,0
    elif 120 <= h < 180:
        r,g,b = 0,c,x
    elif 180 <= h < 240:
        r,g,b = 0,x,c
    elif 240 <= h < 300:
        r,g,b = x,0,c
    elif 300 <= h < 360:
        r,g,b = c,0,x
    
    rgb = map(lambda x : int((x + m) * 255), [r,g,b])
    return rgb
    
def set_component(col, num, comp):
    hsv = RGB_to_HSV(col)
    hsv[comp] = num
    return HSV_to_RGB(hsv)
    
# Functions for use outside.    

def set_hue(col, hue):
    return set_component(col, hue, 0)
    
def set_saturation(col, sat):
    # Done separately because otherwise you get random colours.
    hsv = RGB_to_HSV(col)
    if hsv[1] == 0:
        return HSV_to_RGB(hsv)
    else:
        hsv[1] == sat
        return HSV_to_RGB(hsv)
    
def set_value(col, val):
    return set_component(col, val, 2)
    
def HSV_alter(op, rgb, comp, val):
    # Convert RGB to HSV
    hsv = RGB_to_HSV(rgb)
    # Check component
    if isinstance(comp, basestring):
        trn = {"h":0, "s":1, "v":2}
        if comp in trn.keys():
            comp = trn[comp]
            
    # Operate
    if op == "add":
        hsv[comp] += val
    elif op == "sub" or op == "subtract":
        hsv[comp] -= val
    elif op == "mult" or op == "multiply":
        hsv[comp] *= val
    elif op == "div" or op == "divide":
        hsv[comp] /= val
        
    return HSV_to_RGB(hsv)
