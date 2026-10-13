import math
import pygame
from pygame.math import Vector2 as V
MODEL_SCALE=.56

def rect_polygon(rect,p=(0,0),angle=0):
    origin=V(p)
    return [origin+V(x,y).rotate(angle) for x,y in ((rect.left,rect.top),(rect.right,rect.top),(rect.right,rect.bottom),(rect.left,rect.bottom))]
def polygons_overlap(a,b):
    for poly in (a,b):
        for i in range(len(poly)):
            edge=poly[(i+1)%len(poly)]-poly[i];axis=V(-edge.y,edge.x)
            if axis.length_squared()<1e-12:continue
            pa=[p.dot(axis) for p in a];pb=[p.dot(axis) for p in b]
            if max(pa)<=min(pb)+1e-6 or max(pb)<=min(pa)+1e-6:return False
    return True

def segment_polygon(a,b,poly):
    a,b=V(a),V(b);delta=b-a;hits=[]
    area=sum(poly[i].cross(poly[(i+1)%len(poly)]) for i in range(len(poly)));orientation=1 if area>=0 else -1
    inside=True
    for i,p in enumerate(poly):
        edge=poly[(i+1)%len(poly)]-p
        if edge.cross(a-p)*orientation<-.001:inside=False
        denom=delta.cross(edge)
        if abs(denom)<1e-10:continue
        t=(p-a).cross(edge)/denom;u=(p-a).cross(delta)/denom
        if -.00001<=t<=1.00001 and -.00001<=u<=1.00001:
            normal=V(edge.y,-edge.x)*orientation
            if normal.length_squared():normal=normal.normalize()
            hits.append((max(0,t),a+delta*t,normal))
    if inside:
        normal=-delta.normalize() if delta.length_squared() else V(1,0)
        return (0.,a,normal)
    return min(hits,key=lambda hit:hit[0]) if hits else None

def geometry(spec,base_modules):
    if not spec:
        body=pygame.FRect(-30,-18,60,36);parts=[('body',pygame.FRect(-30,-27,60,54))]
        return body,parts,{k:pygame.FRect(r) for k,r in base_modules.items()},pygame.FRect(24,-5,35,10)
    length,width,kind,offset,radius,gun=spec['model'];scale=MODEL_SCALE
    body=pygame.FRect((-length+3)*scale,-width*scale,(length*2-6)*scale,width*2*scale)
    parts=[('body',body)]
    for side,key in ((-1,'left_track'),(1,'right_track')):
        if spec.get('wheel'):
            for x in (-length*.75,-length*.25,length*.25,length*.75):parts.append((key,pygame.FRect((x-7)*scale,(side*(width+1)-4)*scale,14*scale,8*scale)))
        else:parts.append((key,pygame.FRect(-length*scale,(side*(width+1)-4)*scale,length*2*scale,8*scale)))
    modules={};sx=body.width/60;sy=body.height/36
    for key,(x,y,w,h) in base_modules.items():modules[key]=pygame.FRect(x*sx,y*sy,w*sx,h*sy)
    for key in ('left_track','right_track'):
        pieces=[rect for name,rect in parts if name==key];modules[key]=pieces[0].unionall(pieces[1:])
    for key,(x,y,w,h) in {'gunner':(.05,-.65,.38,.34),'commander':(-.6,-.5,.34,.34),'loader':(.08,.27,.34,.34),'breech':(.2,-.2,.72,.4),'ring':(-.5,-.45,1.,.9)}.items():
        modules[key]=pygame.FRect((offset+x*radius)*scale,y*radius*scale,w*radius*scale,h*radius*scale)
    barrel_start=(offset+12)*scale;barrel_end=gun*scale;barrel_half=(2 if spec.get('barrels',1)==1 else (spec.get('barrels',1)-1)*3.5+1.2)*scale
    barrel=pygame.FRect(barrel_start,-barrel_half,max(.1,barrel_end-barrel_start),barrel_half*2)
    if spec.get('weapon')=='sam':barrel=pygame.FRect(0,0,0,0)
    modules['barrel']=barrel
    return body,parts,modules,barrel

def barrel_parts(spec):
    if spec.get('weapon')=='sam':return []
    _,_,_,offset,_,gun=spec['model'];count=spec.get('barrels',1);half=2 if count==1 else 1.2
    return [pygame.FRect((offset+12)*MODEL_SCALE,((i-(count-1)/2)*7-half)*MODEL_SCALE,(gun-offset-12)*MODEL_SCALE,half*2*MODEL_SCALE) for i in range(count)]
