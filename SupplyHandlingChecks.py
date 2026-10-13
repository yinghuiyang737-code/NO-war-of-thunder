import math,pygame
from pygame.math import Vector2 as V

def run(api):
    from GroundHandling import advance
    Game,Tank=api['Game'],api['Tank']
    g=Game(False,'us',['us_reward_t58']+[None]*11);g.allies=[];g.enemies=[];g.wave=1;t=g.player
    point=g.objectives[0];point.owner=0;point.contested=False;t.p=V(point.p);t.speed=0
    t.premium_ammo=t.shells=10;t.premium_mag=0;t.cd=t.reload_duration=t.stats['rack_reload']
    g.supply_step(2.5);assert t.supply_ammo_active and t.supply_timer==2.5 and t.premium_mag==0
    g.supply_step(2.5);assert t.premium_mag==5 and t.premium_ammo==15 and t.shells==15 and t.cd==0
    assert g.shoot(t);assert (t.premium_mag,t.premium_ammo,t.shells)==(4,14,14)
    g.supply_step(5);assert t.premium_mag==6 and t.premium_ammo==19 and t.shells==19
    g.supply_step(5);assert t.premium_ammo==21 and t.premium_mag==6 and not t.supply_ammo_active
    crew=api['CREW'];t.modules[crew[0]]=t.modules[crew[1]]=0;before=t.crew_alive();g.supply_step(2.5);assert t.supply_crew_active
    g.supply_step(2.5);assert t.crew_alive()==before+1 and t.crew_replenished and not t.supply_crew_active
    g.supply_step(20);assert t.crew_alive()==before+1
    t.shells=t.premium_ammo=10;t.premium_mag=4;g.supply_step(2);t.speed=10;g.supply_step(.1);assert t.supply_timer==0 and not t.supply_ammo_active
    t.speed=0;point.contested=True;g.supply_step(5);assert t.premium_ammo==10
    point.contested=False;point.owner=1;g.supply_step(5);assert t.premium_ammo==10
    point.owner=0;t.crew_replenished=False;g.supply_step(2.5)
    old=(api['W'],api['H'],api['screen'])
    try:
        for size in ((1280,820),(1600,1025)):
            api['W'],api['H']=size;api['screen']=pygame.Surface(size);g.draw()
            x,y=size[0]//2-90,size[1]-80
            assert any(tuple(api['screen'].get_at((x+i,y+j)))[:3]==(149,213,230) for i in range(-22,23) for j in range(-22,23))
    finally:api['W'],api['H'],api['screen']=old
    vehicle=next(k for k,v in api['VEHICLES'].items() if v['name']=='BMPT');auto=Tank((3000,3000),vehicle=vehicle);auto.aim=0
    h=Game(False,'ussr',[vehicle]+[None]*11);h.bullets=[];angles=[]
    for _ in range(20):
        auto.cd=0;assert h.shoot(auto)
        q=h.bullets[-1];angles.append(math.degrees(math.atan2(q[1].y,q[1].x)))
    assert max(angles)-min(angles)>.25
    modern=next(k for k,v in api['VEHICLES'].items() if v['name']=='M1A2 SEP v3') if any(v['name']=='M1A2 SEP v3' for v in api['VEHICLES'].values()) else max(api['VEHICLES'],key=lambda k:api['VEHICLES'][k]['speed'])
    unit=Tank((3000,3000),vehicle=modern);target=unit.stats['speed'];elapsed=0
    while unit.speed<target*.95 and elapsed<90:
        advance(unit,dict(left_speed=target,right_speed=target),1,.05);unit.speed=(unit.left_speed+unit.right_speed)/2;elapsed+=.05
    assert 10<elapsed<60 and unit.speed<=target
    slow=Tank((3000,3000),vehicle=modern);advance(slow,dict(left_speed=target,right_speed=target),1,.1);early=slow.left_speed
    slow.left_speed=slow.right_speed=slow.speed=target*.9;advance(slow,dict(left_speed=target,right_speed=target),1,.1);assert slow.left_speed-target*.9<early
    flat=api['Terrain']();flat.obstacles=[];flat.ponds=[];pivot=Tank((3000,3000),vehicle=modern);pivot.body=0
    for _ in range(30):pivot.drive(0,1,1/60,flat)
    if pivot.stats['dual']:assert pivot.body>10 and abs(pivot.speed)<.01
    print('PASS T58 direct drum supply/counts/fire, five-second ammo/crew progress, one crew maximum, supply interruptions, native ring rendering, independent BMPT spread and tapered acceleration/responsive pivot')
