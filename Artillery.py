"""SPH overhead observation, bounded dispersion and delayed landing-only impacts."""
import math,random,copy
import pygame
from pygame.math import Vector2 as V
from AircraftPhysics import direction,bearing,difference
from VehicleGeometry import segment_polygon,MODEL_SCALE
from VehicleModels import draw_model
from CombatEffects import spall
from VehicleData import explosive

class Artillery:
    def __init__(self,g,api):
        self.g=g;self.api=api;self.enabled=False;self.focus=V(g.player.p);self.normal_zoom=1.;self.shells=[];self.blasts=[];self.settle=0.;self.last_aim=None;self.previous_heading=g.player.aim
    def toggle(self):
        g=self.g
        if g.state!='play' or g.paused or g.player.dead or g.flight.active:return False
        if not g.player.stats.get('artillery'):g.say('这辆载具没有火炮模式');return False
        self.enabled=not self.enabled;self.settle=0.;self.last_aim=None
        if self.enabled:self.normal_zoom=g.zoom;g.zoom=.2;self.focus=V(g.player.p)
        else:g.zoom=self.normal_zoom
        g.camera();g.say('火炮模式：移到屏幕边缘移动观察 · 圆圈为最大落点偏移' if self.enabled else '已返回普通直射视角');return True
    def reset(self):
        if self.enabled:self.g.zoom=self.normal_zoom
        self.enabled=False;self.settle=0.;self.last_aim=None
    def aim(self,mouse=None):
        g=self.g;point=g.screen_to_world(pygame.mouse.get_pos() if mouse is None else mouse)
        point.x=max(0,min(g.world_size[0],point.x));point.y=max(0,min(g.world_size[1],point.y));return point
    def spread(self,t,point,settle=None):
        stable=self.settle if settle is None else settle
        base=t.stats['artillery_dispersion'];distance=t.p.distance_to(point)
        movement=min(2,abs(t.speed)/max(1,t.stats['speed'])*3)
        return (base+distance*.012)*(1+movement+max(0,1-stable)*1.6)
    def valid(self,t,point):
        distance=t.p.distance_to(point)
        return t.stats['artillery_min_range']<=distance<=t.stats['artillery_range']
    def shoot(self,t,point=None,settle=None):
        g=self.g;point=self.aim() if point is None else V(point)
        if t.dead or t.cd>0 or not t.can_fire() or getattr(t,'shells',1)<=0 or not self.valid(t,point):return False
        if abs(difference(bearing(point-t.p),t.aim))>8:
            if t is g.player:g.say('等待炮塔对准落点');return False
            return False
        ammo=copy.deepcopy(t.ammo)
        if ammo is None:return False
        radius=self.spread(t,point,settle);offset=direction(random.uniform(0,360))*math.sqrt(random.random())*radius
        landing=point+offset;distance=t.p.distance_to(landing)
        duration=max(.35,min(5.,distance/max(1000,(ammo.get('velocity') or 655)*3.0)+.2))
        self.shells.append(dict(start=V(t.muzzle()),p=V(t.muzzle()),point=landing,aim=V(point),spread=radius,age=0.,duration=duration,owner=t,ammo=ammo,heading=t.aim))
        t.cd=t.stats['reload']*(1.7 if t.ai or t.enemy else 1.)
        if t.modules['loader']==0:t.cd*=1.8
        elif t.modules['loader']==1:t.cd*=1.25
        t.reload_duration=t.cd
        if hasattr(t,'shells'):t.shells-=1
        g.burst(t.muzzle(),(255,217,117),12);return True
    def record(self,t,result,owner,ammo):
        g=self.g;g.record_hit(t,result,owner,ammo['name'])
        if result['modules']:
            t.last_attacker=owner;t.last_weapon=ammo['name']
            if g.is_player(owner):t.player_credit=True
        if t.dead:g.register_death(t)
    def impact(self,shell):
        g=self.g;point=shell['point'];owner=shell['owner'];ammo=shell['ammo'];self.blasts.append([V(point),0.,owner.stats['blast_radius']])
        g.burst(point,(250,180,76),30)
        if ammo['type'].lower()=='smoke':g.add_smoke(point,'grenade');return
        targets=[t for t in g.vehicles() if not t.dead and t.enemy!=owner.enemy]
        direct=None
        for t in sorted(targets,key=lambda t:t.p.distance_squared_to(point)):
            if t.p.distance_to(point)>t.radius+12:continue
            if any(segment_polygon(point,point+V(.001,0),poly) is not None for poly in t.footprint()):direct=t;break
        if direct is not None:
            t=direct;local=t.local(point);roof=t.stats.get('roof_armor',max(10,t.stats['armor'][2]*.55));pen=ammo['penetration'][0]
            damaged=[];rays=[];burst=None
            hull_or_turret=any(segment_polygon(point,point+V(.001,0),poly) is not None for poly in (t.footprint()[0],t.footprint()[-1]))
            if not hull_or_turret:
                track='left_track' if local.y<0 else 'right_track';t.damage_module(track,2);damaged=[track]
            elif pen>=roof:
                damaged,rays,burst=spall(t,local,direction(random.uniform(0,360)),ammo,random)
                # A vertical entry first intersects the modules below the actual landing point.
                for key in t.module_rects:
                    if t.module_rects[key].collidepoint(local) and t.modules[key]>0:
                        t.damage_module(key,2 if key in ('ammo','engine','driver','gunner','loader','commander') else 1);damaged.append(key)
            result=dict(kind='曲射命中履带' if not hull_or_turret else '曲射命中车顶' if pen>=roof else '曲射命中 · 车顶阻挡',modules=list(dict.fromkeys(damaged)),point=V(point),line=(local,local+V(1,0)),fragments=rays,burst=burst)
            self.record(t,result,owner,ammo)
        # HE splashes are physical radial rays with falloff, cover and hull armour interception.
        if not explosive(ammo):return
        high_explosive=ammo['type'].upper() in ('HE','HE-VT','HE-TF')
        radius=owner.stats['blast_radius']*(1 if high_explosive else .45)
        fragment_pen=65 if high_explosive else 20
        for t in targets:
            if t is direct or t.dead or point.distance_to(t.p)>radius+t.radius:continue
            delta=t.p-point
            if delta.length_squared()<.01:continue
            end=t.p+delta.normalize()*t.radius;contact=t.shell_contact(point,end)
            if not contact or point.distance_to(contact[1])>radius:continue
            blocked=g.terrain.blocks_shell(point,contact[1]) or any(u is not t and not u.dead and u.shell_contact(point,contact[1]) for u in g.vehicles())
            if blocked:continue
            falloff=max(.1,1-point.distance_to(contact[1])/radius*.9);blast_ammo=dict(ammo,penetration=[min(fragment_pen,value)*falloff for value in ammo['penetration']])
            result=t.hit(point,end,delta.normalize()*700,ammo=blast_ammo,barrel_seen={t:'miss'})
            if result:
                result['kind']='落点爆炸溅射 · '+result['kind'];self.record(t,result,owner,ammo)
        for angle in range(0,360,12):g.terrain.strike_tree(point,point+direction(angle)*radius,4)
    def update(self,dt):
        g=self.g
        if g.paused:return
        if self.enabled and (g.player.dead or g.flight.active or g.state!='play'):self.reset();g.camera()
        if self.enabled:
            mouse=V(pygame.mouse.get_pos());view=self.api['VIEW']
            if view.collidepoint(mouse):
                margin=55;pan=V(int(mouse.x>view.right-margin)-int(mouse.x<view.left+margin),int(mouse.y>view.bottom-margin)-int(mouse.y<view.top+margin))
                if pan.length_squared():self.focus+=pan.normalize()*1800*dt;g.camera()
            point=self.aim();moving=abs(g.player.speed)>6 or abs(difference(g.player.aim,self.previous_heading))>1 or (self.last_aim is not None and point.distance_to(self.last_aim)>25)
            self.settle=max(0,self.settle-dt*1.8) if moving else min(1,self.settle+dt*.25)
            self.last_aim=point;self.previous_heading=g.player.aim
        for shell in self.shells[:]:
            shell['age']+=dt;fraction=min(1,shell['age']/shell['duration']);shell['p']=shell['start'].lerp(shell['point'],fraction)
            if fraction>=1:self.shells.remove(shell);self.impact(shell)
        for blast in self.blasts[:]:
            blast[1]+=dt
            if blast[1]>.8:self.blasts.remove(blast)
    def draw_projectiles(self):
        g=self.g;s=self.api['screen'];view=self.api['VIEW'];clip=s.get_clip();s.set_clip(view)
        for shell in self.shells:
            fraction=min(1,shell['age']/shell['duration']);shadow=g.world_to_display(shell['p']);height=math.sin(math.pi*fraction)*65
            at=shadow-V(0,height);pygame.draw.circle(s,(46,45,34),shadow,2);pygame.draw.circle(s,(255,214,130),at,3)
            pygame.draw.line(s,(251,173,79),at,at-direction(shell['heading'])*9,2)
        for point,age,radius in self.blasts:
            pygame.draw.circle(s,(255,184,75),g.world_to_display(point),max(2,int(radius*g.zoom*min(1,age*4))),max(1,int(3*(1-age/.8))))
        s.set_clip(clip)
    def draw_overview(self,mouse):
        g=self.g;s=self.api['screen'];text=self.api['text'];view=self.api['VIEW'];s.fill((16,25,22));s.set_clip(view);pygame.draw.rect(s,(66,83,46),view)
        from Seasons import ground,season,tree
        ground(g,s,view,g.world_to_display,g.zoom)
        def rect(r):
            p=g.world_to_display(r.topleft);return pygame.Rect(p.x,p.y,max(1,r.w*g.zoom),max(1,r.h*g.zoom))
        for road in g.terrain.roads:pygame.draw.rect(s,(151,163,170) if season(g)=='winter' else (112,99,67),rect(road))
        for pond in g.terrain.ponds:
            pygame.draw.rect(s,(92,145,139),rect(pond));pygame.draw.rect(s,(39,77,93),rect(pond.inflate(-180,-160)))
        from BattleRendering import trees,world_bounds,vehicle as draw_ground
        bounds=world_bounds(g,view)
        for r,kind in g.terrain.nearby_obstacles(bounds):
            if kind not in ('deep_water','tree'):pygame.draw.rect(s,((223,232,235) if season(g)=='winter' else (149,118,80)) if kind=='house' else (111,116,96),rect(r))
        for p,radius in trees(g.terrain,bounds):
            at=g.world_to_display(p)
            if view.collidepoint(at):pygame.draw.circle(s,tree(g,p,1),at,max(1,int(radius*g.zoom)))
        g.objective.draw_world(s,text,g.world_to_display,g.zoom)
        from GroundTraces import draw as draw_traces
        draw_traces(g,s,g.world_to_display,view,g.zoom)
        for t in g.wrecks+g.allies+g.enemies+[g.player]:
            if getattr(t,'airborne',False):continue
            at=g.world_to_display(t.p)
            if not view.collidepoint(at):continue
            if t.vehicle_id:draw_ground(s,t.stats,at,MODEL_SCALE*g.zoom,t.body,top=True,turret_yaw=t.aim,color=(56,54,44) if t.dead else t.stats['color'])
            else:pygame.draw.circle(s,(234,128,82) if t.enemy else (133,198,220),at,4)
            if not t.dead:pygame.draw.circle(s,(247,226,134) if t is g.player else (235,132,85) if t.enemy else (134,206,236),at,max(5,int(t.radius*g.zoom+3)),1)
        for cloud in g.smokes:
            radius=max(2,int(cloud['radius']*g.zoom));at=g.world_to_display(cloud['p'])
            from AIRedeployResponse import smoke_image
            fog=smoke_image(radius,cloud['kind']);fog.set_alpha(180);s.blit(fog,at-V(fog.get_width()/2,fog.get_height()/2))
        from Aviation import draw_aircraft
        for plane in g.air.planes:
            if plane['dead']:continue
            at=g.world_to_display(plane['p'])
            if not view.collidepoint(at):continue
            model=plane.get('model')
            if model:draw_aircraft(s,model,at,g.zoom,bearing(plane['v']),units=8,bank=plane.get('bank',0),sweep=plane.get('sweep',0))
        for f in g.fx:pygame.draw.circle(s,f[3],g.world_to_display(f[0]),max(1,int(f[2]*4)))
        from VisionRendering import apply as apply_vision
        apply_vision(g,s,view,MODEL_SCALE,draw_model)
        s.set_clip(None);g.minimap();g.objective.draw(s,text,self.api)
        text('火炮观察 · '+g.player.stats['name'],(20,14),24,(235,222,166))
        text('边缘移动观察 · 滚轮缩放 · '+g.controls.label('ground.artillery')+' 返回直射',(20,81),16,(221,232,185))
        point=self.aim(mouse);radius=self.spread(g.player,point);at=g.world_to_display(point);valid=self.valid(g.player,point);color=(230,221,131) if valid else (245,126,84)
        s.set_clip(view);pygame.draw.circle(s,color,at,max(1,round(radius*g.zoom)),2);pygame.draw.circle(s,color,at,3)
        text(f'最大偏移 ±{radius/8:.1f} m · 飞行约 {max(1.8,min(9,point.distance_to(g.player.p)/max(300,(g.player.ammo.get("velocity") or 655)*.65)+1.2)):.1f} s',at+V(0,max(22,radius*g.zoom+8)),14,color,True)
        s.set_clip(None)
        text('圆圈内随机落点 · 到达落点才造成命中 / 溅射',(640,735),18,(228,216,159),True)
        text('装填 '+f'{g.player.cd:.1f}s' if g.player.cd>0 else '弹药就绪',(640,768),18,(215,226,170),True)
        text(g.player.ammo['name']+' · '+g.player.ammo['type']+(" · 超出曲射范围" if not valid else ''),(640,796),16,color,True)
        if getattr(g.player,'drowning_age',0):text(f'深水溺亡：{max(0,3-g.player.drowning_age):.1f}s',(640,127),24,(255,157,91),True)
        g.draw_battle_feedback()

