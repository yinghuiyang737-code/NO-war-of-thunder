"""Behavior regressions for split batteries, supply and native deployment layouts."""
def run(api):
    from SplitAirDefense import IDS
    from pygame.math import Vector2 as V
    import pygame
    Game=api['Game'];Tank=api['Tank']
    g=Game(False,'de',[IDS['de']]+[None]*7,0);g.wave=1;g.allies=[];g.enemies=[];g.terrain.obstacles=[];g.terrain.ponds=[];g.player.p=V(3000,3000)
    g.battery.attach();radar=g.player
    assert g.battery.toggle() and not g.battery.place(V(4000,3000))
    assert g.battery.place(V(3250,3000));one=g.battery.units[1]
    assert g.battery.toggle() and g.battery.place(V(3000,3250));two=g.battery.units[2]
    assert not g.battery.toggle() and len(g.battery.units)==3
    plane=dict(p=V(3400,3000),v=V(0,0),dead=False,team=1,health=4,bomb=99,life=30)
    g.air.planes=[plane];g.air.lock=plane
    assert not g.air.launch(radar,plane)
    g.battery.step(.1);assert len(g.air.missiles)==1 and one.missile_count==one.stats['missile_capacity']-1
    g.battery.step(.1);assert len(g.air.missiles)==1
    g.battery.step(4.1);assert len(g.air.missiles)==2
    assert g.battery.switch() and g.player is one
    g.air.lock=None;g.battery.step(.1);assert g.air.lock is plane
    one.missile_cd=0;assert g.air.launch() and one.missile_count==one.stats['missile_capacity']-2
    one.missile_count=0;one.missile_cd=0;assert not g.air.launch()
    radar.speed=50;two.speed=20;g.battery.step(.1);assert radar.speed==two.speed==0
    assert g.battery.switch() and g.player is two
    two.dead=True;g.register_death(two);assert g.player is radar and g.state=='play'
    radar.dead=True;g.register_death(radar);assert g.player is one and g.state=='play'
    one.dead=True;g.register_death(one);assert g.state=='wreck'
    h=Game(False,'us',['us_1_14']+[None]*7);h.allies=[];h.enemies=[];t=h.player;t.p=V(h.objectives[0].p);h.objectives[0].owner=0
    t.shells=0;t.mg_rounds=0;t.modules['loader']=0;t.modules['commander']=0
    h.supply_step(5.);assert t.shells==5 and t.mg_rounds==100 and t.crew_replenished and t.crew_alive()==3
    h.supply_step(20.);assert t.crew_alive()==3
    t.shells=0;t.cd=0;assert not h.shoot(t)
    h.objectives[0].owner=1;h.supply_step(5.);assert t.shells==0
    h.objectives[0].owner=0;t.speed=10;h.supply_step(5.);assert t.shells==0
    t.speed=0;h.supply_step(5.);assert t.shells==5
    old=(api['W'],api['H'],api['screen'])
    try:
        for size in ((1280,820),(1600,1025),(1800,1100)):
            api['W'],api['H']=size;api['screen']=pygame.Surface(size)
            d=Game(True);r=d.deployment_map();assert r.right<=size[0]-225 and r.bottom<=size[1]-39
            q=api['DEPLOY_BASES'][False][0];d.choose_deployment((r.x+q.x/api['MW']*r.w,r.y+q.y/api['MH']*r.h));assert d.deploy_selected
            d.draw_deployment();assert d.flight.airport_button().right<=size[0]-20
    finally:api['W'],api['H'],api['screen']=old
    print('PASS: split radar/2-launcher placement, stationarity, interval/finite missiles, AI lock/manual launch, surviving-vehicle control; friendly stationary resupply, one replacement crew; dynamic deployment click geometry')

    from LANBattle import Authority
    from LANSnapshot import Snapshot,Replica
    from InputBindings import get_controls
    import json
    config=dict(country='de',lineup=[IDS['de']]+[None]*7,slot=0,ammo={},missiles={},weapons={})
    start=dict(members=[dict(id=i,name='test'+str(i),connected=True,config=config) for i in range(2)],map_id='wilderness',br=13.7)
    authority=Authority(api,start,get_controls());root=authority.root
    for ident,ctx in authority.contexts.items():authority.action(ident,dict(action='deploy',slot=0,base=ident))
    remote=authority.contexts[1];root.allies=[remote.player];root.enemies=[];root.terrain.obstacles=[];root.terrain.ponds=[];root.wave=1
    remote.player.p=V(3000,3000)
    authority.action(1,dict(action='launcher_deploy'));assert remote.battery.placing
    authority.action(1,dict(action='launcher_place',point=[3250,3000]));assert len(remote.battery.units)==2
    authority.action(1,dict(action='battery_switch'));launcher=remote.player;assert launcher.split_role=='launcher'
    client=Replica(api,start,1);snapshot=Snapshot(authority)
    packet=json.loads(json.dumps(snapshot.build(),allow_nan=False));client.apply(packet)
    assert client.g.player.split_role=='launcher' and client.g.player.stats['split_role']=='launcher'
    assert len(client.g.battery.units)==2 and client.g.battery.radar is not None
    assert client.g.player.shells==launcher.shells and client.g.player.crew_replenished==launcher.crew_replenished
    before=V(launcher.p);authority.accept_input(1,dict(keys=[pygame.K_w],mouse=[3400,3000],fire=False));authority.tick(.1)
    assert launcher.p.distance_to(before)>0
    remote.battery.radar.dead=True;root.register_death(remote.battery.radar);assert not remote.player.dead and remote.state=='play'
    print('PASS: LAN authoritative launcher placement, control switching, moving only controlled unit, radar/launcher roles and finite-stock JSON replication')

    saved=(api['W'],api['H'],api['screen'],api['text'])
    try:
        for width,height in ((1280,820),(1600,1025)):
            api['W'],api['H']=width,height;api['screen']=pygame.Surface((width,height));calls=[]
            api['text']=lambda label,pos,*a,**kw:calls.append((label,pos))
            feedback=Game(False);feedback.state='wreck';feedback.hitview=None;feedback.kill_feed=[];feedback.personal_kills=[dict(victim='test')]
            feedback.draw_battle_feedback()
            pos=next(pos for label,pos in calls if label=='载具被摧毁');assert pos==(width//2,height//2-30)
            pos=next(pos for label,pos in calls if label.startswith('摧毁目标'));assert pos[0]==width/2 and pos[1]<height*.25
    finally:api['W'],api['H'],api['screen'],api['text']=saved
    print('PASS: destroyed-vehicle card centers on native window and target-destroyed announcement remains in upper quarter')
