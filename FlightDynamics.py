"""One flight performance model shared by player and AI control inputs."""
from AircraftPhysics import direction,difference
from pygame.math import Vector2 as V

def step(p,dt,desired,runway_heading,manual=0,translation=None):
    for key in ('cd','mcd','bcd','rcd','cdc','counter'):setattr(p,key,max(0,getattr(p,key)-dt))
    p.fuel=max(0,p.fuel-dt*(.35+.9*p.throttle))
    if p.fuel<=0:p.modules['engine']=0
    if p.stats.get('helicopter'):
        if p.phase=='runway':
            p.speed=0.;p.altitude=max(0,p.altitude+dt*35*p.throttle);p.rotor_clock=getattr(p,'rotor_clock',0)+dt
            if p.altitude>=20:p.phase='airborne'
            return True
        error=difference(desired,p.a);p.a+=max(-70*dt,min(70*dt,error))
        engine=0 if p.modules['engine']==0 else .5 if p.modules['engine']==1 else 1
        hover=bool(getattr(p,'hover',False) and engine>0)
        if not engine:p.hover=False
        if translation is None:
            target=0 if hover else p.stats['speed']*p.throttle*engine;p.speed+=max(-220*dt,min(120*dt,target-p.speed))
            p.bank+=max(-90*dt,min(90*dt,max(-25,min(25,error*.4))-p.bank))
            p.p+=direction(p.a)*p.speed*dt
        else:
            velocity=V(getattr(p,'heli_velocity',V()))
            move=V(translation)
            if move.length_squared()>1:move.normalize_ip()
            if move.length_squared() and hover:
                p.hover=False;p.hover_anchor=None;hover=False
            target=move*p.stats['speed']*p.throttle*engine if not hover else V()
            change=target-velocity
            acceleration=120 if move.length_squared() and not hover else 220 if hover else 65
            if change.length()>acceleration*dt:change.scale_to_length(acceleration*dt)
            velocity+=change
            p.heli_velocity=velocity;p.speed=velocity.length();p.p+=velocity*dt
            side=velocity.dot(direction(p.a).rotate(90))
            bank=max(-25,min(25,side/max(1,p.stats['speed'])*25))
            p.bank+=max(-90*dt,min(90*dt,bank-p.bank))
        if hover and p.speed<3:
            if getattr(p,'hover_anchor',None) is None:p.hover_anchor=p.p.copy()
            p.p=p.hover_anchor.copy();p.speed=0;p.heli_velocity=V()
        p.altitude=getattr(p,'hover_altitude',p.altitude) if hover else max(0,min(100,p.altitude+(25 if engine else -45)*dt))
        return p.altitude>0
    if p.phase=='runway':
        p.bank=0.;p.sweep=max(0,getattr(p,'sweep',0)-dt*.5);p.a=runway_heading
        lift=(210 if p.stats['max_speed']>850 else 140 if p.stats['span']<25 else 180)/3.6*8
        p.speed=max(0,p.speed+(38*p.throttle-8*(1-p.throttle))*dt);p.speed=min(p.speed,lift*1.15)
        p.p+=direction(p.a)*p.speed*dt;p.takeoff_distance+=p.speed*dt
        if p.speed>=lift and p.takeoff_distance>=3200:p.phase='airborne'
        return True
    error=difference(desired,p.a)
    engine=.15 if p.modules['engine']==0 else .55 if p.modules['engine']==1 else 1
    braking=220+min(1800,650*getattr(p,'airbrake',0)*(p.speed/max(180,(155 if p.stats['max_speed']>850 else 95)/3.6*8))**2)
    if p.phase in ('approach','landing'):
        braking=min(braking,getattr(p,'approach_deceleration',80.)*(.35+.65*getattr(p,'airbrake',0)))
    p.speed+=max(-braking*dt,min(160*dt,p.stats['speed']*(max(0,p.throttle) if p.phase in ('approach','landing') else max(.12,p.throttle))*engine-p.speed))
    desired_sweep=max(0,min(1,(p.speed*3.6/8-500)/650)) if p.stats.get('model_family') in ('f14','f111','tornado','su17','su24') else 0.
    p.sweep+=max(-dt*.4,min(dt*.4,desired_sweep-p.sweep))
    turn=1.30*p.stats['turn']*(.55+.1125*(p.modules['left_wing']+p.modules['right_wing']))
    p.a+=max(-turn*dt,min(turn*dt,error))
    if manual:p.bank+=manual*220*dt
    else:p.bank+=max(-320*dt,min(320*dt,difference(max(-90,min(90,error*2.)),p.bank)))
    p.p+=direction(p.a)*p.speed*dt
    safe=(155 if p.stats['max_speed']>850 else 95)/3.6*8
    p.altitude=max(0,min(260,p.altitude+(65 if p.speed>=safe and engine>.15 else -90)*dt))
    return p.altitude>0 or (p.phase in ('approach','landing') and engine>.15)
