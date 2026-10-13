"""Meaningful ammo allocation, depletion, switching, supply and network validation."""
import pygame,json
from pygame.math import Vector2 as V
from AmmoLoadout import groups,sanitize,configure,preset,selected,slots,sync,row,adjust,edit_event,slider

def run(api):
    vehicles=api['VEHICLES'];g=api['Game'](True,'ussr',['ussr_1_7']+[None]*11);v=selected(g);indices,cap,field=groups(v)[0]
    assert cap==44
    counts={str(indices[0]):2,str(indices[1]):3}
    safe=sanitize(v,{str(i):999999 for i in indices});assert sum(safe.values())==cap
    assert not any(sanitize(v,{'0':-1,'1':'invalid','2':True}).values())
    g.ammo_packs[v['id']]=sanitize(v,counts);g.deploy_selected=True;g.deploy_delay=0
    assert g.deploy_player(api['BASES'][False]);t=g.player;g.terrain.obstacles=[];g.enemies=[];g.allies=[]
    assert t.shells==5 and t.shell_capacity==5 and t.mg_rounds==1200
    assert g.select_carried_ammo(0);t.cd=0;before=t.mg_rounds
    assert g.shoot(t) and t.ammo_bins[str(indices[0])]==1 and t.shells==4 and t.mg_rounds==before
    t.cd=0;assert g.shoot(t);t.cd=0;assert not g.shoot(t) and not g.select_carried_ammo(0)
    assert g.select_carried_ammo(1) and t.ammo_index==indices[1] and t.cd>0
    # Generic occupied-point/box refill must refill the intended bins and no uncarried types.
    t.shells+=2;sync(t);assert t.ammo_bins[str(indices[0])]==2 and t.shells==5
    assert sum(t.ammo_bins.values())==5 and all(t.ammo_bins[str(i)]==0 for i in indices[2:])
    g.draw()
    # Actual panel click/edit does not select a map position or deploy accidentally.
    d=api['Game'](True,'ussr',['ussr_1_7']+[None]*11);v=selected(d);preset(d,v);r=row(d,indices[0]);d.choose_deployment((r.right-44,r.y+33));assert d.ammo_edit
    for digit in '99999':assert edit_event(d,pygame.event.Event(pygame.KEYDOWN,key=ord(digit),unicode=digit))
    edit_event(d,pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN,unicode=''));assert sum(preset(d,v).values())==cap and d.state=='deploy'
    bar=slider(d,indices[0]);d.choose_deployment(bar.midleft);assert d.ammo_drag
    edit_event(d,pygame.event.Event(pygame.MOUSEMOTION,pos=bar.center,buttons=(1,0,0),rel=(1,0)))
    assert 0<preset(d,v)[str(indices[0])]<cap
    edit_event(d,pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=bar.midright));assert d.ammo_drag is None and preset(d,v)[str(indices[0])]==cap
    d.draw_deployment()
    # Independent cannon and missile bays cannot borrow from each other.
    aa=vehicles['ussr_modern_aa_pantsir_sm']
    a=api['Game'](False,aa['country'],[aa['id']]+[None]*11);p=a.player
    main,mc,mf=groups(aa)[0];miss,xc,xf=groups(aa)[1]
    configure(p,{str(main[0]):4,str(miss[0]):1});a.air.lock=None;p.missile_cd=0
    assert a.air.launch(p) and p.ammo_bins[str(miss[0])]==0 and p.shells==4
    p.missile_cd=0;assert not a.air.launch(p)
    # Missile-only vehicle carries exactly the configured rounds, not infinite stock.
    sam=vehicles['de_3_8'];a=api['Game'](False,'de',[sam['id']]+[None]*11);p=a.player
    configure(p,{'0':1});p.missile_cd=p.cd=0
    assert a.air.launch(p) and p.missile_count==0
    p.missile_cd=p.cd=0;assert not a.air.launch(p)
    # Four-barrel cannon consumes individual rounds, preserving a final partial volley.
    aa=vehicles['ussr_modern_aa_pantsir_sm'];a=api['Game'](False,'ussr',[aa['id']]+[None]*11);p=a.player
    main=groups(aa)[0][0];configure(p,{str(main[0]):2});p.cd=0;n=len(a.bullets)
    assert a.shoot(p) and len(a.bullets)-n==1 and p.shells==1
    p.cd=0;assert a.shoot(p) and p.shells==0
    p.cd=0;assert not a.shoot(p)
    # Server sanitization rejects oversized / malformed remote allocations.
    from LANBattle import Authority
    from InputBindings import Bindings
    config=dict(country='ussr',lineup=['ussr_1_7']+[None]*11,slot=0,ammo={},missiles={},weapons={})
    auth=Authority(api,dict(members=[dict(id=0,name='test',config=config)],map_id='wilderness',br=10),Bindings())
    auth.action(0,dict(action='deploy',slot=0,base=0,ammo_loadout={'0':99999,'1':99999}))
    p=auth.root.player;assert sum(p.ammo_bins.values())==cap
    from LANSnapshot import Snapshot,Replica
    packet=json.loads(json.dumps(Snapshot(auth).build(),allow_nan=False));replica=Replica(api,dict(members=[dict(id=0,name='test',config=config)],map_id='wilderness',br=10),0);replica.apply(packet)
    assert replica.g.player.ammo_bins==p.ammo_bins;replica.g.draw()
    print('PASS capacity-limited editable deployment, per-type depletion/numeric reload/MG exclusion, finite SAM and cannon bays, bounded resupply, finite autocannon stock, sanitized LAN allocation and replica HUD')
