"""Country helicopter branches with explicit simplified flight and weapon fits."""
import copy,math
import pygame
from pygame.math import Vector2 as V
UNITS={
'us':[('AH-1G','ah_1g',277,13.4,13.4,8.3,'cobra','',0,7.62),('AH-64D','ah_64d',279,17.7,14.6,12.0,'apache','AGM-114K Hellfire',16,30)],
'ussr':[('Mi-4AV','mi_4av',185,16.8,21,8.3,'mi4','9M17M Falanga',4,12.7),('Ka-52','ka_52',300,16,14.5,12.0,'kamov','9K127 Vikhr',12,30)],
'de':[('BO 105 PAH-1','bo_105pah1',242,11.9,9.8,9.3,'bo105','HOT',6,0),('EC-665 Tiger UHT','tiger_uht',290,15.8,13,12.0,'tiger','HOT-3',8,0)],
'cn':[('Z-9W','z_9w',280,13.5,11.9,9.3,'z9','HJ-8',4,0),('Z-10','z_10',300,14.2,13,12.0,'z10','AKD-10',8,23)],
'jp':[('UH-1B','uh_1b',204,12.7,14.6,8.0,'huey','',0,7.62),('AH-64DJP','ah_64d_japan',295,17.7,14.6,11.7,'apache','AGM-114K Hellfire',16,30)]}
# Existing IDs 1 and 2 stay unchanged for saved vehicles and loadouts.
EXTRA={
'us':[('AH-1F','ah_1f',277,13.4,13.4,9.7,'cobra','TOW-2',8,20),('AH-64A','ah_64a',279,17.7,14.6,11.0,'apache','AGM-114B Hellfire',16,30)],
'ussr':[('Mi-24V','mi_24v',335,17.5,17.3,10.0,'hind','9M114 Shturm',8,12.7),('Mi-28N','mi_28n',300,17,17.2,11.3,'havoc','9M120 Ataka',16,30)],
'de':[('BO 105 PAH-1A1','bo_105pah1a1',242,11.9,9.8,9.7,'bo105','HOT-2',6,0),('Mi-24P (Germany)','mi_24p_german',335,17.5,17.3,10.3,'hind','9M114 Shturm',8,30)],
'cn':[('Z-9WA','z_9wa',280,13.5,11.9,10.3,'z9','HJ-8H',8,0),('Z-19','z_19',280,12,11.9,11.3,'z19','AKD-9',8,0)],
'jp':[('AH-1S early','ah_1s_early',277,13.4,13.4,9.3,'cobra','BGM-71C TOW',8,20),('AH-1S','ah_1s_late',277,13.4,13.4,9.7,'cobra','TOW-2',8,20)]}
IDS={}
def register(aircraft):
    from Aviation import AIR_BRANCHES
    from AircraftLandingEquipment import EQUIPMENT
    from AircraftLoadoutData import DATA
    from AircraftWarningData import DATA as WARNING_DATA
    for country,old in UNITS.items():
        AIR_BRANCHES[country]=list(AIR_BRANCHES[country])+['直升机']
        parent=country+'_1_3';IDS[country]=[]
        template=next(v for v in aircraft.values() if v['country']==country and v['branch']==3)
        ordered=[(1,old[0]),(3,EXTRA[country][0]),(4,EXTRA[country][1]),(2,old[1])]
        for stage,(number,unit) in enumerate(ordered,1):
            name,slug,speed,length,rotor,br,shape,missile,amount,caliber=unit
            ident='heli_'+country+'_'+str(number);d=copy.deepcopy(template)
            modern=shape in ('apache','kamov','havoc','tiger','z19','z10')
            d.update(id=ident,name=name,slug=slug,source='https://wiki.warthunder.com/unit/'+slug,country=country,branch=5,tier=stage,parent=parent,cost=300 if stage==1 else 420+stage*100,rank='V' if stage==1 else 'VII' if stage==4 else 'VI',br=br,ground_br=br,helicopter=True,heli_shape=shape,model_family='helicopter',max_speed=speed,speed=speed/3.6*8,turn=70.,length=length,Length=length,span=rotor,Wingspan=rotor,ammo=1200 if caliber else 0,gun=bool(caliber),caliber=caliber,defensive=False,forward_gun=bool(caliber),defensive_gun=False,bombs=False,bomb_count=0,rockets=True,rocket_count=38,missiles=0,missile_types=[],countermeasures=stage>1,radar=False,radar_model=None,radar_type='无搜索雷达',belts=['Default','Ground targets','Universal'],simulation=True)
            d['warning']={'rwr':None,'maw':modern,'cm':{'flare':stage>1,'chaff':stage>1},'source':d['source']};WARNING_DATA[ident]=d['warning']
            equip={'airbrake':False,'chute':False,'hook':False,'source':d['source'],'checked':'2026-10-11'};EQUIPMENT[ident]=equip;d['landing_equipment']=equip
            main=list(range(4));count=6 if modern else 4
            slots=[{'side':(-1 if i<2 else 1) if i<4 else (-1 if i==4 else 1),'source_slot':i+1} for i in range(count)]
            def weapon(label,kind,quantity,guidance='',mm=70,points=None,mass=100):
                return dict(name=label,short=label,count=quantity,kind=kind,mass=float(mass),countermeasures=0,guidance=guidance,explosive=4.5 if kind=='agm' else 1.,caliber=mm,params={'Maximum speed':'600 m/s','Ammunition':'300'},slots=main if points is None else points)
            weapons=[]
            if missile:
                guide='SACLOS wire' if any(k in missile for k in ('HOT','TOW','HJ-8')) else 'SACLOS radio' if missile in ('9M17M Falanga','9M114 Shturm','9M120 Ataka') else 'Laser beam riding' if 'Vikhr' in missile else 'SALH laser'
                points=[0,3] if amount==6 else main;quantity=3 if amount==6 else max(1,amount//4)
                weapons.append(weapon(missile,'agm',quantity,guide,152,points))
                alternatives={'AH-64D':('AGM-114B Hellfire','SALH laser'),'AH-64DJP':('AGM-114B Hellfire','SALH laser'),'Z-9WA':('AKD-9','SALH laser'),'Z-10':('AKD-9','SALH laser'),'Ka-52':('9M120 Ataka','SACLOS radio'),'EC-665 Tiger UHT':('PARS-3 LR','IIR fire-and-forget')}
                if name in alternatives:
                    label,guidance=alternatives[name];weapons.append(weapon(label,'agm',quantity,guidance,152,points))
            if shape in ('hind','havoc','kamov','mi4'):
                weapons+= [weapon('S-5K','rocket',32,'',57),weapon('S-8KO','rocket',20,'',80)]
                if shape in ('havoc','kamov'):weapons.append(weapon('S-13OF','rocket',5,'',122))
            elif country=='cn':
                weapons += [weapon('Type 90-1','rocket',7,'',90),weapon('Type 57-1','rocket',18,'',57)]
            else:weapons += [weapon('Hydra-70 M247','rocket',19,'',70),weapon('FFAR Mighty Mouse','rocket',7,'',70)]
            aam=None
            if country=='cn':aam='TY-90'
            elif shape in ('hind',):aam='R-60M'
            elif shape in ('kamov','havoc'):aam='9M39 Igla'
            elif shape in ('apache','tiger'):aam='FIM-92 Stinger'
            if aam:
                weapons.append(weapon(aam,'aam',4 if country=='cn' else 2,'IR',90,list(range(4,count)) if count>4 else [0,3],70));d['missile_types']=[aam]
            if shape in ('huey','cobra','bo105','z9','tiger'):
                label='M3P gun pod' if shape in ('bo105','tiger') else 'M18A1 gun pod'
                weapons.append(weapon(label,'gunpod',1,'',12.7 if shape in ('bo105','tiger') else 7.62,mass=150))
            if number in (1,2):
                primary=[w for w in weapons if w['kind']=='agm'][:1]
                rocket=[w for w in weapons if w['kind']=='rocket'][:1]
                first=primary+rocket;weapons=first+[w for w in weapons if w not in first]
            fit=dict(slots=slots,weapons=weapons,presets=[],maximum=2200 if modern else 1500,wing_max=0,imbalance=0,source=d['source']);DATA[ident]=fit;d['loadout']=fit;d['station_count']=d['weapon_station_count']=count
            apply_wt_fit(d,fit)
            aircraft[ident]=d;IDS[country].append(ident);parent=ident

def apply_wt_fit(d,fit):
    from HelicopterLoadoutData import DATA
    actual=copy.deepcopy(DATA[d['name']]);legacy=copy.deepcopy(fit['weapons'])
    def code(w):
        text=w['short'].upper().replace(' ', '').replace('-', '')
        for token in ('HELLFIREII','HELLFIRE','AIRTOGROUNDMISSILES','AIRTOAIRMISSILES','MISSILES','ROCKETS'):text=text.replace(token,'')
        return text
    replacements=[]
    for old in legacy:
        pool=[w for w in actual['weapons'] if w['kind']==old['kind']]
        matches=[w for w in pool if code(old) in code(w) or code(w) in code(old)]
        if not matches:matches=pool
        if matches:
            chosen=min(matches,key=lambda w:abs(w['count']-old['count']))
            replacements.append(copy.deepcopy(chosen))
        else:
            old['slots']=[];replacements.append(old)
    for weapon in actual['weapons']:
        if not any(w['name']==weapon['name'] and w['count']==weapon['count'] and w['slots']==weapon['slots'] for w in replacements):replacements.append(weapon)
    fit.update(slots=actual['slots'],weapons=replacements,maximum=actual['maximum'],source=actual['source'],revision=1,legacy_station_count=len(fit['slots']))
    d['source']=actual['source'];d['station_count']=len(fit['slots']);d['weapon_station_count']=len({slot for w in replacements if w['kind']!='pod' for slot in w['slots']})
    d['missile_types']=list(dict.fromkeys(w['short'].split()[0] for w in replacements if w['kind']=='aam' and w['slots']))
    d['bombs']=any(w['kind']=='bomb' and w['slots'] for w in replacements)
    d['rockets']=any(w['kind']=='rocket' and w['slots'] for w in replacements)


def parts(d):
    shape=d['heli_shape'];wide=.17 if shape in ('mi4','huey','hind') else .11
    body=[(.45,0),(.33,-wide),(-.15,-wide),(-.3,-.065),(-.3,.065),(-.15,wide),(.33,wide)]
    out=[('fuselage',body),('tail',[(-.2,-.03),(-.52,-.025),(-.52,.025),(-.2,.03)])]
    if shape not in ('mi4','huey','bo105'):
        out += [('wing',[(-.02,.08*s),(-.08,.24*s),(-.18,.24*s),(-.13,.08*s)]) for s in (-1,1)]
    out += [('tail',[(-.42,-.12),(-.49,-.12),(-.49,.12),(-.42,.12)])]
    return out

def draw(s,d,center,scale,yaw,color,units,bank):
    c=color or (132,149,113);origin=V(center)
    def pt(x,y):return origin+V(x*d['length']*units,y*d['span']*units).rotate(yaw)*scale
    for kind,shape in parts(d):
        points=[pt(*v) for v in shape];pygame.draw.polygon(s,c,points);pygame.draw.polygon(s,(42,55,44),points,max(1,round(scale)))
    pygame.draw.polygon(s,(61,101,112),[pt(.12,-.085),pt(.32,-.075),pt(.4,0),pt(.32,.075),pt(.12,.085)])
    for side in (-1,1):
        pygame.draw.line(s,(42,48,43),pt(-.24,side*.1),pt(.24,side*.1),max(1,round(scale*units*.5)))
        if d['heli_shape'] not in ('mi4','huey','bo105'):pygame.draw.ellipse(s,(57,68,52),(pt(-.1,side*.09).x-3*scale,pt(-.1,side*.09).y-5*scale,10*scale,7*scale))
    hub=pt(-.04,0);radius=d['span']*units*scale*.5;angle=pygame.time.get_ticks()*.5
    blades={'cobra':2,'huey':2,'mi4':4,'apache':4,'kamov':3,'bo105':4,'tiger':4,'z9':4,'z10':4,'z19':4,'hind':5,'havoc':5}[d['heli_shape']]
    rotors=2 if d['heli_shape']=='kamov' else 1
    for layer in range(rotors):
        for i in range(blades):
            direction=V(1,0).rotate(angle*(1 if layer==0 else -1)+i*360/blades)
            pygame.draw.line(s,(163,171,153),hub+direction*radius*.12,hub+direction*radius,max(1,round(scale*units*.35)))
    pygame.draw.circle(s,(58,70,56),hub,max(2,round(scale*units*.65)))
    if rotors==1:
        tail=pt(-.5,0);pygame.draw.line(s,(166,173,155),tail+V(0,-radius*.1).rotate(yaw+angle),tail+V(0,radius*.1).rotate(yaw+angle),max(1,round(scale)))
