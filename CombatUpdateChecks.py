"""Behavior checks for the combat response update."""
def self_test(api):
    import math,random
    import pygame
    from pygame.math import Vector2 as V
    from GroundSystems import missile_guidance
    from InputBindings import key,chord
    Game=api['Game'];Tank=api['Tank']
    for k,d in api['VEHICLES'].items():
        t=Tank((2000,2000),vehicle=k);t.body=t.aim=0
        t.aim_at(V(2000,5000),.1)
        expected=min(d.get('turret_limit',10) if d['model'][2]=='casemate' or d.get('rocket_launcher') else 90,d['aim_response_slew']*.1)
        assert abs(t.aim-expected)<.001,(k,t.aim,expected)
        t.aim=0;t.modules['ring']=1;t.aim_at(V(2000,5000),.1)
        assert abs(t.aim-min(d.get('turret_limit',10) if d['model'][2]=='casemate' or d.get('rocket_launcher') else 90,d['aim_response_slew']*.04))<.001
    g=Game(True,'de',['de_0_9']+[None]*7);g.deploy_selected=True;assert g.deploy_player(api['BASES'][False])
    g.allies=[];g.enemies=[];g.terrain.obstacles=[];g.terrain.ponds=[];owner=g.player;owner.p=V(2000,2000);owner.body=owner.aim=0
    t=Tank((3700,2000),True,vehicle='us_1_11');g.enemies=[t];ammo=owner.missile_ammo
    assert missile_guidance(ammo)=='TOP_ATTACK'
    owner.missile_cd=owner.cd=0;assert not g.air.launch(owner,ammo=ammo)
    g.air.lock=t;assert g.air.launch(owner,ammo=ammo);m=g.air.missiles[-1]
    owner.aim=180;peak=0.;captured=[];old_record=g.record_hit
    def record(target,result,shooter,weapon=''):captured.append(result);old_record(target,result,shooter,weapon)
    g.record_hit=record
    for step in range(600):
        t.p.y+=.2;g.air.update(.02)
        peak=max(peak,m.get('height',0))
        if not g.air.missiles:break
    assert peak>=200 and captured and '攻顶' in captured[0]['kind'] and captured[0]['modules']
    owner.dead=False;owner.missile_cd=owner.cd=0;t.dead=False;g.air.lock=t
    assert g.air.launch(owner,ammo=ammo);owner.dead=True
    for _ in range(600):
        g.air.update(.02)
        if not g.air.missiles:break
    assert not g.air.missiles and len(captured)>=2
    g.score=2499;assert not g.flight.available_nuke;g.score=2500;assert g.flight.available_nuke
    g2=Game(True,'us',['us_5_1']+[None]*7);g2.deploy_selected=True;g2.deploy_player(api['BASES'][False]);g2.player.p=V(2000,2000);g2.player.aim=0;g2.player.cd=0
    assert g2.artillery.shoot(g2.player,V(5000,2000));shell=g2.artillery.shells[-1]
    old=max(1.8,min(9.,3000/max(300,(shell['ammo'].get('velocity') or 655)*.65)+1.2))
    assert shell['duration']<old*.5
    c=g.controls;saved={a:list(c.binds[a]) for a in ('ground.lock','ground.missile','common.nuke')}
    try:
        c.binds['ground.lock']=[chord(key(pygame.K_LALT),key(pygame.K_q))];c.binds['ground.missile']=[key(pygame.K_F6)];c.binds['common.nuke']=[key(pygame.K_F5)]
        owner.dead=False;g.state='play';lines=[];prior=g.air.text;g.air.text=lambda s,*a,**kw:lines.append(s);g.air.hud();g.air.text=prior
        assert any(c.label('ground.lock')+' 锁定' in line for line in lines)
        assert any(c.label('ground.missile') in line and '自动追踪' in line for line in lines)
        screen=api['screen'];screen.fill((83,95,107));g.kill_feed=[dict(attacker='PUMA VJTF',weapon='Spike-LR II',victim='M1A2',attacker_team=0,team=1)];g.hitview=None;g.draw_battle_feedback()
        assert tuple(screen.get_at((781,511)))[:3]==(83,95,107)
    finally:c.binds.update(saved)
    print('PASS: all 168 turret rates and damaged traverse, faster landing shells, Spike lock/tracking/roof damage independent of launcher aim or death, 2500 nuclear threshold, rebound key hints and transparent kill feed.')
