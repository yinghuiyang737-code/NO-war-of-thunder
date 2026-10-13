"""Finite personal ammunition depots for support vehicles."""
import math,pygame
from pygame.math import Vector2 as V
RANGE=200.

def owner(g,t):
    network=getattr(t,'network_owner',None)
    if network is not None:return network
    return 0 if t is g.player else None

def supported(t):return bool(t.stats.get('ammo_box')) and not getattr(t,'airborne',False)

def deploy(g):
    t=g.player;ident=owner(g,t)
    if g.state!='play' or g.paused or t.dead or g.flight.active or not supported(t):g.say('该载具不能部署弹药箱');return False
    if getattr(t,'ammo_box_used',False):g.say('本车已使用弹药箱');return False
    if any(b['owner']==ident for b in g.ammo_boxes):g.say('已有个人弹药箱，最多一个');return False
    if abs(t.speed)>=3:g.say('停车后部署弹药箱');return False
    point=None
    for delta in (180,135,225,90,270,45,315,0):
        p=t.p+V(t.half_length+45,0).rotate(t.body+delta)
        if g.terrain.free(p,15) and not g.terrain.in_shallow(p):point=p;break
    if point is None:g.say('附近没有放置弹药箱的空地');return False
    caps=dict(shells=t.shell_capacity,mg_rounds=1200,missile_count=t.stats.get('missile_capacity') or 0,grenade_count=t.stats.get('secondary_capacity',600) if t.stats.get('grenade') else 0)
    g.ammo_boxes.append(dict(owner=ident,p=point,stock={k:math.ceil(v*1.5) for k,v in caps.items()}))
    t.ammo_box_used=True;g.say('个人弹药箱已放置 · 仅自己可用 · 靠近停车自动补给');return True

def supply_from_box(g,t,dt):
    ident=owner(g,t)
    if ident is None or t.dead or getattr(t,'airborne',False) or abs(t.speed)>=3:return False
    box=next((b for b in g.ammo_boxes if b['owner']==ident and t.p.distance_to(b['p'])<=RANGE),None)
    if box is None:return False
    stock=box['stock'];caps=dict(shells=t.shell_capacity,mg_rounds=1200,missile_count=t.stats.get('missile_capacity') or 0,grenade_count=t.stats.get('secondary_capacity',600) if t.stats.get('grenade') else 0)
    def missing():return any(stock.get(k,0)>0 and (getattr(t,k,0) or 0)<v for k,v in caps.items())
    active=missing();t.supply_ammo_active=active;t.supply_crew_active=False
    t.supply_timer=getattr(t,'supply_timer',0.)+dt if active else 0.
    while t.supply_timer>=5:
        t.supply_timer-=5
        for key,rate in (('shells',5),('mg_rounds',100),('missile_count',1),('grenade_count',50)):
            value=getattr(t,key,0) or 0;amount=min(rate,stock.get(key,0),max(0,caps[key]-value))
            if amount:setattr(t,key,value+amount);stock[key]-=amount
            if key=='shells' and hasattr(t,'premium_ammo'):
                empty=t.premium_mag==0;t.premium_ammo=t.shells;t.premium_mag=min(t.stats['ready_rack'],t.premium_ammo,t.premium_mag+amount)
                if empty and t.premium_mag>0 and t.cd>t.stats['reload']:t.cd=0.;t.reload_duration=t.stats['reload']
        if not missing():t.supply_timer=0.;break
    t.supply_ammo_active=missing()
    if not any(stock.values()):g.ammo_boxes.remove(box)
    return True

def install(Game,api):
    for data in api['VEHICLES'].values():
        data['ammo_box']=bool(data.get('artillery') or data.get('branch')==3 or data.get('weapon')=='auto')
        if data['ammo_box'] and '个人弹药箱' not in data.setdefault('equipment',[]):data['equipment'].append('个人弹药箱')
    old_init=Game.__init__;old_draw=Game.draw
    def init(g,*args,**kw):old_init(g,*args,**kw);g.ammo_boxes=[]
    def draw(g,*args,**kw):
        old_draw(g,*args,**kw)
        if g.state not in ('play','wreck') or g.flight.active or g.paused:return
        screen=api['screen'];clip=screen.get_clip();screen.set_clip(api['VIEW'])
        for b in g.ammo_boxes:
            p=g.world_to_display(b['p']);size=max(9,round(22*g.zoom));r=pygame.Rect(0,0,size*2,size);r.center=p
            pygame.draw.rect(screen,(82,102,58),r,border_radius=2);pygame.draw.rect(screen,(190,187,131),r,1)
            pygame.draw.line(screen,(184,172,105),r.midtop,r.midbottom,2)
            if b['owner']==owner(g,g.player):
                pygame.draw.circle(screen,(127,167,98),p,round(RANGE*g.zoom),1)
                api['text']('个人弹药箱',p+V(0,-size-18),14,(199,224,158),True)
                left=b['stock'];api['text']('炮弹 '+str(left['shells'])+' / 导弹 '+str(left['missile_count']),p+V(0,size+4),14,(199,224,158),True)
        screen.set_clip(clip)
        if supported(g.player) and not g.player.dead:
            label='弹药箱 '+g.controls.label('ground.ammo_box')+' · '+('已使用' if getattr(g.player,'ammo_box_used',False) else '停车放置 · 150% 备弹')
            api['text'](label,(350,api['H']-188),14,(184,205,154))
    Game.__init__=init;Game.draw=draw;Game.deploy_ammo_box=deploy