def reload_ring(g,api,mouse):
    if g.state!='play' or g.paused or g.player.dead or not api['VIEW'].collidepoint(mouse):return
    aircraft=g.flight.active;t=g.flight.plane if aircraft else g.player
    remaining=t.cd;duration=max(.01,getattr(t,'reload_duration',t.stats.get('reload',.09)))
    progress=max(0,min(1,1-remaining/duration));s=api['screen'];radius=21
    if g.artillery.enabled:radius=max(3,min(14,round(g.artillery.spread(g.player,g.artillery.aim(mouse))*g.zoom*.55)))
    pygame.draw.circle(s,(57,69,59),mouse,radius,3)
    color=(249,205,106) if remaining>0 else (151,231,156)
    if progress>=.999:pygame.draw.circle(s,color,mouse,radius,3)
    elif progress>0:pygame.draw.arc(s,color,pygame.Rect(mouse.x-radius,mouse.y-radius,radius*2,radius*2),math.pi/2,math.pi/2+math.tau*progress,3)
    if remaining>0:api['text'](f'{remaining:.1f}',mouse+V(0,29),14,color,True)

def install(Game,api):
    old={key:getattr(Game,key) for key in ('__init__','camera','change_zoom','shoot','update','draw','deploy_player','switch_ammo')}
    def init(g,*a,**kw):old['__init__'](g,*a,**kw);g.artillery=Artillery(g,api)
    def camera(g,*a,**kw):
        artillery=getattr(g,'artillery',None)
        if artillery and artillery.enabled:
            w,h=g.world_size;vw,vh=1280/g.zoom,api['VIEW'].h/g.zoom
            artillery.focus.x=max(min(vw/2,w/2),min(max(w-vw/2,w/2),artillery.focus.x));artillery.focus.y=max(min(vh/2,h/2),min(max(h-vh/2,h/2),artillery.focus.y))
            g.cam=artillery.focus-V(vw/2,vh/2+api['VIEW'].top);g.scope=False;return
        return old['camera'](g,*a,**kw)
    def zoom(g,delta):
        if g.artillery.enabled:g.zoom=max(.14,min(.5,g.zoom*1.12**max(-40,min(40,delta))));g.camera();return
        old['change_zoom'](g,delta)
    def shoot(g,t):
        if t.stats.get('artillery') and ((t is g.player and g.artillery.enabled) or ((t.ai or t.enemy) and getattr(t,'ai_target',None) is not None and t.p.distance_to(t.ai_target.p)>700)):
            point=g.artillery.aim() if t is g.player else V(t.ai_target.p)
            return g.artillery.shoot(t,point,None if t is g.player else .3+.7*getattr(t,'ai_skill',.5))
        result=old['shoot'](g,t)
        if result:t.reload_duration=t.cd
        return result
    def switch_ammo(g,*a,**kw):
        result=old['switch_ammo'](g,*a,**kw)
        if result:g.player.reload_duration=g.player.cd
        return result
    def update(g,dt):
        old['update'](g,dt)
        if g.state in ('play','wreck','deploy') or g.artillery.enabled:g.artillery.update(dt)
    def draw(g,*a,**kw):
        mouse=V(kw.get('mouse_position',a[0] if a else pygame.mouse.get_pos()))
        if g.artillery.enabled and g.state=='play':g.artillery.draw_overview(mouse)
        else:old['draw'](g,*a,**kw)
        if g.state!='deploy':g.artillery.draw_projectiles();reload_ring(g,api,mouse)
        if g.artillery.enabled and g.paused:g.overlay('已暂停','按 '+g.controls.label('common.pause')+' 继续战斗')
    def deploy(g,*a,**kw):
        result=old['deploy_player'](g,*a,**kw)
        if result:g.artillery.reset();g.camera()
        return result
    Game.__init__=init;Game.camera=camera;Game.change_zoom=zoom;Game.shoot=shoot;Game.update=update;Game.draw=draw;Game.deploy_player=deploy;Game.switch_ammo=switch_ammo


