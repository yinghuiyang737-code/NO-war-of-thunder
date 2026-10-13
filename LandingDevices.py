"""Automatic, equipment-specific approach and runway braking."""
import math
import pygame
from pygame.math import Vector2 as V
from AircraftPhysics import direction
from AircraftLandingEquipment import EQUIPMENT
WIRE_POSITIONS=tuple(range(-8800,8801,600))

def landing_speed(p,battle_br):
    """Gameplay approach targets, with higher rollout capacity for fitted brakes."""
    if p.stats['max_speed']>850:
        kmh=1200 if p.landing_equipment['hook'] and battle_br>=8 else 800 if p.landing_equipment['chute'] else 600
    else:kmh=165 if p.stats['span']>=25 else 145
    return min(p.stats['speed']*.8,kmh/3.6*8)
def prepare(p):
    p.landing_equipment=EQUIPMENT[p.ident]
    p.airbrake=0.;p.chute_deployed=False;p.chute_used=False;p.hook_deployed=False;p.cable_engaged=False;p.cable_anchor=None

def airborne(p,dt,target_speed):
    wanted=bool(p.landing_equipment['airbrake'] and p.phase in ('approach','landing') and p.speed>target_speed+8)
    p.airbrake=max(0,min(1,p.airbrake+(2*dt if wanted else -2*dt)))

def rollout(f,p,dt):
    heading=getattr(getattr(f,'service',None),'heading',f.heading)
    equipment=p.landing_equipment;axis=direction(heading);old=(p.p-f.airport).dot(axis);lateral=abs((p.p-f.airport).dot(axis.rotate(90)))
    p.hook_deployed=bool(equipment['hook'] and f.g.battle_br>=8)
    if equipment['chute'] and not p.chute_used and p.speed>80:
        p.chute_deployed=p.chute_used=True
    p.airbrake=min(1,p.airbrake+dt*2) if equipment['airbrake'] else 0.
    braking=60+20*p.airbrake
    if p.chute_deployed:braking+=min(100,40*(p.speed/600)**2)
    if p.hook_deployed and not p.cable_engaged and not p.chute_deployed and any(old<x<old+1000 for x in WIRE_POSITIONS):braking=90+70*p.airbrake
    if p.cable_engaged:braking=max(braking,700,p.speed**2/(2*max(500,11000-old)))
    speed=max(0,p.speed-braking*dt);new=old+(p.speed+speed)*.5*dt
    if p.hook_deployed and not p.cable_engaged and lateral<155:
        wires=[x for x in WIRE_POSITIONS if old<=x<=new]
        if wires:
            p.cable_engaged=True;p.cable_anchor=f.airport+axis*min(wires)
            # Apply cable drag only to the part of this step after crossing it.
            fraction=max(0,min(1,(new-min(wires))/max(.001,new-old)))
            speed=max(0,speed-500*dt*fraction)
            new=max(min(wires),old+(p.speed+speed)*.5*dt)
    p.speed=speed;p.p+=axis*(new-old);p.a=heading;p.bank=0;p.throttle=0.
    if p.speed<60:p.chute_deployed=False

def status(p):
    states=[]
    if p.airbrake>.1:states.append('减速板展开')
    if p.chute_deployed:states.append('减速伞展开')
    if p.cable_engaged:states.append('阻拦索制动')
    elif p.hook_deployed:states.append('阻拦钩放下')
    return ' / '.join(states)

def draw_runway(f,s,at,factor):
    if f.g.battle_br<8:return
    axis=direction(f.heading);side=axis.rotate(90)
    for x in WIRE_POSITIONS:
        anchor=f.airport+axis*x
        pygame.draw.line(s,(199,162,91),at(anchor-side*170),at(anchor+side*170),max(1,int(factor*3)))

def draw_plane(p,s,at,factor,airport_heading):
    q=at(p.p);axis=direction(p.a);side=axis.rotate(90);tail=q-axis*p.stats['length']*4*factor
    if p.airbrake>.1:
        for sign in (-1,1):
            center=q-axis*p.stats['length']*1.2*factor+side*sign*p.stats['span']*1.3*factor
            pygame.draw.polygon(s,(221,147,88),[center-axis*10*factor,center+side*sign*16*factor*p.airbrake,center+axis*8*factor],max(1,int(factor)))
    if p.hook_deployed:
        tip=tail-axis*36*factor
        pygame.draw.line(s,(221,201,135),tail,tip,max(1,int(3*factor)));pygame.draw.line(s,(221,201,135),tip,tip+side*8*factor,max(1,int(2*factor)))
    if p.chute_deployed:
        canopy=tail-axis*130*factor;r=max(4,35*factor)
        for sign in (-1,0,1):pygame.draw.line(s,(203,199,166),tail,canopy+side*sign*r,max(1,int(factor)))
        vertices=[canopy+side*math.cos(a)*r-axis*math.sin(a)*r*.7 for a in [i*math.pi/12 for i in range(13)]]
        pygame.draw.polygon(s,(213,157,86),vertices);pygame.draw.lines(s,(247,219,161),False,vertices,1)
        for a in (.3,.8,1.3,1.8,2.3,2.8):pygame.draw.line(s,(239,205,146),canopy,canopy+side*math.cos(a)*r-axis*math.sin(a)*r*.7,1)
    if p.cable_engaged and p.cable_anchor is not None:
        wire_side=direction(airport_heading).rotate(90)
        pygame.draw.lines(s,(249,210,112),False,[at(p.cable_anchor-wire_side*170),tail,at(p.cable_anchor+wire_side*170)],max(1,int(2*factor)))


