"""Continuous air fuzes, interceptable missile contacts and combat notices."""
import pygame
from pygame.math import Vector2 as V

def closest(a,b,p):
    d=b-a
    return a+d*max(0,min(1,(p-a).dot(d)/d.length_squared())) if d.length_squared() else V(a)

def fuse_radius(ammo,missile=False):
    # Distances here are world units, not quoted real fuze radii.
    if missile:return 42.
    tag=((ammo or {}).get('type','')+' '+(ammo or {}).get('name','')).upper()
    return 24. if any(x in tag for x in ('HE-VT','HEVT','HEF-VT','HEFI-VT','PROXIMITY','近炸')) else 0.

def destroy_missile(g,target,owner):
    if target.get('dead') or target.get('life',1)<=0:return
    target['life']=0.;target['dead']=True;g.burst(target['p'],(255,184,100),12)
    if g.is_player(owner):
        g.score+=25;g.combat_notice=dict(label='拦截导弹 +25',expires=g.time+2.)

def damage_air(g,q,owner,ammo,point):
    q['last_attacker']=owner;q['last_weapon']=(ammo or {}).get('name','近炸弹')
    if q.get('managed'):
        q['ai_plane'].damage(point,True)
        if q['ai_plane'].dead:g.air.kill_plane(q,owner)
    elif q.get('controlled'):
        q['controlled'].g.player.last_attacker=owner;q['controlled'].g.player.last_weapon=q['last_weapon']
        q['controlled'].damage(point,True)
    else:
        q['health']=q.get('health',3)-2
        if q['health']<=0:g.air.kill_plane(q,owner)
    g.record_air_hit(q,point,owner,q['last_weapon']);g.burst(point,(255,183,104),10)

def fragments(g,point,owner,ammo,primary=None):
    """Cast radial fragment rays; armour and real module contacts decide ground damage."""
    import math
    point=V(point);radius=85. if fuse_radius(ammo) else 125.
    team=int(getattr(owner,'enemy',False)) if owner is not None else 0
    from RadarContacts import missiles
    for q in list(g.air.planes)+list(missiles(g)):
        if q is primary or q.get('dead') or q.get('team',1)==team:continue
        if q['p'].distance_to(point)>radius:continue
        if q.get('missile'):destroy_missile(g,q,owner)
        else:damage_air(g,q,owner,ammo,point)
    fragment=dict(ammo or {},type='AP',caliber=5,explosive_kg=0,name=(ammo or {}).get('name','近炸')+' · 破片',penetration=[22.]*6)
    for t in g.vehicles():
        if t.dead or getattr(t,'airborne',False) or int(t.enemy)==team or t.p.distance_to(point)>radius+t.radius:continue
        for n in range(48):
            ray=V(math.cos(n*math.tau/48),math.sin(n*math.tau/48))*radius
            result=t.hit(point,point+ray,ray,0,penetration_value=22,ammo=fragment)
            if result and result.get('modules'):
                t.last_attacker=owner;t.last_weapon=fragment['name'];g.record_hit(t,result,owner,fragment['name'])
                if t.dead:g.register_death(t)
                break
    g.burst(point,(255,192,113),24)

def install(Game,api):
    from AirDefense import AirDefense
    old_shell=AirDefense.shell_hit
    def shell(self,start,end,owner,ammo=None):
        if not owner or not owner.vehicle_id or owner.stats.get('branch')!=3 and not fuse_radius(ammo):return old_shell(self,start,end,owner,ammo)
        from RadarContacts import missiles
        radius=fuse_radius(ammo)
        # Ordinary cannon rounds may intercept on direct contact only.
        for m in missiles(self.g):
            if m['team']==int(owner.enemy):continue
            point=closest(start,end,m['p'])
            if point.distance_to(m['p'])<=max(4,radius):
                if radius:fragments(self.g,point,owner,ammo,primary=m)
                destroy_missile(self.g,m,owner);return True
        if radius:
            for q in self.planes:
                if q['dead'] or q.get('team',1)==int(owner.enemy):continue
                point=closest(start,end,q['p'])
                if point.distance_to(q['p'])<=radius:fragments(self.g,point,owner,ammo,primary=q);damage_air(self.g,q,owner,ammo,point);return True
        return old_shell(self,start,end,owner,ammo)
    AirDefense.shell_hit=shell
    def cycle_range(self):
        t=self.radar_vehicle()
        if not t.stats.get('radar'):self.g.say('这辆载具没有搜索雷达');return False
        values=(.125,.25,.5,1.)
        scale=getattr(t,'radar_scale',1.)
        t.radar_scale=values[(min(range(4),key=lambda i:abs(values[i]-scale))+1)%4]
        self.g.say(f'雷达量程 {self.scan_range/8000:g} km');return True
    def cycle_target(self):
        t=self.g.player
        if not (t.stats.get('radar') or t.stats.get('branch')==3):return False
        candidates=[q for q in self.targets(t) if self.valid(q,t) and self.position(q).distance_to(t.p)<self.scan_range and self.sight(q,t)]
        candidates.sort(key=lambda q:(not (isinstance(q,dict) and q.get('missile')),self.position(q).distance_squared_to(t.p)))
        current=next((i for i,q in enumerate(candidates) if q is self.lock),-1)
        self.lock=candidates[(current+1)%len(candidates)] if candidates else None
        self.g.say('锁定敌方导弹' if isinstance(self.lock,dict) and self.lock.get('missile') else '切换锁定目标' if self.lock is not None else '范围内没有目标');return self.lock is not None
    AirDefense.cycle_range=cycle_range;AirDefense.cycle_target=cycle_target
    old_hit=Game.record_hit;old_air=Game.record_air_hit;old_draw=Game.draw_battle_feedback
    def hit(g,target,result,owner,weapon=''):
        old_hit(g,target,result,owner,weapon)
        if not g.is_player(owner) or not target.enemy or target.dead or result.get('continue'):return
        touched=result.get('modules') or []
        if not touched:return
        critical=any(target.modules.get(k,2)==0 and k in ('gunner','driver','commander','loader','engine','breech') for k in touched)
        g.combat_notice=dict(label='重创目标' if critical else '命中',expires=g.time+2.)
    def air_hit(g,target,point,owner,weapon=''):
        old_air(g,target,point,owner,weapon)
        if not g.is_player(owner) or target.get('team',1)==int(owner.enemy) or target.get('dead'):return
        p=target.get('ai_plane') or (target['controlled'].plane if target.get('controlled') else None)
        critical=p and any(v==0 for v in p.modules.values())
        g.combat_notice=dict(label='重创目标' if critical else '命中',expires=g.time+2.)
    def draw(g):
        old_draw(g);notice=getattr(g,'combat_notice',None)
        if notice and notice['expires']>g.time and not g.personal_kills and g.state in ('play','wreck'):
            s=api['screen'];api['text'](notice['label'],(s.get_width()/2,max(150,s.get_height()*.22)),24,(255,222,152),True)
    Game.record_hit=hit;Game.record_air_hit=air_hit;Game.draw_battle_feedback=draw

