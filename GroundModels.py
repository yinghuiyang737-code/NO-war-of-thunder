"""Named chassis/weapon structures; coordinates in VehicleModels' model units.
Variants share the real chassis but retain their turret, ERA, APS and gun fit.
"""
import math
GROUPS={
 'abrams':['M1','IPM1','M1A1','M1A1 HC','M1A2','M1A2 SEP','M1A2 SEPv2','M1A2 SEPv3','M1A2 (Trophy-HV)'],
 'leopard2':['Leopard 2K','Leopard 2AV','Leopard 2A4','Leopard 2A5','Leopard 2A6','Leopard 2A7V','Leopard 2 PSO','Leopard 2A7A1'],
 'leopard1':['Leopard 1','Leopard A1A1','Leopard 1A5','Gepard','Gepard 1A2'],
 'tseries':['Type 59','Type 69','Type 59D1','T-54 (1947)','T-55A','T-62','T-62M-1','T-64A','T-64B','T-72A','T-72B','T-72B (1989)','T-72B3','T-80B','T-80U','T-80BVM','T-90A','T-90M','T-90M (Arena-M)','BMPT','BMPT-72'],
 'chinese':['ZTZ88A','ZTZ88B','ZTZ96','ZTZ96A','ZTZ99-II','ZTZ99-III','ZTZ99A','MBT-2000','VT4A1'],
 't34':['T-34 (1941)','T-34-85','SU-85','SU-100'],
 'is':['IS-2','IS-3','ISU-122'],
 'panther':['Panther D','Panther A','Panther F','Jagdpanther'],
 'pz4':['Pz.IV F2','Jagdpanzer IV','Wirbelwind','Ostwind II'],
 'pz3':['Pz.III J','StuG III F'],
 'sherman':['M4A1','M4A3 (76) W','M4A3E2','M10','M36'],
 'patton':['M26','M46','M48A1','M60','M60A1 (AOS)','M60A3 TTS','M60A1 RISE (P)','T26E1-1','M247'],
 'bradley':['M3 Bradley','M3A3 Bradley','ADATS'],
 'bmp':['BMP-1','BMP-2','BMP-2M','ZBD86'],
 'bmp3':['BMP-3','2S38','ZBD04A'],
 'marder':['Marder 1A1','Begleitpanzer 57','TAM'],
 'pumaifv':['PUMA','PUMA VJTF'],
 'm113':['M901','M113A1 TOW','M163'],
 'mtlb':['Strela-10M'],
 'sam':['FlaRakPz 1','Tor-M1'],
 'truck':['FlaRakRad','Pantsir-S1','GAZ-AAA (4M)'],
 'halftrack':['M13 MGMC','M16 MGMC'],
 'wheeled':['Puma','PTL02','ZLT11','Radkampfwagen 90','M1128','LAV-AD','AFT09'],
 'sprut':['2S25','2S25M','PTZ89','Object 120'],
 'amphib':['PT-76B','Type 63'],
 'light':['M5A1','M24','M41A1','M551','HSTV-L','M10 Booker','Type 62','BT-5','T-50','Pz.II C','Wiesel 1A2'],
 'open':['SU-76M','ASU-85','M50','M56','M19A1','M42','ZSU-37','Flakpanzer I'],
 'zsu':['ZSU-57-2','ZSU-57-2 (GER)','ZSU-23-4','2S6 Tunguska','ZSD63','PGZ80','PGZ88','PGZ04A','PGZ09'],
 'jaguar':['Kanonenjagdpanzer','Raketenjagdpanzer 2','Jaguar 1'],
 'tiger':['Tiger H1'], 'support':['QN506','WZ141-1'],
}
FAMILIES={name:family for family,names in GROUPS.items() for name in names}
def family(v):return FAMILIES[v['name']]

