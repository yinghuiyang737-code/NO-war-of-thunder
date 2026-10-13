"""Native pixel battle viewport and centered, unscaled menu."""
import pygame
_native_pos=pygame.mouse.get_pos
_native_rel=pygame.mouse.get_rel
LOGICAL=(1280,820)

def viewport(size,logical=LOGICAL):
    rect=pygame.Rect((0,0),logical);rect.center=(size[0]//2,size[1]//2);return rect

def mouse_point(point,size,logical=LOGICAL):
    rect=viewport(size,logical);return round(point[0]-rect.x),round(point[1]-rect.y)

CANVAS=LOGICAL
def logical_mouse():return mouse_point(_native_pos(),pygame.display.get_surface().get_size(),CANVAS)
def logical_rel():return _native_rel()
def event(value):
    if value.type in (pygame.MOUSEMOTION,pygame.MOUSEBUTTONDOWN,pygame.MOUSEBUTTONUP):
        data=dict(value.dict)
        if 'pos' in data:data['pos']=mouse_point(data['pos'],pygame.display.get_surface().get_size(),CANVAS)
        return pygame.event.Event(value.type,data)
    return value

def blit_scaled(canvas,target):
    rect=viewport(target.get_size(),canvas.get_size());target.fill((0,0,0));target.blit(canvas,rect);return rect

def present(canvas):
    from NvidiaDisplay import BACKEND
    if BACKEND=='opengl':
        from NativeOpenGL import present as gl_present
        gl_present(canvas);return
    blit_scaled(canvas,pygame.display.get_surface());pygame.display.flip()

def select(canvas):
    global CANVAS
    CANVAS=canvas.get_size()

def preferred_size(desktop,logical=(1280,820)):
    ratio=min(1.25,max(.5,(desktop[0]-70)/logical[0]),max(.5,(desktop[1]-90)/logical[1]))
    return round(logical[0]*ratio),round(logical[1]*ratio)

def create(logical,test=False):
    if test:return pygame.display.set_mode(logical)
    desktop=pygame.display.get_desktop_sizes()[0]
    from NvidiaDisplay import set_mode
    set_mode(preferred_size(desktop,logical))
    pygame.mouse.get_pos=logical_mouse;pygame.mouse.get_rel=logical_rel
    return pygame.Surface(logical).convert()

def fit(surface,width):
    width=max(1,int(width))
    if surface.get_width()<=width:return surface
    return pygame.transform.smoothscale(surface,(width,max(10,round(surface.get_height()*width/surface.get_width()))))
