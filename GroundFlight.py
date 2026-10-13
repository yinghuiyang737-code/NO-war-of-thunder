"""Player aircraft are vehicles inside the existing ground battle, never a separate match."""
import math,random,os,ctypes
import pygame
from pygame.math import Vector2 as V
from Aviation import AIRCRAFT,draw_aircraft
from AircraftPhysics import Plane,direction,bearing,difference
from VehicleGeometry import segment_polygon
from NuclearMission import select_aircraft,configure as configure_nuclear,NuclearExplosion
from AircraftRadar import Radar
from AircraftModels import wingtips,polygons
from AircraftLoadouts import available as available_stores,consume as consume_store,draw_stores,refresh as refresh_stores

def pcaliber(f):return f.plane.stats.get('caliber',20) if f.plane else 20

class GameInput:
    def __init__(self):self.context=None;self.hwnd=None;self.imm=None;self.disable()
    def disable(self):
        pygame.key.stop_text_input()
        if os.name=='nt' and pygame.display.get_driver()!='dummy':
            try:
                self.hwnd=pygame.display.get_wm_info().get('window')
                if self.hwnd:
                    self.imm=ctypes.WinDLL('imm32');self.imm.ImmAssociateContext.argtypes=(ctypes.c_void_p,ctypes.c_void_p);self.imm.ImmAssociateContext.restype=ctypes.c_void_p
                    old=self.imm.ImmAssociateContext(self.hwnd,None)
                    if old:self.context=old
            except (OSError,AttributeError):pass
    def restore(self):
        if self.imm and self.hwnd and self.context:self.imm.ImmAssociateContext(self.hwnd,self.context);self.context=None

