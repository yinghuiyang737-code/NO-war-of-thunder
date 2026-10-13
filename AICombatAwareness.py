"""Bounded optical projectile awareness and nearby teammate incident reports."""
import math
from pygame.math import Vector2 as V
from AISkill import assign,reaction
CELL=400

def world(g):return getattr(g,'_lan_world',None) or g
def pos(u):return V(u.get('p')) if isinstance(u,dict) else V(u.p)
def team(u):return u.get('team',int(u.get('enemy',False))) if isinstance(u,dict) else int(u.enemy)
def heading(v):return math.degrees(math.atan2(v.y,v.x))
def seen_point(g,t,p):
    d=V(p)-t.p
    return d.length_squared()<=1100**2 and (d.length_squared()<=380**2 or abs((heading(d)-t.aim+180)%360-180)<=60) and g.visible(t.p,p,False)
def emit(g,kind,point,owner=None,victim=None,velocity=None):
    g=world(g);events=getattr(g,'ai_incidents',[])
    g.ai_incident_serial=getattr(g,'ai_incident_serial',0)+1
    events.append(dict(id=('event',g.ai_incident_serial),kind=kind,p=V(point),owner=owner,victim=victim,v=V(velocity or (0,0)),time=g.time))
    g.ai_incidents=[e for e in events[-128:] if g.time-e['time']<3]
    g._ai_incident_cache=None