# Width includes tracks/tyres. Hull length intentionally excludes the barrel.
# Planforms remain simplified drawings, not engineering/production blueprints.
DIMENSIONS={'abrams':(7.93,3.66),'leopard2':(7.72,3.75),'leopard1':(7.09,3.37),
 'tseries':(6.91,3.46),'chinese':(7.60,3.50),'t34':(6.68,3.00),'is':(6.90,3.09),
 'panther':(6.87,3.27),'pz4':(5.92,2.88),'pz3':(5.56,2.95),'sherman':(5.89,2.62),
 'patton':(6.95,3.63),'bradley':(6.55,3.60),'bmp':(6.74,2.94),'bmp3':(7.14,3.20),
 'marder':(6.79,3.24),'pumaifv':(7.60,3.90),'m113':(4.86,2.69),'mtlb':(6.45,2.85),
 'sam':(7.50,3.25),'truck':(10.00,2.55),'halftrack':(6.50,2.23),'wheeled':(7.00,2.80),
 'sprut':(7.07,3.15),'amphib':(6.91,3.14),'light':(5.30,2.60),'open':(5.50,2.70),
 'zsu':(6.50,3.20),'jaguar':(6.61,3.12),'tiger':(6.32,3.56),'support':(6.74,2.94)}
OVERRIDES={'M5A1':(4.84,2.29),'M24':(5.56,3.00),'M41A1':(5.82,3.20),'M551':(6.30,2.82),
 'BT-5':(5.58,2.23),'T-50':(5.20,2.47),'Pz.II C':(4.81,2.28),'Wiesel 1A2':(3.55,1.82),
 'Type 62':(5.58,2.85),'M50':(3.83,2.60),'M56':(4.56,2.57),'SU-76M':(4.88,2.73),
 'Puma':(6.80,2.33),'Pantsir-S1':(9.00,2.55),'FlaRakRad':(8.80,2.55),
 'GAZ-AAA (4M)':(5.34,2.04),'T-34 (1941)':(5.92,3.00),'T-34-85':(6.10,3.00),
 'T-54 (1947)':(6.04,3.27),'T-55A':(6.20,3.27),'Type 59':(6.04,3.27),'Type 69':(6.24,3.30),
 'T-62':(6.63,3.30),'T-62M-1':(6.63,3.30),'T-64A':(6.54,3.42),'T-64B':(6.54,3.42),
 'T-80B':(6.98,3.53),'T-80U':(7.00,3.60),'T-80BVM':(7.00,3.60),
 'M4A3E2':(5.89,2.75),'M10':(5.97,3.05),'M36':(5.97,3.05),'M26':(6.34,3.51),
 'T26E1-1':(6.34,3.51),'M46':(6.35,3.51),'M48A1':(6.88,3.63),
 'M1128':(6.95,2.72),'LAV-AD':(6.39,2.50),'ZSD63':(5.48,2.98),'Flakpanzer I':(4.42,2.06)}
def fit(v):
    n=v['name'];f=family(v);length,width=OVERRIDES.get(n,DIMENSIONS[f])
    # Tracks sit partly under the hull. The old 11-unit subtraction left the
    # hull too narrow and put oversized tracks entirely outside it.
    l,w,k,o,r,g=v['model'];nl=round(length*8/(2*.56)+3);nw=max(4,round(width*8/(2*.56)-5))
    ratio=nl/l;nr=max(6,round(min(r*ratio,nw+4)))
    v['model']=(nl,nw,k,round(o*ratio),nr,round(g*ratio))
    if f=='truck':v['wheel']=True
    v['visual_length_m']=length;v['visual_width_m']=width

def hull(v):
    l,w,kind,o,r,g=v['model'];f=family(v)
    # Physical hull envelope equals the established collision body rectangle.
    front=.94;rear=.96;bevel=.12
    if f in ('abrams','leopard2','chinese'):front=.78;rear=.97;bevel=.18
    elif f in ('tseries','t34','is','panther','amphib'):front=.75;rear=.84;bevel=.22
    elif f in ('bmp','bmp3','sprut'):front=.56;rear=.98;bevel=.25
    elif f in ('wheeled','light'):front=.71;rear=.79;bevel=.23
    elif f in ('sherman','patton'):front=.70;rear=.82;bevel=.19
    x=l-3
    return [(-x,-w*rear),(x*(1-bevel),-w),(x,-w*front),(x,w*front),(x*(1-bevel),w),(-x,w*rear)]

