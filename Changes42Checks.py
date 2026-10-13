"""Focused checks for smoke restraint, UAV piloting and display-resolution optics."""
import math,time,pygame
from pygame.math import Vector2 as V

def run(api):
    from Reconnaissance import toggle,orbit,step,mark
    from LANBattle import RemoteControls
    from InputBindings import Bindings,ACTIONS
    from AITactics import defensive_smoke
    import AITactics
    ident=next(k for k,v in api['VEHICLES'].items() if v.get('scout_drone'))
    g=api['Game'](False,api['VEHICLES'][ident]['country'],[ident]+[None]*11)
    g.state='play';g.player.p=V(3000,3000);g.player.body=0;g.enemies=[];g.allies=[]
    g.controls=RemoteControls(Bindings());g.controls.input=dict(keys=[pygame.K_LSHIFT],mouse=[3000,2000])
    assert toggle(g) and g.input_context()=='drone' and g.drone_pos==g.player.p
    tank=V(g.player.p);start=V(g.drone_pos);step(g,.1)
    assert g.drone_pos!=start and g.player.p==tank and g.drone_heading<0 and g.drone_bank<0 and g.drone_throttle>.65
    assert orbit(g);center=V(g.drone_orbit_center);g.controls.input['keys']=[]
    for _ in range(80):step(g,.2)
    assert abs(g.drone_pos.distance_to(center)-450)<75 and g.player.p==tank
    assert toggle(g) and not g.drone_active and g.drone_orbit
    p=V(g.drone_pos);step(g,.1);assert g.drone_pos!=p
    assert 'drone' in ACTIONS['ground.scout']['contexts'] and 'drone' in ACTIONS['air.roll_right']['contexts']
    # Scout the cursor-selected target rather than whatever sits at camera centre.
    assert toggle(g);a=api['Tank'](g.drone_pos+V(100,0),True);b=api['Tank'](g.drone_pos+V(0,350),True);g.enemies=[a,b]
    g.smoke_blocks=lambda *args:False
    assert mark(g,b.p) and getattr(b,'scout_marks',{}) and not getattr(a,'scout_marks',{})
    g.draw()
    # Smoke decisions remain bounded even under uninterrupted retreat/hit notifications.
    t=g.player;t.smoke_charges=3;t.smoke_cd=0;t.ai_recent_hit=3;g.smokes=[];g.time=100
    original=AITactics.random.random;AITactics.random.random=lambda:0
    try:
        assert defensive_smoke(g,t);count=t.smoke_charges
        for i in range(30):g.time+=.1;t.smoke_cd=0;t.ai_recent_hit=3;assert not defensive_smoke(g,t)
        assert t.smoke_charges==count
        g.time=180;t.ai_recent_hit=3;g.smokes[0]['age']=0;assert not defensive_smoke(g,t)
        g.time=220;t.ai_recent_hit=0;g.smokes=[];assert not defensive_smoke(g,t)
    finally:AITactics.random.random=original
    # Flight bank starts moving on the first mouse turn and automatic roll caps at 90 degrees.
    from AircraftPhysics import Plane
    from Aviation import AIRCRAFT
    from FlightDynamics import step as fly
    air=next(k for k,d in AIRCRAFT.items() if not d.get('helicopter'))
    p=Plane(air,0,(0,0));p.phase='airborne';p.a=0;p.altitude=200;p.bank=0
    fly(p,.016,90,0);assert 0<p.bank<=90
    for _ in range(30):fly(p,.016,p.a+120,0)
    assert 85<=p.bank<=90
    p.bank=0;fly(p,.016,p.a-90,0);assert -90<=p.bank<0
    # All living model pixels keep their bright signature, including dark model details.
    from VisionRendering import apply
    from VehicleModels import draw_model
    from VehicleGeometry import MODEL_SCALE
    g.drone_active=False;g.drone_pos=None;g.zoom=1;g.player.p=V(4000,4000);g.camera();g.vision='thermal';g.wrecks=[];g.allies=[]
    a=api['Tank']((4100,4000),True,vehicle=ident);b=api['Tank']((4200,4000),True,vehicle=ident);b.dead=True;g.enemies=[a];g.wrecks=[b]
    g.visible=lambda *args,**kw:True;surface=pygame.Surface(api['screen'].get_size());surface.fill((80,110,50));view=api['VIEW']
    apply(g,surface,view,MODEL_SCALE,draw_model);first=g.vision_buffer
    pa=g.world_to_display(a.p);pb=g.world_to_display(b.p)
    live=surface.get_at((round(pa.x),round(pa.y)))[:3];dead=surface.get_at((round(pb.x),round(pb.y)))[:3]
    assert min(live)>=215 and max(dead)<=99,(live,dead)
    apply(g,surface,view,MODEL_SCALE,draw_model);assert g.vision_buffer is first and first.get_size()==view.size
    # Native filtering benchmark against the old numpy-copy path at identical resolution.
    image=pygame.Surface((1600,900));image.fill((88,130,56));dest=pygame.Surface(image.get_size())
    start=time.perf_counter()
    for _ in range(8):
        copy=image.copy();pixels=pygame.surfarray.pixels3d(copy)
        gray=(pixels[:,:,0].astype('uint16')*3+pixels[:,:,1].astype('uint16')*6+pixels[:,:,2].astype('uint16'))//10
        for ch in range(3):pixels[:,:,ch]=gray//2+20
        del pixels
    old=(time.perf_counter()-start)/8
    start=time.perf_counter()
    for _ in range(8):
        pygame.transform.grayscale(image,dest);dest.fill((128,128,128),special_flags=pygame.BLEND_RGB_MULT);dest.fill((20,20,20),special_flags=pygame.BLEND_RGB_ADD)
    new=(time.perf_counter()-start)/8
    print(f'PASS restrained smoke, white fixed-wing UAV/mouse scout/circle/return, immediate 90-degree bank, live-vs-wreck thermal brightness; filter benchmark old {old*1000:.2f} ms / new {new*1000:.2f} ms at 1600x900')