def checks(api):
    assert closest(V(0,0),V(100,0),V(50,10))==V(50,0)
    assert fuse_radius({'type':'HE-VT'})>0 and fuse_radius({'type':'APFSDS'})==0
    assert fuse_radius({'type':'HE-TF'})==0
    vehicle=next(k for k,v in api['VEHICLES'].items() if v['country']=='ussr' and v['branch']==3)
    g=api['Game'](False,'ussr',[vehicle]+[None]*11)
    t=g.player;t.stats=dict(t.stats,radar=True,branch=3)
    air=g.air;before=air.scan_range;assert air.cycle_range() and air.scan_range==before*.125
    m={'p':t.p+V(100,0),'v':V(100,0),'life':4.,'owner':g.enemies[0] if g.enemies else None,'team':1,'kind':'missile'}
    g.flight.projectiles.append(m)
    from RadarContacts import missiles
    assert any(q is m for q in missiles(g)) and air.valid(m,t)
    air.lock=m;assert air.cycle_target()
    score=g.score;assert air.shell_hit(t.p,t.p+V(200,0),t,{'type':'AP','name':'测试'})
    assert m['life']==0 and not air.valid(m,t) and g.score==score+25
    # A VT shell passes beside the aircraft; AP must miss the same trajectory.
    q={'p':t.p+V(100,23),'v':V(),'dead':False,'team':1,'health':10,'life':30.,'bomb':100}
    air.planes=[q];g.flight.projectiles=[]
    assert not air.shell_hit(t.p,t.p+V(200,0),t,{'type':'AP'})
    assert air.shell_hit(t.p,t.p+V(200,0),t,{'type':'HE-VT','name':'测试近炸'}) and q['health']==8
    # An actual command-guided missile intercepts the selected incoming missile.
    air.planes=[];m=dict(p=t.p+V(100,0),v=V(),life=5.,team=1,kind='missile')
    g.flight.projectiles=[m];air.lock=m;t.stats.update(missile=True,independent_missiles=True,missile_reload=1.)
    t.stats['ammo_options']=[{'name':'测试拦截弹','type':'SAM'}];t.missile_index=0;t.missile_count=2;t.missile_cd=0;t.aim=0
    assert air.launch() and t.missile_count==1
    air.update(.1);air.update(.1);assert m.get('dead') and m['life']==0
    # A SAM passes outside the aircraft hull but detonates on its air fuze.
    q=dict(p=t.p+V(100,40),v=V(),dead=False,team=1,health=10,life=30.,bomb=100)
    g.flight.projectiles=[];air.planes=[q];air.missiles=[];air.lock=None;t.missile_cd=0
    assert air.launch();air.update(.1);air.update(.1);assert q['dead']
    air.planes=[]
    # Friendly missiles are never lock candidates or interception victims.
    friendly=dict(p=t.p+V(100,0),v=V(),life=5.,team=0,kind='missile');g.flight.projectiles=[friendly]
    assert not air.valid(friendly,t) and not air.shell_hit(t.p,t.p+V(200,0),t,{'type':'HE-VT'})
    target=api['Tank'](t.p+V(50,0),enemy=True,vehicle=vehicle);target.modules['engine']=1
    g.record_hit(target,{'kind':'击穿','modules':['engine']},t);assert g.combat_notice['label']=='命中'
    target.modules['engine']=0;g.record_hit(target,{'kind':'击穿','modules':['engine']},t);assert g.combat_notice['label']=='重创目标'
    print('PASS missile identity, actual interception, friendly exclusion, high-speed VT vs AP, radar ranges and hit/critical notices')




