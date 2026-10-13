"""Additional research vehicles, keeping existing IDs and player unlocks stable."""
import copy,re
from TechExpansionData import GROUND,AIR

def register(vehicles,nations,aircraft):
    from VehicleData import DATA,configure
    from GroundModels import FAMILIES,OVERRIDES,fit
    from VehicleModels import SHAPES
    from GroundEquipment import EQUIPMENT
    from Aviation import GROUND_AIR_BR
    from AircraftModels import PROFILES,ALIASES
    from AircraftLoadoutData import DATA as LOADOUTS
    from AircraftWarningData import DATA as WARNINGS
    from AircraftLandingEquipment import EQUIPMENT as LANDING
    from AircraftRadar import RADARS,FITS,TYPES
    for spec in GROUND:
        k=spec['id'];base=vehicles[spec['base']];parent=vehicles[spec['parent']]
        v=copy.deepcopy(base);d=copy.deepcopy(spec['data'])
        v.update(id=k,name=spec['name'],country=spec['country'],branch=spec['branch'],parent=parent['id'],tier=parent['tier']+1,cost=120+int(d['br']*85),color=nations[spec['country']]['color'],radar=False,premium=False,fictional=False,artillery=False,ammo_capacity=spec['capacity'],shell_capacity=spec['capacity'])
        for key in ('ground_ir_lock','ground_lock_range','split_system','launcher_vehicle','laser_warning','front_profile','effective_front','autoloader','drum_capacity'):v.pop(key,None)
        v['mg']=d['traits']['mg'];DATA[k]=d;configure(v)
        FAMILIES[v['name']]=FAMILIES[base['name']];OVERRIDES[v['name']]=(base.get('visual_length_m',5.9),base.get('visual_width_m',2.6));SHAPES[v['name']]=v['model'];fit(v)
        if v['name']=='T-44':
            FAMILIES[v['name']]='tseries';OVERRIDES[v['name']]=(6.07,3.25);v['model']=(46,25,'round',0,20,77);SHAPES[v['name']]=v['model'];fit(v)
        if v['name']=='Ho-I':
            v['model']=(43,22,'box',0,18,39);SHAPES[v['name']]=v['model'];fit(v)
        EQUIPMENT[k]=copy.deepcopy(EQUIPMENT.get(base['id'],{}));vehicles[k]=v;nations[v['country']]['branches'][v['branch']].append(v['name'])
    PROFILES['mig19']=(.19,-.12,-.27,-.26,.09,.34,2,'jet intake')
    PROFILES['f86k']=(.14,-.10,-.23,-.23,.085,.35,1,'jet intake')
    for spec in AIR:
        k=spec['id'];base=aircraft[spec['base']];parent=aircraft[spec['parent']];d=copy.deepcopy(base);d.update(copy.deepcopy(spec['data']))
        d.update(id=k,name=spec['name'],country=spec['country'],branch=parent['branch'],parent=parent['id'],tier=parent['tier']+1,cost=140+int(d['br']*70),slug=spec['slug'],source=spec['source'],fictional=False,performance_note='WT RB 参考规格；二维飞行、雷达扫描和挂载投射效果为游戏模拟',source_note='WT 官方 Wiki，2026-10-12')
        d['Length']=d['length'];d['Wingspan']=d['span'];d['Ammunition']=d['ammo'];d['speed']=d['max_speed']/3.6*8;d['turn']=1800/max(8,d['Turn time']);d['ground_br']=max(1,d['br']-1) if d['br']>=10 else d['br'];GROUND_AIR_BR[k]=d['ground_br']
        family='mig19' if d['name']=='J-6A' else 'f86k' if d['name']=='F-86K' else 'mig17' if d['name']=='MiG-17' else base['model_family'];d['model_family']=family;ALIASES.insert(0,(d['slug'],family))
        # Exact unit station matrix or complete presets from the public WT table.
        fitdata=copy.deepcopy(spec['fit'])
        d['loadout']=fitdata;LOADOUTS[k]=fitdata;d['station_count']=len(fitdata['slots']);d['weapon_station_count']=len({i for w in fitdata['weapons'] for i in w['slots']})
        allweapons=fitdata['weapons']+[w for p in fitdata['presets'] for w in p['items']]
        d['missile_types']=list(dict.fromkeys(re.findall(r'(?:AIM-|AGM-|R-|PL-)\d+[A-Z]*',' '.join(w['short'] for w in allweapons))))
        d['missiles']=max([max(1,len(w.get('slots',[])))*w['count'] for w in allweapons if w['kind']=='aam']+[0]);d['bombs']=any(w['kind']=='bomb' for w in allweapons);d['rockets']=any(w['kind']=='rocket' for w in allweapons)
        d['bomb_count']=max([w['count']*max(1,len(w.get('slots',[]))) for w in allweapons if w['kind']=='bomb']+[0]);d['rocket_count']=max([w['count']*max(1,len(w.get('slots',[]))) for w in allweapons if w['kind']=='rocket']+[0])
        warning=copy.deepcopy(base['warning']);warning['source']=spec['source'];warning['maw']=False;warning['cm']=dict(flare=d['countermeasures'],chaff=d['countermeasures'])
        if not d['radar']:warning['rwr']=None
        if d['name']=='J-6A':warning['rwr']=dict(model='SPO-2',bands='E, F, G',range=30.,launch=False,tracking=False,iff=False)
        if d['name']=='F-16A':warning['rwr']=dict(model='AN/ALR-69',bands='E, F, G, H, I, J',range=50.,launch=True,tracking=True,iff=False)
        d['warning']=warning;WARNINGS[k]=warning
        landing=copy.deepcopy(base['landing_equipment']);landing['source']=spec['source'];landing['hook']=d['name']=='F-16A';landing['chute']=d['name'] in ('MiG-21SMT','J-6A','F-86F-40');d['landing_equipment']=landing;LANDING[k]=landing
        if d['radar']:
            radar='AN/APG-66' if d['name']=='F-16A' else 'RP-22' if d['name']=='MiG-21SMT' else 'RP-5' if d['name']=='J-6A' else 'AN/APG-37'
            RADARS.setdefault(radar,('mechanical' if d['name']=='F-16A' else 'pulse',('RWS','ACM'),75 if d['name']=='F-16A' else 30,45,2.,1,20));FITS[d['name']]=radar;d.update(radar_model=radar,radar_type=TYPES['mechanical' if d['name']=='F-16A' else 'pulse'],sensor_note=radar)
        else:d.update(radar_model=None,radar_type=TYPES['none'],sensor_note='无搜索雷达')
        aircraft[k]=d

