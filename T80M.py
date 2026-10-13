"""User-defined fictional T80M and infrared ground fire-control assistance."""
import copy,math
from pygame.math import Vector2 as V
IDENT='ussr_t80m_arna_m'

def register(vehicles,nations):
    from VehicleData import DATA,configure
    from GroundModels import FAMILIES
    from VehicleModels import SHAPES
    from GroundEquipment import EQUIPMENT
    parent=next(k for k,d in vehicles.items() if d['name']=='T-80BVM')
    base=vehicles[parent];v=copy.deepcopy(base);d=copy.deepcopy(DATA[parent]);name='T80M Arna-M（架空）'
    v.update(id=IDENT,name=name,parent=parent,tier=base['tier']+1,cost=base['cost']+220,fictional=True,simulation=True,model=(65,26,'box',0,21,106))
    shell=copy.deepcopy(next(a for a in d['ammo'] if a['type']=='APFSDS'))
    shell.update(name='3BM72（架空）',penetration=[613.,607.,596.,580.,564.,548.],velocity=1750.,source='玩家指定架空弹药',source_note='近距穿深 613 mm 为玩家设定，弹速与距离衰减为游戏模拟',explosive_kg=0)
    d['ammo']=[shell]+d['ammo'];d.update(rank='VIII',br=13.3,aps='Arna-M（架空）',status='simulation',source='架空游戏设定',source_note='架空载具：以 T-80BVM 为基础；装甲、动力、红外火控与 Arna-M 主动防御均为游戏设定',br_note='本游戏模拟分房',primary_weapon_name='125 mm 2A46M（架空改进）')
    DATA[IDENT]=d;configure(v)
    v.update(ground_ir_lock=True,ground_lock_range=4000.,front_profile=copy.deepcopy(base['front_profile']),armor_note='架空载具，防护沿 T-80BVM 作游戏模拟',armor_reference='架空游戏设定',visual_length_m=base.get('visual_length_m',7.6),visual_width_m=base.get('visual_width_m',3.6))
    v['equipment']+=['红外地面锁定 / 自动提前量','架空载具 / 游戏设定'];FAMILIES[name]=FAMILIES[base['name']];SHAPES[name]=v['model'];EQUIPMENT[IDENT]=copy.deepcopy(EQUIPMENT.get(parent,{}))
    vehicles[IDENT]=v;nations['ussr']['branches'][v['branch']].append(name)

def lead(t,target):
    speed=max(1,(t.ammo.get('velocity') or 950)*.75 if t.ammo else 850)
    velocity=V(target.speed,0).rotate(target.body);origin=t.muzzle();delta=target.p-origin
    a=velocity.length_squared()-speed*speed;b=2*delta.dot(velocity);c=delta.length_squared()
    roots=[]
    if abs(a)<1e-8:
        if abs(b)>1e-8:roots=[-c/b]
    elif b*b-4*a*c>=0:
        root=math.sqrt(b*b-4*a*c);roots=[(-b-root)/(2*a),(-b+root)/(2*a)]
    flight=min((r for r in roots if r>0),default=delta.length()/speed)
    return target.p+velocity*min(10,flight)

def install(Game,api):
    from AirDefense import AirDefense
    old_lock=AirDefense.lock_target;old_update=AirDefense.update;old_hud=AirDefense.hud
    def lock(self):
        g=self.g;t=g.player
        if not t.stats.get('ground_ir_lock'):return old_lock(self)
        point=g.screen_to_world(__import__('pygame').mouse.get_pos())
        pool=[q for q in g.vehicles() if q is not t and not q.dead and q.enemy!=t.enemy and not getattr(q,'airborne',False) and q.p.distance_to(t.p)<=t.stats['ground_lock_range'] and g.visible(t.p,q.p,True)]
        self.lock=min(pool,key=lambda q:q.p.distance_squared_to(point),default=None)
        g.say('红外锁定地面目标 · 已计算当前炮弹提前量' if self.lock else '没有可见的敌方地面目标');return self.lock is not None
    def update(self,dt):
        old_update(self,dt);t=self.g.player;q=self.lock
        if t.stats.get('ground_ir_lock') and q is not None and (isinstance(q,dict) or not self.valid(q,t) or q.p.distance_to(t.p)>t.stats['ground_lock_range'] or not self.g.visible(t.p,q.p,True)):self.lock=None
    def hud(self):
        old_hud(self);g=self.g;t=g.player
        if not t.stats.get('ground_ir_lock') or t.dead or g.state!='play':return
        api['text']('红外地面锁定 '+g.controls.label('ground.lock')+' · 解除 '+g.controls.label('ground.radar_unlock')+' · 当前炮弹自动提前量',(350,120),14,(177,230,186))
        if self.valid(self.lock,t) and not isinstance(self.lock,dict):
            point=g.world_to_display(lead(t,self.lock))
            if api['VIEW'].collidepoint(point):
                import pygame
                pygame.draw.circle(api['screen'],(255,216,116),point,9,1)
                api['text']('提前量',point+V(0,15),14,(255,216,116),True)
    AirDefense.lock_target=lock;AirDefense.update=update;AirDefense.hud=hud

def checks(api):
    from VehicleData import DATA
    v=api['VEHICLES'][IDENT];assert v['fictional'] and '架空' in v['name'] and v['aps'] and v['ground_ir_lock']
    assert v['ammo_options'][0]['penetration'][0]==613 and v['parent'] in api['VEHICLES']
    t=api['Tank']((1000,1000),vehicle=IDENT);q=api['Tank']((1500,1000),enemy=True,vehicle=IDENT);q.speed=100;q.body=90
    point=lead(t,q);assert point.y>q.p.y
    t.stats=copy.deepcopy(t.stats);t.stats['ammo_options'][0]['velocity']=800
    assert lead(t,q).y>point.y
    g=api['Game'](False,'ussr',[IDENT]+[None]*11);g.state='play';g.player=t;g.enemies=[q];g.terrain.blocks_shell=lambda *a:False;g.visible=lambda *a:True
    assert g.air.lock_target() and g.air.lock is q
    g.visible=lambda *a:False;g.air.update(.01);assert g.air.lock is None
    t.p=V(1000,1000);assert g.try_aps(t,V(800,1000),V(900,1000),V(500,0),dict(type='ATGM'),q)
    print('PASS fictional T80M, 613mm 3BM72, ammo-speed ground lead, infrared lock/loss and active protection')
