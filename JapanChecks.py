import tempfile,os
from types import SimpleNamespace

def run(api):
    a=SimpleNamespace(**api)
    from JapanData import DATA
    from Aviation import AIRCRAFT
    from TechTreeLayout import rows
    from AircraftPhysics import Plane
    from AircraftLoadouts import default,valid
    from NuclearMission import select_aircraft
    from InputBindings import Bindings,key
    from AbandonVehicle import step
    assert len([k for k in DATA if k.startswith('jp_')])==31
    from GroundSystems import missile_guidance
    assert missile_guidance(a.VEHICLES['jp_3_4']['ammo_options'][0])=='IR'
    assert a.VEHICLES['jp_2_4']['weapon']=='auto' and a.VEHICLES['jp_2_4']['independent_missiles']
    assert a.VEHICLES['jp_1_11']['turn']>90
    assert len([k for k in DATA if k.startswith('air_jp_')])==26
    with tempfile.TemporaryDirectory() as tmp:
        p=a.Profile(os.path.join(tmp,'save.json'));p.country='jp';p.research=100000
        for catalog,branches in ((a.VEHICLES,6),(AIRCRAFT,6)):
            positions={k:y+i*60 for _,y,_,groups in rows(catalog,'jp',branches) for group in groups for i,k in enumerate(group) if k}
            for k in positions:
                d=catalog[k]
                if d['parent'] in positions:assert positions[k]>positions[d['parent']]
        pending={k for k in a.VEHICLES if k.startswith('jp_') and not a.VEHICLES[k].get('premium') and k not in p.unlocked}
        while pending:
            ready=[k for k in pending if p.can_research(k)];assert ready
            for k in ready:assert p.unlock(k);pending.remove(k)
        for k,d in a.VEHICLES.items():
            if d['country']!='jp' or d.get('premium'):continue
            assert p.equip(k);battle=a.Game(False,'jp',[k]+[None]*7);battle.draw()
            if d['weapon']!='sam':assert battle.shoot(battle.player)
        garage=a.Garage(a.screen,a.text,p)
        for tab in ('garage','tech','data'):garage.tab=tab;garage.draw()
        for k,d in AIRCRAFT.items():
            if d['country']!='jp' or d.get('premium'):continue
            p.unlocked.add(k);assert p.equip(k)
            plane=Plane(k,0,a.V());assert valid(d,default(d));assert plane.stats['source']==d['source']
            garage.aviation=True;garage.flight.preview=k
            for tab in ('garage','tech','data','loadout'):garage.tab=tab;garage.draw()
            battle=a.Game(False,'jp',[k]+[None]*7);battle.draw();battle.flight.plane.phase='airborne';battle.flight.plane.speed=d['speed'];battle.flight.plane.altitude=180;battle.update(.01)
        assert p.save();assert a.Profile(p.path).selected==p.selected
        assert AIRCRAFT[select_aircraft(AIRCRAFT,'jp',12.7)]['slug']=='f_2a'
    for ident in ('jp_1_11','air_jp_2_6'):
        g=a.Game(False,'jp',[ident]+[None]*7);controls=Bindings();g.controls=controls
        controls.pressed.add(key(a.pygame.K_j));assert not step(g,2.9);assert not g.player.dead
        controls.pressed.clear();step(g,.1);assert g.abandon_elapsed==0
        controls.pressed.add(key(a.pygame.K_j));assert not step(g,2.9);assert step(g,.11)
        assert g.player.dead and g.state=='wreck' and g.death_wait==4
        if ident.startswith('air'):assert g.flight.plane.dead and g.flight.record['dead']
        tickets=list(g.tickets);step(g,1);assert g.tickets==tickets
    controls=Bindings();controls.bind('common.abandon',key(a.pygame.K_LCTRL)+'+'+key(a.pygame.K_j))
    controls.pressed={key(a.pygame.K_j)};assert not controls.keys('ground')[a.pygame.K_F6]
    controls.pressed.add(key(a.pygame.K_LCTRL));assert controls.keys('ground')[a.pygame.K_F6]
    assert key(a.pygame.K_j) not in Bindings().binds['ground.missile']
    print('PASS Japanese 31 ground / 26 air units: all prerequisite edges, research, national slots, saves, unit drawings, live flight, station limits, loadout UI, Japanese nuclear selection; held J cancel, 3-second ground/air death delay, one ticket event, combo binding')