def checks(api):
    from Garage import VEHICLES,AIRCRAFT,NATIONS
    from AircraftLoadouts import default,valid
    from AircraftModels import polygons
    from TechTreeLayout import rows
    from pygame.math import Vector2
    from types import SimpleNamespace
    from MissileRange import prepare,MARGIN
    for spec in GROUND:
        d=VEHICLES[spec['id']];assert d['parent'] is None or (d['parent'] in VEHICLES and VEHICLES[d['parent']]['country']==d['country'] and d['tier']>VEHICLES[d['parent']]['tier']);assert d['ammo_options'] and d['weight']>0
        t=api['Tank']((1000,1000),vehicle=d['id']);assert t.stats['id']==d['id']
    for spec in AIR:
        d=AIRCRAFT[spec['id']];assert d['parent'] is None or AIRCRAFT[d['parent']]['country']==d['country'];assert valid(d,default(d));assert len(polygons(d))>4
    for c in NATIONS:
        assert len([s for s in GROUND if s['country']==c])==3 and len([s for s in AIR if s['country']==c])==3
        rows(VEHICLES,c,6);rows({k:d for k,d in AIRCRAFT.items() if not d.get('helicopter')},c,5)
    g=SimpleNamespace(world_size=(9000,7000));m=dict(p=Vector2(1000,1000),life=.01,kind='missile');prepare(g,[m]);assert m['life']==3600
    m['p'].x=-MARGIN-1;prepare(g,[m]);assert m['life']==0;m['p'].x=0;prepare(g,[m]);assert m['life']==0
    print('PASS 30 research additions, nation/prerequisite edges, weapon fits, model geometry, huge missile bounds')