def turret(v):
    l,w,kind,o,r,g=v['model'];f=family(v);n=v['name']
    if f=='sph':
        rear=1.20 if n=='2S19M1' else 1.08 if n in ('PLZ05','PzH 2000') else 1.
        return [(o-r*rear,-r*.88),(o+r*.65,-r*.92),(o+r,-r*.58),(o+r,r*.58),(o+r*.65,r*.92),(o-r*rear,r*.88)]
    if kind in ('truck','halftrack','launcher'):
        return [(o-r*.8,-r*.65),(o+r*.7,-r*.65),(o+r*.7,r*.65),(o-r*.8,r*.65)]
    if kind in ('casemate','open'):
        if n in ('Wirbelwind','Ostwind II','ZSU-57-2','ZSU-57-2 (GER)'):
            return [(o+math.cos(i*math.pi/4)*r,math.sin(i*math.pi/4)*r) for i in range(8)]
        return [(o-r,-r*.85),(o+r*.60,-r),(o+r,-r*.62),(o+r,r*.62),(o+r*.60,r),(o-r,r*.85)]
    if f=='japan10':points=[(-1.05,-.70),(-.50,-.94),(.42,-.88),(1.08,-.25),(1.08,.25),(.42,.88),(-.50,.94),(-1.05,.70)]
    elif f=='japan90':points=[(-1.12,-.82),(.80,-.82),(1.02,-.52),(1.02,.52),(.80,.82),(-1.12,.82)]
    elif f=='japanearly':points=[(-.90,-.70),(.40,-.94),(.92,-.38),(.92,.38),(.40,.94),(-.90,.70)]
    elif f=='abrams':points=[(-1.15,-.72),(-.43,-1),( .50,-.91),(1.04,-.39),(1.04,.39),(.50,.91),(-.43,1),(-1.15,.72)]
    elif f=='leopard2':
        points=[(-1.08,-.85),(.14,-.97),(1.30,-.46),(1.01,0),(1.30,.46),(.14,.97),(-1.08,.85)] if kind=='wedge' else [(-1.08,-.92),(.70,-.92),(.96,-.52),(.96,.52),(.70,.92),(-1.08,.92)]
    elif f=='chinese':points=[(-1.0,-.75),(-.27,-1),( .55,-.93),(1.08,-.36),(1.08,.36),(.55,.93),(-.27,1),(-1,.75)] if n not in ('ZTZ88A','ZTZ88B') else None
    elif n.startswith('T-90M'):points=[(-1.10,-.78),(-.45,-.98),(.53,-.90),(1.03,-.40),(1.03,.40),(.53,.90),(-.45,.98),(-1.10,.78)]
    elif f in ('bradley','pumaifv','marder','bmp3','sprut'):points=[(-.85,-.73),(.42,-.88),(.94,-.32),(.91,.45),(.18,.79),(-.85,.60)]
    elif f=='pz4':points=[(-.93,-.76),(.40,-1),(.85,-.45),(.85,.45),(.40,1),(-.93,.76)]
    elif f=='pz3':points=[(-.84,-.74),(.30,-.89),(.89,-.43),(.89,.43),(.30,.89),(-.84,.74)]
    elif f=='panther':points=[(-.91,-.65),(.45,-.83),(1.02,-.55),(1.02,.55),(.45,.83),(-.91,.65)]
    elif f=='tiger':points=[(-.90,-.76),(.38,-.88),(.87,-.66),(.91,0),(.87,.66),(.38,.88),(-.90,.76),(-1.01,0)]
    elif n=='M4A1':points=[(-.85,-.57),(-.25,-.85),(.57,-.70),(1.,-.28),(1.,.28),(.57,.70),(-.25,.85),(-.85,.57)]
    elif f=='patton' and 'M60A' in n:points=[(-1.05,-.66),(-.26,-.95),(.52,-.72),(1.2,0),(.52,.72),(-.26,.95),(-1.05,.66)]
    elif f=='t34':points=[(-.92,-.62),(-.32,-.89),(.65,-.63),(1.0,-.32),(1.0,.32),(.65,.63),(-.32,.89),(-.92,.62)]
    else:points=None
    if points is None:
        # Rounded cast turrets retain a flat mantlet, not a circular disc.
        points=[(-.90,-.38),(-.65,-.76),(-.12,-.90),(.48,-.70),(.92,-.30),(.92,.30),(.48,.70),(-.12,.90),(-.65,.76),(-.90,.38)]
    return [(o+x*r,y*r) for x,y in points]

