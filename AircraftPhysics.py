import math,random
import pygame
from pygame.math import Vector2 as V
from Aviation import AIRCRAFT
def direction(a):return V(math.cos(math.radians(a)),math.sin(math.radians(a)))
def bearing(v):return math.degrees(math.atan2(v.y,v.x))
def difference(a,b):return (a-b+180)%360-180
class Plane:
    def __init__(self,ident,team,pos,choices=None):
        self.bank=0.;self.sweep=0.;self.ident=ident;self.stats=AIRCRAFT[ident];self.team=team;self.p=V(pos);self.a=-40 if team==0 else 140;self.throttle=.72;self.speed=self.stats['speed']*.72
        self.modules={'pilot':2,'engine':2,'left_wing':2,'right_wing':2};self.dead=False;self.cd=0;self.mcd=0;self.bcd=0;self.rcd=0;self.cdc=0;self.counter=0
        self.ammo=self.stats['ammo'];self.missiles=self.stats['missiles'];self.bombs=self.stats['bomb_count'];self.rockets=self.stats['rocket_count'];self.flares=30 if self.stats['countermeasures'] else 0
        choices=choices or {};self.belt=max(0,min(len(self.stats['belts'])-1,choices.get('belt',0)));self.missile=max(0,min(len(self.stats['missile_types'])-1,choices.get('missile',0)));self.target=None;self.repair=0;self.focus='搜索'
        from AircraftLoadouts import install_plane
        install_plane(self,choices)
        from LandingDevices import prepare
        prepare(self)
    def hit_polygons(self):
        from AircraftModels import polygons
        return [[self.p+v.rotate(self.a) for v in shape] for _,shape in polygons(self.stats,8,getattr(self,'bank',0),getattr(self,'sweep',0))]
    def hit_polygon(self):
        # Backward-compatible envelope; impacts use hit_polygons instead.
        from AircraftModels import polygons
        points=[v for _,shape in polygons(self.stats,8,getattr(self,'bank',0),getattr(self,'sweep',0)) for v in shape]
        points=sorted(set((v.x,v.y) for v in points))
        def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        lower=[];upper=[]
        for point in points:
            while len(lower)>=2 and cross(lower[-2],lower[-1],point)<=0:lower.pop()
            lower.append(point)
        for point in reversed(points):
            while len(upper)>=2 and cross(upper[-2],upper[-1],point)<=0:upper.pop()
            upper.append(point)
        return [self.p+V(v).rotate(self.a) for v in lower[:-1]+upper[:-1]]
    def damage(self,point,strong=False):
        q=(V(point)-self.p).rotate(-self.a)
        module=('left_wing' if q.y<0 else 'right_wing') if abs(q.y)>self.stats['length']*8*.10 else 'engine' if q.x<0 else 'pilot'
        self.modules[module]=max(0,self.modules[module]-(2 if strong else 1))
        if strong:
            other=random.choice(('engine','left_wing','right_wing'));self.modules[other]=max(0,self.modules[other]-1)
        self.dead=self.modules['pilot']==0 or self.modules['left_wing']==self.modules['right_wing']==0 or (self.modules['engine']==0 and min(self.modules['left_wing'],self.modules['right_wing'])==0)
        return self.dead

