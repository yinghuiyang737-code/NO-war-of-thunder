"""AI perception, remembered sightings and competing attention tasks."""
import math,random
from pygame.math import Vector2 as V
from GroundEquipment import EQUIPMENT
from AISkill import assign,reaction,dispersion
from AITactics import combat_move,safe_goal,team_units,defensive_smoke,face_threat
LABELS={'drive':'驾驶','search':'搜索','aim':'瞄准','repair':'维修','fire':'灭火','escape':'脱离威胁','air':'对空瞄准'}
def angle(v):return math.degrees(math.atan2(v.y,v.x))
def difference(a,b):return (a-b+180)%360-180

def can_see(g,t,target):
    if (target.get('dead',False) if isinstance(target,dict) else target.dead):return False
    p=target['p'] if isinstance(target,dict) else target.p
    delta=V(p)-t.p;distance=delta.length()
    radar=isinstance(target,dict) and t.stats.get('radar',False)
    if radar:
        from RadarContacts import ground_fit
        limit=ground_fit(t)[0]*8000*getattr(t,'radar_scale',1.)
        plane=target.get('ai_plane') or (target['controlled'].plane if target.get('controlled') else None)
        if not target.get('missile') and plane and plane.phase not in ('airborne','approach','landing'):return False
    else:limit=1100
    if distance>limit:return False
    # Crew peripheral awareness remains optical and occlusion-limited.
    if not radar and distance>380 and abs(difference(angle(delta),t.aim))>60:return False
    if isinstance(target,dict):return radar or not g.smoke_blocks(t.p,p)
    return g.visible(t.p,p,t.stats.get('thermal',False))

def select_focus(t,focus,dt):
    if focus!=t.ai_focus:
        t.ai_focus=focus;t.ai_focus_time=0.;t.ai_attention=max(0,t.ai_attention-.55)
    else:t.ai_focus_time+=dt
    t.ai_attention=min(1,t.ai_attention+dt*.55)