def details(v,poly,box,project,surface,scale,tone,c,ta,draw=None):
    import pygame
    draw=draw or pygame.draw
    l,w,kind,o,r,gun=v['model'];f=family(v);n=v['name']
    if f=='sph':
        for i in range(5):box(l*.2+i*3,l*.2+i*3+1,-w*.65,w*.2,28,29,tone(c,.48))
        box(-l*.9,-l*.75,-w*.65,w*.65,28,32,tone(c,.7))
        for side in (-1,1):box(o-r*1.05,o-r*.55,side*r*.65-3,side*r*.65+3,42,46,tone(c,.72))
        draw.line(surface,tone(c,.5),project(gun-4,-4,39,ta),project(gun-4,4,39,ta),max(2,int(scale*2)))
    # Glacis, engine cover and deck arrangement are chassis-specific.
    front_engine=f in ('bmp','bradley','marder','pumaifv','m113','support')
    ex=l*.52 if front_engine else -l*.57
    for x in range(int(ex-10),int(ex+12),3):draw.line(surface,tone(c,.42),project(x,-w*.55,28),project(x,w*.55,28),max(1,int(scale*.5)))
    poly([(l*.65,-w*.84),(l-3,-w*.60),(l-3,w*.60),(l*.65,w*.84)],27,tone(c,1.23))
    if f=='t34':
        for side in (-1,1):box(-l*.8,-l*.35,side*(w+2)-3,side*(w+2)+3,28,34,tone(c,.78))
    if f=='is' and n=='IS-3':poly([(l*.36,-w),(l-3,0),(l*.36,w),(l*.57,0)],28,tone(c,1.4))
    if f=='sherman':
        for side in (-1,1):box(l*.22,l*.47,side*w*.57-5,side*w*.57+5,27,34,tone(c,1.15))
    if f in ('abrams','leopard2','chinese') or n.startswith('T-90M'):
        for side in (-1,1):
            for x in (-.65,-.15,.35):box(o+x*r,o+(x+.37)*r,side*r*.75-3,side*r*.75+3,41,45,tone(c,.83))
    if v.get('era'):
        for side in (-1,1):
            for i in range(4):
                x=o+r*(.12+i*.20);y=side*r*(.80-i*.13)
                draw.polygon(surface,tone(c,.77),[project(x-3,y-3,43,ta),project(x+3,y-3,43,ta),project(x+3,y+3,43,ta),project(x-3,y+3,43,ta)])
    if f in ('bmp','bmp3','bradley','marder','pumaifv','m113'):
        for side in (-1,1):
            for x in (-l*.7,-l*.4):box(x-4,x+4,side*w*.45-4,side*w*.45+4,28,29,tone(c,.72))
        box(-l+4,-l+7,-w*.73,w*.73,24,28,tone(c,.55))
    if n in ('BMPT','BMPT-72','QN506'):
        for side in (-1,1):
            for dy in (-3,3):box(o-13,o+16,side*(r+3)+dy-2,side*(r+3)+dy+2,41,49,(69,79,65))
    if n=='M50':
        for side in (-1,1):
            for dy in (-5,0,5):draw.line(surface,(47,56,45),project(-14,side*13+dy,41,ta),project(gun,side*13+dy,41,ta),max(2,int(scale*3)))
    if n in ('Gepard','Gepard 1A2','2S6 Tunguska'):
        for side in (-1,1):draw.line(surface,(38,47,40),project(o+3,side*r*.85,38,ta),project(gun,side*r*.85,38,ta),max(2,int(scale*3)))
    if n in ('Tor-M1','Strela-10M','FlaRakPz 1','M901','ADATS','Pantsir-S1','FlaRakRad'):
        tubes=4 if n in ('ADATS','Pantsir-S1') else 2
        for side in (-1,1):
            for i in range(tubes):box(o-r*.8,o+r*.7,side*(r*.65+i*3)-2,side*(r*.65+i*3)+2,43,47,tone(c,.66))
    if f=='truck':
        box(l*.48,l*.91,-w*.9,w*.9,26,45,tone(c,.93));box(l*.82,l*.94,-w*.75,w*.75,36,42,(56,91,106))
