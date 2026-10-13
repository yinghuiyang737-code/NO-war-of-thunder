"""Thermal event highlighting and cached high-density trail rendering checks."""
import pygame,time,random
from pygame.math import Vector2 as V

def run(api):
    from VisionRendering import apply
    from VehicleModels import draw_model
    from VehicleGeometry import MODEL_SCALE
    from GroundTraces import draw
    g=api['Game'](False,'ussr',['ussr_1_7']+[None]*11);g.player.p=V(4000,4000);g.camera();g.vision='thermal';g.night_battle=False;g.allies=[];g.wrecks=[]
    target=api['Tank'](g.screen_to_world((700,400)),True,vehicle='ussr_1_7');g.enemies=[target]
    def forbidden(*args,**kwargs):raise AssertionError('thermal highlight must not perform occlusion queries')
    g.visible=forbidden
    g.bullets=[[g.screen_to_world((760,400)),V(100,0)]];g.mg_tracers=[(g.screen_to_world((820,430)),g.screen_to_world((850,430)),1)]
    g.smokes=[dict(kind='grenade',p=g.screen_to_world((900,500)),radius=20,age=1,life=28),dict(kind='ess',p=g.screen_to_world((1000,500)),radius=20,age=1,life=16)]
    screen=pygame.Surface(api['screen'].get_size());screen.fill((80,110,50));apply(g,screen,api['VIEW'],MODEL_SCALE,draw_model)
    assert min(screen.get_at((700,400))[:3])>=215
    assert min(screen.get_at((760,400))[:3])==255 and min(screen.get_at((835,430))[:3])==255
    assert min(screen.get_at((900,500))[:3])>200 and max(screen.get_at((1000,500))[:3])<130
    old=g.thermal_models[target][1];apply(g,screen,api['VIEW'],MODEL_SCALE,draw_model);assert g.thermal_models[target][1] is old
    # Compare identical visible trail data against the old per-mark draw path.
    g.cam=V();g.zoom=1;g.render_view=pygame.Rect(0,68,1280,700);g.time=1;g.map_id='urban_front';view=g.render_view;s=pygame.Surface((1280,820));rng=random.Random(4)
    g.tracks=[(V(rng.randrange(1280),rng.randrange(68,768)),V(rng.randrange(1280),rng.randrange(68,768)),4,151) for _ in range(1000)]
    # Use actual short traces, rather than unrealistically full-screen segments.
    g.tracks=[(a,a+V(5,0),w,life) for a,b,w,life in g.tracks]
    start=time.perf_counter()
    for _ in range(20):
        for a,b,w,life in g.tracks:pygame.draw.line(s,(135,157,171),a,b,4)
    baseline=(time.perf_counter()-start)/20
    draw(g,s,lambda p:p,view);oldtile=g.trace_tiles[(0,0)]
    start=time.perf_counter()
    for _ in range(20):draw(g,s,lambda p:p,view)
    cached=(time.perf_counter()-start)/20
    assert g.trace_tiles[(0,0)] is oldtile
    # Incremental append/drop must update dirty tiles without retaining old history.
    old_first=id(g.tracks[0]);g.tracks=g.tracks[5:]+[(V(100,100),V(106,100),4,152)];g.time=2;draw(g,s,lambda p:p,view)
    assert old_first not in g.trace_registered and len(g.trace_registered)==len(g.tracks)
    print(f'PASS no thermal occlusion, bright shells/tracers/turret smoke, cold ESS, cached thermal sprites and incremental trace raster; 1000-trace draw old {baseline*1000:.2f}ms / cached {cached*1000:.2f}ms')