def index(g):
    g=world(g);cached=getattr(g,'_ai_incident_cache',None)
    if cached and cached[0]==g.time:return cached[1]
    items=[e for e in getattr(g,'ai_incidents',[]) if g.time-e['time']<3]
    g.ai_incidents=items[:]
    for b in g.bullets:
        if len(b)>5 and b[3]>0:items.append(dict(id=('shell',id(b)),kind='projectile',p=V(b[0]),v=V(b[1]),owner=b[5],victim=None,time=g.time))
    authority=getattr(g,'_lan_authority',None)
    contexts=list(authority.contexts.values()) if authority else [g]
    for ctx in contexts:
        for b in getattr(getattr(ctx,'flight',None),'projectiles',[]):
            if b.get('kind') in ('gun','rocket') and b.get('life',0)>0:items.append(dict(id=('airshot',id(b)),kind='projectile',p=V(b['p']),v=V(b['v']),owner=b.get('source') or b.get('owner'),victim=None,time=g.time))
    cells={}
    for e in items:
        # Index every cell crossed by the currently visible tracer segment.
        start=e.get('start',e['p']-e['v']*.05);end=e['p']
        steps=min(12,max(1,int(V(end-start).length()/CELL)+1));occupied=set()
        for n in range(steps+1):
            p=start+(end-start)*(n/steps);key=(int(p.x//CELL),int(p.y//CELL))
            if key not in occupied:cells.setdefault(key,[]).append(e);occupied.add(key)
    g._ai_incident_cache=(g.time,cells);return cells

def nearby(g,p,radius=1100):
    cells=index(g);x,y=int(p.x//CELL),int(p.y//CELL);n=math.ceil(radius/CELL);found={}
    for i in range(x-n,x+n+1):
        for j in range(y-n,y+n+1):
            for e in cells.get((i,j),[]):found[e['id']]=e
    return list(found.values())
def closest(a,b,p):
    d=b-a
    return a+d*max(0,min(1,(p-a).dot(d)/d.length_squared())) if d.length_squared()>0 else V(a)

def observe(g,t,dt):
    from AIController import can_see
    now=g.time;pending=getattr(t,'ai_incident_pending',None)
    if pending and now>=pending['ready']:
        t.ai_incident_pending=None;t.ai_alert_until=now+(5 if pending['kind']=='destroyed' else 3)
        t.ai_alert_kind=pending['kind'];t.ai_alert_point=V(pending['point']);t.ai_alert_heading=pending['heading']
        attacker=pending['owner']
        if attacker is not None and team(attacker)!=int(t.enemy) and can_see(g,t,attacker):
            t.retaliation_attacker=attacker;t.retaliation_until=now+5;t.ai_scan_timer=0.
        elif pending['danger']:
            t.ai_recent_hit=max(t.ai_recent_hit,2.);t.ai_threat_heading=pending['heading']
        else:t.ai_memory[-pending['serial']]=(V(pending['point']),now);t.ai_scan_timer=0.
        t.ai_maneuver={'projectile':'发现来袭弹道','tracer':'发现子弹曳光','hit':'掩护遇袭队友','destroyed':'队友阵亡 · 警戒'}[pending['kind']]
    t.ai_incident_scan=max(0,getattr(t,'ai_incident_scan',0)-dt)
    if t.ai_incident_scan>0 or pending:return
    skill=assign(t);attention=getattr(t,'ai_attention',0)
    t.ai_incident_scan=(.18+.35*(1-skill))*(1+attention*.8)
    known=getattr(t,'ai_incident_seen',[]);best=None
    for e in nearby(g,t.p):
        if e['id'] in known or e['owner'] is t:continue
        victim=e['victim'];point=e['p'];distance=point.distance_to(t.p)
        if e['kind'] in ('hit','destroyed'):
            if victim is t or victim is None or team(victim)!=int(t.enemy):continue
            heard=distance<(420 if e['kind']=='destroyed' else 280)
            if not heard and not seen_point(g,t,point):continue
            danger=e['kind']=='destroyed' and distance<350;direction=heading(point-t.p);priority=2 if danger else 1
        else:
            if e['owner'] is not None and team(e['owner'])==int(t.enemy):continue
            velocity=e['v'];start=e.get('start',point-velocity*.05);view=closest(start,point,t.p)
            if not seen_point(g,t,view):continue
            if velocity.length_squared()<1:continue
            duration=max(0,(t.p-point).dot(velocity)/velocity.length_squared())
            miss=(point+velocity*min(1.5,duration)).distance_to(t.p)
            danger=duration>0 and duration<1.5 and miss<t.radius+100
            point=V(view);direction=heading(-velocity);priority=3 if danger else .5
        known.append(e['id']);known=known[-64:]
        if best is None or priority>best[0]:best=(priority,e,point,danger,direction)
    t.ai_incident_seen=known
    if best:
        _,e,point,danger,direction=best
        t.ai_incident_pending=dict(ready=now+reaction(skill)*(1+attention*.6),kind=e['kind'],point=V(point),danger=danger,heading=direction,owner=e['owner'],serial=getattr(world(g),'ai_incident_serial',0)+len(known)+1)

def observe_air(g,q,dt):
    if q.get('dead') or q.get('ai_nuclear'):return
    p=q['ai_plane']
    if p.phase!='airborne':return
    pending=q.get('incident_pending');now=g.time
    if pending and now>=pending['ready']:
        q['incident_pending']=None;q['egress']=3.+(1-assign(q))*2;q['egress_heading']=p.a+pending['side']*45
        q['attention']=max(0,q.get('attention',0)-.5);q['incident_alert_until']=now+4;q['incident_label']=pending['label']
        attacker=pending['owner']
        if attacker is not None:
            point=pos(attacker);delta=point-p.p
            if delta.length()<16000 and abs((heading(delta)-p.a+180)%360-180)<60 and not g.smoke_blocks(p.p,point):q['retaliation_attacker']=attacker;q['retaliation_until']=now+5
    q['incident_scan']=max(0,q.get('incident_scan',0)-dt)
    if q['incident_scan'] or pending:return
    q['incident_scan']=(.25+.4*(1-assign(q)))*(1+q.get('attention',0))
    known=q.get('incident_seen',[])
    for e in nearby(g,p.p,2400):
        if e['id'] in known or e['owner'] is q:continue
        if e['kind'] in ('hit','destroyed'):
            if e['victim'] is q or e['victim'] is None or team(e['victim'])!=q['team']:continue
            point=e['p'];label='队友遇袭 · 脱离警戒'
        else:
            if e['owner'] is not None and team(e['owner'])==q['team']:continue
            v=e['v'];point=closest(e.get('start',e['p']-v*.05),e['p'],p.p)
            if not v.length_squared():continue
            travel=max(0,(p.p-e['p']).dot(v)/v.length_squared())
            if travel>2 or (e['p']+v*travel).distance_to(p.p)>180:continue
            label='发现来袭弹道 · 规避'
        d=point-p.p
        if d.length()>2400 or abs((heading(d)-p.a+180)%360-180)>75 or g.smoke_blocks(p.p,point):continue
        known.append(e['id']);q['incident_seen']=known[-64:]
        q['incident_pending']=dict(ready=now+reaction(assign(q))*(1+q.get('attention',0)*.6),side=-1 if d.cross(V(1,0).rotate(p.a))>0 else 1,owner=e['owner'],label=label);break

def install(Game,api):
    previous={k:getattr(Game,k) for k in ('ai_step','record_hit','record_air_hit','announce_kill','machine_gun')}
    def ai_step(g,t,dt):
        observe(g,t,dt);previous['ai_step'](g,t,dt)
        if g.time<getattr(t,'ai_alert_until',0) and t.ai_focus in ('drive','search'):
            t.ai_maneuver='弹道方向警戒' if t.ai_alert_kind in ('projectile','tracer') else '搜索队友遇袭方向'
    def hit(g,target,result,owner,weapon=''):
        if result and not result.get('continue') and target is not None:emit(g,'hit',pos(target),owner,target)
        previous['record_hit'](g,target,result,owner,weapon)
    def air_hit(g,target,point,owner,weapon=''):
        emit(g,'hit',pos(target),owner,target);previous['record_air_hit'](g,target,point,owner,weapon)
    def kill(g,attacker,victim,weapon=''):
        if victim is not None and not (victim.get('ai_incident_destroyed',False) if isinstance(victim,dict) else getattr(victim,'ai_incident_destroyed',False)):
            emit(g,'destroyed',pos(victim),attacker,victim)
            if isinstance(victim,dict):victim['ai_incident_destroyed']=True
            else:victim.ai_incident_destroyed=True
        previous['announce_kill'](g,attacker,victim,weapon)
    def mg(g,t=None):
        owner=t or g.player;before=len(g.mg_tracers);result=previous['machine_gun'](g,t)
        if result and len(g.mg_tracers)>before:
            start,end,_=g.mg_tracers[-1];emit(g,'tracer',end,owner,velocity=(end-start)/.08);world(g).ai_incidents[-1]['start']=V(start)
        return result
    for name,fn in (('ai_step',ai_step),('record_hit',hit),('record_air_hit',air_hit),('announce_kill',kill),('machine_gun',mg)):setattr(Game,name,fn)

    from AIFlight import AIFlights
    previous_flight_update=AIFlights.update
    def flight_update(manager,q,dt):
        observe_air(manager.g,q,dt);previous_flight_update(manager,q,dt)
        if manager.g.time<q.get('incident_alert_until',0):q['focus']=q['incident_label'];q['ai_plane'].focus=q['focus']
    AIFlights.update=flight_update
