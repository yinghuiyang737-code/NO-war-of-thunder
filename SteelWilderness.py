import os, sys, math, random, heapq
if '--apply-update' in sys.argv:
    from AutoUpdate import run_update_helper
    raise SystemExit(run_update_helper())
TEST='--test' in sys.argv
if TEST or '--exit-check' in sys.argv:
    os.environ['SDL_VIDEODRIVER']='dummy'
    os.environ['SDL_AUDIODRIVER']='dummy'
import pygame
if TEST:pygame.image.save=lambda *args,**kwargs:None
from pygame.math import Vector2 as V
from Garage import Garage, Profile, NATIONS, VEHICLES, CATALOG, combined_br
from VehicleModels import draw_model, turret_points, hull_points
from VehicleGeometry import MODEL_SCALE, geometry, barrel_parts, rect_polygon, polygons_overlap, segment_polygon
from BattleMaps import MAPS, choose_map
from AirDefense import AirDefense
from GroundFlight import GameInput
from AIController import update as update_ai, can_see as ai_can_see, LABELS as AI_LABELS
from GroundEquipment import EQUIPMENT
from VehicleData import default_ammo, guided, chemical, explosive, penetration_at, ammo_name
pygame.init()
W,H=1280,820
MW,MH=9000,7000
VIEW=pygame.Rect(0,68,W,H-110)
BASES={False:V(430,MH-430),True:V(MW-430,430)}
DEPLOY_BASES={False:(BASES[False],V(430,430)),True:(BASES[True],V(MW-430,MH-430))}
TEAM_SIZE=16
WRECK_LIFETIME=45.
DEPLOY_RADIUS=380
BARREL_HIT_CHANCE=.70
RICOCHET_COS=math.cos(math.radians(70))
from WindowLayout import create as create_window,fit as fit_text,event as window_event,present as present_window
screen=create_window((W,H),TEST)
game_input=GameInput()
pygame.display.set_caption('钢铁旷野 | Steel Wilderness')
clock=pygame.time.Clock()
fontname=pygame.font.match_font('microsoftyahei,simhei,segoeui')
fonts={n:pygame.font.Font(fontname,n) for n in (14,16,18,20,24,30,40,62)}
def text(s,p,size=18,color=(230,236,218),center=False,max_width=None):
    from PresentationSettings import translate
    s=translate(s)
    im=fonts[size].render(s,True,color)
    available=(2*min(p[0],W-p[0])-16) if center else W-p[0]-12
    if p[1]>=H-42 and p[0]<W-140:available=min(available,W-300 if center else W-152-p[0])
    if p[0]<50 and 68<=p[1]<=122:available=min(available,990-p[0])
    im=fit_text(im,min(available,max_width) if max_width is not None else available)
    screen.blit(im,im.get_rect(center=p) if center else p)
def direction(a):return V(math.cos(math.radians(a)),math.sin(math.radians(a)))
def angle(v):return math.degrees(math.atan2(v.y,v.x))
def diff(a,b):return (a-b+180)%360-180
def approach(a,b,s):return a+max(-s,min(s,diff(b,a)))
# Local coordinates: +X is the hull front; +Y is the right side.
MODULES={
 'left_track':(-29,-27,58,9), 'right_track':(-29,18,58,9),
 'engine':(-27,-15,16,30), 'transmission':(22,-16,7,32),
 'ammo':(-9,7,18,10), 'ring':(-8,-7,16,14),
 'driver':(13,-13,9,9), 'gunner':(2,-15,9,8),
 'commander':(-9,-15,9,8), 'loader':(12,6,9,9),
 'breech':(1,-5,18,10), 'barrel':(27,-3,27,6)}
LABELS={'left_track':'左履带','right_track':'右履带','engine':'发动机','transmission':'传动',
 'ammo':'弹药架','ring':'炮塔座圈','driver':'驾驶员','gunner':'炮手','commander':'车长','loader':'装填手','breech':'炮闩','barrel':'炮管'}
