import math,random
import pygame
from pygame.math import Vector2 as V
from VehicleData import guided, explosive
from GroundSystems import missile_guidance
class AirDefense:
    def __init__(self,game,screen,text,view):
        self.g=game;self.screen=screen;self.text=text;self.view=view;self.planes=[];self.missiles=[];self.timer=18.;self.lock=None;self.missile_cd=0.;self.kills=0
        self.scan_clock=0.;self.scan_tracks=[];self.scan_range=40000.
    def radar_vehicle(self):
        battery=getattr(self.g,"battery",None)
        return battery.radar if battery and battery.radar and self.g.player in battery.units else self.g.player
    @property
    def scan_range(self):
        from RadarContacts import ground_fit
        return ground_fit(self.radar_vehicle())[0]*8000*getattr(self.radar_vehicle(),'radar_scale',1.)
    @scan_range.setter
    def scan_range(self,value):pass
    def targets(self,t):
        planes=[p for p in self.planes if not p['dead'] and p.get('team',1)!=(1 if t.enemy else 0)]
        ground=[o for o in (self.g.allies+[self.g.player] if t.enemy else self.g.enemies) if not o.dead and not getattr(o,'airborne',False)]
        from RadarContacts import radar_missiles as missiles
        if t.stats.get('radar') or t.stats.get('branch')==3:planes += [m for m in missiles(self.g) if m['team']!=int(t.enemy)]
        if t.stats.get('name')=='ADATS':return planes+ground
        if t.stats.get('missile_ground'):return ground
        return planes
    def position(self,target):return target['p'] if isinstance(target,dict) else target.p
    def valid(self,target,t):
        if target is None:return False
        if isinstance(target,dict):
            from RadarContacts import radar_missiles as missiles
            return any(q is target for q in (missiles(self.g) if target.get('missile') else self.planes)) and not target.get('dead',False) and target.get('life',1)>0 and target.get('team',1)!=int(t.enemy)
        return not target.dead and target in (self.g.allies+[self.g.player] if t.enemy else self.g.enemies)
    def sight(self,target,t):
        if isinstance(target,dict):return t.stats.get('radar') or not self.g.smoke_blocks(t.p,target['p'])
        return self.g.visible(t.p,target.p,t.stats.get('thermal',False))
    def lock_target(self):
        t=self.g.player
        if getattr(t,'airborne',False):return
        if not t.vehicle_id or not (t.stats.get('radar') or t.stats.get('missile') or t.stats['branch']==3):self.g.say('这辆载具没有防空瞄准或导弹设备');return False
        distance=self.scan_range if t.stats.get('radar') else 4000 if missile_guidance(t.missile_ammo)=='TOP_ATTACK' else 1400
        candidates=[o for o in self.targets(t) if self.position(o).distance_to(t.p)<distance and self.sight(o,t) and (not isinstance(o,dict) or not t.stats.get('radar') or o.get('missile') or any(track['target'] is o for track in self.scan_tracks) or self.position(o).distance_to(t.p)<1400)]
        if not candidates:self.lock=None;self.g.say('范围内没有可锁定目标');return False
        self.lock=min(candidates,key=lambda o:self.position(o).distance_squared_to(t.p));self.g.say('雷达锁定目标' if t.stats.get('radar') else '光学锁定目标');return True
    def launch(self,t=None,target=None,ammo=None):
        t=t or self.g.player
        if t.stats.get('split_system') and getattr(t,'split_role','radar')=='radar':return False
        if t.stats.get('split_system'):
            battery=self.g.battery
            if not battery.radar or battery.radar.dead or t.p.distance_to(battery.radar.p)>1200:return False
        ammo=ammo or (t.missile_ammo if t.stats.get('independent_missiles') else t.ammo if t.ammo and guided(t.ammo) else t.missile_ammo)
        if (ammo or {}).get('kinetic_missile') and abs(t.speed)>25:
            if t is self.g.player:self.g.say('LOSAT 发射时车速须低于 5 km/h')
            return False
        independent=t.stats.get('independent_missiles',False)
        if t.dead or not t.vehicle_id or not t.stats.get('missile') or not t.modules['gunner'] or (not independent and not t.modules['breech']):return False
        if t.missile_count is not None and t.missile_count<=0:return False
        if (t.missile_cd if independent else t.cd)>0:return False
        if t is self.g.player:
            target=target or self.lock
        elif target is None:
            candidates=[o for o in self.targets(t) if self.position(o).distance_to(t.p)<1800 and self.sight(o,t)]
            if candidates:target=min(candidates,key=lambda o:self.position(o).distance_squared_to(t.p))
        mode=missile_guidance(ammo)
        if mode in ('IR','ARH','TOP_ATTACK') and (not self.valid(target,t) or not self.sight(target,t) or (mode=='TOP_ATTACK' and isinstance(target,dict))):
            if t is self.g.player:self.g.say('长钉需要先锁定地面目标，发射后自动追踪攻顶' if mode=='TOP_ATTACK' else '红外自导弹需要先锁定目标')
            return False
        if not self.valid(target,t):target=None
        delta=self.position(target)-t.p if mode in ('IR','ARH','TOP_ATTACK') or (isinstance(target,dict) and t.stats.get('branch')==3) else V(math.cos(math.radians(t.aim)),math.sin(math.radians(t.aim)))*2000
        if delta.length_squared()<1:return False
        if t.missile_count is not None:t.missile_count-=1
        delay=t.stats['missile_reload'] if independent else t.stats['reload']
        if t is self.g.player:self.missile_cd=delay
        if independent:t.missile_cd=delay
        else:t.cd=delay
        self.missiles.append({'p':V(t.p),'v':delta.normalize()*(45 if (ammo or {}).get('kinetic_missile') else 520),'target':target,'owner':t,'life':12.,'ammo':dict(ammo) if ammo else None,'distance':0.,'guidance':mode,'start':V(t.p),'height':0.,'initial_range':delta.length()})
        return True
    def spawn(self):
        if sum(1 for q in self.planes if not q['dead'] and q.get('managed') and q.get('team',1)==1)>=self.g.ai_flights.cap:return None
        pool=self.g.ai_flights.candidates(1)
        if not pool:return None
        import random
        return self.g.ai_flights.spawn(dict(aircraft=random.choice(pool),vehicle=None,elite=False),1)
    def kill_plane(self,p,owner=None):
        if p['dead']:return
        if p.get('controlled'):
            p['controlled'].damage(p['p'],True);return
        if p.get('managed'):self.g.ai_flights.killed(p,owner);return
        p['dead']=True;self.kills+=1;self.g.kills+=1;self.g.score+=150 if self.g.is_player(owner) else 0;self.g.burst(p['p'],(255,168,68),28);self.g.say('击落敌机 +150',(192,232,156))
        if self.lock is p:self.lock=None
    def shell_hit(self,start,end,owner,ammo=None):
        if not owner or not owner.vehicle_id or owner.stats['branch']!=3:return False
        for p in self.planes:
            if p['dead'] or p.get('team',1)==(1 if owner.enemy else 0):continue
            if p.get('controlled'):
                contacts=[hit for shape in p['controlled'].plane.hit_polygons() if (hit:=__import__('VehicleGeometry').segment_polygon(start,end,shape)) is not None]
                contact=min(contacts,key=lambda h:h[0]) if contacts else None
                if contact:
                    p['last_attacker']=owner;p['last_weapon']=(ammo or {}).get('name','防空炮');p['controlled'].g.player.last_attacker=owner;p['controlled'].g.player.last_weapon=p['last_weapon']
                    p['controlled'].damage(contact[1],bool(ammo and explosive(ammo)));return True
                continue
            if p.get('model'):
                from AircraftModels import contact as model_contact
                heading=math.degrees(math.atan2(p['v'].y,p['v'].x));contact=model_contact(p['model'],p['p'],heading,start,end,bank=p.get('bank',0),sweep=p.get('sweep',0))
            else:
                rect=pygame.Rect(0,0,52,42);rect.center=p['p'];contact=rect.clipline(start,end)
            if contact:
                p['last_attacker']=owner;p['last_weapon']=(ammo or {}).get('name','防空炮')
                point=V(contact[1]) if p.get('model') else V(contact[0])
                if p.get('managed'):
                    p['ai_plane'].damage(point,bool(ammo and explosive(ammo)))
                    if p['ai_plane'].dead:self.kill_plane(p,owner)
                    self.g.record_air_hit(p,point,owner,p['last_weapon'])
                    return True
                p['health']-=2 if ammo and explosive(ammo) else 1;self.g.burst(p['p'],(247,199,87),5)
                if p['health']<=0:self.kill_plane(p,owner)
                self.g.record_air_hit(p,point,owner,p['last_weapon'])
                return True
        return False
    def update(self,dt):
        g=self.g;self.missile_cd=max(0,self.missile_cd-dt)
        self.scan_clock+=dt
        if g.player.stats.get('radar') and not getattr(g.player,'airborne',False):
            heading=self.scan_clock*120%360
            from RadarContacts import radar_missiles as missiles
            for plane in self.planes:
                if plane['dead']:continue
                delta=plane['p']-self.radar_vehicle().p;az=math.degrees(math.atan2(delta.y,delta.x))%360
                if delta.length()>self.scan_range or (heading-az)%360>max(4,120*dt):continue
                track=next((q for q in self.scan_tracks if q['target'] is plane),None)
                record={'target':plane,'p':V(plane['p']),'seen':self.scan_clock}
                if track:track.update(record)
                else:self.scan_tracks.append(record)
            self.scan_tracks=[q for q in self.scan_tracks if not q['target'].get('missile') and not q['target']['dead'] and self.scan_clock-q['seen']<4 and q['p'].distance_to(self.radar_vehicle().p)<self.scan_range]
        else:self.scan_tracks=[]
        if self.lock is not None and (not self.valid(self.lock,g.player) or not self.sight(self.lock,g.player)):self.lock=None
        self.timer-=dt
        if self.timer<=0 and g.wave>0 and not g.country and len(g.enemies)+len(g.enemy_queue)+sum(not q['dead'] and q.get('team',1)==1 for q in self.planes)<16:self.timer=28.;self.spawn()
        for p in self.planes[:]:
            if p.get('controlled'):
                if p['dead']:self.planes.remove(p)
                continue
            if p.get('managed'):
                if p['dead']:self.planes.remove(p)
                else:g.ai_flights.update(p,dt)
                continue
            p['p']+=p['v']*dt;p['life']-=dt;p['bomb']-=dt
            if p['dead'] or p['life']<=0 or not pygame.Rect(-100,-100,g.world_size[0]+200,g.world_size[1]+200).collidepoint(p['p']):
                if self.lock is p:self.lock=None
                self.planes.remove(p);continue
            if p['bomb']<=0 and p.get('bombs_left',0)>0:
                p['bombs_left']-=1
                p['bomb']=3.
                targets=[t for t in [g.player]+g.allies if not t.dead and not getattr(t,'airborne',False) and t.p.distance_to(p['p'])<150]
                for t in targets:
                    g.burst(t.p,(242,135,61),18)
                    if random.random()<.55:t.damage_module(random.choice(('engine','left_track','right_track')),1)
                    if t.dead:g.register_death(t)
        for missile in self.missiles[:]:
            missile['age']=missile.get('age',0)+dt
            missile['life']-=dt;t=missile['target'];owner=missile['owner']
            mode=missile.get('guidance','IR')
            if mode=='TOP_ATTACK':
                from SpikeGuidance import update
                update(self,missile,dt)
                continue
            if missile['life']<=0:self.missiles.remove(missile);continue
            if isinstance(t,dict) and not t.get('missile') and __import__('Countermeasures').distracted(g,missile,t,dt):missile['target']=None;t=None
            seeker=mode in ('IR','ARH') or owner.stats.get('branch')==3
            if seeker:
                from MissileSeeker import acquire
                t=acquire(missile,self.targets(owner),lambda q:self.valid(q,owner),lambda q:self.sight(q,owner))
            valid=self.valid(t,owner)
            aim=V(math.cos(math.radians(owner.aim)),math.sin(math.radians(owner.aim)))
            point=self.position(t) if seeker and t is not None or (valid and isinstance(t,dict) and (t.get('missile') or owner.stats.get('branch')==3)) else owner.p+aim*max(1500,missile['p'].distance_to(owner.p)+800)
            delta=point-missile['p'];speed=missile['v'].length()
            if mode=='LASER_BEAM' and valid and not isinstance(t,dict) and abs((math.degrees(math.atan2((t.p-owner.p).y,(t.p-owner.p).x))-owner.aim+180)%360-180)<4:g.illuminate(owner,t)
            if not ((missile.get('ammo') or {}).get('kinetic_missile') and missile['age']>5) and delta.length_squared()>1 and (t is not None and self.sight(t,owner) if seeker else not owner.dead and owner.modules['gunner']>0):
                heading=math.degrees(math.atan2(missile['v'].y,missile['v'].x));desired=math.degrees(math.atan2(delta.y,delta.x));turn=(desired-heading+180)%360-180
                heading+=max(-70*dt,min(70*dt,turn));missile['v']=V(math.cos(math.radians(heading)),math.sin(math.radians(heading)))*min(5600 if isinstance(t,dict) else 850,speed+(1800 if isinstance(t,dict) else 200)*dt)
            if (missile.get('ammo') or {}).get('kinetic_missile'):
                speed=min(1520*.75,speed+1800*.75*dt);missile['v'].scale_to_length(speed)
            old=V(missile['p']);missile['p']+=missile['v']*dt;missile['distance']+=missile['v'].length()*dt
            from NewRewardVehicles import blocks as projectile_blocks
            if owner.stats.get('branch')!=3 and not isinstance(t,dict) and projectile_blocks(g.terrain,old,missile['p'],missile.get('ammo')):g.burst(missile['p'],(233,156,75),12);self.missiles.remove(missile);continue
            if not isinstance(t,dict) and any(g.try_aps(candidate,old,missile['p'],missile['v'],missile.get('ammo'),owner) for candidate in g.vehicles() if candidate.enemy!=owner.enemy):
                self.missiles.remove(missile);continue
            # Command-guided weapons hit the first actual enemy contact, including unlocked targets.
            contacts=[]
            for candidate in ([q for q in self.targets(owner) if isinstance(q,dict) and self.valid(q,owner)]+[q for q in g.vehicles() if not q.dead and q.enemy!=owner.enemy and not getattr(q,'airborne',False)]):
                if isinstance(candidate,dict):
                    from AirIntercept import closest, fuse_radius
                    near=closest(old,missile['p']-candidate.get('v',V())*dt,candidate['p']) if candidate.get('missile') else closest(old+candidate.get('v',V())*dt,missile['p'],candidate['p'])
                    if near.distance_to(candidate['p'])<=fuse_radius(missile.get('ammo'),True):
                        contacts.append((near.distance_squared_to(old),candidate));missile['fuze_point']=V(near);continue
                    if candidate.get('missile'):continue
                    if candidate.get('model'):
                        from AircraftModels import contact as model_contact
                        hit=model_contact(candidate['model'],candidate['p'],math.degrees(math.atan2(candidate['v'].y,candidate['v'].x)),old,missile['p'],bank=candidate.get('bank',0),sweep=candidate.get('sweep',0))
                        point=hit[1] if hit else None
                    else:
                        box=pygame.Rect(0,0,56,48);box.center=candidate['p'];hit=box.clipline(old,missile['p']);point=hit[0] if hit else None
                    if hit:contacts.append((V(point).distance_squared_to(old),candidate))
                else:
                    hit=candidate.shell_contact(old,missile['p'])
                    if hit:contacts.append((V(hit[1]).distance_squared_to(old),candidate))
            if not contacts:continue
            t=min(contacts,key=lambda item:item[0])[1]
            if contacts:
                if isinstance(t,dict):
                    from AirIntercept import fragments
                    fragments(g,missile.get('fuze_point',missile['p']),owner,missile.get('ammo'),primary=t)
                if isinstance(t,dict) and t.get('missile'):
                    from AirIntercept import destroy_missile
                    destroy_missile(g,t,owner)
                elif isinstance(t,dict):
                    t['last_attacker']=owner;t['last_weapon']=(missile.get('ammo') or {}).get('name','防空导弹')
                    if t.get('controlled'):t['controlled'].g.player.last_attacker=owner;t['controlled'].g.player.last_weapon=t['last_weapon']
                    g.record_air_hit(t,t['p'],owner,t['last_weapon']);self.kill_plane(t,owner)
                else:
                    result=t.hit(old,missile['p'],missile['v'],missile['distance'],penetration_value=600,ammo=missile.get('ammo'))
                    if result and result.get('modules'):
                        t.last_attacker=owner;t.last_weapon=(missile.get('ammo') or {}).get('name','导弹')
                        if g.is_player(owner):t.player_credit=True
                    if result:g.record_hit(t,result,owner,(missile.get('ammo') or {}).get('name','导弹'));g.say(result['kind'])
                    from BlastFragments import detonate
                    detonate(g,result['point'] if result else missile['p'],missile.get('ammo') or {},owner,(missile.get('ammo') or {}).get('name','导弹'),int(owner.enemy))
                    g.burst(t.p,(255,173,80),25)
                    if t.dead:g.register_death(t)
                self.missiles.remove(missile)
    def draw(self):
        g=self.g;s=self.screen
        for p in self.planes:
            if p.get('controlled'):continue
            q=g.to_screen(p['p']);a=math.degrees(math.atan2(p['v'].y,p['v'].x))
            if not self.view.inflate(120,120).collidepoint(q):continue
            shadow=q+V(25,30)
            if p.get('model'):
                from AircraftModels import polygons
                for _,shape in polygons(p['model'],8,p.get('bank',0),p.get('sweep',0)):pygame.draw.polygon(s,(36,43,35),[shadow+v.rotate(a) for v in shape])
            else:pygame.draw.ellipse(s,(36,43,35),(shadow.x-26,shadow.y-12,52,24))
            from Aviation import draw_aircraft
            if p.get('model'):draw_aircraft(s,p['model'],q,1,a,units=8,bank=p.get('bank',0),sweep=p.get('sweep',0))
            if p.get('managed'):self.text(('敌军' if p['team'] else '队友')+' '+p['model']['name'],q+V(0,45),14,(240,156,117) if p['team'] else (134,211,246),True)
        for missile in self.missiles:
            q=g.to_screen(missile['p'])-V(0,min(80,missile.get('height',0)*.25));d=missile['v'].normalize();pygame.draw.line(s,(242,220,173),q-d*18,q,3);pygame.draw.circle(s,(255,139,56),q-d*20,3)
        if getattr(g,'flight',None):g.flight.draw_world(s)
        if self.valid(self.lock,g.player):
            q=g.to_screen(self.position(self.lock));pygame.draw.rect(s,(142,249,171),(q.x-35,q.y-29,70,58),2)
            self.text('锁定',(q.x,q.y-42),14,(155,238,169),True)
    def hud(self):
        t=self.g.player
        if getattr(t,'airborne',False):return
        if not t.vehicle_id or not (t.stats['branch']==3 or t.stats.get('missile')):return
        if self.valid(self.lock,t):
            from TargetMarkers import draw as draw_target
            distance=self.position(self.lock).distance_to(t.p)/8000
            draw_target(self.screen,self.text,self.g.world_to_display(self.position(self.lock)),(365,165,625,430),f'锁定 {distance:.2f} km',(142,249,171),self.g.world_to_display(t.p))
        count=len(self.planes);target='已锁定' if self.valid(self.lock,t) else '未锁定'
        label=f'空中目标 {count} · {target} · '+self.g.controls.label('ground.lock')+' 锁定'
        if t.stats.get('missile'):
            cooldown=t.missile_cd if t.stats.get('independent_missiles') else t.cd
            label+=' · '+self.g.controls.label('ground.missile')+f' {t.missile_ammo["name"]} / 冷却 {cooldown:.1f}s'
            label+=' · '+('锁定后自动追踪 / 攻顶' if missile_guidance(t.missile_ammo)=='TOP_ATTACK' else '需锁定' if missile_guidance(t.missile_ammo)=='IR' else '随准星制导，无需锁定')
            if t.stats.get('independent_missiles'):label+=' · '+self.g.controls.label('ground.missile_ammo')+' 换导弹 / '+self.g.controls.label('ground.fire')+' 机炮'
            if t.missile_count is not None:label+=f' · 余弹 {t.missile_count}'
        self.text(label,(18,98),14,(195,228,181))
        if t.stats.get('radar'):
            s=self.screen;r=pygame.Rect(16,147,310,315);pygame.draw.rect(s,(10,24,23),r,border_radius=7)
            self.text('防空搜索雷达 · 360° 扫描',(28,158),18,(167,226,177));
            from RadarContacts import ground_fit
            km,model,estimated=ground_fit(self.radar_vehicle())
            self.text(f'{model} · {self.scan_range/8000:g} / {km:g} km'+('（模拟）' if estimated else ''),(28,186),14)
            center=V(171,321);radius=105
            for rr in (35,70,105):pygame.draw.circle(s,(40,88,57),center,rr,1)
            for angle in range(0,360,45):
                d=V(math.cos(math.radians(angle)),math.sin(math.radians(angle)));pygame.draw.line(s,(35,70,47),center,center+d*radius,1)
            for offset in range(0,28,2):
                angle=math.radians(self.scan_clock*120-offset-t.body-90);d=V(math.cos(angle),math.sin(angle));pygame.draw.line(s,(18,max(30,150-offset*4),53),center,center+d*radius,2)
            from RadarContacts import radar_missiles as missiles
            echoes=[dict(target=m,p=m['p']) for m in missiles(self.g) if m['p'].distance_to(self.radar_vehicle().p)<self.scan_range]
            for i,track in enumerate(self.scan_tracks+echoes):
                delta=(track['p']-self.radar_vehicle().p).rotate(-t.body-90)*radius/self.scan_range
                if delta.length()>radius:delta.scale_to_length(radius-2)
                q=center+delta
                friendly=track['target'].get('team',1)==0;color=(119,182,241) if friendly else (255,119,86)
                if track['target'].get('missile'):pygame.draw.polygon(s,(246,221,104),[q+V(0,-4),q+V(4,0),q+V(0,4),q+V(-4,0)],1)
                elif friendly:pygame.draw.circle(s,color,q,4,1)
                else:pygame.draw.polygon(s,color,[q+V(0,-5),q+V(-5,4),q+V(5,4)],2)
                if self.lock is track['target']:pygame.draw.rect(s,(255,221,118),(q.x-9,q.y-9,18,18),2)
            self.text(self.g.controls.label('ground.radar_range')+' 量程 · '+self.g.controls.label('ground.radar_target')+' 切换目标',(28,438),14,(154,194,162))

