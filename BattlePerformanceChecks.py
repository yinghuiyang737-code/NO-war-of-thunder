"""Checks for exact poses, immediate track tails and wide-view detail costs."""
import pygame,time,math
from pygame.math import Vector2 as V

def run(api):
    from BattleRendering import vehicle,cached_vehicle,trees,world_bounds
    from VehicleModels import draw_model
    from GroundTraces import draw
    from VisionRendering import apply
    s=pygame.Surface((1280,820));samples=[]
    for ident,stats in api['VEHICLES'].items():
        tank=api['Tank']((2000,2000),vehicle=ident);tank.body=37.2;tank.aim=62.4
        vehicle(s,stats,V(400,400),.12,tank.body,turret_yaw=tank.aim)
        cached_vehicle(s,tank,V(400,400),.56,stats['color']);old=tank.rendered_pose
        tank.p+=V(1,0);cached_vehicle(s,tank,V(401,400),.56,stats['color'])
        assert tank.rendered_pose is old
        tank.body+=.1;cached_vehicle(s,tank,V(401,400),.56,stats['color'])
        assert tank.rendered_pose[0]!=old[0] and tank.rendered_pose[1] is old[1]
        samples.append(tank)
    g=api['Game'](False,'ussr',['ussr_1_7']+[None]*11);g.cam=V();g.zoom=1;g.render_view=pygame.Rect(0,68,1280,700);g.map_id='urban_front';g.time=1
    g.tracks=[(V(100,550),V(110,550),4,151)];draw(g,s,lambda p:p,g.render_view)
    g.tracks.append((V(110,550),V(210,550),4,151));g.time=1.016;s.fill((0,0,0));draw(g,s,lambda p:p,g.render_view)
    assert s.get_at((200,550))[:3]==(135,157,171)
    assert len(g.trace_registered)==1
    g.time=1.4;draw(g,s,lambda p:p,g.render_view);assert len(g.trace_registered)==2
    # Sub-degree rotations reach the thermal model, without an integer-angle step.
    target=g.player;target.p=g.screen_to_world((640,400));target.body=37.2;target.aim=62.4
    g.enemies=[];g.allies=[];g.wrecks=[];g.bullets=[];g.mg_tracers=[];g.smokes=[];g.vision='thermal';g.night_battle=False
    calls=[]
    def record(*args):calls.append((args[4],args[6]));return draw_model(*args)
    apply(g,s,g.render_view,.56,record);assert calls[-1]==(37.2,62.4)
    target.body+=.1;apply(g,s,g.render_view,.56,record);assert math.isclose(calls[-1][0],37.3) and calls[-1][1]==62.4
    bounds=world_bounds(g,g.render_view)
    assert {id(item[0]) for item in trees(g.terrain,bounds) if bounds.collidepoint(item[0])}=={id(item[0]) for item in g.terrain.trees if bounds.collidepoint(item[0])}
    original_chunks=g.terrain.tree_chunks
    removed=g.terrain.trees[0];g.terrain.remove_tree(removed)
    list(trees(g.terrain,bounds));assert g.terrain.tree_chunks is original_chunks
    assert not any(item is removed for group in original_chunks.values() for item in group)
    r,kind=g.terrain.obstacles[-1];g.terrain.nearby_obstacles(r);chunks=g.terrain.obstacle_chunks
    g.terrain.remove_obstacle(r,kind);g.terrain.nearby_obstacles(r)
    assert chunks is g.terrain.obstacle_chunks and not any(item[0] is r for group in chunks.values() for item in group)
    selected=samples[:32]
    start=time.perf_counter()
    for _ in range(8):
        for t in selected:draw_model(s,t.stats,V(400,400),.12,t.body,True,t.aim)
    detailed=(time.perf_counter()-start)/8
    start=time.perf_counter()
    for _ in range(8):
        for t in selected:vehicle(s,t.stats,V(400,400),.12,t.body,turret_yaw=t.aim)
    distant=(time.perf_counter()-start)/8
    from FrameStats import draw as fps
    fps(s,pygame.time.Clock())
    print(f'PASS all {len(samples)} vehicle LOD/cached exact poses, live track tail before tile refresh, fractional thermal rotation, indexed trees and FPS; 32 distant vehicles detail {detailed*1000:.2f}ms / LOD {distant*1000:.2f}ms')
