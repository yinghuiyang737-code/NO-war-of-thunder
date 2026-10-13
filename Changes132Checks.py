"""Live respawn-world simulation and observed armour-facing checks."""
import pygame
from pygame.math import Vector2 as V

def run(api):
    from AITactics import face_threat
    from AIController import difference
    ident='ussr_1_7'
    g=api['Game'](False,'ussr',[ident,'ussr_1_1']+[None]*10)
    g.state='play';g.wave=1;g.terrain.obstacles=[];g.terrain.trees=[];g.terrain.ponds=[];g.enemies=[];g.allies=[]
    g.player.p=V(3000,3000);g.player.dead=True;g.player.reason='test';g.register_death(g.player)
    g.death_wait=.01;g.update(.02);assert g.state=='deploy'
    g.deploy_selected=True;g.deploy_choice=V(1500,1500);g.deploy_delay=.3
    corpse_count=len(g.wrecks);used=set(g.used_slots);reserve=g.reserves
    ally=api['Tank']((4000,4000),vehicle=ident);ally.ai=True;g.allies=[ally]
    enemy=api['Tank']((6000,4000),True,vehicle=ident);enemy.ai=True;g.enemies=[enemy]
    g.bullets=[[V(5000,5000),V(100,0),False,.2,0,g.player,{},0,10,False,None]]
    clock=g.time;position=V(ally.p)
    for _ in range(20):g.update(.05)
    assert g.state=='deploy' and g.time>clock+.9 and g.deploy_delay==0 and not g.bullets
    assert ally.p!=position and len(g.wrecks)==corpse_count and g.reserves==reserve and g.used_slots==used
    assert g.deploy_selected and g.deploy_choice==V(1500,1500)
    g.tickets[1]=0;g.update(.05);assert g.state=='win'
    g=api['Game'](False,'ussr',[ident]+[None]*11);g.terrain.obstacles=[];g.terrain.trees=[];g.allies=[];g.enemies=[]
    t=g.player;t.p=V(3000,3000);t.body=90
    enemy=api['Tank']((3500,3000),True,vehicle=ident);g.enemies=[enemy]
    heading,throttle=face_threat(g,t,enemy,'aim',90,0)
    assert heading==0 and throttle==0
    heading,throttle=face_threat(g,t,enemy,'aim',90,-.55)
    assert heading==0 and throttle<0
    heading,throttle=face_threat(g,t,enemy,'drive',90,.72);assert heading==90 and throttle==.72
    t.ai_recent_hit=2;t.ai_threat_heading=0
    heading,throttle=face_threat(g,t,None,'escape',180,.5);assert heading==0 and throttle<0
    t.ai_recent_hit=0;heading,throttle=face_threat(g,t,None,'escape',180,.5);assert heading==180
    # Actual AI turns a stationary firing hull toward a visible flank threat.
    t.ai=True;t.body=90;t.aim=0;t.ai_scan_timer=0;t.ai_candidates=[enemy];t.ai_target=enemy;t.cd=100
    for _ in range(20):g.ai_step(t,.05)
    assert abs(difference(0,t.body))<75,t.body
    print('PASS live death/deployment AI movement, projectile expiry, selection persistence, one death and result transition; observed frontal facing, reverse escape and navigation exclusion')
