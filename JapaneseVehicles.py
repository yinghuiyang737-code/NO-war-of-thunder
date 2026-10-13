"""Japanese normal research trees; reference specs separate from game conversions."""
import copy,re
from JapanData import DATA as RESEARCH

def register(vehicles,nations,aircraft):
    from VehicleData import DATA,configure
    from GroundModels import FAMILIES,DIMENSIONS,OVERRIDES,fit
    from VehicleModels import SHAPES
    from ArtilleryVehicles import SPECS,DATA as SPH_DATA,configure as artillery
    ground={k:d for k,d in RESEARCH.items() if k.startswith('jp_')}
    nations['jp']={'name':'日本','code':'JPN','color':(140,139,98),'branches':[[d['name'] for k,d in ground.items() if d['branch']==b] for b in range(6)]}
    DIMENSIONS.update(japanearly=(5.50,2.33),japan74=(6.70,3.18),japan90=(7.50,3.43),japan10=(6.90,3.24))
    sizes={'Ha-Go':(4.38,2.06),'Ke-Ni':(4.11,2.12),'Chi-Ha':(5.52,2.33),'Chi-Ha Kai':(5.52,2.33),'Chi-He':(5.50,2.20),'Chi-Nu':(5.73,2.33),'Chi-To':(6.42,2.87),'Chi-Ri II':(7.30,3.05),'Type 87 RCV':(5.99,2.48),'Type 16':(8.45,2.98),'Type 60 SPRG':(4.30,2.23),'Type 89':(6.70,3.20),'Type 93':(5.09,2.15),'Type 81 (C)':(7.23,2.48),'Type 75 SPH':(6.64,3.10),'Type 99':(8.00,3.20)}
    for k,raw in ground.items():
        b=raw['branch'];t=raw['tier'];name=raw['name'];modern=raw['br']>=8
        template='us_0_2' if b==0 else 'us_3_5' if b==3 else 'us_5_1' if b==5 else 'us_1_1'
        v=copy.deepcopy(vehicles[template]);d=copy.deepcopy(raw)
        wheel=name in ('Type 87 RCV','Type 16','Type 93','Type 81 (C)')
        family=FAMILIES[name] if name in FAMILIES else 'wheeled' if wheel else 'sph' if b==5 else 'japan10' if name in ('Type 10','TKX') else 'japan90' if 'Type 90' in name else 'japan74' if modern else 'japanearly'
        kind='launcher' if name in ('Type 93','Type 81 (C)') else 'wheel' if wheel else 'open' if name in ('Ho-Ro','Na-To','Ta-Se','So-Ki','Type 60 SPRG') else 'wedge' if family=='japan10' else 'box' if family in ('japan90','sph') or name=='Type 89' else 'round'
        gun=125 if b==5 and t==2 else 88 if b==5 else 98 if modern else 62 if raw['br']>=3 else 38
        model=(50,23,kind,-13 if b==5 else 7 if name in ('Chi-Ha','Chi-Ha Kai') else 0,24 if modern else 16,gun)
        traits=dict(mg=b!=3,night=raw['br']>=6.3,thermal=modern and name not in ('Type 87 RCV','Type 87','Type 74 (E)','Type 74 (F)','STB-1'),stabilizer=2 if modern else 0,dual=modern and not wheel)
        # Real dimensions define the rendered body and collision envelope. Layered armor remains a 2D approximation.
        d.update(status='wiki',source_note='War Thunder 官方 Wiki RB 参考；转向、正面复合防护与二维模型为游戏模拟',checked='2026-10-11',br_source=raw['source'],br_note='WT RB 分房权重',composite=family in ('japan90','japan10'),era=False,independent_missiles=bool(raw['secondary']),missile_reload=10.,traits=traits)
        if name=='Type 89':d['rpm']=200;d['missile_capacity']=4
        if name=='Type 93':d['missile_capacity']=8
        if name=='Type 81 (C)':d['missile_capacity']=8
        if not d.get('rpm'):d.pop('rpm',None)
        if name in ('Type 90','Type 90 (B)','Type 10','TKX'):d['reload']=4.0
        v.update(id=k,name=name,country='jp',branch=b,tier=t,parent=f'jp_{b}_{t-1}' if t>1 else ('jp_1_8' if b==4 else 'jp_2_1' if b==5 else None),cost=0 if t==1 and b<4 else 160+int(raw['br']*100),model=model,color=nations['jp']['color'],wheel=wheel,barrels=2 if name in ('So-Ki','Type 87','Type 60 SPRG') else 1,equipment=[],radar=name=='Type 87',artillery=False)
        if name in ('Type 93','Type 81 (C)'):
            for ammo in d['ammo']:ammo['guidance']='IR'
        DATA[k]=d;configure(v);FAMILIES[name]=family;OVERRIDES[name]=sizes.get(name,DIMENSIONS[family]);SHAPES[name]=model;fit(v)
        if b==5:
            SPECS[k]=dict(roof=15,base_dispersion=48 if t==1 else 34,blast_radius=110,dimensions=sizes[name],gun=gun);SPH_DATA[k]=d;artillery(v)
        if d['composite']:
            v['front_profile']={'hull':(500,850) if family=='japan10' else (420,700),'turret':(600,1000) if family=='japan10' else (520,900),'weak':(80,80),'estimated':True};d['status']='mixed';d['source_note']='基础装甲与动力采用 WT；复合正面等效为游戏模拟估值'
            v['armor_note']='复合装甲正面防护为游戏模拟，非公开真实等效';v['effective_front']=None
        vehicles[k]=v
    register_air(aircraft)

