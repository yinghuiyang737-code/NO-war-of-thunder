"""Aircraft replacements in the ground battle, using national vehicles and stores."""
import random
from types import SimpleNamespace
from pygame.math import Vector2 as V
from AircraftPhysics import Plane,direction,bearing,difference
from Aviation import AIRCRAFT
from AircraftLoadouts import available,consume
from FlightDynamics import step
from AircraftRadar import Radar
from AISkill import assign,reaction
from AIPilot import observe,aim_heading,gun_ready,shot_heading,egress

class AIFlights:
    def __init__(self,g):self.g=g;self.chance=.25;self.cap=2
    def candidates(self,team):
        country=(self.g.enemy_country or 'ussr') if team else (self.g.country or 'us')
        if not country:return []
        pool=[k for k,d in AIRCRAFT.items() if not d.get('helicopter') and d['country']==country and abs(d.get('ground_br',d['br'])-self.g.battle_br)<=1.0]
        armed=[k for k in pool if AIRCRAFT[k]['gun'] or AIRCRAFT[k]['bomb_count'] or AIRCRAFT[k]['rocket_count']]
        return armed
    def decide(self,entry,team):
        if 'aircraft' not in entry:
            pool=self.candidates(team)
            count=sum(1 for p in self.g.air.planes if not p['dead'] and p.get('managed',False) and p.get('team')==team)
            entry['aircraft']=random.choice(pool) if pool and count<self.cap and random.random()<self.chance else None
        if not entry['aircraft']:return False
        count=sum(1 for p in self.g.air.planes if not p['dead'] and p.get('managed',False) and p.get('team')==team)
        if count>=self.cap:return False
        self.spawn(entry,team);return True
    def spawn(self,entry,team):
        g=self.g;airport=V(g.world_size[0]+42000,-32000) if team else V(-42000,g.world_size[1]+32000)
        heading=bearing(V(g.world_size)/2-airport)
        p=Plane(entry['aircraft'],team,airport-direction(heading)*11000)
        p.a=heading;p.speed=0;p.phase='runway';p.bank=0;p.altitude=0;p.takeoff_distance=0;p.throttle=1
        record=dict(p=V(p.p),v=direction(heading)*.001,model=p.stats,team=team,dead=False,health=4,managed=True,ai_plane=p,phase='runway',bank=0,replacement=dict(vehicle=entry.get('vehicle'),elite=entry.get('elite',False)),attack_cd=0.,target=None,focus='机场起飞',age=0.,egress=0.)
        assign(record)
        record['heading']=heading;record['attention']=0.;record['sensor']=SimpleNamespace(g=g,plane=p,record=record)
        record['radar']=Radar(record['sensor'])
        if 'PD' in record['radar'].modes:record['radar'].mode='PD'
        g.air.planes.append(record);g.say(('敌军' if team else '队友')+'重新部署为 '+p.stats['name']+' · 正在远方机场起飞')
        return record
    def killed(self,q,owner=None):
        if q.get('registered'):return
        q['registered']=True;q['dead']=True;q['ai_plane'].dead=True;g=self.g
        entry=dict(q['replacement'],delay=8.)
        if q['team']:
            g.kills+=1;g.ground_kills+=1;g.score+=150 if g.is_player(owner) else 0
            if g.tickets[1]>0:g.enemy_queue.append(entry)
            else:g.enemy_queue.clear();g.state='win'
        else:g.ally_queue.append(entry)
        g.burst(q['p'],(255,168,68),35);g.say(('敌机被击落' if q['team'] else '队友飞机被击落')+' · 8 秒后重新部署')
    def update(self,q,dt):
        g=self.g;p=q['ai_plane']
        if q['dead']:return
        q['age']+=dt;q['attack_cd']=max(0,q['attack_cd']-dt);q['egress']=max(0,q['egress']-dt)
        center=V(g.world_size)/2;desired=q['heading'];target=None;focus='机场起飞'
        if p.phase=='airborne':
            q['radar'].update(dt);target=self.choose_target(q)
            previous=q['target'];q['target']=target
            q['attention']=min(1,q['attention']+dt*(.24+.24*assign(q))) if target is previous else 0.
            from AIRedeployResponse import order_for,matches
            response=order_for(g,q)
            point=V(response['p']) if response else center
            if isinstance(target,dict):
                point=observe(q,target)
                focus='专注对空截击'
            elif target is not None:point=observe(q,target);focus='专注对地攻击'
            else:focus='搜索战区'
            desired=bearing(point-p.p)
            if q.get('ground_pass_until',0) and q['age']>=q['ground_pass_until']:egress(q)
            if q['egress']:desired=q.get('egress_heading',p.a);focus='脱离攻击航线'
            # Full throttle uses exactly the player's full-throttle performance.
            p.throttle=min(1,p.throttle+.28*dt)
            if target is not None and q['attention']>=.6 and q['age']>=q.get('reaction_until',0) and not q['egress']:
                if isinstance(target,dict):self.attack_air(q,target)
                elif abs(difference(desired,p.a))<12 and target.p.distance_to(p.p)<2400:self.attack(q,target)
            if target is not None and not isinstance(target,dict) and target.p.distance_to(p.p)<600 and not q['egress']:egress(q)
            self.defend(q)
        q['focus']=focus;p.focus=focus
        if not step(p,dt,desired,q['heading']):self.killed(q);return
        q['p']=V(p.p);q['v']=direction(p.a)*p.speed;q['bank']=p.bank;q['sweep']=getattr(p,'sweep',0);q['phase']=p.phase
        if p.p.distance_to(center)>150000:p.a=bearing(center-p.p)
    def choose_target(self,q):
        g=self.g;p=q['ai_plane'];radar=q['radar']
        air=[]
        if p.ammo or p.pod_ammo or available(p,'aam'):
            for t in g.air.planes:
                if t is q or t['dead'] or t.get('team',1)==q['team']:continue
                if (t['controlled'].plane.phase if t.get('controlled') else t.get('phase','airborne'))!='airborne':continue
                delta=t['p']-p.p
                visual=delta.length()<16000 and abs(difference(bearing(delta),p.a))<60 and not g.smoke_blocks(p.p,t['p'])
                if radar.has_track(t) or visual:air.append(t)
        enemies=g.enemies if not q['team'] else g.allies+([g.player] if not getattr(g.player,'airborne',False) else [])
        ground=[t for t in enemies if not t.dead and (p.ammo or p.pod_ammo or available(p,'agm') or available(p,'bomb') or available(p,'rocket')) and t.p.distance_to(p.p)<32000 and abs(difference(bearing(t.p-p.p),p.a))<75 and not g.smoke_blocks(p.p,t.p,p.stats.get('thermal',False))]
        from AIRedeployResponse import order_for,matches
        response=order_for(g,q)
        revenge=next((t for t in air+ground if matches(g,t,response)),None)
        if revenge is not None:
            response['p']=V(revenge['p'] if isinstance(revenge,dict) else revenge.p);return revenge
        attacker=q.get('retaliation_attacker')
        if g.time<q.get('retaliation_until',0) and any(candidate is attacker for candidate in air+ground):return attacker
        current=q['target']
        # Fighters intercept first; attackers defend against nearby aircraft before resuming ground support.
        priority=air if p.stats['branch']<3 or any(t['p'].distance_to(p.p)<12000 for t in air) else ground
        if not priority:priority=ground or air
        if any(t is current for t in priority):return current
        return min(priority,key=lambda t:(t['p'] if isinstance(t,dict) else t.p).distance_squared_to(p.p),default=None)
    def attack_air(self,q,target):
        p=q['ai_plane'];g=self.g;distance=target['p'].distance_to(p.p);error=abs(difference(bearing(target['p']-p.p),p.a));radar=q['radar']
        for pending in available(p,'aam'):
            guidance=pending.get('guidance','').upper();guidance='SARH' if 'SARH' in guidance else 'ARH' if 'ARH' in guidance else 'IR'
            if p.mcd or error>(35 if guidance=='IR' else 60) or distance>(40000 if guidance=='IR' else 80000):continue
            if guidance!='IR' and not radar.has_track(target):continue
            if guidance=='SARH':
                radar.mode='PD' if 'PD' in radar.modes else 'RWS';radar.stt=target
            weapon=consume(p,'aam',pending['short'].split()[0])
            g.flight.projectiles.append(dict(p=V(p.p),v=direction(p.a)*(5600+p.speed*.4),life=5.,kind='missile',target=target,guidance=guidance,weapon=weapon,team=p.team,owner=None,source=q))
            p.mcd=random.uniform(4.5,7.);break
        if distance>2600 or p.cd or not (p.ammo or p.pod_ammo) or not gun_ready(q):return
        heading=shot_heading(q,target)
        if heading is None:return
        if p.ammo:p.ammo-=1
        else:p.pod_ammo-=1
        caliber=p.stats.get('caliber',20);pen=13 if caliber<10 else 27 if caliber<20 else min(85,caliber*2)
        belt=p.stats['belts'][p.belt] if p.stats['belts'] else 'Default'
        ammo=dict(name='机炮 '+belt,type='HE' if 'air targets' in belt.lower() else 'AP',velocity=950,penetration=[pen,pen*.9,pen*.75,pen*.5,pen*.3,pen*.2])
        g.flight.projectiles.append(dict(p=V(p.p),v=direction(heading+random.uniform(-1.2,1.2))*(2400+p.speed),life=1.1,kind='gun',ammo=ammo,team=p.team,owner=None,source=q));p.cd=.09
    def defend(self,q):
        p=q['ai_plane']
        if p.cdc or not p.flares:return
        threats=[m for m in self.g.flight.projectiles if m.get('kind')=='missile' and m.get('target') is q and m['p'].distance_to(p.p)<8000]
        threats+= [m for m in self.g.air.missiles if m.get('target') is q and m['p'].distance_to(p.p)<8000]
        if not threats:q.pop('threat_ready',None);return
        if 'threat_ready' not in q:q['threat_ready']=q['age']+random.uniform(.55,1.1)*(1.65-1.05*assign(q))+(.4 if q['target'] is not None and not isinstance(q['target'],dict) else 0.)
        if q['age']>=q['threat_ready']:
            from Countermeasures import release,guidance
            kinds={guidance(m) for m in threats};kind='mixed' if 'IR' in kinds and kinds&{'SARH','ARH','RADAR'} else 'flare' if 'IR' in kinds else 'chaff'
            release(self.g,p,kind)
    def attack(self,q,target):
        p=q['ai_plane'];g=self.g
        if q['egress'] or q['attack_cd']:return
        kind=next((k for k in ('agm','bomb','rocket') if available(p,k) and not getattr(p,{'agm':'mcd','bomb':'bcd','rocket':'rcd'}[k])),None)
        common=dict(p=V(p.p),v=direction(p.a)*(2400+p.speed),team=p.team,owner=None,source=q,life=1.1)
        if kind:
            pending=available(p,kind)[0]
            if 'anti-ship' in pending['short'].lower() or ('anti-radiation' in pending['short'].lower() and not target.stats.get('radar')):kind=None
            elif 'laser' in pending['guidance'].lower() and not (p.pods or any(n in p.stats['name'] for n in ('Su-25','Su-24','Su-34','MiG-27','Q-5L'))):kind=None
            elif kind=='bomb' and not pending['guidance'] and (p.p+direction(p.a)*p.speed*.8).distance_to(target.p+direction(target.body)*target.speed*.8)>120:kind=None
        if kind:
            store=consume(p,kind);common.update(kind=kind,weapon=store,ammo={'name':store['short'],'type':'HEAT' if kind=='agm' else 'HE','velocity':900,'penetration':[900 if kind=='agm' else 100]*6})
            if kind=='bomb':common.update(point=V(target.p) if store['guidance'] else p.p+direction(p.a)*p.speed*.8,life=.8);p.bcd=.45
            if kind=='agm':common.update(target=target,life=18.,v=direction(p.a)*(4500+p.speed*.3));p.mcd=1.2
            if kind=='rocket':common['life']=1.8;common['v']=direction(p.a+random.uniform(-2.5,2.5))*(2400+p.speed);p.rcd=.18
        elif (p.ammo or p.pod_ammo) and not p.cd and gun_ready(q):
            heading=shot_heading(q,target)
            if heading is None:return
            if not q.get('ground_pass_until'):q['ground_pass_until']=q['age']+random.uniform(.9,1.4)
            if p.ammo:p.ammo-=1
            else:p.pod_ammo-=1
            caliber=p.stats.get('caliber',20);pen=13 if caliber<10 else 27 if caliber<20 else min(85,caliber*2)
            belt=p.stats['belts'][p.belt] if p.stats['belts'] else 'Default'
            common.update(kind='gun',ammo={'caliber':caliber,'name':'机炮 '+belt,'type':'HE' if 'air targets' in belt.lower() else 'AP','velocity':950,'penetration':[pen,pen*.9,pen*.75,pen*.5,pen*.3,pen*.2]})
            common['v']=direction(heading+random.uniform(-1.2,1.2))*(2400+p.speed);p.cd=.09
        else:return
        g.flight.projectiles.append(common)
        if kind in ('agm','bomb'):egress(q);q['attack_cd']=random.uniform(9.,14.)
        elif kind=='rocket':
            q['pass_rockets']=q.get('pass_rockets',0)+1
            if q['pass_rockets']>=3:q['pass_rockets']=0;egress(q)
            elif not q.get('ground_pass_until'):q['ground_pass_until']=q['age']+1.2

def install(Game):
    original_init=Game.__init__;original_death=Game.register_death;original_update=Game.update
    def init(self,*a,**kw):original_init(self,*a,**kw);self.ai_flights=AIFlights(self)
    def death(self,t):
        ally=t in self.allies;original_death(self,t)
        if ally and self.ally_queue:self.ally_queue[-1]=dict(delay=8.,vehicle=t.vehicle_id,elite=False)
    def update(self,dt):
        deploying=self.state=='deploy' and not self.paused
        original_update(self,dt)
        if deploying and self.state=='deploy':
            for q in self.air.planes[:]:
                if q.get('managed'):
                    if q['dead']:self.air.planes.remove(q)
                    else:self.ai_flights.update(q,dt)
            for entry in self.ally_queue[:]:
                if not isinstance(entry,dict):continue
                entry['delay']-=dt
                if entry['delay']<=0:
                    self.ally_queue.remove(entry)
                    if not self.ai_flights.decide(entry,0):self.spawn_allies(1,vehicle=entry.get('vehicle') if entry.get('vehicle_selected') else self.choose_ai_ground(False,entry.get('vehicle')))
    Game.__init__=init;Game.register_death=death;Game.update=update