CREW=('driver','gunner','commander','loader')
MECHANICAL=('left_track','right_track','engine','transmission','ring','breech','barrel')
def module_color(n):return (105,201,155) if n==2 else (242,182,67) if n==1 else (218,69,54)
class Terrain:
    def __init__(self,map_id='wilderness'):
        layout=MAPS[map_id]
        rng=random.Random(layout['seed']);self.obstacles=[];self.trees=[];self.grass=[];self.fallen=[];self.tree_events=[]
        self.ponds=[pygame.Rect(*r) for r in [(620,600,400,230),(2390,1640,400,270),(530,2100,330,200),(3820,830,520,310),(4510,2680,550,350),(2030,3590,430,280),(3580,3860,480,290)]]
        self.ponds.extend([pygame.Rect(6500,1250,550,340),pygame.Rect(7200,4600,630,400),pygame.Rect(2200,5700,500,330)])
        self.roads=[pygame.Rect(0,1270,MW,120),pygame.Rect(1730,0,115,MH),pygame.Rect(0,3120,MW,125),pygame.Rect(4230,0,125,MH),pygame.Rect(0,MH//2-60,MW,120),pygame.Rect(MW//2-60,0,120,MH)]
        if map_id=='three_fronts':
            self.ponds=[pygame.Rect(*r) for r in [(1800,1200,650,380),(6300,5250,650,380),(2600,4300,540,320),(5900,2200,540,320),(700,3400,400,550),(7900,3000,400,550)]]
            self.roads=[pygame.Rect(0,y-65,MW,130) for y in (1500,3500,5500)]+[pygame.Rect(x-60,0,120,MH) for x in (2700,4500,6300)]
        self.city_regions=[]
        if map_id=='urban_front':
            from UrbanMap import prepare
            prepare(self,layout)
        # The light outer band is fordable; only the dark central basin blocks tanks.
        for p in self.ponds:self.obstacles.append((p.inflate(-180,-160),'deep_water'))
        for x,y,w,h in [(1470,430,230,125),(1850,690,140,190),(1200,1780,230,120),(2760,650,190,130),(1940,2210,210,115),(3300,620,220,140),(4470,1570,190,150),(3600,2890,240,120),(4850,3700,210,165),(1250,3750,220,130),(2700,4070,180,150)]:
            if not self.city_regions:self.obstacles.append((pygame.Rect(x,y,w,h),'house'))
        for _ in range(230):
            r=pygame.Rect(rng.randrange(100,MW-100),rng.randrange(100,MH-100),rng.randrange(35,85),rng.randrange(30,65))
            if self.city_regions and any(r.inflate(65,65).colliderect(road) for road in self.roads):continue
            if any(V(r.center).distance_to(base)<DEPLOY_RADIUS+150 for bases in DEPLOY_BASES.values() for base in bases):continue
            if not any(r.inflate(90,90).colliderect(o) for o in self.ponds+[ob for ob,k in self.obstacles]):self.obstacles.append((r,'rock'))
        # Clusters alternate with open fields; clear corridors preserve travel routes.
        self.forest_regions=[(1150,980,560,370),(2800,1100,650,420),(5500,900,750,460),
            (7650,1850,600,490),(920,2950,620,420),(2950,2700,710,450),
            (5600,2600,760,460),(7450,3450,720,500),(1550,4900,720,480),
            (3550,5350,750,480),(5650,4950,750,520),(7350,5900,650,400)]
        if map_id=='three_fronts':self.forest_regions=[(MW-x,MH-y,rx,ry) for x,y,rx,ry in self.forest_regions]
        if self.city_regions:self.forest_regions=[(1100,1400,650,600),(7400,1500,800,700),(1200,5200,700,600),(7600,5600,650,600)]
        occupied=set();solid_obstacles=[r for r,k in self.obstacles if k!='deep_water']
        def add_tree(p):
            if any(region.collidepoint(p) for region in self.city_regions):return
            if any(p.distance_to(base)<DEPLOY_RADIUS+170 for bases in DEPLOY_BASES.values() for base in bases):return
            if any(r.inflate(90,90).collidepoint(p) for r in self.roads):return
            if any(p.distance_to(V(point))<520 for label,point in layout['points']):return
            if any(r.inflate(70,70).collidepoint(p) for r in self.ponds):return
            # Grid spacing prevents impassable walls of tree trunks.
            key=(int(p.x)//42,int(p.y)//42)
            if key in occupied:return
            if any(r.inflate(36,36).collidepoint(p) for r in solid_obstacles):return
            occupied.add(key);self.trees.append((p,rng.randrange(23,40)))
            self.obstacles.append((pygame.Rect(p.x-9,p.y-9,18,18),'tree'))
        for _ in range(600):add_tree(V(rng.randrange(60,MW-60),rng.randrange(60,MH-60)))
        for cx,cy,rx,ry in self.forest_regions:
            for _ in range(240):
                theta=rng.uniform(0,math.tau);radius=math.sqrt(rng.random())
                p=V(cx+math.cos(theta)*rx*radius,cy+math.sin(theta)*ry*radius)
                # A winding opening runs through each woodland.
                if abs(p.y-cy-55*math.sin((p.x-cx)/160))<45:continue
                add_tree(p)
        for _ in range(12000):
            p=V(rng.randrange(MW),rng.randrange(MH))
            if not any(region.collidepoint(p) for region in self.city_regions):self.grass.append((p,rng.randrange(3)))
        self.grass_chunks={}
        for p,c in self.grass:self.grass_chunks.setdefault((int(p.x)//512,int(p.y)//512),[]).append((p,c))
    def nearby_obstacles(self,bounds):
        signature=(id(self.obstacles),len(self.obstacles))
        if getattr(self,'obstacle_signature',None)!=signature:
            self.obstacle_signature=signature;self.obstacle_chunks={}
            for item in self.obstacles:
                r=item[0]
                for x in range(math.floor(r.left/256),math.floor(r.right/256)+1):
                    for y in range(math.floor(r.top/256),math.floor(r.bottom/256)+1):self.obstacle_chunks.setdefault((x,y),[]).append(item)
        seen=set();result=[]
        for x in range(math.floor(bounds.left/256),math.floor(bounds.right/256)+1):
            for y in range(math.floor(bounds.top/256),math.floor(bounds.bottom/256)+1):
                for item in self.obstacle_chunks.get((x,y),()):
                    key=id(item[0])
                    if key not in seen:seen.add(key);result.append(item)
        return result
    def segment_obstacles(self,a,b):
        return self.nearby_obstacles(pygame.FRect(min(a[0],b[0]),min(a[1],b[1]),max(1,abs(a[0]-b[0])),max(1,abs(a[1]-b[1]))))
    def free(self,p,radius=34,trees=True):
        r=pygame.Rect(0,0,radius*2,radius*2);r.center=p
        return pygame.Rect(20,20,MW-40,MH-40).contains(r) and not any(r.colliderect(o) for o,k in self.nearby_obstacles(r) if trees or k!='tree')
    def crush_trees(self,p,a,speed,footprint=None):
        if abs(speed)<.1:return
        poly=[p+V(x,y).rotate(a) for x,y in [(-31,-27),(31,-27),(31,27),(-31,27)]]
        for r,k in self.nearby_obstacles(pygame.FRect(p.x-85,p.y-85,170,170)):
            if k!='tree' or V(r.center).distance_to(p)>85:continue
            if footprint is not None:
                if not any(polygons_overlap(shape,rect_polygon(r)) for shape in footprint):continue
            local=(V(r.center)-p).rotate(-a)
            if footprint is None and not (abs(local.x)<31 and abs(local.y)<27) and not any(r.clipline(poly[i],poly[(i+1)%4]) for i in range(4)):continue
            self.obstacles.remove((r,k))
            for tree in self.trees[:]:
                if tree[0].distance_to(V(r.center))<2:
                    self.trees.remove(tree);self.fallen.append([V(tree[0]),tree[1],a+(180 if speed<0 else 0),0.]);self.tree_events.append(V(tree[0]));break
    def strike_tree(self,a,b,energy=1):
        contacts=[]
        for rect,kind in self.segment_obstacles(a,b):
            if kind=='deep_water':continue
            clip=rect.clipline(a,b)
            if clip:contacts.append((V(clip[0]).distance_squared_to(a),rect,kind,V(clip[0])))
        if not contacts:return None
        _,rect,kind,point=min(contacts,key=lambda q:q[0])
        if kind!='tree':return None
        if not hasattr(self,'tree_damage'):self.tree_damage={}
        key=tuple(rect.center);self.tree_damage[key]=self.tree_damage.get(key,0)+energy
        if self.tree_damage[key]>=4:
            self.obstacles.remove((rect,kind));self.tree_damage.pop(key,None)
            for tree in self.trees[:]:
                if tree[0].distance_to(V(rect.center))<2:
                    delta=V(b)-V(a);angle=math.degrees(math.atan2(delta.y,delta.x))
                    self.trees.remove(tree);self.fallen.append([V(tree[0]),tree[1],angle,0.]);self.tree_events.append(V(tree[0]));break
        return point
    def blast_trees(self,p,radius):
        for tree in self.trees[:]:
            if tree[0].distance_to(p)<radius:self.crush_trees(V(tree[0]),angle(V(tree[0])-V(p)),1)
    def update(self,dt):
        for tree in self.fallen:tree[3]=min(1.,tree[3]+dt*2.2)
    def in_shallow(self,p):
        return any(r.collidepoint(p) for r in self.ponds) and not any(k=='deep_water' and r.collidepoint(p) for r,k in self.obstacles)
    def blocks_shell(self,a,b):return any(k!='deep_water' and r.clipline(a,b) for r,k in self.segment_obstacles(a,b))
    def draw(self,g):
        screen.fill((69,83,48));cam=g.cam
        def rect(r):return r.move(-cam.x,-cam.y)
        for road in self.roads:pygame.draw.rect(screen,(115,102,67),rect(road))
        if self.city_regions:
            from UrbanMap import draw_ground
            draw_ground(self,screen,cam,g.render_view)
        nearby_grass=(item for x in range(int(cam.x)//512,int(cam.x+g.render_view.right)//512+1) for y in range(int(cam.y+g.render_view.top)//512,int(cam.y+g.render_view.bottom)//512+1) for item in self.grass_chunks.get((x,y),()))
        for p,c in nearby_grass:
            q=g.to_screen(p)
            if g.render_view.collidepoint(q):pygame.draw.line(screen,[(83,101,56),(57,72,42),(105,110,61)][c],q,q+V(2,-4),1)
        for p in self.ponds:
            rr=rect(p)
            if not rr.colliderect(g.render_view):continue
            pygame.draw.rect(screen,(112,109,73),rr.inflate(14,14),border_radius=12)
            pygame.draw.rect(screen,(97,151,144),rr,border_radius=8)
            deep=rect(p.inflate(-180,-160))
            pygame.draw.rect(screen,(39,77,93),deep,border_radius=5)
            pygame.draw.rect(screen,(67,112,125),deep,2,border_radius=5)
            for y in range(rr.top+20,rr.bottom,25):
                for x in range(rr.left+18,rr.right-20,55):
                    col=(78,120,133) if deep.collidepoint(x,y) else (137,186,173)
                    pygame.draw.line(screen,col,(x,y),(x+16,y),1)
        for r,k in self.obstacles:
            rr=rect(r)
            if not rr.colliderect(g.render_view) or k in ('tree','deep_water'):continue
            if k=='house':
                pygame.draw.rect(screen,(34,40,30),rr.move(9,11),border_radius=4)
                pygame.draw.rect(screen,(121,101,75),rr,border_radius=4)
                pygame.draw.rect(screen,(172,142,103),rr,3,border_radius=4)
                pygame.draw.line(screen,(80,66,48),(rr.centerx,rr.top),(rr.centerx,rr.bottom),4)
                for y in range(rr.top+12,rr.bottom,20):pygame.draw.line(screen,(98,79,56),(rr.left+3,y),(rr.right-3,y),1)
                if self.city_regions:
                    pygame.draw.rect(screen,(130,136,137),rr,border_radius=2)
                    pygame.draw.rect(screen,(190,193,179),rr,4)
                    pygame.draw.rect(screen,(86,94,96),(rr.x+15,rr.y+15,24,19))
                    pygame.draw.rect(screen,(158,163,156),rr.inflate(-22,-30),2)
            else:
                pygame.draw.ellipse(screen,(39,46,33),rr.move(6,6))
                pygame.draw.ellipse(screen,(112,116,95),rr)
                pygame.draw.ellipse(screen,(145,144,119),rr.inflate(-12,-10),2)
        pygame.draw.rect(screen,(177,170,111),rect(pygame.Rect(20,20,MW-40,MH-40)),4)
        for p,r,a,progress in self.fallen:
            q=g.to_screen(p)
            if not g.render_view.inflate(100,100).collidepoint(q):continue
            tip=q+direction(a)*r*2*progress
            pygame.draw.line(screen,(48,54,31),q+V(3,4),tip+V(3,4),10)
            pygame.draw.line(screen,(111,83,47),q,tip,7)
            for offset in (-8,8):
                branch=tip+direction(a+90)*offset
                pygame.draw.line(screen,(99,76,43),q.lerp(tip,.65),branch,3)
                pygame.draw.circle(screen,(61,85,42),branch,max(5,int(r*(1-.45*progress))))
            pygame.draw.circle(screen,(155,119,67),q,5)
    def canopy(self,g):
        signature=(id(self.trees),len(self.trees))
        if getattr(self,'tree_signature',None)!=signature:
            self.tree_signature=signature;self.tree_chunks={}
            for tree in self.trees:self.tree_chunks.setdefault((int(tree[0].x)//512,int(tree[0].y)//512),[]).append(tree)
        bounds=pygame.FRect(g.cam.x+g.render_view.left-90,g.cam.y+g.render_view.top-90,g.render_view.w+180,g.render_view.h+180)
        nearby=(tree for x in range(math.floor(bounds.left/512),math.floor(bounds.right/512)+1) for y in range(math.floor(bounds.top/512),math.floor(bounds.bottom/512)+1) for tree in self.tree_chunks.get((x,y),()))
        for p,r in nearby:
            q=g.to_screen(p)
            if not g.render_view.inflate(90,90).collidepoint(q):continue
            pygame.draw.circle(screen,(41,51,31),q+V(8,9),r)
            pygame.draw.circle(screen,(43,70,40),q,r)
            pygame.draw.circle(screen,(60,91,46),q+V(-6,-6),int(r*.73))
            pygame.draw.circle(screen,(76,106,53),q+V(-9,-9),int(r*.38))
class Tank:
    def __init__(self,p,enemy=False,elite=False,vehicle=None):
        self.mg_cd=0.;self.belt_cursor=0;self.missile_cd=0.;self.smoke_cd=0.;self.ess_active=False;self.ess_timer=0.;self.smoke_charges=3 if vehicle and VEHICLES[vehicle]['smoke_grenades'] else 0;self.missile_index=next((i for i,a in enumerate(VEHICLES[vehicle]['ammo_options']) if guided(a)),0) if vehicle else 0;self.vehicle_id=vehicle;self.ammo_index=default_ammo(VEHICLES[vehicle]) if vehicle else 0
        self.stats=VEHICLES[vehicle] if vehicle else dict(speed=135,reverse=72,turn=65,reload=1.65,armor=(85,48,36),pen=128,color=(122,172,132))
        self.grenade_cd=0.;self.grenade_count=600 if self.stats.get('grenade') else 0;self.missile_count=self.stats.get('missile_capacity')
        self.aps_charges=self.stats.get('aps_charges',0);self.aps_cd=0.
        self.body_rect,self.collision_parts,self.module_rects,self.barrel_rect=geometry(self.stats if vehicle else None,MODULES)
        self.half_length=max(abs(r.left) for _,r in self.collision_parts)
        self.half_width=max(abs(r.top) for _,r in self.collision_parts)
        self.radius=math.hypot(self.half_length,self.half_width)
        self.p=V(p);self.enemy=enemy;self.elite=elite;self.body=-90;self.aim=-90;self.speed=0
        self.left_speed=0.;self.right_speed=0.;self.angular_speed=0.
        self.modules={k:2 for k in MODULES};self.dead=False;self.reason='';self.cd=0
        self.fire=0;self.fire_tick=0;self.extinguishers=2;self.repair=0;self.replace=0
        self.roam=0;self.change=0;self.stuck=0;self.trail=0
        self.route=[];self.nav_timer=0.;self.backing=0.;self.ai=False
        from AISkill import assign
        assign(self)
        self.ai_focus='drive';self.ai_focus_time=0.;self.ai_attention=0.;self.ai_scan_timer=0.;self.ai_candidates=[];self.ai_air_candidates=[];self.ai_observation={};self.ai_memory={};self.ai_target=None;self.ai_air_target=None;self.ai_lane=random.uniform(-350,350);self.ai_patrol_phase=0;self.ai_recent_hit=0.;self.ai_threat_heading=0.
    def local(self,p):return (V(p)-self.p).rotate(-self.body)
    def world(self,p):return self.p+V(p).rotate(self.body)
    def footprint(self,p=None,a=None):
        p=self.p if p is None else V(p);a=self.body if a is None else a
        if not self.vehicle_id:return [rect_polygon(pygame.FRect(-31,-27,62,54),p,a)]
        polygons=[[p+V(x,y).rotate(a)*MODEL_SCALE for x,y in hull_points(self.stats)] if key=='body' else rect_polygon(rect,p,a) for key,rect in self.collision_parts]
        turret_angle=self.aim+(a-self.body if self.stats['stabilizer']<2 else 0)
        polygons.append([p+V(x,y).rotate(turret_angle)*MODEL_SCALE for x,y in turret_points(self.stats)])
        if self.stats.get('missile'):
            _,_,_,offset,radius,_=self.stats['model']
            for side in (-1,1):polygons.append(rect_polygon(pygame.FRect((offset-12)*MODEL_SCALE,(side*(radius+4)-4)*MODEL_SCALE,30*MODEL_SCALE,8*MODEL_SCALE),p,a))
        return polygons
    def overlaps(self,other,p=None,a=None):
        p=self.p if p is None else V(p)
        if p.distance_squared_to(other.p)>(self.radius+other.radius+2)**2:return False
        return any(polygons_overlap(first,second) for first in self.footprint(p,a) for second in other.footprint())
    def clear_at(self,p,a,terrain,tanks=(),trees=True):
        polygons=self.footprint(p,a)
        if any(not (20<point.x<MW-20 and 20<point.y<MH-20) for poly in polygons for point in poly):return False
        bounds=pygame.FRect(p.x-self.radius,p.y-self.radius,self.radius*2,self.radius*2)
        for rect,kind in terrain.nearby_obstacles(bounds):
            if kind=='deep_water' or (not trees and kind=='tree'):continue
            if bounds.colliderect(rect) and any(polygons_overlap(poly,rect_polygon(rect)) for poly in polygons):return False
        return not any(t is not self and V(p).distance_squared_to(t.p)<(self.radius+t.radius+10)**2 and self.overlaps(t,p,a) for t in tanks)
    def shell_contact(self,a,b):
        if not self.vehicle_id:
            clip=pygame.Rect(-30,-27,60,54).clipline(self.local(a),self.local(b))
            if not clip:return None
            entry=V(clip[0]);side=abs(entry.y)>=25 and abs(entry.x)<29
            normal=V(0,-1 if entry.y<0 else 1) if side else V(1 if entry.x>0 else -1,0)
            point=self.world(entry);return ((point-V(a)).length(),point,normal.rotate(self.body))
        polygons=self.footprint()
        hits=[(*hit,'turret' if i==len(self.collision_parts) else 'hull') for i,poly in enumerate(polygons) if (hit:=segment_polygon(a,b,poly)) is not None]
        return min(hits,key=lambda h:h[0]) if hits else None
    def module_angle(self,key):
        return self.aim if self.vehicle_id and key in ('gunner','commander','loader','breech','ring','barrel') else self.body
    def module_world(self,key):return self.p+V(self.module_rects[key].center).rotate(self.module_angle(key))
    def module_clip(self,key,a,b):
        orientation=self.module_angle(key);clip=self.module_rects[key].clipline((V(a)-self.p).rotate(-orientation),(V(b)-self.p).rotate(-orientation))
        return tuple(self.p+V(point).rotate(orientation) for point in clip) if clip else None
    def muzzle(self):
        distance=self.stats['model'][5]*MODEL_SCALE if self.vehicle_id else 62
        return self.p+direction(self.aim)*(distance+2)
    @property
    def ammo(self):return self.stats["ammo_options"][self.ammo_index] if self.vehicle_id else None
    @property
    def missile_ammo(self):return self.stats['ammo_options'][self.missile_index] if self.vehicle_id and self.stats.get('missile') else None
    def crew_alive(self):return sum(self.modules[k]>0 for k in CREW)
    def can_fire(self):return not self.dead and all(self.modules[k]>0 for k in ('gunner','breech','barrel'))
    def drive(self,throttle,steer,dt,terrain,tanks=()):
        if self.dead:return
        previous_body=self.body
        ready=all(self.modules[k]>0 for k in ('engine','transmission','driver'))
        factor=.55 if any(self.modules[k]==1 for k in ('engine','transmission')) else 1
        if any(r.collidepoint(self.p) for r in terrain.ponds):factor*=.3 if EQUIPMENT.get(self.vehicle_id,{}).get('amphibious') else .55
        # Differential drive: each track has its own powered velocity.
        # Steering reverses when actually backing up, including reverse coasting.
        reversing=self.speed<-2 or (abs(self.speed)<=2 and throttle<0)
        reverse_sign=-1 if reversing else 1
        base=throttle*(self.stats["speed"] if throttle>=0 else self.stats["reverse"])*factor
        track_spacing=(abs(self.module_rects["right_track"].centery-self.module_rects["left_track"].centery) if self.vehicle_id else 54)
        turn=steer*reverse_sign*math.radians(self.stats["turn"])*(track_spacing/2)*factor
        if self.vehicle_id and not self.stats["dual"]:
            turn*=.66
            base*=1-.28*abs(steer)
            if throttle:turn=max(-abs(base),min(abs(base),turn))
        if self.vehicle_id and self.stats.get('wheel'):
            turn*=min(1,abs(self.speed)/max(1,self.stats['speed']*.25))
        left=base+turn;right=base-turn
        if self.vehicle_id and not self.stats['dual'] and not throttle:
            left=max(0,left);right=max(0,right)
        single=(self.modules['left_track']>0)!=(self.modules['right_track']>0)
        drag=.65 if single else 1.
        goals={}
        for attr,k,target in (('left_speed','left_track',left),('right_speed','right_track',right)):
            if not ready or self.modules[k]==0:setattr(self,attr,0.);continue
            target*=drag*(.55 if self.modules[k]==1 else 1.)
            target=max(-self.stats["speed"]*factor,min(self.stats["speed"]*factor,target))
            goals[attr]=target
        from GroundHandling import advance
        advance(self,goals,factor,dt)
        self.speed=(self.left_speed+self.right_speed)/2
        self.angular_speed=math.degrees((self.left_speed-self.right_speed)/track_spacing)
        def clear(p,a):return self.clear_at(p,a,terrain,tanks)
        # Substeps keep turning and translation coupled on a single intact track.
        distance=self.speed*dt
        rotation=self.angular_speed*dt
        steps=max(1,math.ceil(abs(distance)/7),math.ceil(abs(rotation)/3))
        for _ in range(steps):
            old_angle=self.body
            self.body+=rotation/steps
            if not clear(self.p,self.body):self.body=old_angle
            nextp=self.p+direction(self.body)*distance/steps
            terrain.crush_trees(nextp,self.body,self.speed,self.footprint(nextp,self.body))
            if clear(nextp,self.body):self.p=nextp;self.stuck=max(0,self.stuck-dt/steps)
            else:
                self.speed=0;self.left_speed=0.;self.right_speed=0.;self.angular_speed=0.
                self.stuck+=dt;break
        if self.vehicle_id and self.stats["stabilizer"]<2:self.aim+=self.body-previous_body
    def aim_at(self,target,dt,terrain=None,tanks=()):
        if self.modules['ring'] and self.modules['gunner']:
            rate=self.stats.get('aim_response_slew',self.stats.get('turret_slew',78))*(.4 if self.modules['ring']==1 else 1)
            desired=angle(V(target)-self.p)
            if self.vehicle_id and self.stats['model'][2]=='casemate':desired=self.body+max(-10,min(10,diff(desired,self.body)))
            previous=self.aim;self.aim=approach(self.aim,desired,rate*dt)
            if self.vehicle_id and terrain is not None and abs(diff(self.aim,previous))>.001 and not self.clear_at(self.p,self.body,terrain,tanks):self.aim=previous
    def damage_module(self,k,amount=1):
        if self.modules[k]<=0:return
        self.modules[k]=max(0,self.modules[k]-amount)
        if k=='ammo' and self.modules[k]==0:self.dead=True;self.reason='弹药殉爆'
        if self.crew_alive()<2:self.dead=True;self.reason='乘员不足'
    def hit(self,a,b,velocity,travel=0,rng=random,barrel_seen=None,penetration_value=128,ammo=None):
        # Each projectile rolls only once for each tank's barrel, even over many frames.
        if barrel_seen is None:barrel_seen={}
        la,lb=self.local(a),self.local(b)
        contact=self.shell_contact(a,b)
        if contact:self.ai_recent_hit=4.;self.ai_threat_heading=angle(-V(velocity))
        clip=(self.local(contact[1]),) if contact else ()
        barrel=self.barrel_rect if self.vehicle_id else pygame.Rect(24,-5,35,10)
        ca=(V(a)-self.p).rotate(-self.aim);cb=(V(b)-self.p).rotate(-self.aim)
        if self.vehicle_id:
            candidates=[(V(barrel_intersection[0]).distance_to(ca),rect,barrel_intersection) for rect in barrel_parts(self.stats) if (barrel_intersection:=rect.clipline(ca,cb))]
            if candidates:_,barrel,barrel_hit=min(candidates,key=lambda hit:hit[0])
            else:barrel_hit=()
        else:barrel_hit=barrel.clipline(ca,cb)
        barrel_first=barrel_hit and (not clip or V(barrel_hit[0]).distance_to(ca)+.1<V(clip[0]).distance_to(la))
        if barrel_first and self.modules['barrel']>0 and self not in barrel_seen:
            entry_gun=V(barrel_hit[0]);point=self.p+entry_gun.rotate(self.aim)
            gun_dir=V(velocity).normalize().rotate(-self.aim)
            if rng.random()<BARREL_HIT_CHANCE:
                cap=entry_gun.x<=barrel.left+1 or entry_gun.x>=barrel.right-2
                normal=V(-1 if entry_gun.x<barrel.centerx else 1,0) if cap else V(0,-1 if entry_gun.y<0 else 1)
                incidence=abs(gun_dir.dot(normal))
                barrel_seen[self]='hit'
                if incidence<RICOCHET_COS:
                    reflected=V(velocity).reflect(normal.rotate(self.aim))*.65
                    return {'kind':'炮管跳弹','modules':[],'point':point,'line':(self.local(point),self.local(point)+reflected.normalize()*35),'reflect':reflected}
                self.damage_module('barrel',2)
                return {'kind':'炮管命中','modules':['barrel'],'point':point,'line':(self.local(point),self.local(point)+V(velocity).normalize().rotate(-self.body)*14)}
            barrel_seen[self]='miss'
            if not clip:
                return {'kind':'擦过炮管','modules':[],'point':point,'line':(self.local(point),self.local(point)+V(velocity).normalize().rotate(-self.body)*35),'continue':True}
        if not clip:return None
        barrel_missed=barrel_seen.get(self)=='miss'
        entry=V(clip[0]);local_dir=V(velocity).normalize().rotate(-self.body);touched=[]
        for k in ('left_track','right_track'):
            if any(name==k and rect.clipline(la,lb) for name,rect in self.collision_parts) if self.vehicle_id else pygame.Rect(MODULES[k]).clipline(la,lb):self.damage_module(k,2);touched.append(k)
        zone=contact[3] if len(contact)>3 else 'hull'
        surface_angle=self.aim if zone=='turret' else self.body
        normal_local=contact[2].rotate(-surface_angle)
        side=abs(normal_local.y)>.5 if self.vehicle_id else abs(entry.y)>=25 and abs(entry.x)<29
        front=normal_local.x>0 if self.vehicle_id else entry.x>0
        plates=self.stats.get('turret_armor',self.stats['armor']) if zone=='turret' else self.stats['armor']
        armor=(plates[1] if side else plates[0] if front else plates[2])*(1.2 if self.elite and not self.vehicle_id else 1)
        # Layered armour is a reduced 2D representation; base plates remain individually sourced.
        if self.vehicle_id and self.stats.get('composite') and front and not side:
            effective=self.stats.get('effective_front') if zone=='hull' else None
            armor=effective[1 if ammo and chemical(ammo) else 0] if effective else armor*(5 if ammo and chemical(ammo) else 2.8)
        incidence=abs(V(velocity).normalize().dot(contact[2])) if self.vehicle_id else abs(local_dir.y if side else local_dir.x)
        penetration=penetration_at(ammo,travel) if ammo else max(60,penetration_value-travel*.017)
        prefix='擦过炮管 → ' if barrel_missed else ''
        threshold=math.cos(math.radians(80 if ammo and ('APFSDS' in ammo['type'] or chemical(ammo)) else 70))
        if incidence<threshold and not (ammo and ammo['type'].startswith('HE')):
            normal=normal_local if self.vehicle_id else V(0,-1 if entry.y<0 else 1) if side else V(1 if entry.x>0 else -1,0)
            reflected=V(velocity).reflect(normal.rotate(surface_angle))*.65
            return {'kind':prefix+'车体跳弹','modules':touched,'point':self.world(entry),'line':(entry,entry+reflected.normalize().rotate(-self.body)*35),'reflect':reflected}
        from ReactiveArmor import react
        penetration,local_dir,era_armor,era_prefix,rod_broken=react(self,entry,zone,normal_local,front,side,ammo,incidence,penetration,local_dir,rng)
        armor+=era_armor;prefix+=era_prefix
        if penetration<armor/max(.12,incidence):
            fragments=[]
            if ammo and explosive(ammo):
                from CombatEffects import external_spall
                damaged,fragments=external_spall(self,contact[1],contact[2],rng);touched.extend(damaged)
            return {'kind':prefix+'未击穿','modules':list(dict.fromkeys(touched)),'point':self.world(entry),'line':(entry,entry+local_dir*12),'external_fragments':fragments}
        end=entry+local_dir*(max(85,self.radius*2+12) if self.vehicle_id else 85);hits=[]
        for k,r in self.module_rects.items():
            if k in ('left_track','right_track','barrel') or self.modules[k]==0:continue
            intersect=self.module_clip(k,self.world(entry),self.world(end)) if self.vehicle_id else pygame.Rect(r).inflate(5,5).clipline(entry,end)
            if intersect:hits.append(((V(intersect[0]).distance_to(self.world(entry)) if self.vehicle_id else V(intersect[0]).distance_to(entry)),k))
        hits.sort()
        for _,k in hits[:(1 if rod_broken else 4 if ammo and explosive(ammo) else 2 if ammo else 3)]:
            self.damage_module(k,2 if k in CREW or k in ('engine','breech') else 1);touched.append(k)
            if k=='engine' and rng.random()<.55:self.fire=15
        from CombatEffects import spall
        fragments_hit,fragments,burst=spall(self,entry,local_dir,ammo,rng,energy_scale=.55 if rod_broken else 1.)
        touched=list(dict.fromkeys(touched+fragments_hit))
        return {'kind':prefix+(self.reason if self.dead else '击穿车体' if barrel_missed else '击穿'),'modules':touched,'point':self.world(entry),'line':(entry,end),'fragments':fragments,'burst':burst}
    def service(self,dt,repairing=False):
        self.grenade_cd=max(0,self.grenade_cd-dt)
        self.aps_cd=max(0,self.aps_cd-dt)
        self.cd=max(0,self.cd-dt);self.missile_cd=max(0,self.missile_cd-dt);self.smoke_cd=max(0,self.smoke_cd-dt)
        if self.dead:return
        if self.fire>0:
            self.fire-=dt;self.fire_tick+=dt
            if self.fire_tick>=3:
                self.fire_tick=0;self.damage_module('ammo',1)
                if not self.dead:
                    living=[k for k in CREW if self.modules[k]]
                    if living:self.damage_module(living[0],1)
        damaged=[k for k in MECHANICAL if self.modules[k]<2]
        if repairing and max(abs(self.left_speed),abs(self.right_speed))<3 and not self.fire and damaged:
            self.repair+=dt
            if self.repair>=5:self.modules[damaged[0]]=2;self.repair=0
        else:self.repair=0
        if self.crew_alive()>=2 and (not self.modules['driver'] or not self.modules['gunner']):
            self.replace+=dt
            if self.replace>=7:
                donors=[k for k in ('commander','loader') if self.modules[k]]
                if donors:
                    role='driver' if not self.modules['driver'] else 'gunner'
                    self.modules[role]=self.modules[donors[0]];self.modules[donors[0]]=0
                self.replace=0
        else:self.replace=0
    def extinguish(self):
        if self.fire and self.extinguishers>0:self.fire=0;self.fire_tick=0;self.extinguishers-=1
    def draw(self,g,wreck=False):
        q=g.to_screen(self.p)
        if not g.render_view.inflate(100,100).collidepoint(q):return
        col=(205,161,96) if self.elite else (162,87,66) if self.enemy else (92,155,189) if self.ai else self.stats["color"]
        if wreck:col=(54,51,43)
        if not wreck and g.terrain.in_shallow(self.p) and abs(self.speed)>3:
            ripple=pygame.Rect(0,0,82+int(g.time*15)%12,65+int(g.time*15)%10);ripple.center=q
            pygame.draw.ellipse(screen,(162,210,193),ripple,1)
        if self.vehicle_id:
            draw_model(screen,self.stats,q,MODEL_SCALE,self.body,True,self.aim,(55,53,46) if wreck else self.stats['color'])
            if not self.modules['barrel']:pygame.draw.circle(screen,(175,56,37),q+direction(self.aim)*40,4)
            for side,key in ((-1,'left_track'),(1,'right_track')):
                if not self.modules[key]:pygame.draw.line(screen,(165,57,40),q+V(-self.half_length,side*(self.half_width-3)).rotate(self.body),q+V(self.half_length,side*(self.half_width-3)).rotate(self.body),4)
        else:
            surf=pygame.Surface((86,86),pygame.SRCALPHA)
            for x,k in ((16,'left_track'),(58,'right_track')):
                color=(30,32,26) if self.modules[k] else (95,44,30)
                pygame.draw.rect(surf,color,(x,12,12,62),border_radius=3)
                for y in range(16,73,7):pygame.draw.line(surf,(87,84,67),(x+1,y),(x+10,y),2)
            pygame.draw.rect(surf,col,(28,13,30,60),border_radius=6)
            pygame.draw.rect(surf,(62,76,56) if not wreck else (29,29,23),(31,53,24,15),border_radius=2)
            for y in range(55,67,4):pygame.draw.line(surf,(33,41,31),(33,y),(52,y),2)
            pygame.draw.line(surf,(184,187,132),(30,18),(55,18),2)
            rot=pygame.transform.rotate(surf,-self.body-90);screen.blit(rot,rot.get_rect(center=q))
            turret=pygame.Surface((104,104),pygame.SRCALPHA)
            pygame.draw.line(turret,(31,36,28),(52,52),(98,52),9)
            pygame.draw.line(turret,col if self.modules['barrel'] else (111,45,31),(52,52),(97 if self.modules['barrel'] else 79,52),5)
            pygame.draw.rect(turret,col,(37,39,29,26),border_radius=8)
            pygame.draw.circle(turret,(54,69,50) if not wreck else (27,28,22),(47,47),7)
            rot=pygame.transform.rotate(turret,-self.aim);screen.blit(rot,rot.get_rect(center=q))
        if self.fire>0:
            for i in range(5):
                pos=q+V(-17,0).rotate(self.body)+V(random.randrange(-10,10),random.randrange(-12,10))
                pygame.draw.circle(screen,(245,random.randrange(85,180),35),pos,random.randrange(3,8))
        if self.enemy and not wreck:pygame.draw.polygon(screen,(228,119,79),[q+V(-5,-44),q+V(5,-44),q+V(0,-37)])
        if getattr(self,'network_name',None) and not wreck:
            pygame.draw.circle(screen,(142,223,255),q+V(0,-42),4);text(self.network_name,(q.x,q.y-60),14,(174,231,248),True)
        elif self.ai and not self.enemy and not wreck:
            pygame.draw.circle(screen,(142,223,255),q+V(0,-42),4)
            text('友军 · '+__import__('AISkill').label(self.ai_skill)+' · '+(getattr(self,'ai_maneuver',getattr(self,'ai_role',AI_LABELS[self.ai_focus])) if self.ai_focus in ('drive','aim','search') else AI_LABELS[self.ai_focus]),(q.x,q.y-60),14,(174,231,248),True)
from Matchmaking import lineup_br, pool as battle_pool, pick as battle_pick, GroundRoster

class Game:
    def __init__(self,deployment=False,nation=None,lineup=None,start_slot=0,ammo_choices=None,missile_choices=None,map_id=None):
        self.map_id=map_id or ('wilderness' if TEST else choose_map());self.map_layout=MAPS[self.map_id];self.map_name=self.map_layout['name']
        self.ammo_choices=dict(ammo_choices or {});self.missile_choices=dict(missile_choices or {});self.world_size=(MW,MH);self.smokes=[]
        self.country=nation;self.lineup=list(lineup) if lineup else None;self.active_vehicle_slot=start_slot;self.used_slots=set();self.reward_paid=False
        equipped=[v for v in self.lineup if v is not None] if self.lineup else []
        if nation and (nation not in NATIONS or not self.lineup or len(self.lineup) not in (3,8,12) or not equipped or len(set(equipped))!=len(equipped) or any(v not in CATALOG or CATALOG[v]["country"]!=nation for v in equipped)):raise ValueError("Invalid national lineup")
        if self.lineup:
            self.lineup=(self.lineup+[None]*12)[:12]
            if not 0<=start_slot<12 or self.lineup[start_slot] is None:self.active_vehicle_slot=next(i for i,v in enumerate(self.lineup) if v is not None)
            if not deployment:self.used_slots.add(self.active_vehicle_slot)
        self.enemy_country={"cn":"de","ussr":"us","de":"ussr","us":"de","jp":"ussr"}.get(nation)
        self.battle_br=combined_br(self.lineup) if self.lineup else 1.0
        if self.enemy_country and not any(VEHICLES[k]['branch']!=3 for k in battle_pool(VEHICLES,self.enemy_country,self.battle_br)):
            self.enemy_country=max((c for c in NATIONS if c!=nation),key=lambda c:sum(VEHICLES[k]['branch']!=3 for k in battle_pool(VEHICLES,c,self.battle_br)))
        self.ai_ground_selector=GroundRoster(VEHICLES)
        self.terrain=Terrain(self.map_id);self.player=Tank(BASES[False],vehicle=(self.lineup[self.active_vehicle_slot] if self.lineup[self.active_vehicle_slot] in VEHICLES else f'{nation}_1_1') if self.lineup else None);self.enemies=[];self.allies=[];self.wrecks=[];self.bullets=[];self.fx=[];self.tracks=[]
        self.vision="day";self.night_battle=False;self.scope_zoom=1.;self.mg_tracers=[];self.cam=V();self.scope=False;self.zoom=1.;self.scope_focus=V(self.player.p);self.fire_armed=True
        self.wave=0;self.score=0;self.kills=0;self.wait=1.5;self.state='play';self.paused=False
        self.render_view=VIEW.copy();self.time=0;self.messages=[];self.hitview=None;self.xray=False;self.camera()
        self.enemy_queue=[];self.ground_kills=0;self.kill_goal=40
        self.ally_queue=[];self.reserves=(len(equipped)-(0 if deployment else 1)) if self.lineup else (3 if deployment else 2);self.deploy_delay=0.;self.deploy_choice=V(BASES[False]);self.deploy_selected=False;self.deploy_hint=''
        self.nav_grid=None;self.air=AirDefense(self,screen,text,VIEW);self.apply_ammo(self.player)
        if deployment:
            self.state='deploy'
        else:self.spawn_allies(TEAM_SIZE-1)
    def apply_ammo(self,t):
        if t.vehicle_id:
            index=self.ammo_choices.get(t.vehicle_id,default_ammo(t.stats))
            t.ammo_index=index if isinstance(index,int) and 0<=index<len(t.stats['ammo_options']) and not (t.stats['independent_missiles'] and guided(t.stats['ammo_options'][index])) else default_ammo(t.stats)
            selected=self.missile_choices.get(t.vehicle_id,t.missile_index)
            if isinstance(selected,int) and 0<=selected<len(t.stats['ammo_options']) and guided(t.stats['ammo_options'][selected]):t.missile_index=selected
    def switch_ammo(self,step=1):
        t=self.player
        if self.paused or self.state!='play' or not t.vehicle_id or t.dead:return False
        indices=[i for i,a in enumerate(t.stats['ammo_options']) if not (t.stats['independent_missiles'] and guided(a))]
        count=len(indices)
        if count<2:self.say('这辆载具只有一种主武器弹药');return False
        t.ammo_index=indices[(indices.index(t.ammo_index)+step)%count];self.ammo_choices[t.vehicle_id]=t.ammo_index
        t.cd=max(t.cd,t.stats['ammo_reload'])
        if not t.stats['independent_missiles']:self.air.missile_cd=max(self.air.missile_cd,t.cd)
        self.say('换弹：'+ammo_name(t.ammo));return True
    def switch_missile(self):
        t=self.player
        if self.paused or self.state!='play' or t.dead or not t.stats.get('independent_missiles'):return False
        indices=[i for i,a in enumerate(t.stats['ammo_options']) if guided(a)]
        if len(indices)<2:self.say('独立发射器仅配有一种导弹');return False
        t.missile_index=indices[(indices.index(t.missile_index)+1)%len(indices)]
        self.missile_choices[t.vehicle_id]=t.missile_index;t.missile_cd=max(t.missile_cd,t.stats['missile_reload'])
        self.say('导弹换装：'+ammo_name(t.missile_ammo));return True
    def smoke_blocks(self,a,b,thermal=False):
        a=V(a);b=V(b);delta=b-a
        for cloud in self.smokes:
            if thermal and cloud['kind']=='ess':continue
            f=max(0,min(1,(cloud['p']-a).dot(delta)/delta.length_squared())) if delta.length_squared() else 0
            if (a+delta*f).distance_squared_to(cloud['p'])<cloud['radius']**2:return True
        return False
    def visible(self,a,b,thermal=False,radar=False):return not self.terrain.blocks_shell(a,b) and (radar or not self.smoke_blocks(a,b,thermal))
    def add_smoke(self,p,kind):
        self.smokes.append({'p':V(p),'kind':kind,'age':0.,'life':22. if kind=='grenade' else 12.,'radius':25.,'max_radius':110. if kind=='grenade' else 70.})
        self.smokes=self.smokes[-160:]
    def deploy_smoke(self,t=None):
        t=t or self.player
        if self.state!='play' or self.paused or t.dead:return False
        if not t.stats.get('smoke_grenades'):
            if t is self.player:self.say('这辆载具没有烟雾弹发射器')
            return False
        if t.smoke_cd>0 or t.smoke_charges<=0:return False
        t.smoke_charges-=1;t.smoke_cd=8.
        for angle_offset in (-36,-12,12,36):self.add_smoke(t.p+direction(t.aim+angle_offset)*150,'grenade')
        if t is self.player:self.say('烟雾弹已发射 · 剩余 '+str(t.smoke_charges)+' 组')
        return True
    def toggle_ess(self):
        t=self.player
        if self.state!='play' or self.paused or t.dead:return False
        if not t.stats.get('ess'):self.say('这辆载具没有发动机烟幕系统');return False
        if not t.modules['engine']:self.say('发动机损坏，无法产生烟幕');return False
        t.ess_active=not t.ess_active;self.say('发动机烟幕 '+('开启' if t.ess_active else '关闭'));return True
    def update_smoke(self,dt):
        for cloud in self.smokes[:]:
            cloud['age']+=dt;cloud['radius']=min(cloud['max_radius'],25+cloud['age']*55);cloud['p']+=V(3,-1)*dt
            if cloud['age']>=cloud['life']:self.smokes.remove(cloud)
        for t in [self.player]+self.allies+self.enemies:
            if t.dead or not t.modules['engine']:t.ess_active=False
            if t.ess_active:
                t.ess_timer-=dt
                if t.ess_timer<=0:self.add_smoke(t.p-direction(t.body)*(t.half_length+25),'ess');t.ess_timer=.55
    def draw_smoke(self):
        for cloud in self.smokes:
            if self.vision=='thermal' and cloud['kind']=='ess':continue
            q=self.to_screen(cloud['p']);radius=int(cloud['radius'])
            if not self.render_view.inflate(radius*2,radius*2).collidepoint(q):continue
            fade=min(1,cloud['age']/.5,max(0,(cloud['life']-cloud['age'])/4));alpha=int(210*fade)
            image=pygame.Surface((radius*2+8,radius*2+8),pygame.SRCALPHA)
            center=V(radius+4,radius+4)
            for i in range(5):
                p=center+direction(i*72+cloud['age']*9)*radius*.22
                for ring in range(16,0,-1):
                    opacity=int(alpha*(1-ring/17)**1.3)
                    pygame.draw.circle(image,(184,189,181,opacity),p,max(1,int(radius*.73*ring/16)))
            screen.blit(image,q-center)
    def vehicles(self):return ([self.player] if not self.player.dead else [])+self.allies+self.enemies+self.wrecks
    def deployment_valid(self,p,enemy=False,vehicle=None):
        if vehicle:
            candidate=Tank(p,enemy,vehicle=vehicle);candidate.body=angle(BASES[not enemy]-V(p));candidate.aim=candidate.body
            return min(V(p).distance_to(base) for base in DEPLOY_BASES[enemy])<=DEPLOY_RADIUS-candidate.radius-2 and candidate.clear_at(V(p),candidate.body,self.terrain,[t for t in self.vehicles() if t is not self.player or self.player.dead])
        return min(V(p).distance_to(base) for base in DEPLOY_BASES[enemy])<=DEPLOY_RADIUS-44 and self.terrain.free(p,44) and all(V(p).distance_to(t.p)>95 for t in self.vehicles() if t is not self.player or self.player.dead)
    def spawn_position(self,enemy=False,vehicle=None,base=None):
        if base is None:base=random.choice(DEPLOY_BASES[enemy])
        for _ in range(350):
            p=base+direction(random.uniform(0,360))*math.sqrt(random.random())*(DEPLOY_RADIUS-50)
            if self.deployment_valid(p,enemy,vehicle) and (enemy or self.state=='deploy' or self.player.dead or p.distance_to(self.player.p)>100):return p
        for y in range(int(base.y-DEPLOY_RADIUS+50),int(base.y+DEPLOY_RADIUS-49),65):
            for x in range(int(base.x-DEPLOY_RADIUS+50),int(base.x+DEPLOY_RADIUS-49),65):
                p=V(x,y)
                if self.deployment_valid(p,enemy,vehicle) and (enemy or self.state=='deploy' or self.player.dead or p.distance_to(self.player.p)>100):return p
        return None
    def choose_ai_ground(self,enemy=False,previous=None):
        country=self.enemy_country if enemy else self.country
        if country is None or not self.lineup:return None
        active=[t.vehicle_id for t in (self.enemies if enemy else self.allies) if not t.dead]
        queued=self.enemy_queue if enemy else self.ally_queue
        return self.ai_ground_selector.pick(int(enemy),country,self.battle_br,active,queued,previous)
    def spawn_allies(self,count,vehicle=None):
        air=sum(1 for q in self.air.planes if not q['dead'] and q.get('managed',False) and q.get('team')==0)
        count=min(count,max(0,TEAM_SIZE-1-sum(not t.dead for t in self.allies)-len(self.ally_queue)-air))
        for _ in range(count):
            selected=vehicle if vehicle is not None else self.choose_ai_ground(False)
            p=self.spawn_position(False,selected)
            if p is None:self.ally_queue.append(dict(delay=2.,vehicle=selected,elite=False,vehicle_selected=True,aircraft=None));continue
            t=Tank(p,vehicle=selected);t.ai=True;t.body=angle(BASES[True]-p);t.aim=t.body;self.allies.append(t)
    def deploy_player(self,p):
        if self.state!='deploy' or self.deploy_delay>0 or self.reserves<=0 or not self.deploy_selected or not any(V(p).distance_to(base)<=1 for base in DEPLOY_BASES[False]):return False
        if self.lineup and (self.active_vehicle_slot in self.used_slots or self.lineup[self.active_vehicle_slot] is None):return False
        position=self.spawn_position(False,self.lineup[self.active_vehicle_slot] if self.lineup else None,base=V(p))
        if position is None:self.deploy_hint='部署区内暂无安全位置，请等待或重新开始';return False
        self.vision="day";self.mg_tracers=[]
        self.player=Tank(position,vehicle=self.lineup[self.active_vehicle_slot] if self.lineup else None);self.apply_ammo(self.player);
        if self.lineup:self.used_slots.add(self.active_vehicle_slot)
        self.player.body=angle(BASES[True]-position);self.player.aim=self.player.body
        self.reserves-=1;self.state='play';self.paused=False;self.scope=False;self.fire_armed=False;self.camera()
        if self.wave==0 and not self.allies:self.spawn_allies(TEAM_SIZE-1)
        self.say('已随机部署至己方基地范围内 · 与 AI 队友协同作战',(147,221,240));return True
    def try_aps(self,t,start,end,velocity,ammo,owner=None):
        if not ammo or not t.stats.get('aps') or t.dead or t.aps_charges<=0 or t.aps_cd>0:return False
        if t.modules['ring']<=0 or t.modules['commander']<=0:return False
        if owner is t or (owner is not None and owner.enemy==t.enemy):return False
        kind=ammo['type'].upper()
        if not any(k in kind for k in ('ATGM','HEAT','SAM')) or velocity.length()>1200:return False
        delta=V(end)-V(start)
        if delta.length_squared()==0 or (t.p-V(start)).dot(velocity)<=0:return False
        f=max(0,min(1,(t.p-V(start)).dot(delta)/delta.length_squared()));point=V(start)+delta*f
        if point.distance_to(t.p)>t.radius+90 or not t.shell_contact(start,V(end)+velocity.normalize()*220):return False
        if self.terrain.blocks_shell(start,point):return False
        t.aps_charges-=1;t.aps_cd=.65;self.burst(point,(133,228,255),22)
        if t is self.player or owner is self.player:self.say(t.stats['aps']+' 主动防御拦截 · 剩余 '+str(t.aps_charges)+' 发',(150,221,245))
        return True
    def build_nav(self):
        self.nav_grid={(x,y) for x in range(MW//80) for y in range(MH//80) if self.terrain.free(V(x*80+40,y*80+40),42,trees=False)}
    def find_route(self,start,goal,amphibious=False):
        if self.nav_grid is None:self.build_nav()
        blocked=set()
        for t in self.wrecks:
            x,y=int(t.p.x//80),int(t.p.y//80)
            for i in range(x-2,x+3):
                for j in range(y-2,y+3):
                    if V(i*80+40,j*80+40).distance_squared_to(t.p)<85**2:blocked.add((i,j))
        if amphibious:
            if not hasattr(self,'amphibious_nav'):
                self.amphibious_nav={(x,y) for x in range(MW//80) for y in range(MH//80) if self.terrain.free(V(x*80+40,y*80+40),42,trees=False) or (any(r.collidepoint(x*80+40,y*80+40) for r,k in self.terrain.obstacles if k=='deep_water') and not any(k not in ('tree','deep_water') and r.colliderect(pygame.Rect(x*80-2,y*80-2,84,84)) for r,k in self.terrain.nearby_obstacles(pygame.Rect(x*80-2,y*80-2,84,84))))}
            available=self.amphibious_nav-blocked
        else:available=self.nav_grid-blocked
        def nearest(p):
            x,y=int(p.x//80),int(p.y//80)
            if (x,y) in available:return (x,y)
            candidates=[(i,j) for i in range(x-5,x+6) for j in range(y-5,y+6) if (i,j) in available]
            return min(candidates,key=lambda c:V(c[0]*80+40,c[1]*80+40).distance_squared_to(p)) if candidates else None
        a,b=nearest(start),nearest(goal)
        if a is None or b is None:return []
        queue=[(0.,0.,a)];cost={a:0.};came={};found=False
        while queue:
            _,d,c=heapq.heappop(queue)
            if d>cost[c]:continue
            if c==b:found=True;break
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                n=(c[0]+dx,c[1]+dy)
                if n not in available:continue
                if dx and dy and ((c[0]+dx,c[1]) not in available or (c[0],c[1]+dy) not in available):continue
                nd=d+(1.414214 if dx and dy else 1.)
                if nd>=cost.get(n,float('inf')):continue
                cost[n]=nd;came[n]=c;heapq.heappush(queue,(nd+math.hypot(n[0]-b[0],n[1]-b[1]),nd,n))
        if not found:return []
        nodes=[];c=b
        while c!=a:nodes.append(V(c[0]*80+40,c[1]*80+40));c=came[c]
        nodes.reverse();return nodes
    def ai_step(self,t,dt):update_ai(self,t,dt)
    def camera(self,dt=0.,scope_pressed=False,mouse=None):
        # The optional legacy argument is ignored: right mouse has no camera action.
        self.scope=False;self.scope_focus=V(self.player.p);self.scope_zoom=self.zoom
        vw,vh=W/self.zoom,VIEW.h/self.zoom;focus=self.player.p
        self.cam=V(max(0,min(MW-vw,focus.x-vw/2)),max(-VIEW.top,min(MH-vh-VIEW.top,focus.y-vh/2-VIEW.top)))
    def change_zoom(self,delta):
        self.zoom=max(.65,min(3.5,self.zoom*(1.12**max(-40,min(40,delta)))))
        self.camera()
    def toggle_vision(self,mode):
        if not self.player.vehicle_id or not self.player.stats[mode]:self.say("这辆载具没有"+("夜视仪" if mode=="night" else "热成像"));return False
        self.vision="day" if self.vision==mode else mode;return True
    def to_screen(self,p):return V(p)-self.cam
    def screen_to_world(self,p):
        return self.cam+V(p[0]/self.zoom,VIEW.top+(p[1]-VIEW.top)/self.zoom)
    def world_to_display(self,p):
        q=self.to_screen(p);return V(q.x*self.zoom,VIEW.top+(q.y-VIEW.top)*self.zoom)
    def say(self,msg,col=(237,217,166)):
        self.messages.append([msg,col,4.]);self.messages=self.messages[-4:]
    def burst(self,p,col,n=15):
        for _ in range(n):self.fx.append([V(p),direction(random.uniform(0,360))*random.uniform(25,150),random.uniform(.2,.65),col])
    def shoot(self,t):
        if t.cd>0 or not t.can_fire():return False
        if t.ammo and guided(t.ammo):return self.air.launch(t,ammo=t.ammo)
        spread=0.
        if t.vehicle_id:
            stabilization=t.stats["stabilizer"]
            spread=(abs(t.speed)/t.stats["speed"])*(.15 if stabilization==2 else .9 if stabilization==1 and abs(t.speed)<60 else 3.8)
        if t.ai or t.enemy:
            from AISkill import assign,dispersion
            spread+=dispersion(assign(t))
        if t.stats.get('weapon')=='auto':
            caliber=float((t.ammo or {}).get('caliber',30));spread+=max(.4,min(1.1,1.05-caliber*.009))
        shot_ammo=dict(t.ammo) if t.ammo else None
        if shot_ammo:
            import re
            caliber=re.search(r'(\d+(?:\.\d+)?)\s*mm',t.stats.get('research_data',{}).get('primary_weapon_name',''))
            if caliber:shot_ammo['caliber']=float(caliber[1])
        if shot_ammo and shot_ammo['type'].lower()=='smoke':shot_ammo['smoke_range']=max(80,min(3500,t.p.distance_to(self.screen_to_world(pygame.mouse.get_pos()))))
        if shot_ammo and '/' in shot_ammo['type']:
            parts=shot_ammo['type'].split('/');shot_ammo['effect_type']=parts[t.belt_cursor%len(parts)];t.belt_cursor+=1
        d=direction(t.aim+random.uniform(-spread,spread));self.bullets.append([t.muzzle(),d*((t.ammo.get("velocity") or 950)*.75 if t.ammo else 850),t.enemy,5.2,0.,t,{},0,t.ammo["penetration"][0] if t.ammo else t.stats["pen"],bool(t.vehicle_id and t.stats["branch"]==3 and isinstance(self.air.lock,dict)),shot_ammo])
        if t.stats.get('name') in ('BMPT','BMPT-72'):
            shot=self.bullets[-1];side=direction(t.aim+90)*3.5;shot[0]-=side
            other=list(shot);other[0]=shot[0]+side*2;other[1]=direction(t.aim+random.uniform(-spread,spread))*shot[1].length();other[6]={};other[10]=dict(shot_ammo) if shot_ammo else None
            self.bullets.append(other)
        t.cd=t.stats["reload"]*(1.7 if t.ai or t.enemy else 1)
        if not t.modules['loader']:t.cd*=1.8
        elif t.modules['loader']==1:t.cd*=1.25
        self.burst(t.muzzle(),(255,213,118),9);return True
    def machine_gun(self,t):
        if t.dead or not t.vehicle_id or not t.stats['mg'] or t.mg_cd>0 or not t.modules['gunner']:return False
        t.mg_cd=.105;offset=t.stats['model'][3];start=t.p+V((offset+20)*MODEL_SCALE,7*MODEL_SCALE).rotate(t.aim);end=start+direction(t.aim+random.uniform(-.8,.8))*950
        contacts=[]
        for ob,kind in self.terrain.obstacles:
            if kind=='deep_water':continue
            clip=ob.clipline(start,end)
            if clip:contacts.append((V(clip[0]).distance_to(start),V(clip[0]),None,None))
        targets=([self.player]+self.allies) if t.enemy else self.enemies
        for target in targets:
            if target.dead or getattr(target,'airborne',False):continue
            local_start,local_end=target.local(start),target.local(end);contact=target.shell_contact(start,end);clip=(target.local(contact[1]),) if contact else ()
            if clip:
                point=target.world(clip[0]);contacts.append((point.distance_to(start),point,target,contact[2]))
        if contacts:
            _,end,target,normal=min(contacts,key=lambda c:c[0]);self.burst(end,(230,201,119),2)
            if target is None:self.terrain.strike_tree(start,end+direction(t.aim)*2,1)
            if target and target.vehicle_id:
                touched=[];normal=normal.rotate(-target.body);side=abs(normal.y)>.5
                plate=target.stats['armor'][1] if side else target.stats['armor'][0] if normal.x>0 else target.stats['armor'][2]
                penetrates=t.stats['mg_pen']>plate
                if (target.stats['model'][2]=='open' or penetrates) and random.random()<.18:
                    module=random.choice(CREW);target.damage_module(module,1);touched.append(module)
                    target.last_attacker=t;target.last_weapon='机枪'
                    if self.is_player(t):target.player_credit=True
                entry=target.local(end);vector=direction(t.aim-target.body);fragments=[]
                if penetrates:
                    from CombatEffects import spall
                    damaged,fragments,_=spall(target,entry,vector,dict(type='AP',caliber=12.7 if t.stats['mg_pen']>20 else 7.62),random)
                    touched=list(dict.fromkeys(touched+damaged))
                    if touched:
                        target.last_attacker=t;target.last_weapon='机枪'
                        if self.is_player(t):target.player_credit=True
                self.record_hit(target,dict(kind='机枪命中' if penetrates or target.stats['model'][2]=='open' else '机枪未击穿',modules=touched,fragments=fragments,point=V(end),line=(entry,entry+vector*(25 if penetrates else 8))),t,'机枪')
                if target.dead:self.register_death(target)
        self.mg_tracers.append([start,end,.08]);return True
    def grenade_launcher(self,t=None):
        t=t or self.player;weapon=t.stats.get('grenade')
        if not weapon or t.dead or t.grenade_cd>0 or t.grenade_count<=0 or t.modules['gunner']<=0:return False
        t.grenade_cd=max(.12,60/weapon.get('rpm',400));t.grenade_count-=1
        ammo=dict(weapon['ammo'][0]);ammo['type']='HE';speed=ammo['velocity']*.75;heading=t.body
        muzzle=t.p+direction(heading)*(t.half_length+8)
        self.bullets.append([muzzle,direction(heading)*speed,t.enemy,4.,0.,t,{},0,ammo['penetration'][0],False,ammo])
        return True
    def update_enemy_redeploy(self,dt):
        for entry in self.enemy_queue[:]:
            entry['delay']-=dt
            if entry['delay']>0:continue
            if self.ai_flights.decide(entry,1):self.enemy_queue.remove(entry);continue
            if not entry.get('vehicle_selected'):
                entry['vehicle']=self.choose_ai_ground(True,entry.get('vehicle'));entry['vehicle_selected']=True
            position=self.spawn_position(True,entry['vehicle'])
            if position is None:entry['delay']=2.;continue
            tank=Tank(position,True,entry['elite'],vehicle=entry['vehicle']);tank.ai=True
            tank.body=angle(BASES[False]-position);tank.aim=tank.body
            tank.battle_id=entry.get('battle_id');self.enemies.append(tank);self.enemy_queue.remove(entry)
    def spawn_wave(self):
        self.wave+=1;self.wait=3
        for i in range(max(0,TEAM_SIZE-len(self.enemies)-len(self.enemy_queue)-sum(not q['dead'] and q.get('team',1)==1 for q in self.air.planes))):
            vehicle=None
            if self.enemy_country:
                vehicle=self.choose_ai_ground(True)
            p=self.spawn_position(True,vehicle)
            if p is not None:
                t=Tank(p,True,self.wave>=3 and i%3==0,vehicle=vehicle);t.ai=True;t.body=angle(BASES[False]-p);t.aim=t.body;self.enemies.append(t)
            else:self.enemy_queue.append(dict(delay=2.,vehicle=vehicle,elite=self.wave>=3 and i%3==0,vehicle_selected=True,aircraft=None))
        self.say('敌军已从右侧两个角落部署区出发 · 每方 16 人')
    def register_death(self,t):
        if t is self.player:
            if self.state in ('deploy','lose'):return
            self.wrecks.append(t);self.burst(t.p,(253,137,53),55)
            if self.reserves>0:
                self.state='deploy';
                if self.lineup:self.active_vehicle_slot=next(i for i,v in enumerate(self.lineup) if v is not None and i not in self.used_slots)
                self.deploy_delay=5.;self.deploy_choice=V(BASES[False]);self.deploy_selected=False;self.camera()
                self.deploy_hint=t.reason+' · 选择己方部署点重新部署'
            else:self.state='lose'
            return
        if t in self.allies:
            self.allies.remove(t);self.wrecks.append(t);self.ally_queue.append(8.)
            self.say('AI 队友被摧毁 · 8 秒后从己方部署区补充',(147,195,221));self.burst(t.p,(253,137,53),40)
            return
        if t in self.enemies:
            self.enemies.remove(t);self.wrecks.append(t);self.kills+=1;self.ground_kills+=1;self.score+=(200 if t.elite else 100) if getattr(t,'player_credit',False) else 0
            self.wave=min(5,1+self.ground_kills//6)
            if self.tickets[1]>0:self.enemy_queue.append(dict(delay=8.,vehicle=t.vehicle_id,elite=t.elite))
            else:self.enemy_queue.clear();self.state='win'
            self.say(('目标摧毁 · 敌军 8 秒后重新部署 · ' if self.tickets[1]>0 else '歼灭目标已完成 · ')+t.reason,(143,228,160));self.burst(t.p,(253,137,53),55)
    def update(self,dt):
        if self.state=='deploy':
            self.deploy_delay=max(0,self.deploy_delay-dt);self.update_enemy_redeploy(dt);return
        if self.state!='play':return
        if self.paused:self.camera();return
        self.time+=dt;p=self.player;keys=self.controls.keys(self.input_context())
        if self.flight.active:
            self.flight.update_controls(dt);self.camera(dt)
            if self.state!='play':return
        else:
            throttle=int(keys[pygame.K_w])-int(keys[pygame.K_s]);steer=int(keys[pygame.K_d])-int(keys[pygame.K_a])
            repairing=keys[pygame.K_f]
            p.drive(0 if repairing else throttle,0 if repairing else steer,dt,self.terrain,self.vehicles())
            p.mg_cd=max(0,p.mg_cd-dt)
            if keys[pygame.K_LCTRL] and not repairing:self.machine_gun(p)
            if keys[pygame.K_g] and not repairing:self.grenade_launcher(p)
            for tracer in self.mg_tracers[:]:
                tracer[2]-=dt
                if tracer[2]<=0:self.mg_tracers.remove(tracer)
            p.service(dt,repairing);self.camera(dt)
            aim_point=self.screen_to_world(pygame.mouse.get_pos())
            if p.vehicle_id and p.stats['branch']==3 and isinstance(self.air.lock,dict) and self.air.valid(self.air.lock,p):
                target=self.air.lock;aim_point=target['p']+target['v']*(target['p'].distance_to(p.p)/850)
            p.aim_at(aim_point,dt,self.terrain,self.vehicles())
            left_held=self.controls.buttons("ground")[0]
            if not left_held:self.fire_armed=True
            if ((left_held and self.fire_armed) or keys[pygame.K_SPACE]) and not repairing and VIEW.collidepoint(pygame.mouse.get_pos()):self.shoot(p)
        if self.tickets[1]<=0:self.enemy_queue.clear();self.state='win';return
        if self.wave==0:
            self.wait-=dt
            if self.wait<=0:self.spawn_wave()
        self.update_enemy_redeploy(dt)
        for i in range(len(self.ally_queue)-1,-1,-1):
            entry=self.ally_queue[i]
            if isinstance(entry,dict):
                entry['delay']-=dt
                if entry['delay']<=0:
                    self.ally_queue.pop(i)
                    if not self.ai_flights.decide(entry,0):self.spawn_allies(1,vehicle=entry.get('vehicle') if entry.get('vehicle_selected') else self.choose_ai_ground(False,entry.get('vehicle')))
            else:
                self.ally_queue[i]-=dt
                if self.ally_queue[i]<=0:self.ally_queue.pop(i);self.spawn_allies(1)
        for e in self.allies[:]+self.enemies[:]:self.ai_step(e,dt)
        self.air.update(dt)
        self.update_smoke(dt)
        self.terrain.update(dt)
        for point in self.terrain.tree_events:self.burst(point,(118,150,73),12)
        self.terrain.tree_events.clear()
        for t in [p]+self.allies+self.enemies:
            if getattr(t,'airborne',False):continue
            t.trail+=dt
            if abs(t.speed)>8 and t.trail>.09:
                t.trail=0
                for side,k in ((-22,'left_track'),(22,'right_track')):
                    if t.modules[k]:self.tracks.append((t.world((-15,side)),t.body))
        self.tracks=self.tracks[-1800:]
        for b in self.bullets[:]:
            if len(b)<6:b.append(None)
            if len(b)<7:b.append({})
            if len(b)<8:b.append(0)
            if len(b)<9:b.append(128)
            if len(b)<10:b.append(False)
            if len(b)<11:b.append(None)
            old=V(b[0]);b[0]+=b[1]*dt;b[3]-=dt;b[4]+=b[1].length()*dt
            hit=b[3]<=0 or not pygame.Rect(0,0,MW,MH).collidepoint(b[0])
            if not hit and self.air.shell_hit(old,b[0],b[5],b[10]):hit=True
            smoke_bullet=bool(b[10] and b[10]['type'].lower()=='smoke')
            wallhit=not b[9] and self.terrain.blocks_shell(old,b[0])
            if smoke_bullet and (wallhit or b[4]>=b[10].get('smoke_range',1000) or b[3]<=0):self.add_smoke(b[0],'grenade');hit=True
            if wallhit:
                point=self.terrain.strike_tree(old,b[0],4)
                if point is not None:b[0]=point
                self.burst(b[0],(187,161,111),7);hit=True
            if not hit and not b[9]:
                targets=(self.allies[:]+([p] if not p.dead else [])) if b[2] else self.enemies[:]
                for t in sorted(targets,key=lambda t:t.p.distance_squared_to(old)):
                    if getattr(t,'airborne',False):continue
                    if t.p.distance_to(old)>t.radius+max(65,t.barrel_rect.right)+b[1].length()*dt:continue
                    if smoke_bullet:
                        contact=t.shell_contact(old,b[0])
                        if contact:self.add_smoke(contact[1],'grenade');hit=True;break
                        continue
                    if self.try_aps(t,old,b[0],b[1],b[10],b[5]):hit=True;break
                    result=t.hit(old,b[0],b[1],b[4],barrel_seen=b[6],penetration_value=b[8],ammo=b[10])
                    if result:
                        passthrough=result.get('continue',False)
                        reflection=result.get('reflect')
                        hit=not passthrough
                        if not passthrough:self.burst(result['point'],(255,190,91),18)
                        if reflection is not None and b[7]<3:
                            b[1]=V(reflection);b[0]=result['point']+b[1].normalize()*5;b[7]+=1;hit=False
                        names=' / '.join(LABELS[k] for k in result['modules'])
                        owner=b[5] if len(b)>5 else None
                        if t is p or owner is p or (owner is None and t.enemy):
                            self.say(('受到攻击：' if t is p else '弹道反馈：' if passthrough else '命中目标：')+result['kind']+(' · '+names if names else ''),(247,145,109) if t is p else (231,221,156))
                        self.record_hit(t,result,owner,b[10]['name'] if b[10] else '主炮')
                        if result.get('modules'):
                            t.last_attacker=b[5];t.last_weapon=b[10]['name'] if b[10] else '主炮'
                            if self.is_player(b[5]):t.player_credit=True
                        if t.dead:self.register_death(t)
                        if not passthrough:break
            if hit:self.bullets.remove(b)
        if p.dead:self.register_death(p)
        for f in self.fx[:]:
            f[0]+=f[1]*dt;f[1]*=.96;f[2]-=dt
            if f[2]<=0:self.fx.remove(f)
        for m in self.messages[:]:
            m[2]-=dt
            if m[2]<=0:self.messages.remove(m)
    def schematic(self,t,origin,scale=2,hit=None):
        o=V(origin)
        outline=rect_polygon(t.body_rect)
        pygame.draw.polygon(screen,(98,107,87),[o+point*scale for point in outline],1)
        for k,rect in t.module_rects.items():
            if rect.width<=0 or rect.height<=0:continue
            points=[o+point.rotate(t.module_angle(k)-t.body)*scale for point in rect_polygon(rect)]
            pygame.draw.polygon(screen,module_color(t.modules[k]),points);pygame.draw.polygon(screen,(21,29,24),points,1)
        if hit:
            for start,end in hit.get('external_fragments',[]):pygame.draw.line(screen,(246,177,80),o+start*scale,o+end*scale,1)
            for start,end in hit.get('fragments',[]):pygame.draw.line(screen,(241,132,63),o+start*scale,o+end*scale,1)
            if hit.get('overpressure'):pygame.draw.circle(screen,(237,91,72),o+hit['pressure_origin']*scale,max(1,int(hit['pressure_radius']*scale)),2)
            if hit.get('burst') is not None:pygame.draw.circle(screen,(255,181,66),o+hit['burst']*scale,5,1)
            a,b=hit['line'];pygame.draw.line(screen,(255,244,196),o+a*scale,o+b*scale,2)
        text('车头 →',(o.x+15,o.y-27*scale-22),14,(171,182,153),True)
    def minimap(self):
        if self.flight.active:return
        r=pygame.Rect(W-218,85,200,156);pygame.draw.rect(screen,(23,36,29),r,border_radius=5)
        def pt(p):return V(r.x+p.x/MW*r.w,r.y+p.y/MH*r.h)
        for pond in self.terrain.ponds:
            pygame.draw.rect(screen,(97,151,144),(r.x+pond.x/MW*r.w,r.y+pond.y/MH*r.h,max(2,pond.w/MW*r.w),max(2,pond.h/MH*r.h)))
        for ob,k in self.terrain.obstacles:
            if k=='tree':continue
            pygame.draw.rect(screen,(39,77,93) if k=='deep_water' else (118,116,83),(r.x+ob.x/MW*r.w,r.y+ob.y/MH*r.h,max(2,ob.w/MW*r.w),max(2,ob.h/MH*r.h)))
        for team,base in ((team,base) for team,bases in DEPLOY_BASES.items() for base in bases):pygame.draw.circle(screen,(207,109,79) if team else (101,191,216),pt(base),int(DEPLOY_RADIUS/MW*r.w),1)
        for e in self.enemies:pygame.draw.circle(screen,(229,109,73),pt(e.p),3)
        for ally in self.allies:pygame.draw.circle(screen,(122,211,253),pt(ally.p),3)
        q=pt(self.player.p);pygame.draw.circle(screen,(130,248,173),q,4);pygame.draw.line(screen,(207,255,211),q,q+direction(self.player.body)*11,2)
        pygame.draw.rect(screen,(203,219,169),(r.x+self.cam.x/MW*r.w,r.y+(self.cam.y+68)/MH*r.h,W/self.zoom/MW*r.w,VIEW.h/self.zoom/MH*r.h),1)
        pygame.draw.rect(screen,(133,147,113),r,1,border_radius=5)
        text(f'{MW} × {MH} · 战术地图',(r.x,r.bottom+5),14)
        text('深水溺亡 3 秒 · 两栖车可渡水',(r.x,r.bottom+24),14,(163,199,180))
    def draw(self,mouse_position=None):
        global screen
        if self.state=='deploy':self.draw_deployment();return
        world_view=pygame.Rect(0,VIEW.top,math.ceil(W/self.zoom),math.ceil(VIEW.h/self.zoom))
        display_screen=screen
        screen=pygame.Surface((world_view.width,world_view.bottom))
        self.render_view=world_view;self.air.screen=screen;self.air.view=world_view
        screen.set_clip(world_view);self.terrain.draw(self)
        self.objective.draw_world(screen,text,self.to_screen)
        for team,base in ((team,base) for team,bases in DEPLOY_BASES.items() for base in bases):
            q=self.to_screen(base);pygame.draw.circle(screen,(202,112,76) if team else (104,190,205),q,DEPLOY_RADIUS,2)
            text('敌方部署区' if team else '己方部署区',(q.x,q.y-DEPLOY_RADIUS+24),20,(232,173,129) if team else (155,225,237),True)
        for p,a in self.tracks:
            q=self.to_screen(p)
            if self.render_view.collidepoint(q):pygame.draw.line(screen,(123,171,162) if self.terrain.in_shallow(p) else (52,61,36),q-direction(a)*5,q+direction(a)*5,4)
        for t in self.wrecks:t.draw(self,True)
        for t in self.enemies+self.allies+[self.player]:t.draw(self)
        for b in self.bullets:
            q=self.to_screen(b[0]);pygame.draw.line(screen,(255,209,136),q-b[1].normalize()*15,q,2)
        for start,end,life in self.mg_tracers:pygame.draw.line(screen,(255,225,131),self.to_screen(start),self.to_screen(end),1)
        for f in self.fx:pygame.draw.circle(screen,f[3],self.to_screen(f[0]),max(1,int(f[2]*8)))
        self.terrain.canopy(self)
        self.air.draw()
        if self.xray:
            for t in self.enemies+self.allies+[self.player]:
                if self.to_screen(t.p).distance_to(V(W/2,H/2))<800:self.schematic(t,self.to_screen(t.p),1)
        if self.vision in ('night','thermal'):
            image=screen.subsurface(world_view).copy();pixels=pygame.surfarray.pixels3d(image)
            gray=(pixels[:,:,0].astype('uint16')*3+pixels[:,:,1].astype('uint16')*6+pixels[:,:,2].astype('uint16'))//10
            if self.vision=='night':
                pixels[:,:,0]=gray//4;pixels[:,:,1]=gray.clip(25,220);pixels[:,:,2]=gray//5
            else:
                for channel in range(3):pixels[:,:,channel]=gray//2+20
            del pixels;screen.blit(image,world_view.topleft)
            if self.vision=='thermal':
                for target in self.enemies+self.allies+[self.player]+self.wrecks:
                    if target is not self.player and not self.visible(self.player.p,target.p,thermal=True):continue
                    heat=(245,245,245) if not target.dead else (99,99,99)
                    if target.vehicle_id:draw_model(screen,target.stats,self.to_screen(target.p),MODEL_SCALE,target.body,True,target.aim,heat)
                    else:pygame.draw.rect(screen,heat,pygame.Rect(self.to_screen(target.p)-V(25,20),(50,40)),border_radius=8)
        elif self.night_battle:
            darkness=pygame.Surface(world_view.size,pygame.SRCALPHA);darkness.fill((1,5,15,185));screen.blit(darkness,world_view.topleft)
        self.draw_smoke()
        screen.set_clip(None)
        world_image=screen.subsurface(world_view).copy()
        screen=display_screen;self.air.screen=screen;self.air.view=VIEW
        screen.blit(pygame.transform.scale(world_image,VIEW.size),VIEW.topleft)
        if self.player.vehicle_id and not getattr(self.player,'airborne',False):text(('夜间' if self.night_battle else '白昼')+' · '+{'day':'日间光学','night':'夜视仪','thermal':'白热热成像'}[self.vision]+f' · 视角 {self.zoom:.2f}× · '+self.controls.label('ground.mg')+' 机枪 / '+self.controls.label('ground.night')+' 夜视 / '+self.controls.label('ground.thermal')+' 热成像',(18,77),14,(211,224,184))
        self.air.hud()
        mouse=V(pygame.mouse.get_pos() if mouse_position is None else mouse_position)
        if VIEW.collidepoint(mouse):
            pygame.draw.circle(screen,(241,232,179),mouse,12,1)
            for d in (V(1,0),V(0,1),V(-1,0),V(0,-1)):pygame.draw.line(screen,(241,232,179),mouse+d*7,mouse+d*17,1)
        screen.set_clip(None)
        pygame.draw.rect(screen,(15,24,21),(0,0,W,68));pygame.draw.rect(screen,(15,24,21),(0,H-42,W,42))
        text('钢铁旷野',(22,15),30);text('STEEL WILDERNESS',(184,27),14,(133,157,123))
        text(f'歼灭 {self.ground_kills}/{self.kill_goal} · 敌军 {len(self.enemies)} · 待部署 {len(self.enemy_queue)}',(390,25),18)
        p=self.player;text(f'乘员 {p.crew_alive()}/4   灭火器 {p.extinguishers}   {abs(p.speed)*.2:.0f} km/h'+(' · 涉水' if self.terrain.in_shallow(p.p) else ''),(W-455,25),18)
        text((f'编成 BR {self.battle_br:.1f} · ' if self.lineup else '')+f'滚轮缩放 {self.zoom:.2f}× · '+('视角跟随飞机' if self.flight.active else '视角跟随坦克'),(390,50),14,(194,230,164))
        self.minimap()
        panel=pygame.Rect(16,H-340,310,281);pygame.draw.rect(screen,(18,28,23),panel,border_radius=8)
        text('车体模块 · 无总血量',(30,panel.y+10),20);self.schematic(p,(88,panel.y+103),1.4)
        for i,k in enumerate(('engine','transmission','left_track','right_track','breech','barrel','ring')):
            status=('损毁','受损','正常')[p.modules[k]];text(LABELS[k]+' '+status,(177,panel.y+43+i*21),14,module_color(p.modules[k]))
        for i,k in enumerate(CREW):
            text(LABELS[k]+(' 失能' if not p.modules[k] else ' 受伤' if p.modules[k]==1 else ' 在位'),(30+(i%2)*142,panel.y+187+(i//2)*22),14,module_color(p.modules[k]))
        text('绿 正常   黄 受损   红 失效',(30,panel.bottom-40),14,(164,182,151))
        if p.repair:text(f'修理中 {p.repair/5*100:.0f}% · 保持 F',(30,panel.bottom-23),14,(238,218,121))
        elif p.replace:text(f'乘员换位 {max(0,7-p.replace):.1f}s',(30,panel.bottom-23),14,(238,218,121))
        elif p.fire:text('发动机起火！按 '+self.controls.label('ground.extinguish')+' 灭火',(30,panel.bottom-23),14,(255,122,71))
        elif (p.modules['left_track']>0)!=(p.modules['right_track']>0):text('单侧驱动 · 偏转行驶 · '+self.controls.label('ground.repair')+' 修理',(30,panel.bottom-23),14,(238,218,121))
        else:text('停车按住 '+self.controls.label('ground.repair')+' 修理机械模块',(30,panel.bottom-23),14)
        for i,m in enumerate(self.messages):text(m[0],(350,H-310-i*23),16,m[1])
        if p.stats.get('grenade'):text(f'G 榴弹发射器 · 余弹 {p.grenade_count}',(350,H-239),14,(218,214,170))
        if p.stats.get('aps'):text(p.stats['aps']+f' 主动防御 {p.aps_charges} 发 / '+('损坏' if p.modules['ring']<=0 or p.modules['commander']<=0 else f'冷却 {p.aps_cd:.1f}s' if p.aps_cd>0 else '就绪'),(350,H-215),14,(151,217,230))
        if p.vehicle_id:text(('Z 烟雾 '+str(p.smoke_charges)+' 组  ' if p.stats['smoke_grenades'] else '')+('H 发动机烟幕 '+('开' if p.ess_active else '关') if p.stats['ess'] else ''),(350,H-191),14,(186,209,180))
        if p.cd>0:text(f'装填 {p.cd:.1f}s',(W/2,H-111),20,(243,216,143),True)
        elif not p.can_fire():text('火炮失效 / 等待乘员换位',(W/2,H-111),20,(245,123,89),True)
        else:text('弹药已就绪',(W/2,H-111),18,(203,226,172),True)
        if p.ammo:text('B 换炮弹 · '+ammo_name(p.ammo),(W/2,H-139),16,(220,213,163),True)
        text(' / '.join(self.controls.label('ground.'+a) for a in ('forward','reverse','left','right'))+' 驾驶 · '+self.controls.label('ground.fire')+' 开火 · '+self.controls.label('ground.repair')+' 修理 · 按键设置可查看全部操作',(W/2,H-22),16,(186,200,167),True)
        if self.paused:self.overlay('已暂停',self.controls.label('common.pause')+' 继续战斗')
        elif self.state in ('win','lose'):self.overlay('战斗胜利' if self.state=='win' else '战斗失败',f'{p.reason if self.state=="lose" else "敌方战场分数耗尽"} · 得分 {self.score}',self.controls.label('common.restart')+' 重新开始 · '+self.controls.label('common.back')+' 返回菜单')
    def deployment_map(self):
        area=pygame.Rect(225,135,W-450,H-174);ratio=min(area.w/830,area.h/646)
        r=pygame.Rect(0,0,round(830*ratio),round(646*ratio));r.center=area.center;return r
    def deployment_slot(self,i):
        step=min(34,max(18,(H-155-416)//12));return pygame.Rect(24,416+i*step,170,step-3)
    def deployment_button(self):return pygame.Rect(24,H-104,170,48)
    def choose_deployment(self,pos):
        if self.lineup:
            for i in range(len(self.lineup)):
                if self.deployment_slot(i).collidepoint(pos):
                    if i not in self.used_slots and self.lineup[i] is not None:self.active_vehicle_slot=i
                    else:self.deploy_hint="该栏为空或载具已在本场使用"
                    return
        if self.deployment_button().collidepoint(pos):
            if not self.deploy_player(self.deploy_choice):
                self.deploy_hint='等待重新部署倒计时结束' if self.deploy_delay>0 else '请先选择己方蓝色部署点' if not self.deploy_selected else '部署区内暂无安全位置'
            return
        r=self.deployment_map()
        if not r.collidepoint(pos):return
        clicked=V((pos[0]-r.x)/r.w*MW,(pos[1]-r.y)/r.h*MH)
        base=min(DEPLOY_BASES[False],key=lambda base:clicked.distance_squared_to(base))
        self.deploy_selected=clicked.distance_to(base)<=DEPLOY_RADIUS
        self.deploy_choice=V(base)
        self.deploy_hint='已选己方部署点，确认后在范围内随机生成' if self.deploy_selected else '只能选择己方蓝色部署点'
    def draw_deployment(self):
        screen.fill((15,24,21));r=self.deployment_map()
        text('选择部署点',(180,37),30,(176,225,204),True)
        text(self.map_name+' · 选择蓝色部署点，再点击“部署”；范围内随机生成。',(W/2,94),20,center=True)
        pygame.draw.rect(screen,(64,78,47),r)
        def pt(p):return V(r.x+p.x/MW*r.w,r.y+p.y/MH*r.h)
        for road in self.terrain.roads:pygame.draw.rect(screen,(123,107,73),(r.x+road.x/MW*r.w,r.y+road.y/MH*r.h,max(2,road.w/MW*r.w),max(2,road.h/MH*r.h)))
        for pond in self.terrain.ponds:
            pygame.draw.rect(screen,(97,151,144),(r.x+pond.x/MW*r.w,r.y+pond.y/MH*r.h,pond.w/MW*r.w,pond.h/MH*r.h))
        for ob,k in self.terrain.obstacles:
            col=(39,77,93) if k=='deep_water' else (38,59,32) if k=='tree' else (158,135,91) if k=='house' else (124,124,103)
            pygame.draw.rect(screen,col,(r.x+ob.x/MW*r.w,r.y+ob.y/MH*r.h,max(2,ob.w/MW*r.w),max(2,ob.h/MH*r.h)))
        for team,base in ((team,base) for team,bases in DEPLOY_BASES.items() for base in bases):
            q=pt(base);rad=int(DEPLOY_RADIUS/MW*r.w);col=(223,127,91) if team else (112,205,239)
            tint=pygame.Surface((rad*2+2,rad*2+2),pygame.SRCALPHA);pygame.draw.circle(tint,(*col,45),(rad+1,rad+1),rad)
            screen.blit(tint,q-V(rad+1,rad+1));pygame.draw.circle(screen,col,q,rad,2)
            pygame.draw.circle(screen,col,q,6)
            text('敌方部署区' if team else '己方部署区',(q.x,q.y-rad-16),18,col,True)
        for t in self.allies+self.enemies+self.wrecks:
            pygame.draw.circle(screen,(81,82,65) if t.dead else (231,117,84) if t.enemy else (145,219,249),pt(t.p),4)
        valid=self.deploy_selected;q=pt(self.deploy_choice)
        col=(169,249,167) if valid else (255,101,80)
        if valid:
            pygame.draw.circle(screen,col,q,12,2)
            text('已选择 · 范围内随机部署',(q.x+135,q.y+5),16,col,True)
        pygame.draw.rect(screen,(145,165,132),r,2)
        for i,line in enumerate(['部署规则','己方：左上 / 左下角附近','敌方：右上 / 右下角附近','半径 380 内随机生成','每方 16 人 · AI 可重新部署','最多携带 12 辆载具']):text(line,(24,180+i*28),16,(192,215,180))
        text(f'剩余部署次数：{self.reserves}',(24,363),18,(227,223,157))
        if self.lineup:text(f'编成 BR {self.battle_br:.1f}',(24,390),16,(194,218,190))
        text(f'等待 {self.deploy_delay:.1f} 秒' if self.deploy_delay>0 else '选择基地后点击部署',(24,H-133),14,(212,217,169))
        ready=valid and self.deploy_delay<=0 and self.reserves>0
        pygame.draw.rect(screen,(76,126,98) if ready else (48,60,48),self.deployment_button(),border_radius=6)
        pygame.draw.rect(screen,(155,207,155) if ready else (77,88,69),self.deployment_button(),1,border_radius=6)
        text('部署',self.deployment_button().center,24,(234,242,210) if ready else (140,151,126),True)
        text('也可按 '+self.controls.label('deploy.confirm')+' 确认',(24,H-46),14,(164,183,145))
        if self.lineup:
            for i,ident in enumerate(self.lineup):
                r=self.deployment_slot(i);used=i in self.used_slots or ident is None
                pygame.draw.rect(screen,(38,43,39) if used else (85,107,67) if i==self.active_vehicle_slot else (42,60,47),r,border_radius=4)
                text(('未装备' if ident is None else CATALOG[ident]['name']+f' {CATALOG[ident].get("ground_br",CATALOG[ident]["br"]):.1f}'+(' 已用' if i in self.used_slots else '')),(32,r.y+max(1,(r.h-14)//2)),14,(120,128,115) if used else (224,226,191))
        text(self.deploy_hint or ('已选己方基地，点击部署' if valid else '请先点击己方蓝色部署点'),(W/2,H-17),16,(174,224,173) if valid else (230,169,136),True)
    def overlay(self,title,sub,extra=''):
        shade=pygame.Surface((W,H),pygame.SRCALPHA);shade.fill((9,17,13,222));screen.blit(shade,(0,0))
        text(title,(W/2,260),62,(181,222,155),True);text(sub,(W/2,350),24,center=True)
        if extra:text(extra,(W/2,404),20,(212,212,177),True)
from GroundFlight import install as install_ground_flight
install_ground_flight(Game,Tank,globals())
from AIFlight import install as install_ai_flight
install_ai_flight(Game)
from BattleFeedback import install as install_battle_feedback
install_battle_feedback(Game,globals())
from InputBindings import install as install_input_bindings
install_input_bindings(Game)
from BattleObjectives import install as install_objectives
install_objectives(Game,globals())
from GroundSystems import install as install_ground_systems
install_ground_systems(Game,Tank,globals())
from Artillery import install as install_artillery
install_artillery(Game,globals())
from Overpressure import install as install_pressure
install_pressure(Game,Tank,globals())
from AbandonVehicle import install as install_abandon
install_abandon(Game,globals())
from Reconnaissance import install as install_recon
install_recon(Game,globals())
from SplitAirDefense import install as install_split_sam
install_split_sam(Game,Tank,globals())

from BattleRoster import install as install_roster
install_roster(Game,globals())
from NuclearSequence import install as install_nuclear_sequence
install_nuclear_sequence(Game,globals())
from AICombatAwareness import install as install_ai_combat_awareness
install_ai_combat_awareness(Game,globals())

from AirIntercept import install as install_air_intercept
install_air_intercept(Game,globals())

from LateJoin import install as install_late_join
install_late_join(Game,Garage,globals())
from AmmoBoxes import install as install_ammo_boxes
install_ammo_boxes(Game,globals())

def self_test():
    from AmmoBoxChecks import run as ammo_box_checks
    ammo_box_checks(globals())
    from LateJoinChecks import run as late_join_checks
    late_join_checks(globals())
    from PortableAudioChecks import run as portable_audio_checks
    portable_audio_checks(globals())
    from AirIntercept import checks
    checks(globals())
    from SupplyHandlingChecks import run as supply_handling_checks
    supply_handling_checks(globals())
    from AICombatChecks import run as ai_combat_checks
    ai_combat_checks(globals())
    from BattleAudioChecks import run as battle_audio_checks
    battle_audio_checks(globals())
    from RosterChecks import run as roster_checks
    roster_checks(globals())
    from HelicopterChecks import run as helicopter_checks
    helicopter_checks(globals())
    from SplitChecks import run as check_split
    check_split(globals())
    from WindowChecks import run as check_window
    check_window(globals())
    from PresentationChecks import run as check_presentation
    check_presentation(globals())
    from AutoUpdateChecks import run as check_updates
    check_updates()
    from ReactiveArmorChecks import run as check_era
    check_era(globals())
    from ReconChecks import run as check_recon
    check_recon(globals())
    random.seed(7);g=Game();t=g.player
    t.p=V(350,2450);t.body=0;start=V(t.p)
    t.drive(1,0,.2,g.terrain);assert t.p.x>start.x and t.p.y==start.y
    t.speed=0;t.drive(-1,0,.2,g.terrain);assert t.p.x<start.x+7
    old=t.body;t.drive(0,1,.2,g.terrain);assert t.body>old
    t.modules['engine']=0;old=V(t.p);t.drive(1,1,.2,g.terrain);assert t.p==old
    t.service(5.1,True);assert t.modules['engine']==2
    t.modules['barrel']=0;assert not g.shoot(t)
    t.modules['barrel']=2;t.modules['gunner']=0;assert not g.shoot(t)
    for _ in range(8):t.service(1)
    assert t.modules['gunner']>0 and t.crew_alive()==3
    t.cd=0;assert g.shoot(t)
    hit=Tank((1000,1000));hit.body=0
    r=hit.hit(V(950,975),V(1050,975),V(1,0));assert r and hit.modules['left_track']==0
    hit=Tank((1000,1000));hit.body=0
    r=hit.hit(V(950,1000),V(1050,1000),V(1,0));assert r['kind']=='击穿' and hit.modules['engine']==0
    front=Tank((1000,1000),elite=True);front.body=0
    r=front.hit(V(1040,960),V(1020,1010),V(-20,50));assert r['kind'] in ('跳弹','未击穿')
    class FixedRoll:
        def __init__(self,value):self.value=value;self.calls=0
        def random(self):self.calls+=1;return self.value
    intercept=Tank((1000,1000));intercept.body=0;intercept.aim=0
    direct=intercept.hit(V(1070,1000),V(1015,1000),V(-850,0),rng=FixedRoll(0.))
    assert direct['kind']=='炮管命中' and intercept.modules['barrel']==0
    assert all(intercept.modules[k]==2 for k in MODULES if k!='barrel'), 'Barrel must intercept before the hull'
    miss=Tank((1000,1000));miss.body=0;miss.aim=0;seen={};roll=FixedRoll(.99)
    first=miss.hit(V(1070,1000),V(1050,1000),V(-850,0),rng=roll,barrel_seen=seen)
    assert first['continue'] and miss.modules['barrel']==2 and roll.calls==1
    second=miss.hit(V(1050,1000),V(1035,1000),V(-850,0),rng=roll,barrel_seen=seen)
    assert second is None and roll.calls==1, 'Barrel probability must not be rerolled on later frames'
    third=miss.hit(V(1035,1000),V(1015,1000),V(-850,0),rng=roll,barrel_seen=seen)
    assert third['kind']=='擦过炮管 → 击穿车体' and miss.modules['barrel']==2
    assert any(miss.modules[k]<2 for k in MODULES if k!='barrel')
    same_frame=Tank((1000,1000));same_frame.body=0;same_frame.aim=0
    result=same_frame.hit(V(1070,1000),V(1015,1000),V(-850,0),rng=FixedRoll(.99))
    assert result['kind']=='擦过炮管 → 击穿车体' and same_frame.modules['barrel']==2
    rear=Tank((1000,1000));rear.body=0;rear.aim=0
    result=rear.hit(V(950,1000),V(1070,1000),V(850,0),rng=FixedRoll(0.))
    assert rear.modules['barrel']==2 and rear.modules['engine']==0, 'The first physical surface takes priority'
    broken=Tank((1000,1000));broken.body=0;broken.aim=0;broken.modules['barrel']=0
    assert broken.hit(V(1070,1000),V(1050,1000),V(-850,0),rng=FixedRoll(0.)) is None
    graze=Tank((1000,1000));graze.body=0;graze.aim=0
    result=graze.hit(V(1065,990),V(1015,1000),V(-850,170),rng=FixedRoll(0.))
    assert result['kind']=='炮管跳弹' and result['reflect'].y<0 and graze.modules['barrel']==2
    for orientation in (0,37,125):
        plate=Tank((1000,1000));plate.body=orientation;plate.aim=orientation+90
        result=plate.hit(plate.world((40,-40)),plate.world((20,40)),V(-20,80).rotate(orientation),rng=FixedRoll(.99))
        assert result['kind']=='车体跳弹' and result['reflect'].rotate(-orientation).x>0
        assert all(plate.modules[k]==2 for k in MODULES if k not in ('left_track','right_track'))
    probability_rng=random.Random(819);barrel_hits=0
    for _ in range(1000):
        sample=Tank((1000,1000));sample.body=0;sample.aim=0
        result=sample.hit(V(1070,1000),V(1050,1000),V(-850,0),rng=probability_rng)
        barrel_hits+=result['kind']=='炮管命中'
    assert 650<barrel_hits<750
    # Verify that a missed barrel does not consume the moving projectile before hull impact.
    battle=Game();battle.terrain.obstacles=[];battle.terrain.ponds=[];battle.allies=[]
    battle.player.p=V(1400,1000);victim=Tank((1000,1000),True);victim.body=0;victim.aim=0;victim.cd=100
    for k in ('left_track','right_track','ring'):victim.modules[k]=0
    victim.ai=True;battle.enemies=[victim];battle.wave=1
    battle.bullets=[[V(1050,1000),V(-850,0),False,2.4,0.,battle.player,{victim:'miss'},0]]
    for _ in range(4):battle.update(1/60)
    assert victim.modules['barrel']==2 and any(victim.modules[k]<2 for k in ('transmission','breech','driver'))
    bounce_game=Game();bounce_game.terrain.obstacles=[];bounce_game.terrain.ponds=[];bounce_game.allies=[]
    bounce_game.player.p=V(1400,1400);plate=Tank((1000,1000),True);plate.body=0;plate.aim=90;plate.cd=100
    plate.modules['left_track']=0;plate.modules['right_track']=0;plate.modules['ring']=0
    bounce_game.enemies=[plate];bounce_game.wave=1
    bounce_game.bullets=[[V(1040,960),V(-200,800),False,2.4,0.,bounce_game.player,{},0]]
    for _ in range(5):bounce_game.update(1/60)
    assert bounce_game.bullets and bounce_game.bullets[0][7]==1 and bounce_game.bullets[0][1].x>0
    hit.damage_module('ammo',2);assert hit.dead and hit.reason=='弹药殉爆'
    crew=Tank((1000,1000))
    for k in CREW[:3]:crew.damage_module(k,2)
    assert crew.dead and crew.reason=='乘员不足'
    fire=Tank((1000,1000));fire.fire=15;fire.extinguish();assert not fire.fire and fire.extinguishers==1
    fire.fire=15
    for _ in range(6):fire.service(1)
    assert fire.dead and fire.reason=='弹药殉爆'
    col=Tank((100,100));col.body=0
    fake=Terrain();fake.obstacles=[(pygame.Rect(134,50,20,100),'house')]
    col.drive(1,0,1,fake);assert col.p.x<104
    g=Game();g.spawn_wave();assert len(g.enemies)==TEAM_SIZE
    assert all(g.terrain.free(e.p) for e in g.enemies)
    g.player.p=V(1800,1400);g.camera();assert g.cam.x>0 and g.cam.y>0
    g.wave=5;g.tickets[1]=0;g.enemies=[];g.wait=0;g.update(.016);assert g.state=='win'
    g=Game();g.reserves=0;g.player.dead=True;g.player.reason='测试';g.update(.016);assert g.state=='wreck';g.update(4.1);assert g.state=='lose'
    g=Game();g.terrain.obstacles=[];g.player.p=V(800,1200)
    victim=Tank((1100,1200),True);victim.body=0;victim.cd=100;g.enemies=[victim]
    g.bullets=[[V(1055,1200),V(850,0),False,2.4,0,g.player]]
    for _ in range(5):g.update(.016)
    assert victim.modules['engine']==0 and g.hitview is not None
    flat=Terrain();flat.obstacles=[];flat.ponds=[]
    left=Tank((500,500));left.body=0;left.modules['left_track']=0
    right=Tank((500,500));right.body=0;right.modules['right_track']=0
    for _ in range(60):
        left.drive(1,0,1/60,flat);right.drive(1,0,1/60,flat)
    assert left.p.distance_to(V(500,500))>10 and left.right_speed>0 and left.left_speed==0 and left.body<0
    assert right.p.distance_to(V(500,500))>10 and right.left_speed>0 and right.right_speed==0 and right.body>0
    assert abs(left.p.x-right.p.x)<.01 and abs((left.p.y-500)+(right.p.y-500))<.01
    left.modules['right_track']=0;old=V(left.p);a=left.body
    left.drive(1,1,.2,flat);assert left.p==old and left.body==a
    for steer in (-1,1):
        forward=Tank((500,500));forward.body=0
        backward=Tank((500,500));backward.body=0
        for _ in range(30):
            forward.drive(1,steer,1/60,flat);backward.drive(-1,steer,1/60,flat)
        assert forward.body*steer>0 and backward.body*steer<0
        assert forward.speed>0 and backward.speed<0
        old=backward.body;backward.drive(0,steer,1/60,flat)
        assert (backward.body-old)*steer<0
    water=Terrain();water.ponds=[pygame.Rect(200,200,400,300)]
    water.obstacles=[(water.ponds[0].inflate(-180,-160),'deep_water')]
    assert water.in_shallow(V(250,350)) and water.free(V(250,350))
    wet=Tank((250,350));wet.body=90;dry=Tank((250,350));dry.body=90
    for _ in range(60):
        wet.drive(1,0,1/60,water);dry.drive(1,0,1/60,flat)
    assert wet.p.y>380 and wet.speed<dry.speed and wet.p.y<dry.p.y
    edge=Tank((250,350));edge.body=0
    for _ in range(120):edge.drive(1,0,1/60,water)
    assert edge.p.x>300  # Deep water is physically enterable; drowning is handled by the battle.
    assert not water.blocks_shell(V(200,350),V(600,350))
    single_reverse=Tank((500,500));single_reverse.body=0;single_reverse.modules['left_track']=0
    for _ in range(60):single_reverse.drive(-1,0,1/60,flat)
    assert single_reverse.speed<0 and single_reverse.body>0
    tree_terrain=Terrain();tree_terrain.ponds=[];tree_terrain.obstacles=[(pygame.Rect(551,491,18,18),'tree')]
    tree_terrain.trees=[(V(560,500),25)];tree_terrain.fallen=[]
    ram=Tank((500,500));ram.body=0
    assert tree_terrain.blocks_shell(V(500,500),V(620,500))
    for _ in range(60):ram.drive(1,0,1/60,tree_terrain)
    assert ram.p.x>575 and not tree_terrain.trees and len(tree_terrain.fallen)==1
    assert not tree_terrain.blocks_shell(V(500,500),V(620,500))
    tree_terrain.update(.6);assert tree_terrain.fallen[0][3]==1.
    # Turning while stationary does not fell a nearby tree.
    tree_terrain.trees=[(V(650,500),25)];tree_terrain.obstacles=[(pygame.Rect(641,491,18,18),'tree')]
    tree_terrain.crush_trees(V(650,500),0,0);assert len(tree_terrain.trees)==1
    dep=Game(True);assert dep.state=='deploy' and dep.reserves==3
    assert not dep.deploy_player(BASES[True]) and dep.reserves==3
    assert not dep.deploy_player(V(1700,1400))
    assert not dep.deployment_valid(V(695,2200)), 'Deployment into deep water must be rejected'
    assert not dep.deploy_player(BASES[False]), 'A base must be selected first'
    dep.choose_deployment(dep.deployment_button().center);assert dep.state=='deploy' and dep.reserves==3
    r=dep.deployment_map();blue=V(r.x+(BASES[False].x+90)/MW*r.w,r.y+BASES[False].y/MH*r.h)
    dep.choose_deployment(blue);assert dep.deploy_selected and dep.deploy_choice==BASES[False]
    dep.choose_deployment(dep.deployment_button().center)
    assert dep.state=='play' and dep.player.p!=BASES[False]
    assert dep.state=='play' and dep.reserves==2 and len(dep.allies)==TEAM_SIZE-1
    assert all(min(a.p.distance_to(base) for base in DEPLOY_BASES[False])<DEPLOY_RADIUS-44 for a in dep.allies)
    dep.spawn_wave();assert len(dep.enemies)==TEAM_SIZE
    assert all(min(e.p.distance_to(base) for base in DEPLOY_BASES[True])<DEPLOY_RADIUS-44 for e in dep.enemies)
    for wave in range(1,6):
        spawn_check=Game();spawn_check.wave=wave-1;spawn_check.spawn_wave()
        assert len(spawn_check.enemies)==TEAM_SIZE
        assert all(min(e.p.distance_to(base) for base in DEPLOY_BASES[True])<=DEPLOY_RADIUS-44 and spawn_check.terrain.free(e.p,44) for e in spawn_check.enemies)
    route=dep.find_route(dep.allies[0].p,dep.enemies[0].p);assert len(route)>20
    ally=dep.allies[0];old=V(ally.p)
    for _ in range(90):dep.ai_step(ally,1/60)
    assert ally.p.distance_to(old)>30
    ally.dead=True;ally.reason='测试';dep.register_death(ally)
    assert len(dep.allies)==TEAM_SIZE-2 and len(dep.ally_queue)==1
    dep.ally_queue[0]=0;dep.update(.016);assert len(dep.allies)==TEAM_SIZE-1
    dep.player.dead=True;dep.player.reason='测试';dep.register_death(dep.player)
    assert dep.state=='wreck' and dep.death_wait==4 and dep.reserves==2
    assert not dep.deploy_player(dep.deploy_choice)
    dep.update(5.1);dep.choose_deployment(blue);assert dep.deploy_player(BASES[False]) and dep.reserves==1
    random_positions=[]
    for _ in range(10):
        trial=Game(True);trial.deploy_selected=True;assert trial.deploy_player(BASES[False])
        assert trial.player.p.distance_to(BASES[False])<=DEPLOY_RADIUS-44 and trial.terrain.free(trial.player.p,44)
        random_positions.append((round(trial.player.p.x),round(trial.player.p.y)))
    assert len(set(random_positions))>=8
    occupied=Game(True);occupied.deploy_selected=True;occupied.terrain.free=lambda *a,**kw:False
    assert not occupied.deploy_player(BASES[False]) and occupied.reserves==3 and occupied.state=='deploy'
    optics=Game();optics.player.p=V(1800,1400);optics.camera();follow=V(optics.cam)
    center=V(W/2,VIEW.centery);optics.camera(.016,True,center)
    assert not optics.scope and optics.zoom==1. and optics.cam==follow
    optics.change_zoom(5);assert optics.zoom>1. and optics.screen_to_world(center).distance_to(optics.player.p)<.01
    zoom=optics.zoom;optics.camera(.016,False,center);assert optics.zoom==zoom
    optics.change_zoom(-100);assert optics.zoom==.65;optics.draw(center)
    optics.change_zoom(100);assert optics.zoom==3.5;optics.draw(center)
    for point in (V(350,210),V(1000,690)):
        assert optics.world_to_display(optics.screen_to_world(point)).distance_to(point)<.01
    aim_world=optics.screen_to_world(V(800,500));optics.player.aim_at(aim_world,10.)
    assert abs(diff(optics.player.aim,angle(aim_world-optics.player.p)))<.01
    assert optics.shoot(optics.player)
    optics.paused=True;optics.camera(.016,True,center);assert optics.zoom==3.5 and not optics.scope
    fight=Game();fight.terrain.obstacles=[];fight.terrain.ponds=[];fight.allies=[];fight.enemies=[]
    fight.player.p=V(800,1000);friend=Tank((1000,1000));friend.ai=True;friend.body=0;friend.aim=0
    enemy=Tank((1200,1000),True);enemy.body=0;enemy.aim=180;enemy.cd=100
    fight.allies=[friend];fight.enemies=[enemy];fight.wave=1;fight.player.aim=0
    pristine=dict(friend.modules);fight.shoot(fight.player)
    for _ in range(35):fight.update(1/60)
    assert friend.modules==pristine and any(n<2 for n in enemy.modules.values())
    # Enemy AI selects an exposed teammate instead of always targeting the player.
    foe=Tank((1200,1000),True);foe.ai=True;foe.body=180;foe.aim=180;foe.cd=100
    fight.player.p=V(800,1800);fight.enemies=[foe];fight.allies=[friend]
    fight.ai_step(foe,.1);assert abs(diff(foe.aim,180))<5
    dep=Game(True);dep.choose_deployment(blue);dep.draw()
    output_dir=os.path.dirname(sys.executable if getattr(sys,'frozen',False) else os.path.abspath(__file__))
    import tempfile
    with tempfile.TemporaryDirectory() as testdir:
        profile=Profile(os.path.join(testdir,'profile.json'))
        assert not profile.equip('de_1_1') and not profile.unlock('cn_1_3')
        assert profile.unlock('cn_1_2') and profile.unlock('cn_1_3') and profile.research==120
        assert profile.equip('cn_1_3') and profile.selected=='cn_1_3'
        restored=Profile(profile.path);assert restored.selected==profile.selected and restored.research==120
        restored.select_country('de');assert all(VEHICLES[x]['country']=='de' for x in restored.lineups['de'] if x is not None)
        restored.select_country('cn');assert restored.selected=='cn_1_3'
        garage=Garage(screen,text,restored);garage.draw();pygame.image.save(screen,os.path.join(output_dir,'车库预览.png'))
        garage.tab='tech';garage.draw();pygame.image.save(screen,os.path.join(output_dir,'科技树预览.png'))
        national=Game(True,'cn',restored.lineups['cn'],0);national.deploy_selected=True
        assert national.deploy_player(BASES[False]) and national.player.vehicle_id=='cn_1_3' and national.used_slots=={0}
        assert all(VEHICLES[a.vehicle_id]['country']=='cn' for a in national.allies)
        national.spawn_wave();assert all(VEHICLES[a.vehicle_id]['country']=='de' for a in national.enemies)
        national.shoot(national.player);assert national.bullets[-1][8]==VEHICLES['cn_1_3']['pen']
        assert national.player.cd==VEHICLES['cn_1_3']['reload']
        national.player.dead=True;national.register_death(national.player);assert national.active_vehicle_slot==1
        national.choose_deployment((40,660));assert national.active_vehicle_slot==1
        national.update(5.1);national.deploy_selected=True;assert national.deploy_player(BASES[False])
        assert national.player.vehicle_id==restored.lineups['cn'][1] and national.used_slots=={0,1}
        try:Game(True,'cn',['cn_0_1','de_1_1','cn_2_1'])
        except ValueError:pass
        else:raise AssertionError('Foreign vehicle accepted')
        national.kills=2;national.wave=2;national.state='win';assert garage.collect_game(national)==190
        assert garage.collect_game(national)==0
    pygame.image.save(screen,os.path.join(output_dir,'部署预览.png'))
    g=Game();g.player.p=V(1610,1470);g.player.body=-35;g.player.aim=-65;g.camera();g.wave=2
    g.allies=[Tank((1430,1500)),Tank((1510,1290)),Tank((1660,1650)),Tank((1350,1660))]
    for ally in g.allies:ally.ai=True;ally.body=-30;ally.aim=-35
    g.enemies=[Tank((1910,1160),True),Tank((1350,1190),True),Tank((2080,1450),True,True)]
    visible_tree=min(g.terrain.trees,key=lambda tree:tree[0].distance_squared_to(g.player.p))
    g.terrain.crush_trees(V(visible_tree[0]),25,50);g.terrain.update(.6)
    target=g.enemies[0];result={'kind':'击穿','modules':['engine'],'line':(V(-30,0),V(30,0))};target.modules['engine']=0
    g.hitview=(target,result,5);g.say('AI 队友正在协同进攻 · 双方从对角基地部署');g.draw()
    path=os.path.join(os.path.dirname(sys.executable if getattr(sys,'frozen',False) else os.path.abspath(__file__)),'游戏预览.png')
    pygame.image.save(screen,path)
    g.change_zoom(5)
    g.draw(V(940,330));pygame.image.save(screen,os.path.join(output_dir,'缩放预览.png'))
    with tempfile.TemporaryDirectory() as td:
        modern_profile=Profile(os.path.join(td,'modern.json'));modern_profile.select_country('us');modern_profile.research=20000
        for tier in range(2,len(NATIONS['us']['branches'][1])+1):assert modern_profile.unlock(f'us_1_{tier}')
        final_id=f'us_1_{len(NATIONS["us"]["branches"][1])}';assert VEHICLES[final_id]['name']=='M1A3'
        modern_profile.equip(final_id);modern=Game(True,'us',modern_profile.lineups['us'],0);modern.deploy_selected=True;assert modern.deploy_player(BASES[False])
        modern.terrain.obstacles=[];modern.terrain.ponds=[];modern.player.p=V(1800,1400);modern.player.aim=0;modern.allies=[];modern.enemies=[]
        modern.camera(.016,True,V(W/2,VIEW.centery));assert not modern.scope and modern.zoom==1.
        modern.change_zoom(-100);assert modern.zoom==.65
        point=V(780,430);assert modern.world_to_display(modern.screen_to_world(point)).distance_to(point)<.01
        modern.change_zoom(100);assert modern.zoom==3.5
        modern.camera(.016,False);assert modern.zoom==3.5 and modern.scope_focus==modern.player.p
        assert modern.toggle_vision('night') and modern.vision=='night';modern.draw()
        assert modern.toggle_vision('thermal') and modern.vision=='thermal';modern.draw()
        modern.enemies=[Tank((2040,1390),True,vehicle='ussr_1_12'),Tank((1920,1610),True,vehicle='ussr_1_11')]
        modern.zoom=1.8;modern.camera(.016,True,V(W/2,VIEW.centery));modern.draw();pygame.image.save(screen,os.path.join(output_dir,'热成像预览.png'))
        assert modern.machine_gun(modern.player) and not modern.machine_gun(modern.player)
        modern.player.cd=0;assert modern.shoot(modern.player) and modern.bullets[-1][3]==5.2
        assert VEHICLES['de_1_10']['name']=='Leopard 2A7V' and VEHICLES['ussr_1_12']['name']=='T-80BVM'
        unsupported=Game(True,'de',['de_1_1','de_0_1','de_2_1']);assert not unsupported.toggle_vision('thermal')
        assert VEHICLES['de_1_3']['stabilizer']==0 and VEHICLES['us_1_1']['stabilizer']==1
        dual=Tank((1800,1400),vehicle=final_id);old=Tank((1800,1400),vehicle='ussr_1_1');dual.body=old.body=0;dual.aim=old.aim=0
        for _ in range(30):dual.drive(0,1,1/60,modern.terrain);old.drive(0,1,1/60,modern.terrain)
        assert abs(dual.aim)<.01 and abs(old.aim)>1 and dual.p.distance_to(V(1800,1400))<.01 and old.p.distance_to(V(1800,1400))>1
        garage=Garage(screen,text,modern_profile);garage.draw();pygame.image.save(screen,os.path.join(output_dir,'现代车库预览.png'))
        garage.tab='tech';garage.scroll(-100);assert garage.tech_row==garage.max_scroll()
        assert final_id in [ident for ident,r in garage.nodes()];garage.draw();pygame.image.save(screen,os.path.join(output_dir,'现代科技树预览.png'))
        for nation in NATIONS:
            garage.profile.select_country(nation);garage.tech_row=0
            for row in range(0,garage.max_scroll()+1,144):garage.tech_row=row;garage.draw()
        # Render every model and its in-battle silhouette; validate all catalogue entries.
        atlas=pygame.Surface((1280,math.ceil(len(VEHICLES)/5)*180));atlas.fill((25,32,31))
        for i,vehicle in enumerate(VEHICLES.values()):
            x=(i%5)*256;y=(i//5)*180
            draw_model(atlas,vehicle,(x+110,y+95),1.05,-15);draw_model(atlas,vehicle,(x+214,y+132),.35,0,True)
            atlas.blit(fonts[14].render(vehicle['name'],True,(222,227,207)),(x+12,y+12))
            assert vehicle['reload']>0 and vehicle['model'] and vehicle['country'] in NATIONS
        pygame.image.save(atlas,os.path.join(output_dir,'全载具模型预览.png'))
    print('PASS: modern tech progression, all models, persistent wheel zoom, machine guns, night/thermal rendering, stabilizers, dual transmission, national restrictions, save compatibility')
    small=Tank((1800,1400),vehicle='de_2_8');large=Tank((1800,1400),vehicle='ussr_3_7');small.body=large.body=small.aim=large.aim=0
    terrain=Terrain();terrain.obstacles=[(pygame.FRect(1820,1398,4,4),'house')]
    assert small.clear_at(small.p,0,terrain) and not large.clear_at(large.p,0,terrain)
    assert not small.shell_contact(V(1825,1398),V(1825,1402)) and large.shell_contact(V(1833,1398),V(1833,1402))
    partner=Tank((1836,1400),vehicle='de_2_8');partner.body=0;assert not small.overlaps(partner)
    partner=Tank((1868,1400),vehicle='ussr_3_7');partner.body=0;assert large.overlaps(partner)
    for ident,spec in VEHICLES.items():
        sample=Tank((1800,1400),vehicle=ident)
        assert abs(sample.body_rect.width-(spec['model'][0]*2-6)*MODEL_SCALE)<.001
        for rotation in (0,37,90,153):
            sample.body=sample.aim=rotation
            assert sample.shell_contact(sample.world((-100,0)),sample.world((100,0)))
    print('PASS: size-specific hulls, tracks/wheels, turret/barrel hits, 168 vehicles at four rotations, small/large obstacles and vehicle overlaps')
    assert len(VEHICLES)==210 and all(len(n['branches'])==6 for n in NATIONS.values())
    aa=Game(True,'de',['de_3_8','de_3_5','de_0_9']);aa.deploy_selected=True;assert aa.deploy_player(BASES[False])
    aa.player.p=V(1800,1400);aa.player.aim=0;aa.terrain.obstacles=[];aa.allies=[];aa.enemies=[]
    aa.air.planes=[{'p':V(2450,1400),'v':V(-80,0),'dead':False,'health':3,'bomb':100,'life':30.}]
    assert aa.air.lock_target() and aa.air.launch() and not aa.air.launch()
    for _ in range(240):aa.air.update(1/60)
    assert aa.air.kills==1 and not aa.air.planes
    aa.air.planes=[{'p':V(1950,1400),'v':V(),'dead':False,'health':3,'bomb':100,'life':30.}]
    cannon=Tank((1800,1400),vehicle='de_3_5')
    assert not aa.air.shell_hit(V(1900,1400),V(2000,1400),Tank((1800,1400),vehicle='de_1_10'))
    for _ in range(3):assert aa.air.shell_hit(V(1900,1400),V(2000,1400),cannon)
    assert aa.air.planes[0]['dead'];aa.shoot(cannon);assert abs(cannon.cd-cannon.stats["reload"])<1e-6
    print('PASS: six national branches, 168 vehicles, aircraft locking, guided missile interception, anti-aircraft cannon damage')
    print('PASS: barrel interception/probability, missed-barrel hull impact across frames, no repeated rolls, barrel/hull ricochet and reflected flight, rotated armor, random deployment, wheel zoom/right-button inactivity, allied AI, trees, driving, water, modules, win/lose, rendering')
    from VehicleData import DATA
    assert len(DATA)==len(VEHICLES)==210
    for ident,vehicle in VEHICLES.items():
        research=DATA[ident]
        assert all(field in research for field in ('weight','hp','forward','reverse','hull','turret'))
        assert vehicle['speed']==research['forward']*5 and vehicle['reverse']==research['reverse']*5
        assert all(ammo in research['ammo']+research['secondary'] for ammo in vehicle['ammo_options'])
    ammunition_game=Game(False,'us',['us_1_14','us_0_6','us_3_8'],0,{'us_1_14':3})
    assert ammunition_game.player.ammo['name']=='M829A3' and ammunition_game.shoot(ammunition_game.player)
    snapshot=ammunition_game.bullets[-1][10]
    assert ammunition_game.switch_ammo() and ammunition_game.player.cd>=ammunition_game.player.stats['ammo_reload']
    assert snapshot['name']=='M829A3' and not ammunition_game.shoot(ammunition_game.player)
    assert penetration_at(snapshot,2000)<penetration_at(snapshot,10)
    print('PASS: 168 individual sourced specifications, compatible ammunition, initial selection, projectile identity, switching/reloading and range penetration')
    assert (MW,MH)==(9000,7000)
    combined=Game(False,'de',['de_3_6','de_1_1','de_0_1'])
    plane={'p':combined.player.p+V(350,0),'v':V(0,0),'dead':False,'health':3,'bomb':99,'life':20}
    combined.air.planes=[plane];combined.air.lock=plane
    assert combined.shoot(combined.player) and combined.air.launch()
    combined.player.cd=0;assert combined.shoot(combined.player) and not combined.air.launch()
    smoke_game=Game(False,'ussr',['ussr_1_12','ussr_0_1','ussr_2_1'])
    smoke_game.terrain.obstacles=[];smoke_game.smokes=[]
    assert smoke_game.deploy_smoke() and not smoke_game.deploy_smoke()
    smoke_game.smokes=[];smoke_game.add_smoke((1200,1000),'ess');smoke_game.update_smoke(2)
    assert not smoke_game.visible((1000,1000),(1400,1000)) and smoke_game.visible((1000,1000),(1400,1000),thermal=True)
    assert sum(v['independent_missiles'] for v in VEHICLES.values())==23
    assert VEHICLES['ussr_0_1']['br']==1.0 and VEHICLES['ussr_1_5']['br']==8.7
    low_battle=Game(True,'ussr',['ussr_0_1']+[None]*7)
    low_battle.deploy_selected=True;assert low_battle.deploy_player(BASES[False])
    for wave_index in range(5):
        low_battle.enemies=[];low_battle.spawn_wave()
        assert low_battle.enemies and all(t.stats['br']<=2 for t in low_battle.enemies+low_battle.allies)
    print('PASS: BR-based matchmaking, BT-5 low bracket across five waves and compatible AI teammates')
    redeploy_test=Game();redeploy_test.ai_flights.chance=0;redeploy_test.spawn_wave();lost=redeploy_test.enemies[0]
    lost.dead=True;lost.reason='Test';redeploy_test.register_death(lost);redeploy_test.register_death(lost)
    assert len(redeploy_test.enemy_queue)==1 and redeploy_test.ground_kills==1
    redeploy_test.update_enemy_redeploy(7.9);assert len(redeploy_test.enemies)==TEAM_SIZE-1
    redeploy_test.update_enemy_redeploy(.11);assert len(redeploy_test.enemies)==TEAM_SIZE and not redeploy_test.enemy_queue
    bmpt_test=Game(True,'ussr',['ussr_2_11']+[None]*7);bmpt_test.deploy_selected=True
    assert bmpt_test.deploy_player(BASES[False]);assert bmpt_test.shoot(bmpt_test.player)
    assert len(bmpt_test.bullets)==2 and bmpt_test.player.missile_count==4
    assert bmpt_test.grenade_launcher() and bmpt_test.player.grenade_count==599
    print('PASS: timed enemy redeployment, duplicate death guard, BMPT dual guns and independent grenade weapon')
    aps_game=Game();aps_game.terrain.blocks_shell=lambda *a:False
    for country in ('cn','ussr','de','us'):
        last=f"{country}_4_{len(NATIONS[country]['branches'][4])}"
        protected=Tank((1000,1000),vehicle=last);protected.body=protected.aim=0
        attacker=Tank((700,1000),True)
        aps_round={'name':'APS self-test','type':'ATGM','penetration':[600]*6,'velocity':500}
        assert aps_game.try_aps(protected,V(800,1000),V(900,1000),V(500,0),aps_round,attacker)
        assert protected.aps_charges==7
        assert not aps_game.try_aps(protected,V(800,1000),V(900,1000),V(500,0),aps_round,attacker)
    print('PASS: four fifth-branch endpoints and active protection interception/cooldown')
    print('PASS: independent cannon/missile fire and reloads, equipment-specific smoke, thermal distinction and expanded map')
    from GroundFlight import combined_self_test
    from AircraftModels import model_self_test
    model_self_test(globals())
    from AircraftRadar import radar_self_test
    radar_self_test(globals())
    from AircraftLoadouts import loadout_self_test
    loadout_self_test(globals())
    combined_self_test(globals())
    from Artillery import self_test as artillery_self_test
    artillery_self_test(globals())
    from BattleObjectives import map_self_test
    map_self_test(globals())
    from NuclearMission import self_test as nuclear_self_test
    nuclear_self_test(globals())
    from CombatUpdateChecks import self_test as combat_update_test
    combat_update_test(globals())
    from LandingDevices import self_test as landing_devices_test
    landing_devices_test(globals())
    from LANChecks import run as lan_checks
    lan_checks(globals())
    from JapanChecks import run as japan_checks
    japan_checks(globals())
    from ModernChecks import run as modern_checks
    modern_checks(globals())
    from PremiumChecks import run as premium_checks
    premium_checks(globals())


def main():
    global screen,W,H
    import WindowLayout
    menu_screen=screen if TEST else pygame.Surface(pygame.display.get_surface().get_size()).convert()
    screen=menu_screen
    W,H=screen.get_size();VIEW.update(0,68,W,H-110)
    battle_screen=pygame.Surface(pygame.display.get_surface().get_size()).convert()
    if TEST:self_test();pygame.quit();return
    from InputBindings import get_controls
    controls=get_controls()
    from LANSquad import Room
    from LANSession import Session
    garage=Garage(screen,text);g=None;menu=True;running=True;room=Room(garage.profile);session=None
    squad_button=pygame.Rect(1045,588+garage.bottom_offset(),205,42)
    from DailyRewards import Panel
    rewards=Panel(garage)
    from AutoUpdate import Updater
    updater=Updater(frozen=False) if '--exit-check' in sys.argv else Updater()
    import PresentationSettings
    presentation=PresentationSettings.Settings();PresentationSettings.ACTIVE=presentation
    presentation_button=pygame.Rect(510,H-37,285,30)
    def battle():
        p=garage.profile
        battle=Game(True,p.country,p.lineups[p.country],p.active[p.country],p.ammo_choices,p.missile_choices)
        battle.flight.weapons=p.aviation.weapons
        if p.late_join:
            from LateJoin import seed_battle
            seed_battle(battle)
        return battle
    if '--exit-check' in sys.argv:pygame.event.clear();pygame.event.post(pygame.event.Event(pygame.QUIT))
    while running:
        dt=min(clock.tick(60)/1000,.04)
        screen=menu_screen if menu else battle_screen
        W,H=screen.get_size();VIEW.update(0,68,W,H-110);WindowLayout.select(screen)
        for ev in pygame.event.get():
            if ev.type==pygame.VIDEORESIZE:
                pygame.display.set_mode((max(1280,ev.w),max(820,ev.h)),pygame.RESIZABLE)
                battle_screen=pygame.Surface(pygame.display.get_surface().get_size()).convert()
                menu_screen=pygame.Surface(battle_screen.get_size()).convert();garage.screen=menu_screen
                presentation_button.y=menu_screen.get_height()-37
                squad_button.y=588+garage.bottom_offset()
                continue
            ev=window_event(ev)
            if ev.type==pygame.QUIT:running=False
            if ev.type==pygame.DROPFILE:
                presentation.import_drop(ev.file);presentation.open=True;menu=True;continue
            if ev.type in (pygame.WINDOWFOCUSGAINED,pygame.WINDOWENTER):game_input.disable()
            if menu and presentation.open:
                presentation.event(ev);continue
            if menu and not rewards.open and not room.open and ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1 and presentation_button.collidepoint(ev.pos):
                presentation.open=True;continue
            if menu and not rewards.open and not room.open and ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                handled,restart_update=updater.click(ev.pos)
                if handled:
                    if restart_update:running=False
                    continue
            if menu and rewards.open:
                rewards.event(ev);continue
            if menu and not room.open and ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1 and rewards.button().collidepoint(ev.pos):
                rewards.open=True;continue
            if menu and room.open:
                room.event(ev);continue
            if menu and ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1 and squad_button.collidepoint(ev.pos):
                room.open=True;continue
            if not menu and g.state=='play' and not g.player.dead and g.battery.placing and ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                point=list(g.screen_to_world(ev.pos))
                if session:session.issue('launcher_place',point=point)
                else:g.battery.place(point)
                continue
            ev=controls.event(ev,'garage' if menu else (session.input_context() if session else g.input_context()),None if menu else g)
            if ev is None:continue
            if menu:
                if ev.type==pygame.KEYDOWN:
                    if ev.key==pygame.K_RETURN:
                        if any(garage.profile.lineups[garage.profile.country]):g=battle();menu=False
                        else:garage.notice='请先装备至少一辆载具'
                    elif ev.key==pygame.K_t:garage.tab='tech'
                    elif ev.key==pygame.K_ESCAPE:
                        if garage.tab=='tech':garage.tab='garage';garage.preview=garage.profile.selected
                        else:running=False
                elif ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                    if garage.click(ev.pos)=='battle':g=battle();menu=False
                elif ev.type==pygame.MOUSEBUTTONDOWN and ev.button==3:garage.remove_slot(ev.pos)
                elif ev.type==pygame.MOUSEWHEEL and garage.tab=='tech':garage.scroll(ev.y)
                elif ev.type==pygame.MOUSEBUTTONUP and ev.button==1:garage.dragging=False
                elif ev.type==pygame.MOUSEMOTION:garage.motion(ev.pos)
            else:
                if session:
                    session.event(ev);continue
                if ev.type==pygame.KEYDOWN:
                    if ev.key==pygame.K_ESCAPE:garage.collect_game(g);menu=True;garage.preview=garage.profile.selected
                    elif ev.key==pygame.K_F3 and not g.flight.active:g.deploy_ammo_box()
                    elif ev.key==pygame.K_F11 and not g.flight.active:g.battery.toggle()
                    elif ev.key==pygame.K_F12 and not g.flight.active:g.battery.switch()
                    elif ev.key==pygame.K_u and not g.flight.active:
                        from Reconnaissance import toggle
                        toggle(g)
                    elif ev.key==pygame.K_t and not g.flight.active:
                        from Reconnaissance import mark
                        mark(g,g.screen_to_world(pygame.mouse.get_pos()))
                    elif g.drone_active and ev.key not in (pygame.K_r,pygame.K_p):pass
                    elif g.flight.event(ev):
                        if ev.key in (pygame.K_m,pygame.K_n):garage.profile.aviation.weapons=g.flight.weapons;garage.profile.save()
                    elif ev.key==pygame.K_RETURN and g.state=='deploy':g.deploy_player(g.deploy_choice)
                    elif ev.key==pygame.K_r:garage.collect_game(g);g=battle()
                    elif ev.key==pygame.K_p and g.state in ('play','wreck'):g.paused=not g.paused
                    elif ev.key==pygame.K_b:
                        if g.switch_ammo():garage.profile.ammo_choices.update(g.ammo_choices);garage.profile.save()
                    elif ev.key==pygame.K_m:
                        if g.switch_missile():garage.profile.missile_choices.update(g.missile_choices);garage.profile.save()
                    elif ev.key==pygame.K_o:g.artillery.toggle()
                    elif ev.key==pygame.K_z:g.deploy_smoke()
                    elif ev.key==pygame.K_h:g.toggle_ess()
                    elif ev.key==pygame.K_F2:g.air.cycle_range()
                    elif ev.key==pygame.K_y:g.air.cycle_target()
                    elif ev.key==pygame.K_q:g.air.lock_target()
                    elif ev.key==pygame.K_j:g.air.launch()
                    elif ev.key==pygame.K_n:g.toggle_vision('night')
                    elif ev.key==pygame.K_v:g.toggle_vision('thermal')
                    elif ev.key==pygame.K_l:g.night_battle=not g.night_battle
                    elif ev.key==pygame.K_x:g.xray=not g.xray
                    elif ev.key==pygame.K_e and not g.paused and g.state=='play':g.player.extinguish()
                elif ev.type==pygame.MOUSEWHEEL:g.change_zoom(ev.y)
                elif ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1 and g.state=='deploy':g.choose_deployment(ev.pos)
                elif ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1 and g.battery.placing:g.battery.place(g.screen_to_world(ev.pos))
        screen=menu_screen if menu else battle_screen
        W,H=screen.get_size();VIEW.update(0,68,W,H-110);WindowLayout.select(screen)
        if menu:
            room.update(dt)
            if room.started:
                session=Session(room,globals(),room.started);g=session.g;menu=False
            garage.time+=dt
            if presentation.open:presentation.draw(screen,text,garage.button)
            elif room.open:room.draw(screen,text)
            elif rewards.open:rewards.draw()
            else:
                garage.draw();garage.button(squad_button,"局域网小队");garage.button(rewards.button(),"每日任务 / 高级载具");updater.draw(garage);garage.button(presentation_button,"声音 / 自定义语言包")
        elif session:
            session.update(dt);session.draw();g=session.g
            if session.exit or session.to_lobby:
                garage.collect_game(g);menu=True
                if session.exit:room.close(keep_notice=True);room.open=False
                session=None
        else:
            g.update(dt);g.draw()
            if g.state in ('win','lose'):garage.collect_game(g)
        presentation.update(None if menu else g,dt)
        controls.draw(screen,text)
        present_window(screen)
    if g:garage.collect_game(g)
    updater.close()
    if presentation.bank:presentation.bank.close()
    if presentation.channel and pygame.mixer.get_init():presentation.channel.stop()
    room.close();game_input.restore();pygame.quit()
if __name__=='__main__':main()


