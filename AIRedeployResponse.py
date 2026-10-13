"""Dense smoke textures and bounded, perception-limited AI counter deployments."""
import random,pygame
from pygame.math import Vector2 as V
from BattleRoster import row,get,root
from Matchmaking import pool

_SMOKE={}
def smoke_image(radius,kind):
    radius=max(8,((radius+7)//8)*8);key=(radius,kind)
    if key not in _SMOKE:
        image=pygame.Surface((radius*2+8,radius*2+8),pygame.SRCALPHA);center=(radius+4,radius+4)
        color=(245,245,245) if kind=='thermal' else (174,180,170) if kind=='grenade' else (112,121,110)
        for ring in range(24,0,-1):
            alpha=int(30+220*(1-ring/25)**.45)
            pygame.draw.circle(image,(*color,alpha),center,max(1,int(radius*ring/24)))
        pygame.draw.circle(image,(*color,247),center,int(radius*.65))
        if len(_SMOKE)>=48:_SMOKE.clear()
        _SMOKE[key]=image
    return _SMOKE[key]

def order_for(g,unit):
    return getattr(root(g),'ai_response_orders',{}).get(get(unit,'battle_id'))

def matches(g,unit,order):
    if isinstance(unit,dict) and unit.get('missile'):return False
    return bool(order and row(g,unit)['id']==order['attacker'])

def counter_vehicle(g,team,attacker,vehicles,rng=random):
    country=(g.enemy_country or 'ussr') if team else g.country
    candidates=pool(vehicles,country,g.battle_br)
    if not candidates:return None
    flying=isinstance(attacker,dict) or get(attacker,'airborne',False)
    stats=get(attacker,'model',{}) if isinstance(attacker,dict) else attacker.stats
    armor=stats.get('effective_front') or stats.get('armor',(100,50,30))
    front=max(1,armor[0])
    def score(k):
        d=vehicles[k]
        if flying:return (8 if d.get('branch')==3 else 0)+(3 if d.get('radar') else 0)+min(2,4/max(.1,d.get('reload',4)))
        pen=d.get('pen',100)
        return min(3,pen/front)*3+min(2,5/max(.1,d.get('reload',5)))+min(1,d.get('speed',100)/180)-(3 if d.get('branch')==3 else 0)
    ranked=sorted(candidates,key=score,reverse=True)
    if flying and any(vehicles[k].get('branch')==3 for k in ranked):ranked=[k for k in ranked if vehicles[k].get('branch')==3]
    best=score(ranked[0]);choices=[k for k in ranked if score(k)>=best-.7][:5]
    return rng.choice(choices)

def schedule(g,victim,attacker,entry,vehicles,rng=random):
    if attacker is None or get(attacker,'dead',False) or rng.random()>=.35:return False
    v=row(g,victim);a=row(g,attacker)
    if v['human'] or v['team']==a['team']:return False
    ident=counter_vehicle(g,v['team'],attacker,vehicles,rng)
    if not ident:return False
    world=root(g)
    if not hasattr(world,'ai_response_orders'):world.ai_response_orders={}
    # Only the death incident location is shared. Never copy an unseen attacker's live position.
    point=V(victim['p'] if isinstance(victim,dict) else victim.p)
    world.ai_response_orders[v['id']]=dict(attacker=a['id'],deaths=a['deaths'],p=point,until=g.time+90)
    entry.update(vehicle=ident,vehicle_selected=True,aircraft=None,battle_id=v['id'])
    return True

def install(Game,api):
    from AIFlight import AIFlights
    old_death=Game.register_death;old_update=Game.update;old_killed=AIFlights.killed
    def death(g,t):
        active=t in g.allies or t in g.enemies;attacker=get(t,'last_attacker')
        old_death(g,t)
        queue=g.enemy_queue if t.enemy else g.ally_queue
        if active and queue and isinstance(queue[-1],dict):schedule(g,t,attacker,queue[-1],api['VEHICLES'])
    def killed(manager,q,owner=None):
        active=not q.get('registered');attacker=owner or q.get('last_attacker')
        old_killed(manager,q,owner)
        queue=manager.g.enemy_queue if q['team'] else manager.g.ally_queue
        if active and queue and isinstance(queue[-1],dict):schedule(manager.g,q,attacker,queue[-1],api['VEHICLES'])
    def update(g,dt):
        world=root(g);orders=getattr(world,'ai_response_orders',{})
        for ident,order in list(orders.items()):
            attacker=world.battle_roster.get(order['attacker'])
            if g.time>=order['until'] or not attacker or attacker['deaths']>order['deaths']:orders.pop(ident,None)
        old_update(g,dt)
    Game.register_death=death;Game.update=update;AIFlights.killed=killed

def self_test(api):
    from types import SimpleNamespace
    from CombatEffects import spall
    class Fixed:
        def random(self):return 0.
        def choice(self,values):return values[0]
    vehicles={'weak':dict(country='us',br=10.,pen=80,reload=8,speed=100,branch=1),
              'counter':dict(country='us',br=10.,pen=700,reload=5,speed=150,branch=4),
              'aa':dict(country='us',br=10.,pen=30,reload=.1,speed=100,branch=3,radar=True),
              'too_high':dict(country='us',br=14.,pen=1200,reload=1,speed=200,branch=4)}
    game=SimpleNamespace(country='us',enemy_country='us',battle_br=10.)
    tank=SimpleNamespace(stats=dict(armor=(500,50,30)),airborne=False)
    assert counter_vehicle(game,0,tank,vehicles,Fixed())=='counter'
    assert counter_vehicle(game,0,dict(model={}),vehicles,Fixed())=='aa'
    assert smoke_image(160,'grenade').get_at((164,164)).a>=240
    class Hull:
        def __init__(self,engine):
            self.radius=60;self.half_length=60;self.body_rect=pygame.Rect(-60,-60,120,120)
            self.module_rects={'gunner':pygame.Rect(15,-60,20,120)}
            self.modules={'gunner':2};self.fire=0
            if engine is not None:self.module_rects['engine']=pygame.Rect(-35,-60,20,120);self.modules['engine']=engine
        def world(self,p):return V(p)
        def module_clip(self,k,a,b):return self.module_rects[k].clipline(a,b)
        def damage_module(self,k,amount):self.modules[k]=max(0,self.modules[k]-amount)
    counts=[]
    for engine in (None,2,0):
        hits=0
        for seed in range(20):
            hull=Hull(engine);damage,rays,_=spall(hull,V(-55,0),V(1,0),dict(type='AP',caliber=75),random.Random(seed))
            hits+='gunner' in damage
        counts.append(hits)
    assert counts[0]>counts[1] and counts[0]>counts[2],counts
    g=api['Game'](True,'us',[next(k for k,d in api['VEHICLES'].items() if d['country']=='us' and not d.get('premium'))]+[None]*11)
    g.enemy_country='us';victim=api['Tank'](V(1000,1000),True,vehicle=g.player.vehicle_id);entry={}
    assert schedule(g,victim,g.player,entry,api['VEHICLES'],Fixed())
    order=order_for(g,victim);point=V(order['p'])
    assert entry['vehicle_selected'] and entry['aircraft'] is None
    assert abs(api['VEHICLES'][entry['vehicle']]['br']-g.battle_br)<=1.00001
    g.player.p+=V(3000,0)
    assert order['p']==point
    controlled=dict(controlled=SimpleNamespace(g=g),model={},team=0,dead=False,p=V(g.player.p))
    assert matches(g,controlled,order)
    count=len(g.battle_roster);assert not matches(g,dict(missile=True),order) and len(g.battle_roster)==count
    g.time=order['until']+1;g.update(0)
    assert order_for(g,victim) is None
    print('PASS: dense smoke core, legal ground/air counters, bounded incident search, intact and damaged module fragment absorption')
