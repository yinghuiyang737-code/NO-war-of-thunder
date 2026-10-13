import math,tempfile,os,json
from pygame.math import Vector2 as V

def run(api):
    from AmmoBoxes import RANGE,supply_from_box
    keys=[k for k,v in api['VEHICLES'].items() if v['country']=='ussr' and v.get('ammo_box')]
    aa=next(k for k in keys if api['VEHICLES'][k]['name']=='BMPT')
    g=api['Game'](False,'ussr',[aa,keys[0]]+[None]*10);t=g.player
    for p in g.objectives:p.owner=None
    assert g.deploy_ammo_box() and len(g.ammo_boxes)==1 and t.ammo_box_used
    b=g.ammo_boxes[0];assert b['stock']['shells']==math.ceil(t.shell_capacity*1.5) and b['stock']['missile_count']==math.ceil(t.stats['missile_capacity']*1.5)
    g.draw();assert not g.deploy_ammo_box()
    t.shells-=10;t.missile_count-=2;t.mg_rounds-=100;t.modules[api['CREW'][0]]=0
    old=dict(b['stock']);g.supply_step(2.5);assert t.supply_ammo_active and t.supply_timer==2.5
    g.supply_step(2.5);assert t.shells==t.shell_capacity-5 and t.missile_count==t.stats['missile_capacity']-1 and t.mg_rounds==1200
    assert b['stock']['shells']==old['shells']-5 and b['stock']['missile_count']==old['missile_count']-1 and b['stock']['mg_rounds']==old['mg_rounds']-100
    assert t.modules[api['CREW'][0]]==0 and not t.supply_crew_active
    ally=api['Tank'](t.p,vehicle=aa);ally.shells=0;assert not supply_from_box(g,ally,5) and ally.shells==0
    ally.network_owner=1;assert not supply_from_box(g,ally,5)
    g.supply_step(2);t.speed=20;g.supply_step(.1);assert t.supply_timer==0 and not t.supply_ammo_active
    t.speed=0;t.p=b['p']+V(RANGE+1,0);g.supply_step(5);assert t.shells==t.shell_capacity-5
    t.p=V(b['p']);g.supply_step(5);assert t.shells==t.shell_capacity and t.missile_count==t.stats['missile_capacity']
    # A friendly captured point supplies independently without spending the box stock.
    t.shells-=5;point=g.objectives[0];point.owner=0;point.contested=False;t.p=V(point.p);b['p']=V(t.p);old=dict(b['stock'])
    g.supply_step(5);assert t.shells==t.shell_capacity and b['stock']==old
    point.owner=None;b['stock']={k:0 for k in b['stock']};b['stock']['shells']=2;t.shells-=5
    g.supply_step(5);assert t.shells==t.shell_capacity-3 and not g.ammo_boxes
    assert not g.deploy_ammo_box();g.draw()
    # The host alone creates boxes; owner and finite inventory survive the JSON snapshot.
    from LANBattle import Authority
    from LANSquad import configuration
    from LANSnapshot import Snapshot,Replica
    from InputBindings import get_controls
    with tempfile.TemporaryDirectory() as tmp:
        profile=api['Profile'](os.path.join(tmp,'profile.json'));profile.country='ussr';profile.lineups['ussr']=[aa,keys[0]]+[None]*10
        start=dict(members=[dict(id=i,name='测试'+str(i),config=configuration(profile)) for i in range(2)],br=12.,map_id=g.map_id)
        a=Authority(api,start,get_controls())
        for ident,ctx in a.contexts.items():a.action(ident,dict(action='deploy',slot=0,base=ident))
        a.action(1,dict(action='ammo_box'));assert len(a.root.ammo_boxes)==1 and a.root.ammo_boxes[0]['owner']==1
        a.action(1,dict(action='ammo_box'));assert len(a.root.ammo_boxes)==1
        packet=json.loads(json.dumps(Snapshot(a).build(),allow_nan=False));replica=Replica(api,start,1);replica.apply(packet)
        assert replica.g.ammo_boxes[0]['owner']==1 and replica.g.ammo_boxes[0]['stock']==a.root.ammo_boxes[0]['stock']
    print('PASS eligible support vehicles, personal finite 150% stock, one box, proximity/parking/progress, exact withdrawals, no ally/crew supply, point priority and LAN owner replication')