def self_test(api):
    from Aviation import AIRCRAFT
    from AircraftPhysics import Plane
    from FlightDynamics import step
    from types import SimpleNamespace
    import copy
    assert set(EQUIPMENT)==set(AIRCRAFT)
    for key in AIRCRAFT:
        p=Plane(key,0,V());assert p.landing_equipment is EQUIPMENT[key]
        p.phase='approach';p.speed=900;airborne(p,.5,300)
        assert bool(p.airbrake)==p.landing_equipment['airbrake']
    hook_id=next(k for k,d in AIRCRAFT.items() if d['name']=='F-16CM')
    chute_id=next(k for k,d in AIRCRAFT.items() if d['name']=='J-7E')
    assert EQUIPMENT[hook_id]['hook'] and not EQUIPMENT[hook_id]['chute']
    assert EQUIPMENT[chute_id]['chute'] and not EQUIPMENT[chute_id]['hook']
    def plane(key):
        p=Plane(key,0,V(-8900,0));p.phase='landing';p.altitude=0;p.speed=420;p.a=0;p.throttle=0;return p
    f=SimpleNamespace(heading=0,airport=V(),g=SimpleNamespace(battle_br=11.))
    hooked=plane(hook_id);baseline=plane(hook_id);baseline.landing_equipment=dict(baseline.landing_equipment,hook=False,airbrake=False)
    positions={};cable=False
    for i in range(400):
        for p in (hooked,baseline):
            if p.speed>0:rollout(f,p,.02)
        cable=cable or hooked.cable_engaged
        if hooked.speed==0 and baseline.speed==0:break
    assert cable and hooked.p.x+8900<(baseline.p.x+8900)*.65
    low=plane(hook_id);f.g.battle_br=7.7
    for _ in range(20):rollout(f,low,.02)
    assert not low.hook_deployed and not low.cable_engaged
    f.g.battle_br=11.;chute=plane(chute_id);plain=plane(chute_id);plain.landing_equipment=dict(plain.landing_equipment,chute=False,airbrake=False)
    for _ in range(400):
        for p in (chute,plain):
            if p.speed>0:rollout(f,p,.02)
        if chute.speed==plain.speed==0:break
    assert chute.chute_used and chute.p.x+8900<(plain.p.x+8900)*.85
    prepare(chute);assert not chute.chute_used and not chute.airbrake
    fast=plane(hook_id);fast.phase='approach';fast.altitude=120;fast.speed=1800;fast.airbrake=1
    idle=copy.deepcopy(fast);idle.airbrake=0
    step(fast,.5,0,0);step(idle,.5,0,0);assert fast.speed<idle.speed-15 and fast.speed>=1760
    # Full-speed straight approach reaches service without an unnecessary turn back to entry.
    Game=api['Game'];g=Game(False,'us',[hook_id]+[None]*7);flight=g.flight;p=flight.plane;axis=direction(flight.heading)
    p.phase='airborne';p.p=flight.airport-axis*15000;p.a=flight.heading;p.altitude=180;p.speed=min(3000,p.stats['speed']);p.throttle=1
    assert flight.service.request();reversed_heading=False;used_board=False
    for _ in range(12000):
        flight.update_controls(1/60);used_board=used_board or p.airbrake>.1
        error=(p.a-flight.heading+180)%360-180;reversed_heading=reversed_heading or abs(error)>90
        if p.phase=='service':break
    assert p.phase=='service' and not reversed_heading
    assert p.cable_engaged and abs((p.p-flight.airport).dot(axis))<12000
    flight.service.update(8.1);assert p.phase=='runway' and not p.cable_engaged and not p.hook_deployed and p.airbrake==0
    # Offset and opposite-end arrivals directly intercept the runway without
    # visiting the old distant entry waypoint or completing a holding circle.
    for along,side,reverse in ((-5000,2000,False),(5000,-2000,True),(-30000,2000,False),(-15000,5000,False),(15000,-5000,True)):
        g=Game(False,'us',[hook_id]+[None]*7);flight=g.flight;p=flight.plane;axis=direction(flight.heading)
        p.phase='airborne';p.p=flight.airport+axis*along+axis.rotate(90)*side
        p.a=flight.heading+(180 if reverse else 0);p.altitude=180;p.speed=min(3000,p.stats['speed']);p.throttle=1
        assert flight.service.request();turn_total=0.;before=p.a
        for _ in range(12000):
            flight.update_controls(1/60)
            turn_total+=abs((p.a-before+180)%360-180);before=p.a
            assert flight.service.stage=='align'
            if p.phase=='service':break
        assert p.phase=='service' and p.cable_engaged and turn_total<180,(along,side,p.phase,turn_total)
        assert abs((p.p-flight.airport).dot(direction(flight.service.heading)))<12000
    g=Game(False,'cn',[chute_id]+[None]*7);flight=g.flight;p=flight.plane;axis=direction(flight.heading)
    p.phase='airborne';p.p=flight.airport-axis*15000;p.a=flight.heading;p.altitude=180;p.speed=min(2000,p.stats['speed']);p.throttle=1
    assert flight.service.request();touchdown=None;touchdown_speed=0.
    for _ in range(12000):
        flight.update_controls(1/60)
        if p.altitude>0:assert not p.chute_used
        if p.phase=='landing' and p.altitude==0 and touchdown is None:touchdown=V(p.p);touchdown_speed=p.speed
        if p.phase=='service':break
    assert p.phase=='service' and p.chute_used and touchdown is not None
    assert touchdown_speed>1600 and 1000<p.p.distance_to(touchdown)<18000
    assert abs((p.p-flight.airport).dot(axis))<12000
    print('PASS: all 116 landing equipment fits, equipment-only airbraking, shorter chute/cable rollout, modern BR cable gate, direct high-speed approach, finite service and reset.')
