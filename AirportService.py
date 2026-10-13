"""Friendly runway approach, landing and finite service cycle."""
import copy
import math
from pygame.math import Vector2 as V
from AircraftPhysics import direction,bearing,difference
from FlightDynamics import step
from AircraftLoadouts import install_plane
from LandingDevices import airborne,rollout,status,prepare,landing_speed

class AirportService:
    def __init__(self,flight):self.f=flight;self.timer=0.;self.stage='align';self.heading=flight.heading
    def request(self):
        f=self.f;p=f.plane
        if not f.active or p.phase!='airborne':f.g.say('请在飞行中申请自动降落');return False
        if p.p.distance_to(f.airport)>32000:f.g.say('请飞到友方机场 4 km 范围内申请自动降落');return False
        p.hover=False;p.hover_anchor=None;p.approach_entry_speed=p.speed;p.heli_velocity=V()
        axis=direction(f.heading)
        self.heading=f.heading+(180 if (p.p-f.airport).dot(axis)>0 else 0)
        p.phase='approach';self.stage='align';self.timer=0.;f.lock=None;p.cable_engaged=False;p.cable_anchor=None
        f.g.say('自动降落：进入跑道航线，停稳后维修补给');return True
    def update(self,dt):
        f=self.f;p=f.plane;heading=self.heading;axis=direction(heading)
        if p.phase=='service':
            self.timer=max(0,self.timer-dt)
            if self.timer<=0:self.finish()
            return
        if p.stats.get('helicopter'):
            delta=f.airport-p.p;p.speed=max(0,min(500,delta.length()*1.5));p.p+=delta.normalize()*min(delta.length(),p.speed*dt) if delta.length_squared()>1 else delta;p.a=bearing(delta) if delta.length_squared()>1 else p.a
            p.altitude=max(0,p.altitude-30*dt) if delta.length()<300 else max(40,p.altitude)
            if delta.length()<15 and p.altitude==0:p.p=V(f.airport);p.speed=0;p.phase='service';self.timer=8.
            f.sync();return
        if p.phase=='landing' and p.altitude<=0:
            rollout(f,p,dt)
            if p.speed<10:p.speed=0;p.phase='service';self.timer=8.;f.g.say('飞机已停稳：维修、加油及补充弹药中（8 秒）')
            return
        safe=(155 if p.stats['max_speed']>850 else 95)/3.6*8
        lateral=(p.p-f.airport).dot(axis.rotate(90));along=(p.p-f.airport).dot(axis)
        remaining=max(0,-7000-along)
        p.approach_deceleration=80. # 10 m/s² in the world's eight units per metre.
        final_speed=landing_speed(p,f.g.battle_br)
        target_speed=min(p.stats['speed'],max(final_speed*.4,getattr(p,'approach_entry_speed',p.speed)),math.sqrt(final_speed**2+2*p.approach_deceleration*remaining))
        airborne(p,dt,target_speed)
        p.hook_deployed=bool(p.landing_equipment['hook'] and f.g.battle_br>=8 and p.phase=='landing')
        engine=.55 if p.modules['engine']==1 else 1.
        # Idle is real zero throttle; the normal flight speed floor must not defeat braking.
        p.throttle=0. if p.speed>target_speed+12 else min(1.,target_speed/(p.stats['speed']*engine))
        lateral=(p.p-f.airport).dot(axis.rotate(90));along=(p.p-f.airport).dot(axis)
        # Intercept the centreline ahead of the aircraft. Never send it back
        # to a fixed distant entry point after it has passed that point.
        lookahead=max(800,p.speed*.45)
        desired=heading+bearing(V(lookahead,-lateral))
        if p.phase=='approach' and abs(lateral)<160 and abs(difference(p.a,heading))<12 and p.speed<final_speed+80:
            p.phase='landing'
        if p.phase=='approach' and along>7500:
            self.heading=(heading+180)%360
        old_alt=p.altitude
        if p.modules['engine']==0 or not step(p,dt,desired,heading):
            f.destroy();f.g.say('飞机动力或升力不足，自动降落失败');return
        if p.phase=='approach':p.altitude=old_alt+max(-60*dt,min(65*dt,40-old_alt))
        else:
            along=(p.p-f.airport).dot(axis);lateral=abs((p.p-f.airport).dot(axis.rotate(90)))
            slope=max(0,min(120,(-9000-along)*.04))
            aligned=lateral<160 and abs(difference(p.a,heading))<12
            if not aligned:slope=max(40,slope)
            if along>8000:
                self.heading=(heading+180)%360;p.phase='approach';self.stage='align';slope=120
            p.altitude=max(slope,old_alt-60*dt);p.bank=max(-15,min(15,p.bank))
            if aligned and -10000<along<8000 and p.altitude<.01:
                p.altitude=0.;p.a=heading;p.bank=0.;p.throttle=0.
    def finish(self):
        f=self.f;p=f.plane;nuclear=getattr(p,'nuclear',False);bombs=p.bombs
        choices={'loadout':copy.deepcopy(p.loadout),'belt':p.belt,'missile':p.missile}
        for module in p.modules:p.modules[module]=2
        p.ammo=p.stats['ammo'];p.flares=30 if p.stats.get('countermeasures') else 0
        install_plane(p,choices)
        if nuclear:
            from NuclearMission import configure
            configure(p,bombs)
        prepare(p);p.heli_velocity=V()
        for name in ('cd','mcd','bcd','rcd','cdc','counter'):setattr(p,name,0.)
        p.p=f.airport-direction(f.heading)*11000;p.a=f.heading;p.bank=0.;p.speed=0.;p.altitude=0.;p.throttle=.35;p.takeoff_distance=0.;p.phase='runway'
        if p.stats.get('helicopter'):p.p=V(f.airport);p.pods=True
        f.lock=None;f.radar.stt=None;f.sync();f.g.say('维修补给完成，已移至起飞位置 · '+f.g.controls.label('air.throttle_up')+' 增加油门')
    def label(self):
        p=self.f.plane
        base={'runway':'跑道滑跑','airborne':'鼠标引导航向','approach':'自动进场','landing':'自动降落','service':f'维修补给 {self.timer:.0f}s'}.get(p.phase,p.phase)
        return base
