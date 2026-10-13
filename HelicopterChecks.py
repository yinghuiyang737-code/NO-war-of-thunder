import os,tempfile,json,math
from pygame.math import Vector2 as V
def run(api):
    from Helicopters import IDS
    from Aviation import AIRCRAFT
    from AircraftPhysics import Plane,bearing,difference
    from AircraftModels import draw,polygons
    from FlightDynamics import step
    from AircraftLoadouts import valid,guidance_label,selected,install_plane,items
    from LANSquad import validate_config
    from HelicopterLoadoutData import DATA as WT_FITS
    assert len(WT_FITS)==20
    for country,ids in IDS.items():
        for ident in ids:
            d=AIRCRAFT[ident];fit=d['loadout'];actual=WT_FITS[d['name']]
            assert fit['source']==actual['source'] and fit['slots']==actual['slots']
            for real in actual['weapons']:
                index=next(i for i,w in enumerate(fit['weapons']) if w['name']==real['name'] and w['count']==real['count'] and w['slots']==real['slots'])
                for slot in real['slots']:
                    config={'stations':[-1]*len(fit['slots']),'fit_revision':1};config['stations'][slot]=index
                    assert valid(d,config),(ident,real['name'],slot)
                    fitted=Plane(ident,0,V(),{'loadout':config})
                    assert fitted.agms==real['count'] if real['kind']=='agm' else True
                    if real['kind']=='aam':assert fitted.missiles==real['count']
                    if real['kind']=='bomb':assert fitted.bombs==real['count']
                    if real.get('attached_rockets'):assert fitted.pod_ammo>0 and fitted.rockets==3
            empty=Plane(ident,0,V(),{'loadout':{'stations':[-1]*len(fit['slots']),'fit_revision':1}})
            assert not empty.agms and not empty.missiles and not empty.rockets and not empty.bombs
    for ident,kind,match in [('heli_jp_1','agm','AGM-22'),('heli_de_1','gunpod','3 × FFAR'),('heli_ussr_2','bomb','OFAB-250')]:
        d=AIRCRAFT[ident];fit=d['loadout'];index=next(i for i,w in enumerate(fit['weapons']) if w['kind']==kind and match in w['name'] and w['slots'])
        weapon=fit['weapons'][index];config={'stations':[-1]*len(fit['slots']),'fit_revision':1};config['stations'][weapon['slots'][0]]=index
        battle=api['Game'](False,d['country'],[ident]+[None]*11);battle.flight.weapons[ident]={'loadout':config};battle.flight.start(ident)
        plane=battle.flight.plane;plane.phase='airborne';plane.altitude=80;plane.a=0
        battle.flight.laser_point=plane.p+V(4000,0)
        if kind=='agm':
            before=plane.agms;assert battle.flight.launch_ground() and plane.agms==before-1
        elif kind=='bomb':
            before=plane.bombs;assert battle.flight.bomb() and plane.bombs==before-1
        else:
            assert battle.flight.gun() and battle.flight.rocket() and plane.rockets==2
    with tempfile.TemporaryDirectory() as tmp:
        profile=api['Profile'](os.path.join(tmp,'profile.json'));assert all(len(x)==12 for x in profile.lineups.values())
        for c,ids in IDS.items():
            assert len(ids)==4 and ids[0]==f"heli_{c}_1" and ids[-1]==f"heli_{c}_2"
            profile.country=c;profile.research=10000;profile.unlocked.add(c+'_1_3')
            for ident in ids:
                ancestor=AIRCRAFT[ident]['parent']
                while ancestor is not None:
                    profile.unlocked.add(ancestor);ancestor=AIRCRAFT[ancestor]['parent']
                if ident not in profile.unlocked:assert profile.aviation.unlock(ident)
                profile.active[c]=11;assert profile.equip(ident)
                p=Plane(ident,0,(0,0));p.phase='runway';p.altitude=0;p.takeoff_distance=0;p.nuclear=False
                for _ in range(120):assert step(p,.05,0,0)
                assert p.phase=='airborne';p.throttle=0
                for _ in range(200):assert step(p,.05,0,0)
                assert p.speed<1 and p.altitude>0 and valid(p.stats,p.loadout)
                assert polygons(p.stats);draw(api['screen'],p.stats,(500,300),1,35)
            validate_config(dict(country=c,lineup=profile.lineups[c],slot=11))
        saved=json.loads(open(profile.path,encoding='utf-8').read());saved['lineups']['us']=saved['lineups']['us'][:8];saved['active']['us']=0
        open(profile.path,'w',encoding='utf-8').write(json.dumps(saved));restored=api['Profile'](profile.path);assert len(restored.lineups['us'])==12 and restored.lineups['us'][:8]==saved['lineups']['us']
        ident=IDS['us'][-1];g=api['Game'](True,'us',[ident]+[None]*11,0);g.wave=1;g.flight.start(ident);p=g.flight.plane;p.phase='airborne';p.altitude=80;p.throttle=0;g.enemies=[];g.allies=[]
        # Helipad base rendering survives death and clearing the plane; no runway is drawn.
        import LandingDevices,pygame
        original_runway=LandingDevices.draw_runway;calls=[]
        try:
            LandingDevices.draw_runway=lambda *args:calls.append(args)
            surface=pygame.Surface(api['screen'].get_size())
            g.flight.draw_world(surface,True);p.dead=True;g.flight.draw_world(surface,True)
            g.flight.plane=None;g.flight.draw_world(surface,True)
            assert not calls and g.flight.base_kind=='helipad'
            g.flight.plane=p;p.dead=False
        finally:LandingDevices.draw_runway=original_runway
        p.speed=500;p.throttle=.8
        assert g.flight.toggle_hover()
        for _ in range(100):assert step(p,.05,90,0)
        anchor=p.p.copy();height=p.altitude
        for _ in range(100):assert step(p,.05,180,0)
        assert p.p.distance_to(anchor)<.001 and p.speed==0 and p.altitude==height
        assert g.flight.toggle_hover() and not p.hover
        # Player translation is independent of mouse yaw, accelerates and coasts.
        p.heli_velocity=V();p.throttle=1;p.hover=False;p.speed=0;start=p.p.copy()
        for _ in range(60):assert step(p,1/60,90,0,translation=V(1,0))
        assert 110<p.speed<125 and p.p.x>start.x+50 and abs(p.p.y-start.y)<.001
        velocity=V(p.heli_velocity);before=p.p.copy()
        assert step(p,.1,-90,0,translation=V())
        assert 0<p.speed<velocity.length() and p.p.x>before.x and abs(p.p.y-before.y)<.001
        for _ in range(120):assert step(p,1/60,180,0,translation=V())
        assert p.speed<.001
        for _ in range(60):assert step(p,1/60,0,0,translation=V(0,-1))
        assert p.heli_velocity.y<-110 and abs(p.heli_velocity.x)<.001
        p.hover=True;p.hover_altitude=p.altitude;p.hover_anchor=None
        for _ in range(120):assert step(p,1/60,90,0,translation=V())
        assert p.speed==0 and p.hover
        assert step(p,.1,90,0,translation=V(-1,0)) and not p.hover and p.heli_velocity.x<0
        p.heli_velocity=V();p.speed=0
        legacy={'stations':[0,0,0,0]}
        migrated=selected(p.stats,{'loadout':legacy});assert valid(p.stats,migrated) and len(migrated['stations'])==6
        assert sum(w['count'] for _,w in items(p.stats,migrated) if w['kind']=='agm')==16
        assert guidance_label({'guidance':'SARH'})=='半主动雷达'
        assert guidance_label({'guidance':'ARH'})=='主动雷达'
        assert guidance_label({'guidance':'SALH laser'})=='半主动激光'
        assert guidance_label({'guidance':'SACLOS wire'})=='有线指令'
        p.stats['warning']['maw']=True
        incoming=dict(p=p.p+V(4000,0),v=V(-4800,0),life=2,kind='agm',missile_event=True,team=1,target=None)
        g.flight.projectiles.append(incoming);g.flight.warning.update(.1);assert any(c['level']==3 for c in g.flight.warning.contacts)
        g.flight.projectiles.remove(incoming)
        g.flight.laser_point=p.p+V(4000,0);stock=p.agms;assert stock==16 and g.flight.launch_ground() and p.agms==15
        m=g.flight.projectiles[-1];assert m['cursor_guided'] and m['missile_event'] and m['target'] is None
        assert g.flight.guided_missile() is m
        g.camera();missile_camera=g.cam.copy();m['p']+=V(800,0);g.camera();assert abs(g.cam.x-missile_camera.x-800)<.001
        target=api['Tank'](p.p+V(100000,0),True,vehicle='us_1_1');p.ground_lock=target
        g.draw(mouse_position=(800,350))
        assert len(g.flight.last_target_markers)==1 and g.flight.last_target_markers[0]['edge']
        target.dead=True;g.draw(mouse_position=(800,350));assert not g.flight.last_target_markers
        p.ground_lock=None
        old_tree=g.terrain.strike_tree
        def blocked_tree(*args):raise AssertionError('Helicopter missile collided with terrain')
        g.terrain.strike_tree=blocked_tree
        g.flight.update_ordnance(.01);assert m in g.flight.projectiles and m['overfly_terrain']
        g.terrain.strike_tree=old_tree
        assert not g.flight.launch_ground() and p.agms==15
        g.flight.laser_point=p.p+V(0,4000);before=bearing(m['v']);g.flight.update_ordnance(.1);assert difference(bearing(m['v']),before)>0
        g.flight.laser_point=p.p+V(0,-4000);before=bearing(m['v']);g.flight.update_ordnance(.1);assert difference(bearing(m['v']),before)<0
        g.camera();missile_camera=g.cam.copy();m['life']=0;assert g.flight.guided_missile() is None
        g.camera();assert g.cam.distance_to(missile_camera)>10
        g.flight.projectiles.remove(m)
        from LANSnapshot import Snapshot,Replica
        packed=Snapshot.__new__(Snapshot).pack({'token':p.guided_camera});assert Replica.__new__(Replica).unpack(packed)['token']==p.guided_camera
        from JapanData import DATA,DART_VELOCITIES
        for vehicle_id,vehicle in DATA.items():
            if not vehicle_id.startswith('jp_'):continue
            for round in vehicle['ammo']:
                if round['type']=='APFSDS':assert round['velocity']==DART_VELOCITIES[round['name']] and round['velocity']>1300
        tank=api['Tank']((1000,1000),vehicle=next(k for k,v in DATA.items() if v['name']=='Type 10'));tank.ammo_index=next(i for i,a in enumerate(tank.stats['ammo_options']) if a['name']=='Type 10');tank.cd=0
        assert g.shoot(tank) and abs(g.bullets[-1][1].length()-1780*.75)<.001
        tank.body=0;tank.aim=90;tank.smoke_cd=0;tank.smoke_charges=2;g.smokes=[]
        assert g.deploy_smoke(tank) and len(g.smokes)==4
        center=sum((cloud['p']-tank.p for cloud in g.smokes),V())/4
        assert abs(center.x)<.001 and center.y>100 and tank.smoke_charges==1
        assert not g.deploy_smoke(tank)
        p.agms=0
        for w in p.stores:w['remaining']=0
        p.mcd=0;assert not g.flight.launch_ground()
        assert g.flight.service.request()
        for _ in range(1000):
            g.flight.service.update(.05)
            if p.phase=="runway":break
        assert p.phase in ('runway','airborne') and p.agms==16
        garage=api['Garage'](api['screen'],api['text'],restored);restored.country='us'
        for index,rect in garage.slot_buttons():restored.lineups['us'][index]=None
        restored.save();again=api['Profile'](restored.path);assert again.lineups['us']==[None]*12
        garage.draw();assert garage.click(garage.start_button().center) is None
        assert not any(a.colliderect(b) for i,a in garage.slot_buttons() for j,b in garage.slot_buttons() if i!=j)
    print('PASS: five national helicopter branches, research/equip slot 12, vertical takeoff/hover, distinct geometry, finite mouse-guided missiles, helipad service, legacy eight-slot migration and entirely empty roster')