class GroundFlight:
    def __init__(self,game,api):
        self.g=game;self.api=api;self.plane=None;self.record=None;self.projectiles=[];self.weapons={};self.lock=None;self.nuke_used=False;self.nuke_pending=False;self.nuke_timer=None;self.nuke_point=None;self.nuke_flash=0.;self.nuke_detonated=False;self.nuke_animation=None
        self.base_kind='airport';self.helipad_enabled=False;self.helipad=V(-1800,game.world_size[1]+1800);self.fixed_airport=V(-42000,game.world_size[1]+32000);self.airport=V(self.fixed_airport);self.heading=bearing(V(game.world_size)/2-self.airport)
        from AirportService import AirportService
        self.service=AirportService(self)
    @property
    def active(self):return self.plane is not None and not self.plane.dead
    @property
    def selected_aircraft(self):return bool(self.g.lineup and self.g.lineup[self.g.active_vehicle_slot] in AIRCRAFT)
    @property
    def available_nuke(self):return self.g.score>=2500 and not self.nuke_used
    def nuclear_model(self):
        return select_aircraft(AIRCRAFT,self.g.country or 'us',self.g.battle_br)
    def request_nuke(self):
        if self.g.paused or self.g.state not in ('play','deploy') or not self.available_nuke:
            self.g.say('核弹机需要 2500 个人陆战分，且每场仅可出动一次');return False
        self.nuke_pending=True;self.g.state='deploy';self.g.deploy_selected=False;self.g.deploy_delay=0;self.g.deploy_hint='核弹任务：'+AIRCRAFT[self.nuclear_model()]['name']+' · 点击地图外机场，再确认部署';return True
    def start(self,ident,nuclear=False):
        g=self.g
        if self.record:self.record['dead']=True
        self.base_kind='helipad' if AIRCRAFT[ident].get('helicopter') else 'airport'
        self.airport=V(-1800,self.g.world_size[1]+1800) if AIRCRAFT[ident].get('helicopter') else V(-42000,self.g.world_size[1]+32000)
        if self.base_kind=='helipad':self.helipad_enabled=True
        self.heading=bearing(V(self.g.world_size)/2-self.airport)
        self.plane=Plane(ident,0,self.airport-direction(self.heading)*11000,self.weapons.get(ident));p=self.plane
        p.a=self.heading;p.speed=0.;p.throttle=.35;p.altitude=0.;p.bank=0.;p.phase='runway';p.nuclear=nuclear;p.service_time=0.;p.bombs=1 if nuclear else p.bombs;p.takeoff_distance=0.
        if p.stats.get('helicopter'):p.p=V(self.airport);p.throttle=.35;p.pods=True
        if nuclear:self.nuke_used=True;self.nuke_pending=False;configure_nuclear(p)
        # This anchor only keeps the ground renderer and camera interfaces stable. It is not a tank target.
        ground=next((k for k in (g.lineup or []) if k in self.api['VEHICLES']),f'{g.country or "us"}_1_1')
        g.player=self.api['Tank'](p.p,vehicle=ground);g.player.airborne=True;g.player.draw=lambda *a,**k:None;g.player.can_fire=lambda:False;g.player.shell_contact=lambda *a,**k:None
        g.player.body=g.player.aim=p.a;g.player.speed=0;g.player.ess_active=False
        self.record={'p':p.p.copy(),'v':V(),'dead':False,'health':999,'bomb':999,'life':999999.,'team':0,'controlled':self,'model':p.stats,'nuclear':nuclear}
        self.radar=Radar(self)
        from AircraftWarnings import Warnings
        self.warning=Warnings(self)
        self.trails=[[],[]];self.trail_clock=0.;self.lock_sensor=None
        g.zoom=.38;g.air.planes.append(self.record);g.state='play';g.paused=False;self.lock=None;g.vision='day';g.xray=False;g.hitview=None;g.camera()
        if g.wave==0 and not g.allies:g.spawn_allies(self.api['TEAM_SIZE']-1)
        g.say(('直升机停机坪 · 增加油门垂直起飞，按悬停键保持位置' if p.stats.get('helicopter') else ('核弹机已在远方机场待命 · ' if nuclear else '远方机场 · ')+g.controls.label('air.throttle_up')+' 增加节流阀，沿跑道加速起飞'))
    def deploy(self):
        g=self.g;nuclear=self.nuke_pending
        if g.state!='deploy' or g.deploy_delay>0 or not g.deploy_selected:return False
        if not nuclear and (not self.selected_aircraft or g.reserves<=0 or g.active_vehicle_slot in g.used_slots):return False
        if not nuclear:g.used_slots.add(g.active_vehicle_slot);g.reserves-=1
        elif g.active_vehicle_slot not in g.used_slots:g.used_slots.add(g.active_vehicle_slot);g.reserves=max(0,g.reserves-1)
        self.start(self.nuclear_model() if nuclear else g.lineup[g.active_vehicle_slot],nuclear);return True
    def damage(self,point,strong=False):
        if not self.active:return False
        p=self.plane;died=p.damage(point,strong)
        if died:self.destroy()
        return died
    def destroy(self):
        if not self.plane or getattr(self.plane,'registered_ground',False):return
        self.plane.registered_ground=True;self.plane.dead=True;self.g.burst(self.plane.p,(251,145,66),40)
        self.g.zoom=max(.65,self.g.zoom)
        if self.record:self.record['dead']=True
        self.g.player.dead=True;self.g.player.reason='核弹机被击落' if self.plane.nuclear else '飞机被击落 / 坠毁';self.g.register_death(self.g.player)
    def sync(self):
        p=self.plane;g=self.g;g.player.p=V(p.p);g.player.body=g.player.aim=p.a;g.player.speed=p.speed
        if self.record:self.record['p']=V(p.p);self.record['v']=V(getattr(p,'heli_velocity',direction(p.a)*p.speed)) if p.stats.get('helicopter') and p.phase=='airborne' else direction(p.a)*p.speed;self.record['bank']=p.bank;self.record['sweep']=getattr(p,'sweep',0);self.record['phase']=p.phase
    def update_controls(self,dt,keys=None,mouse=None,buttons=None):
        if not self.active:return
        g=self.g;p=self.plane;keys=g.controls.keys("air") if keys is None else keys;mouse=pygame.mouse.get_pos() if mouse is None else mouse;buttons=g.controls.buttons("air") if buttons is None else buttons
        if p.phase in ('approach','landing','service'):
            self.service.update(dt);self.sync();self.radar.update(dt);return
        up=bool(keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]);down=bool(keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]);
        if up or down:p.hover=False;p.hover_anchor=None
        p.throttle=max(0.,min(1.,p.throttle+(int(up)-int(down))*dt*.28))
        target=g.screen_to_world(mouse);self.laser_point=V(target);delta=target-p.p;desired=p.a if self.guided_missile() else bearing(delta) if delta.length_squared()>100 else p.a
        manual=int(bool(keys[pygame.K_d]))-int(bool(keys[pygame.K_a]))
        from FlightDynamics import step
        previous=p.phase
        translation=V(int(bool(keys[pygame.K_KP6]))-int(bool(keys[pygame.K_KP4])),int(bool(keys[pygame.K_KP2]))-int(bool(keys[pygame.K_KP8]))) if p.stats.get('helicopter') else None
        if not step(p,dt,desired,self.heading,manual,translation):self.destroy();g.say('失速或动力损失导致坠毁');return
        if previous=='runway' and p.phase=='airborne':g.say(('离地起飞 · WASD 位移，鼠标控制朝向' if p.stats.get('helicopter') else '离地起飞 · 鼠标指引航向，A/D 主动滚转'))
        if p.phase=='airborne':
            if buttons[0] or keys[pygame.K_SPACE]:self.gun()
            if p.stats.get('defensive') and not p.nuclear:
                nearby=[q for q in g.air.planes if not q['dead'] and q.get('team',1)==1 and q['p'].distance_to(p.p)<600]
                if nearby:self.gun(min(nearby,key=lambda q:q['p'].distance_to(p.p)))
        # The airport and all flight space lie outside ground collision and tank deployment rules.
        center=V(g.world_size)/2
        if p.p.distance_to(center)>150000:p.a=bearing(center-p.p);g.say('接近飞行边界，已引导航向战区')
        self.sync()
        self.radar.update(dt)
        if p.phase=='airborne':self.auto_ground_target()
        self.trail_clock+=dt
        tips=[p.p+tip.rotate(p.a) for tip in wingtips(p.stats,p.bank,getattr(p,'sweep',0))]
        for i,tip in enumerate(tips):
            self.trails[i]=[(stamp,pos) for stamp,pos in self.trails[i] if self.trail_clock-stamp<.45]
            if p.phase=='airborne' and p.speed>800:self.trails[i].append((self.trail_clock,V(tip)))
        if self.lock is not None and self.lock_sensor=='radar' and not self.radar.has_track(self.lock):self.lock=None;self.g.say('雷达丢失目标锁定')
    def missile_kind(self):
        if not self.active or not self.plane.stats['missile_types']:return ''
        name=self.plane.stats['missile_types'][self.plane.missile]
        stores=[w for w in available_stores(self.plane,'aam') if w['short'].split()[0]==name]
        if stores and stores[0]['guidance']:
            guidance=stores[0]['guidance'].upper()
            return 'SARH' if 'SARH' in guidance else 'ARH' if 'ARH' in guidance else 'IR'
        return 'ARH' if any(x in name for x in ('120','PL-12','R-77','AIM-54')) else 'SARH' if any(x in name for x in ('AIM-7','R-27R','R-27ER','PL-11','R-24R','R-23R','R-3R')) else 'IR'
    def lock_target(self):
        if not self.active:return False
        if self.lock is not None:
            self.lock=None;self.radar.stt=None;self.lock_sensor=None;self.g.say('已解除目标锁定');return False
        target=self.radar.lock() if self.radar.enabled and self.radar.kind not in ('none','ranging') else None
        if target is not None:self.lock=target;self.lock_sensor='radar'
        else:
            p=self.plane;targets=[q for q in self.g.air.planes if q is not self.record and q.get('team',1)==1 and not q['dead'] and self.api['VIEW'].collidepoint(self.g.world_to_display(q['p'])) and abs(difference(bearing(q['p']-p.p),p.a))<60]
            self.lock=min(targets,key=lambda q:q['p'].distance_to(p.p),default=None);self.lock_sensor='visual'
        self.g.say('雷达锁定目标' if self.lock is not None and self.lock_sensor=='radar' else '目视锁定目标' if self.lock else '未发现可锁定目标');return self.lock is not None
    def launch(self):
        if not self.active:return False
        p=self.plane;q=self.lock
        if p.phase!='airborne' or not p.missiles or p.mcd or not isinstance(q,dict) or q['dead']:return False
        if self.missile_kind()=='IR' and (q['p'].distance_to(p.p)>40000 or abs(difference(bearing(q['p']-p.p),p.a))>35):self.g.say('红外弹需要靠近并对准目标');return False
        if self.missile_kind()=='SARH' and not self.radar.has_track(q):self.g.say('半主动导弹需要有效雷达跟踪');return False
        if self.missile_kind()=='SARH' and self.radar.mode in ('TWS','RAM'):
            self.radar.mode='PD' if 'PD' in self.radar.modes else 'RWS';self.radar.stt=q
        name=p.stats['missile_types'][p.missile]
        guidance=self.missile_kind()
        store=consume_store(p,'aam',name)
        if store is None:self.g.say('所选型号未挂载或已用完，请按 '+self.g.controls.label('air.missile_ammo')+' 切换导弹');return False
        self.projectiles.append({'p':V(p.p),'v':direction(p.a)*(5600+p.speed*.4),'life':5.,'kind':'missile','target':q,'guidance':guidance,'weapon':store});p.mcd=1.2;return True
    def gun(self,target=None):
        p=self.plane
        if p.nuclear or (not p.stats['gun'] and not p.pod_ammo and not (target and p.stats.get('defensive'))) or not (p.ammo or p.pod_ammo) or p.cd:return False
        main=bool(p.ammo and (p.stats['gun'] or (target and p.stats.get('defensive'))))
        if main:p.ammo-=1
        else:p.pod_ammo-=1
        p.cd=.09;caliber=p.stats.get('caliber',20) if main else max((w['caliber'] or 20 for w in p.stores if w['kind']=='gunpod'),default=20);pen=13 if caliber<10 else 27 if caliber<20 else min(85,caliber*2)
        belt=p.stats['belts'][p.belt] if p.stats['belts'] else 'Default';typ='HE' if 'air targets' in belt.lower() else 'AP'
        ammo={'name':belt,'type':typ,'caliber':caliber,'velocity':950,'penetration':[pen,pen*.9,pen*.75,pen*.5,pen*.3,pen*.2]}
        aim=bearing(target['p']-p.p) if target else p.a
        self.projectiles.append({'p':V(p.p),'v':direction(aim+random.uniform(-1.2,1.2))*(2400+p.speed),'life':1.1,'kind':'gun','ammo':ammo})
        if main and p.pod_ammo:
            p.pod_ammo-=1;pod_ammo=dict(ammo);pod_ammo['name']='挂载机炮吊舱';pod_ammo['penetration']=[max(30,pen)]*6
            self.projectiles.append({'p':p.p+direction(p.a+90)*14,'v':direction(aim+random.uniform(-1.4,1.4))*(2400+p.speed),'life':1.1,'kind':'gun','ammo':pod_ammo})
        return True
    def bomb(self):
        if not self.active:return False
        p=self.plane;g=self.g
        if p.phase!='airborne' or p.altitude<40 or not p.bombs or p.bcd:return False
        point=p.p+direction(p.a)*p.speed*.8
        if p.nuclear:
            if point.distance_to(V(g.world_size)/2)>1300:g.say('核弹投放要求进入战区中心黄色范围');return False
            p.bombs=0;p.bcd=4.;self.nuke_timer=4.;self.nuke_point=point;g.say('核弹已投放，4 秒后引爆');return True
        pending=available_stores(p,'bomb')[0]
        if pending['guidance'] and (p.ground_lock is None or p.ground_lock.dead):self.g.say('制导炸弹等待自动地面锁定');return False
        if pending['guidance'] and p.ground_lock.p.distance_to(p.p)>80000:self.g.say('已保持目标锁定，进入 10 km 投放范围后再投弹');return False
        if 'laser' in pending['guidance'].lower() and not (p.pods or any(n in p.stats['name'] for n in ('Su-25','Su-24','Su-34','MiG-27','Q-5L'))):self.g.say('激光制导炸弹需要目标指示吊舱');return False
        store=consume_store(p,'bomb')
        if not store:return False
        q=p.ground_lock
        if store['guidance'] and q is not None and not q.dead:point=V(q.p)
        p.bcd=.45;self.projectiles.append({'p':V(p.p),'v':direction(p.a)*p.speed,'life':.8,'kind':'bomb','point':point,'weapon':store});return True
    def rocket(self):
        if not self.active:return False
        p=self.plane
        if p.phase!='airborne' or not p.rockets or p.rcd or p.nuclear:return False
        store=consume_store(p,'rocket')
        if not store:return False
        p.rcd=.18;ammo={'name':store['short'],'type':'HEAT' if 'HEAT' in store['guidance'] or 'S-8' in store['short'] or 'Hydra' in store['short'] else 'HE','velocity':900,'penetration':[400]*6}
        self.projectiles.append({'p':V(p.p),'v':direction(p.a)*(2400+p.speed),'life':1.8,'kind':'rocket','ammo':ammo});return True
    def countermeasure(self):
        if not self.active:return False
        from Countermeasures import release
        return release(self.g,self.plane)
    def cycle_countermeasure(self):
        from Countermeasures import modes,LABELS
        p=self.plane;options=modes(p)
        if not options:self.g.say('此机没有可用干扰弹');return False
        p.cm_mode=options[(options.index(p.cm_mode)+1)%len(options)];self.g.say('干扰弹模式：'+LABELS[p.cm_mode]);return True
    def ground_candidates(self):
        p=self.plane
        return sorted((t for t in self.g.enemies if not t.dead and t.p.distance_to(p.p)<160000 and not self.g.smoke_blocks(p.p,t.p,p.stats.get('thermal',False))),key=lambda t:(abs(difference(bearing(t.p-p.p),p.a))>85,t.p.distance_squared_to(p.p)))
    def auto_ground_target(self):
        if not self.active:return None
        p=self.plane
        if p.ground_lock is not None and not p.ground_lock.dead and p.ground_lock in self.g.enemies:return p.ground_lock
        pool=self.ground_candidates();p.ground_lock=pool[0] if pool else None
        return p.ground_lock
    def ground_target(self):
        if not self.active:return False
        p=self.plane;pool=self.ground_candidates()
        if not pool:self.g.say('20 km 内没有可锁定地面目标');return False
        index=next((i for i,t in enumerate(pool) if t is p.ground_lock),-1)
        p.ground_lock=pool[(index+1)%len(pool)]
        self.g.say('已切换地面目标 · 自动保持锁定 / '+self.g.controls.label('air.agm')+' 对地导弹 / '+self.g.controls.label('air.bomb')+' 制导炸弹')
        return True
    def cycle_ground_store(self):
        if not self.active:return False
        p=self.plane;pool=list(dict.fromkeys(w['short'] for w in available_stores(p,'agm')))
        if not pool:self.g.say('没有剩余的对地导弹挂载');return False
        p.ground_choice=(p.ground_choice+1)%len(pool);self.g.say('对地挂载：'+pool[p.ground_choice]);return True
    def launch_ground(self):
        if self.guided_missile():self.g.say('正在引导导弹，等待命中或失效');return False
        if not self.active:return False
        p=self.plane;q=p.ground_lock;pool=list(dict.fromkeys(w['short'] for w in available_stores(p,'agm')))
        if p.nuclear or p.phase!='airborne' or p.mcd or not pool:return False
        name=pool[p.ground_choice%len(pool)];weapon=next(w for w in available_stores(p,'agm') if w['short']==name)
        if 'anti-ship' in name.lower():self.g.say('该挂载是反舰武器，当前陆战地图没有舰船目标');return False
        if p.stats.get('helicopter') and any(k in weapon['guidance'].lower() for k in ('laser','command','saclos')):
            store=consume_store(p,'agm',weapon['short'].split()[0])
            if not store:return False
            aim=getattr(self,'laser_point',p.p+direction(p.a)*4000);delta=V(aim)-p.p
            if delta.length_squared()<1:delta=direction(p.a)
            ammo={'name':store['short'],'type':'HEAT','guidance':'LASER_BEAM' if 'laser' in weapon['guidance'].lower() else 'SACLOS','penetration':[650.]*6,'explosive':store['explosive'],'velocity':600.,'caliber':store['caliber']}
            missile=dict(p=V(p.p),v=delta.normalize()*4800,life=18.,kind='agm',cursor_guided=True,missile_event=True,overfly_terrain=True,target=None,weapon=store,ammo=ammo,team=p.team)
            if 'laser' in weapon['guidance'].lower():
                import uuid
                p.guided_camera=uuid.uuid4().hex;missile['camera_token']=p.guided_camera
                self.g.say('导弹视角 · 鼠标引导，命中或失效后返回载具')
            self.projectiles.append(missile);p.mcd=1.2;self.g.camera();return True
        if q is None or q.dead:self.g.say('尚无地面目标，自动搜索中');return False
        if 'anti-radiation' in name.lower() and not q.stats.get('radar'):self.g.say('反辐射导弹需要正在使用雷达的敌车');return False
        if 'laser' in weapon['guidance'].lower() and not (p.pods or any(n in p.stats['name'] for n in ('Su-25','Su-24','Su-34','MiG-27','Q-5L'))):self.g.say('此激光武器需要挂载目标指示吊舱');return False
        if q.p.distance_to(p.p)>80000 or abs(difference(bearing(q.p-p.p),p.a))>65:self.g.say('地面目标超出发射范围或机头角度');return False
        store=consume_store(p,'agm',name.split()[0]);ammo={'name':name,'type':'HEAT','velocity':900,'penetration':[900]*6}
        self.projectiles.append({'p':V(p.p),'v':direction(p.a)*(4500+p.speed*.3),'life':18.,'kind':'agm','target':q,'weapon':store,'ammo':ammo,'overfly_terrain':bool(p.stats.get('helicopter'))});p.mcd=1.2;return True
    def switch(self,kind):
        if not self.active or self.plane.nuclear:return False
        p=self.plane;opts=p.stats['missile_types' if kind=='missile' else 'belts']
        if not opts:return False
        choices=[i for i,name in enumerate(opts) if any(w['short'].split()[0]==name for w in available_stores(p,'aam'))] if kind=='missile' else list(range(len(opts)))
        if not choices:self.g.say('没有剩余的该类挂载');return False
        index=choices.index(getattr(p,kind)) if getattr(p,kind) in choices else -1
        setattr(p,kind,choices[(index+1)%len(choices)]);self.weapons.setdefault(p.ident,{})[kind]=getattr(p,kind);self.g.say('已切换 '+opts[getattr(p,kind)]);return True
    def guided_missile(self):
        token=getattr(self.plane,'guided_camera',None) if self.active else None
        return next((b for b in self.projectiles if token and b.get('camera_token')==token and b.get('life',0)>0),None)
    def toggle_hover(self):
        if not self.active or not self.plane.stats.get('helicopter') or self.plane.phase!='airborne':self.g.say('悬停模式仅用于飞行中的直升机');return False
        p=self.plane;p.hover=not getattr(p,'hover',False);p.hover_anchor=None;p.hover_altitude=p.altitude
        self.g.say('悬停模式开启：减速后保持位置和高度，可继续瞄准' if p.hover else '悬停模式关闭');return True
    def event(self,event):
        if event.type!=pygame.KEYDOWN:return False
        if event.key==pygame.K_F4:self.toggle_hover();return True
        if event.key==pygame.K_k:self.request_nuke();return True
        if not self.active:return False
        if event.key==pygame.K_i:self.cycle_countermeasure();return True
        if event.key in (pygame.K_F7,pygame.K_F8):
            from Countermeasures import release
            release(self.g,self.plane,'flare' if event.key==pygame.K_F7 else 'chaff');return True
        if event.key==pygame.K_F9:self.warning.toggle();return True
        if event.key==pygame.K_l:self.service.request();return True
        if event.key==pygame.K_TAB:self.radar.toggle();self.g.say(self.radar.notice);return True
        if event.key==pygame.K_t:self.radar.cycle_mode();self.g.say(self.radar.notice);return True
        if event.key==pygame.K_f:self.radar.cycle_range();self.g.say(self.radar.notice);return True
        if event.key==pygame.K_BACKSPACE:self.radar.selected=self.radar.stt=None;self.lock=None;self.g.say('已取消雷达锁定');return True
        if event.key==pygame.K_y:self.radar.cycle_target();self.g.say(self.radar.notice or '已选择雷达目标');return True
        if event.key==pygame.K_e:self.ground_target();return True
        if event.key==pygame.K_u:self.cycle_ground_store();return True
        if event.key==pygame.K_h:self.launch_ground();return True
        actions={pygame.K_q:self.lock_target,pygame.K_j:self.launch,pygame.K_c:self.countermeasure,pygame.K_b:self.bomb,pygame.K_g:self.rocket,pygame.K_m:lambda:self.switch('missile'),pygame.K_n:lambda:self.switch('belt')}
        if event.key in actions:actions[event.key]();return True
        return event.key in (pygame.K_z,pygame.K_h,pygame.K_v,pygame.K_l,pygame.K_x,pygame.K_e)
    def illumination(self,projectile,target):
        source=projectile.get('source')
        if source is not None:return not source['dead'] and source['radar'].has_track(target) and source['radar'].stt is target
        return self.active and self.radar.has_track(target)
    def update_ordnance(self,dt):
        g=self.g
        if g.paused:return
        from Countermeasures import update_clouds
        update_clouds(g,dt)
        if self.active:self.warning.update(dt)
        if self.nuke_animation:self.nuke_animation.update(dt)
        if self.nuke_timer is not None:
            self.nuke_timer-=dt
            if self.nuke_timer<=0:
                self.nuke_timer=None;self.nuke_flash=0.;self.nuke_detonated=True;self.nuke_animation=NuclearExplosion(self.nuke_point)
                g.nuclear_result='win';g.say('核弹引爆 · 战场继续运行')
        self.nuke_flash=max(0,self.nuke_flash-dt)
        if g.state=='win':return
        for b in self.projectiles[:]:
            old=V(b['p']);b['p']+=b['v']*dt;b['life']-=dt;hit=False;blast_point=None;intercepted=False
            team=b.get('team',0);owner=b.get('owner',g.player)
            attacker=owner if owner is not None else b.get('source')
            weapon=b.get('weapon',{}).get('short',b.get('ammo',{}).get('name',b['kind']))
            if b['kind']=='gun':weapon=weapon+' · '+b.get('ammo',{}).get('type','AP')
            targets=g.enemies[:] if team==0 else g.allies[:]+([g.player] if not getattr(g.player,'airborne',False) else [])
            if b['kind']=='bomb' and b['life']<=0:
                from BlastFragments import detonate
                detonate(g,b['point'],b.get('weapon',{}),attacker,weapon,team)
            elif b['kind'] in ('gun','missile','rocket','agm'):
                if b.get('cursor_guided'):
                    if not self.active:b['cursor_guided']=False;b['target']=None
                    else:
                        aim=getattr(self,'laser_point',b['p']+b['v']);delta=difference(bearing(aim-b['p']),bearing(b['v']));b['v']=direction(bearing(b['v'])+max(-110*dt,min(110*dt,delta)))*b['v'].length()
                elif b['kind']=='agm':
                    target=b['target']
                    if target is not None and not target.dead:b['ground_point']=V(target.p)
                    if target is not None and not target.dead:
                        delta=difference(bearing(target.p-b['p']),bearing(b['v']));b['v']=direction(bearing(b['v'])+max(-110*dt,min(110*dt,delta)))*b['v'].length()
                if b['kind']=='missile':
                    from MissileSeeker import acquire,steer
                    def valid(q):return not q.get('dead') and q.get('team',1)!=team and not q.get('missile')
                    def visible(q):return b.get('guidance')!='SARH' or self.illumination(b,q)
                    q=acquire(b,g.air.planes,valid,visible)
                    if q is not None and __import__('Countermeasures').distracted(g,b,q,dt):b['target']=None;q=None
                    if q is not None:
                        from FlightView import intercept
                        prediction=intercept(b['p'],q['p'],q['v'],b['v'].length())
                        steer(b,prediction[0] if prediction else q['p'],dt)
                if b['kind'] not in ('rocket','agm') or b.get('cursor_guided'):
                    for q in g.air.planes:
                        if q.get('team',1)==team or q['dead']:continue
                        from AircraftModels import contact
                        rect=pygame.Rect(0,0,64,48);rect.center=q['p']
                        relative_start=old+q.get('v',V())*dt
                        impact=contact(q['model'],q['p'],bearing(q['v']),relative_start,b['p'],bank=q.get('bank',0),sweep=q.get('sweep',0)) if q.get('model') else rect.clipline(relative_start,b['p'])
                        from AirIntercept import closest,fuse_radius
                        near=closest(relative_start,b['p'],q['p'])
                        proximity=b['kind']=='missile' and near.distance_to(q['p'])<=fuse_radius(None,True)
                        if impact or proximity:
                            point=near if proximity else V(impact[1]) if q.get('model') else V(impact[0])
                            if proximity:
                                from AirIntercept import fragments
                                fragments(g,point,attacker,dict(b.get('ammo') or {},name=weapon),primary=q)
                            q['last_attacker']=attacker;q['last_weapon']=weapon
                            if q.get('controlled'):g.player.last_attacker=attacker;g.player.last_weapon=weapon
                            if q.get('managed'):
                                q['ai_plane'].damage(point,(b['kind']=='missile' or b.get('cursor_guided',False)))
                                if q['ai_plane'].dead:g.air.kill_plane(q,owner)
                            elif q.get('controlled'):q['controlled'].damage(point,(b['kind']=='missile' or b.get('cursor_guided',False)))
                            else:
                                q['health']-=3 if b['kind']=='missile' or b.get('cursor_guided') else 1
                                if q['health']<=0:g.air.kill_plane(q,owner)
                            g.record_air_hit(q,point,attacker,weapon)
                            hit=True;break
                if not hit and b['kind']!='missile' and not b.get('overfly_terrain'):
                    point=g.terrain.strike_tree(old,b['p'],1 if b['kind']=='gun' and pcaliber(self)<15 else 4)
                    if point is not None:g.burst(point,(165,149,87),8);hit=True;blast_point=point
                if not hit and b['kind']!='missile':
                    for t in targets:
                        if t.p.distance_to(b['p'])>t.radius+b['v'].length()*dt:continue
                        if b['kind'] in ('rocket','agm') and g.try_aps(t,old,b['p'],b['v'],b['ammo'],owner):hit=True;intercepted=True;break
                        result=t.hit(old,b['p'],b['v'],0,penetration_value=b['ammo']['penetration'][0],ammo=b['ammo'])
                        if result:
                            if result['modules']:
                                t.last_attacker=attacker;t.last_weapon=weapon
                                if g.is_player(owner):t.player_credit=True
                            g.record_hit(t,result,attacker,weapon);g.burst(result['point'],(255,189,104),12);hit=not result.get('continue',False)
                            if t.dead:g.register_death(t)
                            if hit:blast_point=result['point'];break
                if not hit and b['kind']=='agm':
                    from AirIntercept import closest
                    target=b.get('target')
                    ground=getattr(self,'laser_point',None) if b.get('cursor_guided') else b.get('ground_point')
                    if target is not None and not getattr(target,'dead',True):ground=target.p
                    if ground is not None and closest(old,b['p'],V(ground)).distance_to(ground)<12:hit=True;blast_point=V(ground)
                    if not hit and not b.get('overfly_terrain') and g.terrain.blocks_shell(old,b['p']):hit=True;blast_point=V(b['p'])
                if hit and b['kind']=='agm' and not intercepted:
                    from BlastFragments import detonate
                    detonate(g,blast_point if blast_point is not None else b['p'],b.get('weapon',{}),attacker,weapon,team)
            if hit or b['life']<=0:self.projectiles.remove(b)
    def draw_world(self,surface,display=False):
        g=self.g;factor=g.zoom if display else 1.;at=g.world_to_display if display else g.to_screen;center=at(self.airport);d=direction(self.heading);right=d.rotate(90)
        from Countermeasures import draw_clouds
        draw_clouds(g,surface,at,factor)
        # Outside the battle map the flight corridor has world-anchored ground
        # details, so altitude/translation remain visible throughout transit.
        if self.active:
            a=g.screen_to_world((0,0));b=g.screen_to_world((self.api['W'],self.api['H']-180))
            for x in range(int(min(a.x,b.x)//320)*320,int(max(a.x,b.x))+321,320):
                for y in range(int(min(a.y,b.y)//320)*320,int(max(a.y,b.y))+321,320):
                    if 0<=x<=g.world_size[0] and 0<=y<=g.world_size[1]:continue
                    h=((x//320)*73856093^(y//320)*19349663)&65535
                    q=at(V(x+(h%150),y+(h//150%140)))
                    if (V(x,y).distance_to(self.airport)<300 if self.plane.stats.get('helicopter') else abs((V(x,y)-self.airport).dot(right))<300 and abs((V(x,y)-self.airport).dot(d))<12600):continue
                    pygame.draw.circle(surface,(43,66,47),q,max(1,int((17+h%15)*factor)))
                    pygame.draw.circle(surface,(59,79,51),q-V(4,5)*factor,max(1,int((13+h%10)*factor)))
        heli=self.base_kind=='helipad'
        from LandingDevices import draw_runway,draw_plane
        if self.helipad_enabled:
            center=at(self.helipad)
            radius=max(6,round(220*factor));pygame.draw.circle(surface,(102,108,103),center,radius)
            pygame.draw.circle(surface,(229,224,191),center,max(3,round(190*factor)),max(1,round(7*factor)))
            for sign in (-1,1):pygame.draw.line(surface,(235,231,204),center+V(sign*55,-65)*factor,center+V(sign*55,65)*factor,max(1,round(12*factor)))
            pygame.draw.line(surface,(235,231,204),center+V(-55,0)*factor,center+V(55,0)*factor,max(1,round(12*factor)))
            if g.render_view.inflate(200,200).collidepoint(center):self.api['text']('直升机停机坪',center+V(0,radius+14),16,center=True)
        if not heli:
            center=at(self.fixed_airport);d=direction(bearing(V(g.world_size)/2-self.fixed_airport));right=d.rotate(90)
            poly=[center+(d*x+right*y)*factor for x,y in [(-12000,-180),(12000,-180),(12000,180),(-12000,180)]];pygame.draw.polygon(surface,(93,98,99),poly)
            for x in range(-11600,11700,600):pygame.draw.line(surface,(219,219,191),center+d*x*factor,center+d*(x+300)*factor,max(1,int(5*factor)))
            if g.render_view.inflate(200,200).collidepoint(center):self.api['text']('远方机场 · 跑道起飞',(center.x,center.y+145),20,center=True)
            draw_runway(self,surface,at,factor)
        if not self.active:return
        p=self.plane;q=at(p.p);shadow=q+V(30,34)*(p.altitude/260)*factor
        
        for _,shape in polygons(p.stats,8,p.bank,getattr(p,'sweep',0)):pygame.draw.polygon(surface,(37,47,36),[shadow+v.rotate(p.a)*factor for v in shape])
        model=p.stats
        col=(140,151,159) if math.cos(math.radians(p.bank))>=0 else (96,113,130);draw_aircraft(surface,model,q,factor,p.a,col,units=8,bank=p.bank,sweep=getattr(p,'sweep',0))
        draw_stores(surface,model,q,factor,p.a,stores=p.stores,bank=p.bank,sweep=getattr(p,'sweep',0))
        draw_plane(p,surface,at,factor,self.heading)
        if p.phase=='airborne' and p.speed>800:
            tips=[p.p+tip.rotate(p.a) for tip in wingtips(p.stats,p.bank,getattr(p,'sweep',0))]
            for i,tip in enumerate(tips):
                history=[at(pos) for stamp,pos in self.trails[i] if self.trail_clock-stamp<.45]
                history.append(at(tip))
                if len(history)>1:pygame.draw.lines(surface,(148,169,169),False,history,1)
        if p.nuclear:self.api['text']('核弹任务机',q+V(0,65),18,(244,214,124),True)
        if p.bombs:
            point=p.p+direction(p.a)*p.speed*.8;pygame.draw.circle(surface,(239,208,117),at(point),max(3,int(25*factor)),1)
        if p.nuclear:pygame.draw.circle(surface,(230,211,125),at(V(g.world_size)/2),max(3,int(1300*factor)),2)
        for b in self.projectiles:
            pt=at(b['p']);pygame.draw.line(surface,(247,216,149),pt,pt-b['v'].normalize()*max(2,14*factor),2)
    def hud(self):
        g=self.g;s=self.api['screen'];t=self.api['text'];dx=s.get_width()-1280;dy=s.get_height()-820
        if self.active:
            self.radar.draw(s,t)
            self.warning.draw(s,t)
            p=self.plane;pygame.draw.rect(s,(17,28,31),(16,480+dy,320,285),border_radius=8);t('飞机模块 · 陆战支援',(30,493+dy),20)
            for i,(key,label) in enumerate([('pilot','飞行员'),('engine','发动机'),('left_wing','左机翼'),('right_wing','右机翼')]):t(label+' '+('失效','受损','正常')[p.modules[key]],(30,535+dy+i*29),18,[(233,105,78),(245,202,99),(164,231,193)][p.modules[key]])
            t(f'高度 {p.altitude:.0f} · 滚转 {p.bank%360:.0f}°',(30,676+dy),16);t(('悬停模式 · 已锁定位置' if getattr(p,'hover',False) else self.service.label()),(30,710+dy),18)
            from LandingDevices import status
            t((g.controls.label('air.hover')+' 悬停开关' if p.stats.get('helicopter') else status(p)),(30,740+dy),14,(244,211,144))
            pygame.draw.rect(s,(17,28,31),(345,640+dy,665,120));t(f'节流阀 {p.throttle*100:.0f}% · 空速 {p.speed*3.6/8:.0f} km/h',(355,650+dy),20)
            t(('核弹 '+str(p.bombs)+' 枚 · 仅携带热诱 / 箔条' if p.nuclear else f'机炮 {p.ammo+p.pod_ammo} · 空空弹 {p.missiles} · 对地弹 {p.agms} · 炸弹 {p.bombs} · 火箭 {p.rockets}'),(355,681+dy),16)
            t((g.controls.label('air.bomb')+' 投放核弹 · 燃油 '+str(int(p.fuel))+'s') if p.nuclear else g.controls.label('air.ground_target')+' 换地面目标 · '+g.controls.label('air.ground_store')+' 换挂载 · '+g.controls.label('air.agm')+' 发射 · 燃油 '+str(int(p.fuel))+'s',(355,706+dy),14,max_width=640)
            t('热诱 '+str(p.heat_flares)+' · 箔条 '+str(p.chaff)+' · '+g.controls.label('air.counter')+' '+__import__('Countermeasures').LABELS[p.cm_mode]+' · '+g.controls.label('air.cm_mode')+' 切模式',(355,735+dy),14,max_width=640)
            pygame.draw.rect(s,(15,24,21),(800+dx,5,480,61));t(('核弹机 '+p.stats['name'] if p.nuclear else p.stats['name'])+(' · '+self.service.label()),(810+dx,18),18)
            pygame.draw.rect(s,(15,24,21),(0,778+dy,s.get_width(),42));t(g.controls.label('air.throttle_up')+'/'+g.controls.label('air.throttle_down')+' 油门 · '+(g.controls.label('air.heli_forward')+'/'+g.controls.label('air.heli_reverse')+'/'+g.controls.label('air.heli_left')+'/'+g.controls.label('air.heli_right')+' 位移 · 鼠标朝向 · ' if p.stats.get('helicopter') else '鼠标转向 · ')+g.controls.label('air.land')+' 自动降落（友方机场4km内） · 按键设置查看全部操作',(s.get_width()/2,798+dy),16,center=True)
            mini=pygame.Rect(1028+dx,85,235,175);pygame.draw.rect(s,(22,37,35),mini);pygame.draw.rect(s,(126,166,155),mini,1)
            lo=V(min(-1000,self.airport.x-13000),-2000);extent=V(g.world_size[0]+2000,self.airport.y+14000)-lo
            def mp(point):
                q=V(point)-lo;return V(mini.x+q.x/extent.x*mini.w,mini.y+q.y/extent.y*mini.h)
            a=mp(V());b=mp(V(g.world_size));pygame.draw.rect(s,(74,104,79),(a.x,a.y,b.x-a.x,b.y-a.y),1)
            airport=mp(self.airport);pygame.draw.circle(s,(126,214,237),airport,5);t('停机坪' if self.base_kind=='helipad' else '机场',airport+V(5,3),14)
            for target in g.enemies:pygame.draw.circle(s,(226,113,81),mp(target.p),2)
            q=mp(p.p);pygame.draw.circle(s,(242,230,145),q,4);pygame.draw.line(s,(242,230,145),q,q+direction(p.a)*12,2)
            closest=V(max(0,min(g.world_size[0],p.p.x)),max(0,min(g.world_size[1],p.p.y)))
            distance=p.p.distance_to(closest)/8000
            t(f'距战区 {distance:.1f} km',(1030+dx,267),14)
            mouse=V(pygame.mouse.get_pos())
            if pygame.Rect(340,130,675,488).collidepoint(mouse):
                pygame.draw.circle(s,(173,229,235),mouse,23,2);pygame.draw.line(s,(173,229,235),mouse-V(35,0),mouse+V(35,0));pygame.draw.line(s,(173,229,235),mouse-V(0,35),mouse+V(0,35))
        t(f'个人陆战分 {g.score} / 2500'+(' · '+g.controls.label('common.nuke')+' 部署核弹机' if self.available_nuke else ' · 核弹机已使用' if self.nuke_used else ''),(355,112),18,(242,214,141))
        if self.nuke_timer is not None:t(f'核弹引爆 {max(0,self.nuke_timer):.1f}s',(640,345),30,(250,225,160),True)
        if self.nuke_animation and not self.nuke_animation.finished:self.nuke_animation.draw(s,t,g.world_to_display(self.nuke_animation.point))
        if self.nuke_detonated and g.state=='win' and (not self.nuke_animation or self.nuke_animation.finished):g.overlay('核爆胜利','核弹任务完成 · 陆战结束',g.controls.label('common.back')+' 返回机库 · '+g.controls.label('common.restart')+' 重新出战')
    def nuke_button(self):return pygame.Rect(self.api['W']-200,320,174,65)
    def airport_button(self):return pygame.Rect(self.api['W']-200,160,174,100)
    def deployment_ui(self):
        g=self.g;s=self.api['screen'];t=self.api['text'];dx=s.get_width()-1280;dy=s.get_height()-820;r=self.airport_button();air=self.selected_aircraft or self.nuke_pending
        heli=bool(not self.nuke_pending and self.selected_aircraft and AIRCRAFT[g.lineup[g.active_vehicle_slot]].get('helicopter'))
        if heli:
            pygame.draw.circle(s,(77,90,80),r.center,43);pygame.draw.circle(s,(128,219,232) if g.deploy_selected else (214,218,180),r.center,40,3)
            t('H',r.center,30,center=True);t('直升机停机坪',(r.centerx,r.bottom+15),18,center=True)
        else:
            pygame.draw.rect(s,(47,79,91) if air else (35,46,48),r,border_radius=7);pygame.draw.rect(s,(128,219,232) if g.deploy_selected and air else (119,140,141),r,2,border_radius=7)
            t('远方机场',(r.centerx,r.y+23),20,center=True);t('战区外约 6.6 km',(r.centerx,r.y+54),14,center=True);t('3 km 跑道 · 点击起飞',(r.centerx,r.y+79),14,center=True)
        if air:
            pygame.draw.rect(s,(15,24,21),(200,79,880,35));t('直升机从圆形停机坪垂直起飞 · '+g.controls.label('air.hover')+' 开关悬停' if heli else '飞机必须先在地图外机场沿跑道起飞',(640,95),20,(237,219,162),True)
        if air and not g.deploy_selected:
            pygame.draw.rect(s,(15,24,21),(200,self.api['H']-31,self.api['W']-400,30));t('请先点击右侧停机坪，再确认部署' if heli else '请先点击右侧远方机场，再确认部署',(self.api['W']/2,self.api['H']-17),16,(235,202,139),True)
        if self.nuke_pending:
            t('核弹任务：占用当前载具栏',(1085,285),16,(244,213,131))
            model=AIRCRAFT[self.nuclear_model()];t(model['name']+' · BR '+str(model['ground_br']),(355,126),18,(244,213,131))
            rr=pygame.Rect(24,416+g.active_vehicle_slot*34,170,29);pygame.draw.rect(s,(103,91,51),rr,border_radius=4);t('核弹任务机 · 当前栏',(32,rr.y+7),14)
        nr=self.nuke_button();pygame.draw.rect(s,(97,88,48) if self.available_nuke else (38,43,39),nr,border_radius=5);t('核弹任务机 · '+g.controls.label('common.nuke'),nr.center-V(0,12),18,(242,216,140) if self.available_nuke else (142,150,144),True);t('已解锁 / 每场一次' if self.available_nuke else '需 2500 个人陆战分',nr.center+V(0,15),14,center=True)

def install(Game,Tank,api):
    original={k:getattr(Game,k) for k in ('__init__','deploy_player','camera','update','draw','choose_deployment','draw_deployment','register_death','vehicles','change_zoom')}
    def init(self,*args,**kwargs):
        original['__init__'](self,*args,**kwargs);self.flight=GroundFlight(self,api)
        if self.state=='play' and self.flight.selected_aircraft:self.flight.start(self.lineup[self.active_vehicle_slot])
    def deploy(self,pos):
        if self.flight.selected_aircraft or self.flight.nuke_pending:return self.flight.deploy()
        if self.flight.plane and self.flight.plane.dead:self.zoom=max(.65,self.zoom)
        return original['deploy_player'](self,pos)
    def camera(self,*args,**kwargs):
        if getattr(self,'flight',None) and self.flight.active:
            self.scope=False;p=self.flight.plane;missile=self.flight.guided_missile()
            focus=V(missile['p']) if missile else V(p.p)+direction(p.a)*min(2000,p.speed*.35,190/self.zoom)
            self.cam=focus-V(api['W']/self.zoom/2,api['VIEW'].h/self.zoom/2+api['VIEW'].top);return
        return original['camera'](self,*args,**kwargs)
    def update(self,dt):
        original['update'](self,dt);self.flight.update_ordnance(dt)
    def draw(self,*args,**kwargs):
        if self.flight.active and self.state in ('play','win'):
            from FlightView import draw as draw_flight
            draw_flight(self.flight,kwargs.get('mouse_position',args[0] if args else None));return
        original['draw'](self,*args,**kwargs)
        if self.state!='deploy':self.flight.hud()
    def change_zoom(self,delta):
        if self.flight.active:self.zoom=max(.10,min(2.2,self.zoom*(1.12**max(-40,min(40,delta)))));self.camera();return
        return original['change_zoom'](self,delta)
    def choose(self,pos):
        if self.flight.nuke_button().collidepoint(pos):self.flight.request_nuke();return
        if self.flight.airport_button().collidepoint(pos) and (self.flight.selected_aircraft or self.flight.nuke_pending):self.deploy_selected=True;self.deploy_choice=api['BASES'][False].copy();self.deploy_hint='停机坪已选，确认后垂直起飞' if self.flight.selected_aircraft and AIRCRAFT[self.lineup[self.active_vehicle_slot]].get('helicopter') else '机场已选，确认后在跑道起飞';return
        before=self.active_vehicle_slot;original['choose_deployment'](self,pos)
        if before!=self.active_vehicle_slot:self.deploy_selected=False
        if self.flight.selected_aircraft and self.deployment_map().collidepoint(pos):self.deploy_selected=False;self.deploy_hint='飞机只能选择右侧地图外机场'
    def deployment_draw(self):original['draw_deployment'](self);self.flight.deployment_ui()
    def death(self,t):
        if t is self.player and getattr(t,'airborne',False):
            if self.state in ('deploy','lose','win'):return
            if self.reserves>0:
                self.state='deploy';self.active_vehicle_slot=next(i for i,k in enumerate(self.lineup) if k and i not in self.used_slots);self.deploy_delay=5.;self.deploy_selected=False;self.deploy_hint=t.reason+' · 选择下一载具'
            elif self.flight.available_nuke:self.state='deploy';self.deploy_delay=5.;self.deploy_selected=False;self.deploy_hint='载具耗尽，仍可按 '+self.controls.label('common.nuke')+' 部署已解锁核弹机'
            else:self.state='lose'
            return
        original['register_death'](self,t)
        if t is self.player and self.state=='lose' and self.flight.available_nuke:self.state='deploy';self.deploy_delay=5.;self.deploy_selected=False
    def vehicles(self):return [t for t in original['vehicles'](self) if not getattr(t,'airborne',False)]
    for name,method in [('__init__',init),('deploy_player',deploy),('camera',camera),('update',update),('draw',draw),('choose_deployment',choose),('draw_deployment',deployment_draw),('register_death',death),('vehicles',vehicles),('change_zoom',change_zoom)]:setattr(Game,name,method)

def combined_self_test(api):
    import tempfile,collections,json
    Game=api['Game'];Profile=api['Profile'];Garage=api['Garage'];BASES=api['BASES'];Tank=api['Tank'];V=api['V']
    with tempfile.TemporaryDirectory() as root:
        profile=Profile(os.path.join(root,'profile.json'));garage=Garage(api['screen'],api['text'],profile);profile.country='cn';profile.research=100000
        ground=list(profile.lineups['cn']);profile.active['cn']=3
        plane_id=next(k for k,d in AIRCRAFT.items() if d['name']=='J-10C')
        for k,d in sorted(AIRCRAFT.items(),key=lambda item:(item[1]['branch'],item[1]['tier'])):
            if d['country']=='cn' and d['parent'] and not d.get('helicopter'):assert profile.aviation.unlock(k)
        assert profile.aviation.equip(plane_id);assert profile.lineups['cn'][3]==plane_id and profile.lineups['cn'][:3]==ground[:3]
        assert len(profile.lineups['cn'])==12 and profile.aviation.lineups is profile.lineups
        profile.save();restored=Profile(profile.path);assert restored.lineups==profile.lineups and plane_id in restored.unlocked
        garage.flight.preview=plane_id;garage.aviation=True
        for tab in ('garage','tech','data'):garage.tab=tab;garage.draw()
        game=Game(True,'cn',profile.lineups['cn'],3);game.flight.weapons=profile.aviation.weapons
        assert not game.deploy_player(BASES[False]);game.choose_deployment(game.flight.airport_button().center);assert game.deploy_player(game.deploy_choice)
        p=game.flight.plane;assert p.phase=='runway' and p.speed==0 and p.p.x<0 and p.p.y>game.world_size[1]
        assert game.used_slots=={3} and game.reserves==3 and game.player not in game.vehicles()
        keys=collections.defaultdict(int);keys[pygame.K_LSHIFT]=1
        for _ in range(1500):game.flight.update_controls(1/60,keys,(900,350),(False,False,False));game.camera()
        assert p.phase=='airborne' and p.altitude>0 and p.throttle>.9
        before=p.a;game.flight.update_controls(.2,collections.defaultdict(int),(900,200),(False,False,False));assert p.a!=before
        before=p.bank;keys[pygame.K_LSHIFT]=0;keys[pygame.K_d]=1;game.flight.update_controls(.2,keys,(900,350),(False,False,False));assert p.bank!=before
        throttle=p.throttle;keys[pygame.K_LCTRL]=1;keys[pygame.K_d]=0;game.flight.update_controls(.2,keys,(900,350),(False,False,False));assert p.throttle<throttle
        game.draw();assert game.state=='play'
        game.flight.destroy();assert game.state=='wreck' and game.active_vehicle_slot==0
        game.update(5.1);game.deploy_selected=True;assert game.deploy_player(BASES[False]);assert not game.flight.active and game.used_slots=={0,3}
        # Personal score excludes kills without player damage; damage attribution persists for assists.
        game.spawn_wave();target=game.enemies[0];target.dead=True;before=game.score;game.register_death(target);assert game.score==before
        target=game.enemies[0];target.dead=True;target.player_credit=True;game.register_death(target);assert game.score>before
        game.score=2499;assert not game.flight.request_nuke();game.score=2500;assert game.flight.request_nuke()
        game.choose_deployment(game.flight.airport_button().center);assert game.deploy_player(game.deploy_choice);assert game.flight.plane.nuclear and game.flight.nuke_used
        assert game.reserves==2 and not game.flight.request_nuke()
        p=game.flight.plane;p.phase='airborne';p.altitude=200;p.speed=200
        assert not game.flight.bomb();p.p=V(game.world_size)/2;p.a=0;game.flight.sync();assert game.flight.bomb()
        for _ in range(241):game.flight.update_ordnance(1/60)
        assert game.state=='play' and game.flight.nuke_detonated;game.draw()
        # Legacy separate aviation saves migrate into empty common slots only once.
        path=os.path.join(root,'legacy.json');old={'country':'cn','research':123,'unlocked':ground[:3],'lineups':{'cn':ground},'aviation':{'unlocked':[plane_id],'lineups':{'cn':[plane_id]+[None]*7}}}
        json.dump(old,open(path,'w',encoding='utf8'));legacy=Profile(path);assert legacy.lineups['cn'][:3]==ground[:3] and plane_id in legacy.lineups['cn']
        legacy.save();again=Profile(path);assert again.lineups==legacy.lineups and again.research==123
    print('PASS: shared ground research and eight slots, mixed-lineup saves/migration, airport runway takeoff, Shift/Ctrl throttle, mouse steering, active roll, aircraft/tank redeployment, personal score, 2500-point one-use nuclear mission, flight delivery and nuclear victory')

