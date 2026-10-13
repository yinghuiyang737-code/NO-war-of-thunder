"""Payload-scaled radial blast fragments for aircraft ground ordnance.

The cube-root range is a 2D gameplay approximation; payload masses are kg TNT.
Armour and module traversal are delegated to the normal projectile model.
"""
import math,random,re
from pygame.math import Vector2 as V

def charge(payload):
    if payload.get('kinetic_missile'):return 0.
    params=payload.get('params',payload.get('parameters',{}))
    if isinstance(params,dict):
        value=params.get('TNT equivalent')
        if value:
            m=re.search(r'([\d.]+)\s*(kg|g)',str(value))
            if m:return float(m[1])*(.001 if m[2]=='g' else 1.)
    return max(0,float(payload.get('tnt_equivalent',payload.get('explosive_kg',payload.get('explosive',0))) or 0))

def radius(payload):return 45*charge(payload)**(1/3)

def detonate(g,point,payload,attacker,weapon,team=0):
    mass=charge(payload)
    if not mass:return []
    point=V(point);reach=radius(payload);g.burst(point,(255,176,87),min(60,16+int(mass**(1/3)*4)))
    g.terrain.blast_trees(point,reach)
    # A bounded fan keeps large bombs from creating thousands of update objects.
    for i in range(48):
        angle=math.tau*i/48;v=V(math.cos(angle),math.sin(angle))
        g.fx.append([V(point),v*reach*2,.5,(236,198,119)])
    targets=g.enemies[:] if team==0 else g.allies[:]+([g.player] if not getattr(g.player,'airborne',False) else [])
    hits=[]
    for t in targets:
        if t.dead or getattr(t,'airborne',False) or t.p.distance_to(point)>reach+t.radius:continue
        damaged=[];rays=[];first=None
        # Several radial rays intersect different actual hull/crew modules.
        for offset in (-.75,-.25,.25,.75):
            delta=t.p-point
            if delta.length_squared()<.01:delta=V(1,0)
            lateral=delta.normalize().rotate(90)*t.radius*offset
            end=t.p+lateral+delta.normalize()*t.radius
            contact=t.shell_contact(point,end)
            if not contact or point.distance_to(contact[1])>reach:continue
            if g.terrain.blocks_shell(point,contact[1]):continue
            if any(u is not t and not u.dead and u.shell_contact(point,contact[1]) for u in g.vehicles()):continue
            falloff=max(.03,1-point.distance_to(contact[1])/reach)
            pen=(28+min(100,mass**(1/3)*7))*falloff
            ammo=dict(name=weapon,type='AP',caliber=6,velocity=1000,explosive_kg=0,penetration=[pen]*6)
            result=t.hit(point,end,delta.normalize()*1000,ammo=ammo,barrel_seen={t:'miss'})
            if result:
                first=first or result;damaged.extend(result.get('modules',[]));rays.extend(result.get('fragments',[]))
            if t.dead:break
        if first:
            first.update(kind='爆炸破片 · '+first['kind'],modules=list(dict.fromkeys(damaged)),fragments=rays)
            if damaged:
                t.last_attacker=attacker;t.last_weapon=weapon
                if g.is_player(attacker):t.player_credit=True
            g.record_hit(t,first,attacker,weapon);hits.append(t)
            if t.dead:g.register_death(t)
    return hits
def checks(api):
    import tempfile,os,json
    from Garage import Profile
    from PremiumVehicles import IDS
    assert abs(charge({'params':{'TNT equivalent':'540 g'},'explosive':999})-.54)<1e-6
    assert radius({'explosive':1000})>radius({'explosive':10})>radius({'explosive':1})
    assert radius({'explosive':10,'count':8})==radius({'explosive':10,'count':1})
    assert charge({'kinetic_missile':True,'explosive':100})==0
    with tempfile.TemporaryDirectory() as folder:
        path=os.path.join(folder,'save.json');p=Profile(path)
        assert p.daily.claim_selected(IDS[0]) is None
        p.internal_premium_claim=True;p.save();p=Profile(path)
        before=p.research;daily=dict(p.daily.state)
        assert p.daily.claim_selected(IDS[0])==IDS[0] and p.daily.claim_selected(IDS[0]) is None
        assert p.research==before and p.daily.state==daily
        assert IDS[0] in Profile(path).unlocked and Profile(path).internal_premium_claim
    g=api['Game'](False,'us',['us_1_1']+[None]*11)
    g.terrain.obstacles=[];g.terrain.trees=[];g.enemies=[];g.allies=[]
    t=api['Tank']((2200,2000),enemy=True,vehicle='us_1_1');g.enemies=[t]
    t.body=0;t.aim=90;g.player.p=V(2000,2100)
    prior=dict(g.player.modules)
    assert not detonate(g,V(2000,2000),{'explosive':1},g.player,'test bomb',0)
    hits=detonate(g,V(2000,2000),{'explosive':1000},g.player,'test bomb',0)
    assert t in hits and g.player.modules==prior
    # Actual bomb landing dispatch uses the same payload/fragment system.
    called=[];original=globals()['detonate']
    globals()['detonate']=lambda *args,**kw:called.append(args)
    try:
        g.flight.projectiles=[dict(p=V(2000,2000),v=V(),life=.01,point=V(2000,2000),kind='bomb',weapon={'short':'test','explosive':50},owner=g.player,team=0)]
        g.flight.update_ordnance(.02)
        assert len(called)==1 and called[0][2]['explosive']==50 and not g.flight.projectiles
    finally:globals()['detonate']=original
    print('PASS internal per-vehicle claims/save/normal-save restriction; TNT conversion, monotonic blast range, radial hull fragments, friendly protection and bomb detonation')
