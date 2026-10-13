"""Direct WGL frame presentation, visible to GPU frame capture and FPS tools.
The scene remains pygame-rendered; one texture is uploaded without a pixel copy.
"""
import ctypes as C,pygame
_gl=None
_texture=None
_size=None
INFO={}

def initialize():
    global _gl,_texture,_size,INFO
    _gl=C.WinDLL('opengl32.dll')
    signatures={
        'glGetString':(C.c_char_p,[C.c_uint]),'glGenTextures':(None,[C.c_int,C.POINTER(C.c_uint)]),
        'glBindTexture':(None,[C.c_uint,C.c_uint]),'glTexParameteri':(None,[C.c_uint,C.c_uint,C.c_int]),
        'glTexImage2D':(None,[C.c_uint,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,C.c_uint,C.c_uint,C.c_void_p]),
        'glTexSubImage2D':(None,[C.c_uint,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,C.c_uint,C.c_uint,C.c_void_p]),
        'glViewport':(None,[C.c_int]*4),'glMatrixMode':(None,[C.c_uint]),'glLoadIdentity':(None,[]),
        'glOrtho':(None,[C.c_double]*6),'glEnable':(None,[C.c_uint]),'glDisable':(None,[C.c_uint]),
        'glClearColor':(None,[C.c_float]*4),'glClear':(None,[C.c_uint]),'glBegin':(None,[C.c_uint]),
        'glEnd':(None,[]),'glTexCoord2f':(None,[C.c_float]*2),'glVertex2f':(None,[C.c_float]*2),
        'glPixelStorei':(None,[C.c_uint,C.c_int]),
        'glReadPixels':(None,[C.c_int,C.c_int,C.c_int,C.c_int,C.c_uint,C.c_uint,C.c_void_p]),
        'glGetError':(C.c_uint,[])}
    for name,(restype,args) in signatures.items():
        f=getattr(_gl,name);f.restype=restype;f.argtypes=args
    INFO={name:(_gl.glGetString(key) or b'').decode(errors='replace') for name,key in (('vendor',0x1F00),('renderer',0x1F01),('version',0x1F02))}
    if not INFO['renderer'] or 'GDI Generic' in INFO['renderer']:raise pygame.error('No hardware OpenGL context')
    _texture=C.c_uint();_gl.glGenTextures(1,C.byref(_texture));_gl.glBindTexture(0x0DE1,_texture)
    _gl.glTexParameteri(0x0DE1,0x2801,0x2600);_gl.glTexParameteri(0x0DE1,0x2800,0x2600)
    _gl.glDisable(0x0B71);_gl.glDisable(0x0BE2);_gl.glEnable(0x0DE1);_size=None

def present(canvas,check=False):
    global _size
    width,height=pygame.display.get_window_size();cw,ch=canvas.get_size()
    _gl.glViewport(0,0,width,height);_gl.glMatrixMode(0x1701);_gl.glLoadIdentity();_gl.glOrtho(0,width,height,0,-1,1)
    _gl.glMatrixMode(0x1700);_gl.glLoadIdentity();_gl.glClearColor(0,0,0,1);_gl.glClear(0x4000)
    _gl.glBindTexture(0x0DE1,_texture);_gl.glPixelStorei(0x0CF5,4)
    if _size!=(cw,ch):
        _gl.glTexImage2D(0x0DE1,0,0x1908,cw,ch,0,0x80E1,0x1401,None);_size=(cw,ch)
    # A surface view pins the pixels for the duration of the upload. BGRX alpha
    # is immaterial with blending disabled. No tobytes allocation every frame.
    assert canvas.get_bytesize()==4 and canvas.get_pitch()==cw*4
    pixels=canvas.get_buffer();array=(C.c_ubyte*(canvas.get_pitch()*ch)).from_buffer(pixels)
    _gl.glTexSubImage2D(0x0DE1,0,0,0,cw,ch,0x80E1,0x1401,C.addressof(array))
    del array,pixels
    x=(width-cw)//2;y=(height-ch)//2
    _gl.glBegin(7)
    for u,v,px,py in ((0,0,x,y),(1,0,x+cw,y),(1,1,x+cw,y+ch),(0,1,x,y+ch)):
        _gl.glTexCoord2f(u,v);_gl.glVertex2f(px,py)
    _gl.glEnd()
    if check:
        pixel=(C.c_ubyte*4)();_gl.glReadPixels(width//2,height//2,1,1,0x1908,0x1401,pixel)
        assert tuple(pixel[:3])==(255,220,80),tuple(pixel)
        assert _gl.glGetError()==0
    # pygame calls SDL_GL_SwapWindow -> WGL SwapBuffers on Windows, supplying
    # a real frame boundary to NVIDIA's external overlay rather than a fake FPS.
    pygame.display.flip()