def register_air(aircraft):
    from Aviation import AIR_BRANCHES,GROUND_AIR_BR
    from AircraftModels import PROFILES,ALIASES
    from AircraftRadar import RADARS,FITS,TYPES
    from AircraftLoadoutData import DATA as LOADOUTS
    from AircraftWarningData import DATA as WARNINGS
    from AircraftLandingEquipment import EQUIPMENT
    AIR_BRANCHES['jp']=['陆军战斗','海军战斗','多用途','重战 / 攻击','轰炸机']
    profiles={'ki10':(.20,.10,-.11,-.15,.085,.29,1,'biplane'),'ki27':(.14,.09,-.14,-.18,.08,.28,1,'radial'),'ki43':(.15,.06,-.12,-.20,.075,.28,1,'radial'),'ki84':(.11,.03,-.12,-.24,.085,.30,1,'radial'),'a6m':(.16,.07,-.14,-.22,.082,.31,1,'radial'),'n1k':(.10,.01,-.15,-.23,.09,.32,1,'radial'),'ki61':(.12,.04,-.14,-.23,.073,.30,1,''),'ki100':(.13,.03,-.14,-.22,.083,.30,1,'radial'),'j7w':(-.14,-.23,-.39,-.36,.09,0,1,'canard pusher'),'ki45':(.16,.05,-.10,-.19,.075,.29,2,'radial'),'ki102':(.15,.02,-.12,-.22,.075,.30,2,'radial'),'ki109':(.10,.02,-.10,-.22,.11,.30,2,'radial'),'ki21':(.13,.08,-.07,-.20,.10,.28,2,'radial'),'g4m':(.10,.07,-.08,-.20,.105,.28,2,'radial'),'g8n':(.13,.06,-.08,-.20,.11,.28,4,'radial'),'r2y':(.12,.03,-.12,-.22,.085,.30,2,'jet sideintake'),'t2':(.14,-.17,-.26,-.26,.07,.31,2,'jet sideintake'),'f1jp':(.14,-.17,-.26,-.26,.075,.31,2,'jet sideintake'),'f2jp':(.19,-.12,-.25,-.28,.078,.36,1,'jet chinintake lerx')}
    PROFILES.update(profiles)
    for k,raw in RESEARCH.items():
        if not k.startswith('air'):continue
        b=raw['branch'];t=raw['tier'];slug=raw['slug'];jet=raw['max_speed']>900
        template='air_us_0_5' if jet else 'air_us_4_3' if b==4 else 'air_us_0_2';d=copy.deepcopy(aircraft[template]);d.update(copy.deepcopy(raw));d.pop('fit',None)
        family='f15' if slug.startswith('f_15') else 'f4' if slug.startswith('f-4') else 'f86' if slug.startswith('f-86') else 'f2jp' if slug=='f_2a' else 'f1jp' if slug=='f1' else 't2' if slug=='t2' else 'a6m' if slug.startswith('a6m') else 'n1k' if slug.startswith('n1k') else 'j7w' if slug.startswith('j7w') else 'r2y' if slug.startswith('r2y') else next((p for p in ('ki10','ki27','ki43','ki84','ki61','ki100','ki45','ki102','ki109','ki21','g4m','g8n') if slug.replace('-','').replace('_','').startswith(p)),None)
        assert family,slug
        ALIASES.insert(0,(slug,family));d['model_family']=family
        guns=raw.get('guns',[]);caliber=re.search(r'(\d+(?:\.\d+)?) mm',guns[0]) if guns else None
        d.update(strike=slug in ('f1','f_2a'),country='jp',parent=f'air_jp_{b}_{t-1}' if t>1 else None,cost=0 if t==1 else int(100+raw['br']*40),ground_br=max(1.,raw['br']-1 if raw['br']>=10 else raw['br']),length=raw.get('Length',10),span=raw.get('Wingspan',12),speed=raw['max_speed']/3.6*8,turn=1800/max(8,raw.get('Turn time',20)),ammo=int(raw.get('Ammunition',600)),gun=bool(guns),forward_gun=b!=4 and bool(guns),defensive=b==4,defensive_gun=b==4,caliber=float(caliber[1]) if caliber else 7.7,belts=raw.get('belts') or ['Default'],missiles=6 if raw['missile_types'] else 0,bomb_count=6 if raw['bombs'] else 0,rocket_count=24 if raw['rockets'] else 0)
        fit=copy.deepcopy(raw['fit']);d['loadout']=fit;LOADOUTS[k]=fit;d['station_count']=len(fit['slots']);d['weapon_station_count']=len({i for w in fit['weapons'] for i in w['slots']})
        for w in fit['weapons']:
            if w['kind']=='aam' and w['short'].split()[0] not in d['missile_types']:d['missile_types'].append(w['short'].split()[0])
        radar='J/APG-2' if slug=='f_2a' else 'AN/APG-63(V)1' if slug=='f_15j_kai' else 'AN/APG-63 PSP' if slug=='f_15j' else 'AN/APG-66' if slug=='f-4ej_kai' else 'AN/APQ-120' if slug=='f-4ej' else 'J/AWG-11' if slug=='t2' else 'J/AWG-12' if slug=='f1' else 'AN/APG-30' if slug.startswith('f-86') else None
        if radar and radar not in RADARS:RADARS[radar]=RADARS['KLJ-10A' if radar=='J/APG-2' else 'AN/APG-63 PSP' if '63' in radar else 'AN/APG-68(V)7']
        FITS[d['name']]=radar;d['radar_model']=radar;d['radar_type']=TYPES[RADARS[radar][0]] if radar else TYPES['none'];d['radar']=bool(radar and RADARS[radar][0]!='ranging');d['sensor_note']=radar or '无搜索雷达'
        EQUIPMENT[k]=d['landing_equipment'];WARNINGS[k]=d['warning'];GROUND_AIR_BR[k]=d['ground_br'];aircraft[k]=d
