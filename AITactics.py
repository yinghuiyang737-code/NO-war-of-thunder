"""Small capture parties, distributed support and cautious advance using observed threats."""
import math,random
from pygame.math import Vector2 as V
from GroundEquipment import EQUIPMENT

def team_units(g,t):
    return [u for u in (g.enemies if t.enemy else g.allies) if not u.dead and not getattr(u,'airborne',False) and getattr(u,'network_owner',None) is None]

def objective_goal(obj,t):
    g=obj.g;team=int(t.enemy);units=team_units(g,t)
    if hasattr(g.objective,'assign'):units=[u for u in g.objective.assign(team) if u.ai_objective is obj]
    # Keep assignments stable between deaths; choose nearby non-AA tanks as the capture party.
    signature=tuple(id(u) for u in units)
    if not hasattr(obj,'tactical_rosters'):obj.tactical_rosters={}
    cached=obj.tactical_rosters.get(team)
    if cached is None or cached[0]!=signature:
        fighters=sorted(units,key=lambda u:(u.stats.get('branch') in (3,5),u.p.distance_squared_to(obj.p)))
        survivors=[u for u in cached[1] if u in units] if cached else []
        guards=survivors+[u for u in fighters if u not in survivors][:max(0,2-len(survivors))]
        others=[u for u in units if u not in guards]
        cached=(signature,guards,others);obj.tactical_rosters[team]=cached
    _,guards,others=cached
    forward=V(-1 if team else 1,0);side=V(0,1)
    if t in guards:
        index=guards.index(t);t.ai_role='驻守' if obj.owner==team else '占点'
        return obj.p-forward*90+side*(-145 if index==0 else 145)
    index=others.index(t) if t in others else 0
    flank=-1 if index%2==0 else 1;rank=index//2
    if t.stats.get('artillery'):
        t.ai_role='后方火炮';return obj.p-forward*(1150+rank%3*180)+side*flank*(650+rank%2*200)
    if t.stats.get('branch')==3:
        t.ai_role='后方防空';return obj.p-forward*(650+rank%3*140)+side*flank*(400+rank%2*160)
    if obj.owner!=team:
        t.ai_role='外围掩护';return obj.p-forward*(380+rank%3*160)+side*flank*(440+rank%3*150)
    age=max(0,g.time-getattr(obj,'owner_since',g.time))
    delay=(rank%3)*4.;stage=max(0,int((age-delay)/10)) if age>=delay else -1
    distance=450 if stage<0 else min(2900,850+stage*400)
    t.ai_role='等待掩护' if stage<0 else '分批推进'
    # Per-vehicle staging is completed once. Rechecking position trapped units at the flank.
    token=(team,id(obj),obj.owner_since)
    if getattr(t,'ai_advance_token',None)!=token:
        t.ai_advance_token=token;t.ai_flank_ready=False
    flank_point=obj.p-forward*350+side*flank*(600+rank%3*190)
    if not t.ai_flank_ready:
        relative=t.p-obj.p
        if t.p.distance_to(flank_point)<260 or abs(relative.y)>350 or relative.dot(forward)>250:
            t.ai_flank_ready=True
        else:return flank_point
    return obj.p+forward*distance+side*flank*(650+rank%3*260)

def defensive_smoke(g,t):
    # One decision per incident, generous team spacing, and no smoke for routine retreat.
    if not t.smoke_charges or t.smoke_cd>0 or t.ai_recent_hit<=0:return False
    now=g.time
    if now<getattr(t,'ai_smoke_decision_after',0):return False
    t.ai_smoke_decision_after=now+24.
    if now-getattr(t,'ai_smoke_used_at',-100)<50:return False
    if any(c['kind']=='grenade' and c['age']<22 and c['p'].distance_to(t.p)<450 for c in g.smokes):return False
    if random.random()>.28:return False
    if g.deploy_smoke(t):t.ai_smoke_used_at=now;return True
    return False

def combat_move(g,t,target,damaged):
    delta=target.p-t.p;distance=delta.length();away=-delta.normalize() if distance>1 else V(-1,0)
    visible=t.ai_candidates
    hostile=sum(o.p.distance_to(t.p)<750 for o in visible)
    friendly=1+sum(u is not t and not u.dead and u.p.distance_to(t.p)<850 for u in team_units(g,t))
    support=t.stats.get('branch') in (2,3,5) or t.stats.get('weapon')=='sam'
    desired=1050 if t.stats.get('artillery') else 700 if support else 540
    retreat=(hostile>friendly and distance<700) or (damaged and t.ai_recent_hit>0) or distance<(380 if support else 240)
    if retreat:
        t.ai_maneuver='后撤交战'
        if damaged or hostile>friendly:defensive_smoke(g,t)
        return t.p+away*280,-.55
    if distance<=desired or (getattr(t,'ai_role','')=='驻守' and t.p.distance_to(getattr(t,'ai_objective',g.objective).p)<getattr(t,'ai_objective',g.objective).radius-40):
        t.ai_maneuver='停车交战';return V(t.p),0.
    # Advance toward a standoff position, rather than straight into the target's hull.
    t.ai_maneuver='谨慎接敌'
    return target.p+away*desired,.38

def safe_goal(g,t,goal):
    # Select a nearby traversable position when a formation point lies inside scenery.
    amphibious=EQUIPMENT.get(t.vehicle_id,{}).get('amphibious',False)
    def clear(p):
        return t.clear_at(p,t.body,g.terrain,(),trees=False) and (amphibious or not any(k=='deep_water' and r.collidepoint(p) for r,k in g.terrain.nearby_obstacles(__import__('pygame').Rect(p.x-50,p.y-50,100,100))))
    if clear(goal):return goal
    for radius in (100,180,280):
        for degrees in (0,90,180,270,45,135,225,315):
            point=goal+V(radius,0).rotate(degrees)
            if clear(point):return point
    return V(t.p)


def face_threat(g,t,target,focus,heading,throttle):
    """Armour facing uses observed enemies or the stored incoming-fire bearing."""
    if focus not in ('aim','escape'):return heading,throttle
    front=t.stats.get('effective_front') or t.stats.get('armor',(0,0,0))
    front=front[0] if isinstance(front,(tuple,list)) else front
    side=t.stats.get('armor',(0,0,0))[1]
    if front<=side*1.1:return heading,throttle
    if target is not None:
        delta=target.p-t.p
        if delta.length_squared()<1:return heading,throttle
        if focus=='aim' and throttle>0 and delta.length()>650:return heading,throttle
        desired=math.degrees(math.atan2(delta.y,delta.x))
    elif focus=='escape' and t.ai_recent_hit>0:desired=t.ai_threat_heading
    else:return heading,throttle
    if focus=='escape':
        backward=V(-100,0).rotate(desired)
        throttle=-.45 if t.clear_at(t.p+backward,desired,g.terrain,g.vehicles(),trees=False) else 0.
    elif throttle>0 and abs((desired-t.body+180)%360-180)>25:throttle=0.
    t.ai_maneuver='正面对敌 · 倒车后撤' if throttle<0 else '正面对敌'
    return desired,throttle
