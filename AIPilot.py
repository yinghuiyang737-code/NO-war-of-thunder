"""Human-scale perception, imperfect lead and bounded attack passes."""
import random
from AISkill import assign,reaction,dispersion
from pygame.math import Vector2 as V
from AircraftPhysics import direction,bearing,difference

def observe(q,target):
    now=q['age'];air=isinstance(target,dict);skill=assign(q)
    if q.get('observed_target') is not target:
        q['observed_target']=target;q['sighting']=None;q['pending_sighting']=None;q['next_sample']=0.
        q['reaction_until']=now+random.uniform(1.2,2.2)*(1.55-.85*skill)
        q['aim_bias']=random.uniform(-1,1)*dispersion(skill);q['lead_fraction']=random.uniform(.4+.4*skill,.65+.3*skill)
        q['ground_pass_until']=0.
    pending=q.get('pending_sighting')
    if pending and now>=pending['ready']:
        q['sighting']=pending;q['pending_sighting']=None
    if now>=q['next_sample'] and not q.get('pending_sighting'):
        pos=V(target['p'] if air else target.p)
        velocity=V(target['v']) if air else direction(target.body)*target.speed
        sample=dict(pos=pos,velocity=velocity*random.uniform(.55+.3*skill,1.2-.15*skill),stamp=now,ready=now+random.uniform(.25,.45)*(1.6-.9*skill))
        q['pending_sighting']=sample;q['next_sample']=now+random.uniform(.45,.7)*(1.5-.8*skill)
        if q['sighting'] is None:q['sighting']=dict(sample,velocity=V())
    sight=q['sighting'];p=q['ai_plane']
    # A stale observation is extrapolated approximately; no exact live intercept.
    travel=min(1.1,p.p.distance_to(sight['pos'])/(2400+p.speed))
    elapsed=min(.7,max(0,now-sight['stamp']))
    return sight['pos']+sight['velocity']*(elapsed+travel*q['lead_fraction'])

def aim_heading(q,target):
    point=observe(q,target);p=q['ai_plane']
    return bearing(point-p.p)+q['aim_bias']*(1.25-.5*q.get('attention',0))

def gun_ready(q):
    now=q['age'];p=q['ai_plane']
    if now<q.get('gun_rest_until',0) or abs(difference(p.bank,0))>40:return False
    if q.get('gun_until',0) and now>=q['gun_until']:
        q['gun_until']=0.;q['gun_rest_until']=now+random.uniform(2.2,3.8)*(1.4-.6*assign(q));return False
    if not q.get('gun_until'):q['gun_until']=now+random.uniform(.65,1.15)
    return True

def shot_heading(q,target):
    p=q['ai_plane'];wanted=aim_heading(q,target)
    if abs(difference(wanted,p.a))>5:return None
    return p.a+random.uniform(-1,1)*dispersion(assign(q))

def egress(q):
    q['egress']=random.uniform(8.,12.);q['egress_heading']=q['ai_plane'].a+random.choice((-1,1))*random.uniform(18,35)
    q['ground_pass_until']=0.;q['pass_rockets']=0;q['attention']=0.;q['reaction_until']=q['age']+q['egress']+1.2