def self_test(api):
    Game,Tank=api['Game'],api['Tank'];g=Game(True,'us',['us_5_1']+[None]*7)
    g.deploy_selected=True;assert g.deploy_player(api['BASES'][False]);g.state='play'
    g.allies=[];g.enemies=[];g.terrain.obstacles=[];g.terrain.ponds=[];g.player.p=V(2000,2000);g.player.aim=g.player.body=0
    normal=g.zoom;assert g.artillery.toggle() and g.zoom<.3
    target=Tank((4000,2000),True,vehicle='us_5_1');g.enemies=[target]
    assert g.artillery.shoot(g.player,V(target.p),1);shell=g.artillery.shells[-1]
    assert shell['point'].distance_to(shell['aim'])<=shell['spread']
    shell['point']=V(target.p);before=dict(target.modules)
    g.artillery.update(shell['duration']*.5);assert target.modules==before and g.artillery.shells
    g.artillery.update(shell['duration']*.51);assert target.modules!=before and not g.artillery.shells
    g.draw(mouse_position=(640,420));assert g.artillery.toggle() and g.zoom==normal
    from ArtilleryVehicles import SPECS
    assert len(SPECS)==10 and all(api['VEHICLES'][uid]['artillery'] for uid in SPECS)
    print('PASS: four SPH research branches, 8 source-backed vehicles, overhead mode, bounded dispersion, landing-only module impacts, reload-ring rendering')