def update(g,t,dt):
    skill=assign(t)
    t.ai_recent_hit=max(0,t.ai_recent_hit-dt);t.mg_cd=max(0,t.mg_cd-dt)
    opponents=[o for o in (g.enemies if not t.enemy else g.allies+([g.player] if not g.player.dead else [])) if not o.dead and not getattr(o,'airborne',False)]
    aircraft=[p for p in g.air.targets(t) if isinstance(p,dict) and not p['dead'] and p.get('team',1)!=(1 if t.enemy else 0)] if t.stats.get('branch')==3 else []
    t.ai_scan_timer-=dt
    # Existing tracked contacts may be checked each frame; new contacts require a deliberate scan.
    t.ai_candidates=[o for o in t.ai_candidates if o in opponents and can_see(g,t,o)]
    t.ai_air_candidates=[o for o in t.ai_air_candidates if o in aircraft and can_see(g,t,o)]
    for o in opponents+aircraft:
        if not can_see(g,t,o):t.ai_observation.pop(id(o),None)
    if t.ai_scan_timer<=0:
        for o in opponents+aircraft:
            key=id(o)
            if not can_see(g,t,o):
                t.ai_observation.pop(key,None);continue
            first=t.ai_observation.setdefault(key,g.time)
            # Sustained observation confirms a contact. Strong focus slows discovery of new events.
            delay=(.65-.45*skill)*(0.8 if t.ai_focus=='search' else 1+t.ai_attention*.5)
            if isinstance(o,dict) and o.get('missile'):delay*=.18
            if g.time-first>=delay:
                if isinstance(o,dict):
                    if o not in t.ai_air_candidates:t.ai_air_candidates.append(o)
                elif o not in t.ai_candidates:t.ai_candidates.append(o)
        interval={'drive':.32,'search':.2,'aim':.65,'air':.65,'repair':1.0,'fire':1.2,'escape':.8}[t.ai_focus]
        t.ai_scan_timer=interval*(1+t.ai_attention*.6)*(1.5-.8*skill)
    target=t.ai_target if t.ai_target in t.ai_candidates else min(t.ai_candidates,key=lambda o:o.p.distance_squared_to(t.p),default=None)
    from AIRedeployResponse import order_for,matches
    response=order_for(g,t)
    revenge=next((o for o in t.ai_candidates if response and getattr(o,'battle_id',None)==response['attacker']),None)
    if revenge is not None:target=revenge;response['p']=V(revenge.p)
    attacker=getattr(t,'retaliation_attacker',None)
    retaliating=g.time<getattr(t,'retaliation_until',0) and attacker in opponents and can_see(g,t,attacker)
    if retaliating:
        target=attacker
        if attacker not in t.ai_candidates:t.ai_candidates.append(attacker)
    # A tracked far target must not suppress a newly observed tank beside the hull.
    nearby=min(t.ai_candidates,key=lambda o:o.p.distance_squared_to(t.p),default=None)
    if not retaliating and nearby is not None and nearby.p.distance_to(t.p)<400 and (target is None or target.p.distance_to(t.p)>nearby.p.distance_to(t.p)+180):target=nearby
    if getattr(t,'ai_skill_target',None) is not target:
        t.ai_skill_target=target;t.ai_reaction_until=g.time+reaction(skill)*(.65 if retaliating else 1.)
        t.ai_aim_bias=random.gauss(0,dispersion(skill)*.65);t.ai_bias_until=g.time+2.5
    if g.time>=getattr(t,'ai_bias_until',0):
        t.ai_aim_bias=random.gauss(0,dispersion(skill)*.65);t.ai_bias_until=g.time+2.5
    t.ai_target=target
    air_target=min(t.ai_air_candidates,key=lambda o:(not o.get('missile',False),o['p'].distance_squared_to(t.p)),default=None)
    revenge_air=next((o for o in t.ai_air_candidates if matches(g,o,response)),None)
    if revenge_air is not None:air_target=revenge_air;response['p']=V(revenge_air['p'])
    t.ai_air_target=air_target
    # Memory stores only the position observed at that instant, never a hidden unit's live position.
    for o in t.ai_candidates:t.ai_memory[id(o)]=(V(o.p),g.time)
    t.ai_memory={key:record for key,record in t.ai_memory.items() if g.time-record[1]<8}
    immobilized=not all(t.modules[k]>0 for k in ('engine','transmission','driver')) or not any(t.modules[k]>0 for k in ('left_track','right_track'))
    gun_disabled=not t.can_fire()
    needs_repair=any(t.modules[k]<2 for k in ('engine','transmission','left_track','right_track','ring','barrel','breech'))
    if t.fire>0:focus='fire'
    elif immobilized:focus='repair'
    elif t.ai_recent_hit>0 and (gun_disabled or not target):focus='escape'
    elif air_target and t.stats.get('branch')==3 and not (retaliating and target and target.p.distance_to(t.p)<230) and not gun_disabled:focus='air'
    elif retaliating and not gun_disabled:focus='aim'
    elif air_target and (target is None or target.p.distance_to(t.p)>650):focus='air'
    elif target:focus='escape' if gun_disabled else 'aim'
    elif needs_repair and (gun_disabled or not t.ai_memory):focus='repair'
    elif t.ai_memory:focus='search'
    else:focus='drive'
    select_focus(t,focus,dt)
    repairing=focus=='repair'
    t.service(dt,repairing)
    if focus=='fire' and t.extinguishers:t.extinguish()
    if t.dead:g.register_death(t);return
    if focus in ('fire','repair'):
        t.drive(0,0,dt,g.terrain,g.vehicles())
        # Repair consumes most attention, leaving only a slow optical sweep.
        t.aim_at(t.p+V(math.cos(math.radians(t.body)),math.sin(math.radians(t.body)))*500,dt*.12,g.terrain,g.vehicles())
        return
    if getattr(g,'objective',None):g.objective.ai_goal(t)
    world_w,world_h=g.world_size
    if focus=='air':
        speed=(t.ammo.get('velocity') or 950)*.75 if t.ammo else 850
        point=air_target['p']+air_target['v']*min(1.,air_target['p'].distance_to(t.p)/speed)
        dest=V(t.p);shot_target=point
    elif target:
        dest=V(target.p)
        # The AI knows an aim point on the visible silhouette, not the internal module inventory.
        offset=V(0,(-.3 if int(g.time//5)%2 else .3)*target.half_width).rotate(target.body)
        velocity=V(math.cos(math.radians(target.body)),math.sin(math.radians(target.body)))*target.speed
        muzzle_velocity=(t.ammo.get('velocity') or 950)*.75 if t.ammo else 850
        lead=velocity*min(1.5,dest.distance_to(t.p)/muzzle_velocity)*(.25+.65*skill)
        shot_target=t.p+(dest+offset+lead-t.p).rotate(t.ai_aim_bias)
    elif response:
        dest=V(response['p']);shot_target=None
        t.ai_maneuver='搜索击杀者最后出现区域'
        t.aim_at(dest,dt*.6,g.terrain,g.vehicles())
    elif t.ai_memory:
        dest=V(max(t.ai_memory.values(),key=lambda r:r[1])[0]);shot_target=None
        if dest.distance_to(t.p)<100:
            # Inspect the last seen location rather than following an unseen moving target.
            t.ai_memory.clear();t.ai_patrol_phase=(t.ai_patrol_phase+1)%3
    else:
        if getattr(g,'objective',None):dest=g.objective.ai_goal(t)
        else:dest=V(world_w*.5+t.ai_lane,world_h*.5-t.ai_lane)
        shot_target=None
    if focus=='escape':
        radians=math.radians(t.ai_threat_heading+180)
        dest=t.p+V(math.cos(radians),math.sin(radians))*400;shot_target=None
        defensive_smoke(g,t)
    t.nav_timer-=dt
    if focus=='aim':
        dest,throttle=combat_move(g,t,target,needs_repair or gun_disabled)
        if throttle<0:
            # Reverse along the escape direction while retaining the armour toward the threat.
            heading=angle(t.p-dest)
        else:heading=angle(dest-t.p) if throttle else t.body
    elif focus=='air':heading=t.body;throttle=0
    else:
        dest=safe_goal(g,t,dest)
        if getattr(t,'ai_nav_goal',dest).distance_to(dest)>160:t.nav_timer=0.;t.route=[]
        t.ai_nav_goal=V(dest)
        if t.nav_timer<=0 and dest.distance_to(t.p)>=55:
            t.route=g.find_route(t.p,dest,amphibious=EQUIPMENT.get(t.vehicle_id,{}).get("amphibious",False));t.nav_timer=2.5+random.random()
        while t.route and t.route[0].distance_to(t.p)<45:t.route.pop(0)
        waypoint=t.route[0] if t.route else dest
        heading=angle(waypoint-t.p);throttle=0 if dest.distance_to(t.p)<70 else .5 if focus=='search' else .72
        if not t.route and dest.distance_to(t.p)>=70:
            # An unreachable waypoint is not an instruction to drive through obstacles.
            check=t.p+(dest-t.p).normalize()*90
            if not t.clear_at(check,heading,g.terrain,(),trees=False):throttle=0
        t.ai_maneuver=getattr(t,'ai_role','搜索') if focus=='drive' else '低速搜索'
    heading,throttle=face_threat(g,t,target,focus,heading,throttle)
    turn=difference(heading,t.body)
    if abs(turn)>65:throttle=0
    # Avoid pushing teammates in the same narrow approach lane.
    travel=V(math.cos(math.radians(t.body)),math.sin(math.radians(t.body)))*(1 if throttle>=0 else -1)
    crowded=bool(throttle) and any(u is not t and (u.p-t.p).length()<t.radius+u.radius+55 and (u.p-t.p).dot(travel)>0 and abs((u.p-t.p).cross(travel))<t.radius+u.radius for u in team_units(g,t))
    t.ai_yield_time=getattr(t,'ai_yield_time',0.)+dt if crowded else 0.
    if crowded:
        throttle=0.;t.ai_maneuver='让行'
        if t.ai_yield_time>1. and not (getattr(t,'ai_detour_point',None) is not None and g.time<getattr(t,'ai_detour_until',0)):
            for degrees in ((70,-70,110,-110) if t.ai_lane>=0 else (-70,70,-110,110)):
                detour=t.p+travel.rotate(degrees)*(t.radius*2+100)
                bearing=angle(detour-t.p)
                if t.clear_at(detour,bearing,g.terrain,g.vehicles(),trees=False):
                    t.ai_detour_point=detour;t.ai_detour_until=g.time+2.5;break
    detour=getattr(t,'ai_detour_point',None)
    if detour is not None and g.time<getattr(t,'ai_detour_until',0) and detour.distance_to(t.p)>35:
        turn=difference(angle(detour-t.p),t.body);throttle=.3 if abs(turn)<65 else 0.;t.ai_maneuver='绕行'
    elif detour is not None:
        t.ai_detour_point=None;t.nav_timer=0.
    if t.stuck>.45 and t.backing<=0:t.backing=.9;t.stuck=0;t.nav_timer=0
    if t.backing>0:
        t.backing-=dt
        if focus not in ('aim','air'):throttle=-.55;turn=45 if int(t.p.x+t.p.y)%2 else -45
    steer=max(-1,min(1,turn/22))
    if t.speed<-2 or (abs(t.speed)<=2 and throttle<0):steer=-steer
    if focus=='aim' and target and target.p.distance_to(t.p)<540 and throttle>0:
        throttle=0.;t.ai_maneuver='近敌停车交战'
    if throttle and not EQUIPMENT.get(t.vehicle_id,{}).get('amphibious',False):
        probe=t.p+travel*max(80,abs(t.speed)*.6)
        if any(k=='deep_water' and r.inflate(t.radius*2,t.radius*2).collidepoint(probe) for r,k in g.terrain.nearby_obstacles(__import__('pygame').Rect(probe.x-150,probe.y-150,300,300))):
            throttle=0.;t.nav_timer=0.;t.ai_maneuver='避开深水'
    if focus in ('drive','search') and any(o.p.distance_to(t.p)<380 and can_see(g,t,o) for o in opponents):
        throttle=0.;t.ai_maneuver='观察近敌'
    previous_position=V(t.p);previous_body=t.body
    t.drive(throttle,steer,dt,g.terrain,g.vehicles())
    # Blocked pivot turns previously never counted as stuck because translation was zero.
    if focus not in ('aim','air') and abs(steer)>.25 and abs(difference(t.body,previous_body))<.05 and t.p.distance_to(previous_position)<.2:
        t.ai_pivot_stall=getattr(t,'ai_pivot_stall',0.)+dt
        if t.ai_pivot_stall>1.5:t.stuck=max(t.stuck,.5);t.ai_pivot_stall=0.
    else:t.ai_pivot_stall=0.
    if shot_target is not None:
        aim_factor=(.55+.45*skill) if focus in ('aim','air') else .25
        t.aim_at(shot_target,dt*aim_factor,g.terrain,g.vehicles())
    else:
        # Deliberate search sweeps replace omniscient steering toward opponents.
        bearing=(getattr(t,'ai_alert_heading',t.body)+math.sin(g.time*1.2)*25) if g.time<getattr(t,'ai_alert_until',0) and focus in ('drive','search','escape') else t.body+math.sin(g.time*(.85 if focus=='search' else .55)+t.ai_lane*.01)*75
        radians=math.radians(bearing)
        t.aim_at(t.p+V(math.cos(radians),math.sin(radians))*600,dt*(.65 if focus=='search' else .35),g.terrain,g.vehicles())
    if focus=='air' and g.time>=getattr(t,'ai_reaction_until',0) and t.ai_focus_time>=reaction(skill) and can_see(g,t,air_target):
        if t.stats.get('missile'):g.air.launch(t,air_target)
        if t.stats.get('weapon')!='sam' and abs(difference(angle(shot_target-t.p),t.aim))<5:g.shoot(t)
    elif focus=='aim' and target and g.time>=t.ai_reaction_until and can_see(g,t,target) and abs(difference(angle(shot_target-t.p),t.aim))<3:
        friends=([g.player]+g.allies) if not t.enemy else g.enemies
        blocked=any(o is not t and not o.dead and o.shell_contact(t.muzzle(),shot_target) for o in friends)
        if not blocked:
            g.shoot(t)
            if t.stats.get('independent_missiles') and t.stats.get('missile_ground'):g.air.launch(t,target)
            g.machine_gun(t)
            if t.p.distance_to(target.p)<450 and abs(difference(angle(target.p-t.p),t.body))<20:g.grenade_launcher(t)
