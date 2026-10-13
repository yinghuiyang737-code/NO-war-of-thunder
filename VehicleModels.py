import math
import pygame
# Silhouettes use measured-looking proportions, not engineering drawings.
# (half hull length, half width, turret type, turret offset, turret radius, barrel length)
SHAPES={
'M5A1':(39,20,'round',7,12,42),'Type 62':(43,21,'round',4,16,62),'PTL02':(48,22,'wheel',5,18,77),
'T-34-85':(47,24,'round',7,20,73),'Type 59':(47,24,'round',1,22,77),'Type 69':(48,24,'round',1,22,79),
'SU-76M':(40,19,'open',-13,16,59),'ISU-122':(53,26,'casemate',8,23,86),'IS-2':(53,25,'round',3,21,86),
'BT-5':(41,18,'round',8,11,40),'T-50':(39,20,'round',5,14,43),'PT-76B':(49,24,'round',3,16,59),
'T-34 (1941)':(46,24,'round',10,16,55),'T-54 (1947)':(47,24,'round',1,22,78),
'SU-85':(47,24,'casemate',8,21,71),
'Pz.II C':(36,19,'box',7,11,36),'Pz.III J':(43,22,'box',2,16,51),'Puma':(45,20,'wheel',2,14,44),
'Pz.IV F2':(45,24,'box',0,18,64),'Panther D':(53,26,'box',5,18,84),'Leopard 1':(51,25,'round',1,21,85),
'StuG III F':(43,22,'casemate',5,19,68),'Jagdpanzer IV':(45,24,'casemate',11,21,73),'Tiger H1':(51,28,'box',-1,22,74),
'M24':(42,21,'round',6,16,54),'M41A1':(46,23,'round',3,18,72),'M4A1':(44,24,'round',4,17,56),
'M4A3 (76) W':(45,24,'round',1,20,71),'M26':(50,25,'round',2,22,72),
'M10':(46,24,'open',0,20,73),'M36':(47,24,'open',-1,21,81),'T26E1-1':(51,25,'round',1,23,96),
'M46':(51,25,'round',1,22,78),'M48A1':(52,26,'round',0,24,77),'M60':(53,26,'round',0,24,85),
'M60A1 (AOS)':(54,26,'point',0,24,89),'M60A3 TTS':(54,26,'point',0,24,91),
'M1':(57,27,'abrams',-1,25,89),'M1A1':(58,27,'abrams',-1,26,94),'M1A2':(58,28,'abrams',-1,27,94),
'M1A2 SEP':(58,28,'abrams',-1,28,94),'M1A2 SEPv2':(58,28,'abrams',-1,28,95),'M1A2 SEPv3':(59,29,'abrams',-1,29,95),
'Leopard A1A1':(51,25,'round',1,22,85),'Leopard 1A5':(51,25,'box',1,22,85),'Leopard 2K':(55,27,'box',0,24,94),
'Leopard 2A4':(57,28,'box',0,27,94),'Leopard 2A5':(57,28,'wedge',0,28,94),'Leopard 2A6':(57,28,'wedge',0,28,106),'Leopard 2A7V':(59,29,'wedge',0,29,108),
'T-55A':(47,24,'round',1,22,78),'T-62':(49,25,'round',0,23,83),'T-64A':(48,24,'round',0,22,88),
'T-72A':(49,25,'round',0,23,90),'T-64B':(48,24,'round',0,23,89),'T-80B':(50,25,'round',0,23,90),
'T-80U':(50,26,'round',0,24,92),'T-72B3':(49,26,'round',0,24,91),'T-80BVM':(51,26,'round',0,24,92)}
NIGHT={'Type 62','PTL02','Type 59','Type 69','T-54 (1947)','T-55A','T-62','T-64A','T-72A','T-64B','T-80B','T-80U','T-72B3','T-80BVM','M46','M48A1','M60','M60A1 (AOS)','M60A3 TTS','M1','M1A1','M1A2','M1A2 SEP','M1A2 SEPv2','M1A2 SEPv3','Leopard 1','Leopard A1A1','Leopard 1A5','Leopard 2K','Leopard 2A4','Leopard 2A5','Leopard 2A6','Leopard 2A7V'}
THERMAL={'PTL02','M60A3 TTS','M1','M1A1','M1A2','M1A2 SEP','M1A2 SEPv2','M1A2 SEPv3','Leopard 1A5','Leopard 2A4','Leopard 2A5','Leopard 2A6','Leopard 2A7V','T-72B3','T-80BVM'}
STABLE={'Type 59','Type 69','PTL02','PT-76B','T-55A','T-62','T-64A','T-72A','T-64B','T-80B','T-80U','T-72B3','T-80BVM','M60A1 (AOS)','M60A3 TTS','M1','M1A1','M1A2','M1A2 SEP','M1A2 SEPv2','M1A2 SEPv3','Leopard A1A1','Leopard 1A5','Leopard 2K','Leopard 2A4','Leopard 2A5','Leopard 2A6','Leopard 2A7V'}
SINGLE={'M5A1','M24','M4A1','M4A3 (76) W','Type 59','PT-76B'}
DUAL={'Panther D','Tiger H1','M26','T26E1-1','M46','M48A1','M60','M60A1 (AOS)','M60A3 TTS','M1','M1A1','M1A2','M1A2 SEP','M1A2 SEPv2','M1A2 SEPv3','Leopard 1','Leopard A1A1','Leopard 1A5','Leopard 2K','Leopard 2A4','Leopard 2A5','Leopard 2A6','Leopard 2A7V'}
def configure_vehicle(v):
    name=v['name'];v['model']=SHAPES[name];v['mg']=name not in {'SU-76M','SU-85'}
    v['night']=name in NIGHT;v['thermal']=name in THERMAL;v['stabilizer']=1 if name in SINGLE else 2 if name in STABLE else 0
    v['dual']=name in DUAL;v['era']=name in {'T-64B','T-80B','T-80U','T-72B3','T-80BVM'}
    if name=='PT-76B':v['night']=True;v['stabilizer']=2;v['armor']=(13,13,6)
    if name=='T-54 (1947)':v['night']=False
    if name=='T-80U':v['thermal']=True
    v['mg_pen']=23 if name.startswith(('M1','M4','M6','T-6','T-7','T-8','Type')) or name in {'IS-2','ISU-122','M24','M26','M36','T26E1-1','M46','M48A1'} else 9
    if name=='Puma':v['armor']=(30,8,8)
    if name=='BT-5':v['armor']=(13,13,10)
    v['equipment']=[label for key,label in [('mg','机枪'),('night','夜视'),('thermal','热成像'),('dual','双流传动')] if v[key]]
    if v['stabilizer']:v['equipment'].append('单向稳定' if v['stabilizer']==1 else '双向稳定')
    if v['tier']>3:
        v['speed']=min(260,v['speed']);v['armor']=(min(410,100+(v['tier']-3)*30),min(110,50+v['tier']*3),40)
        v['pen']=min(620,160+(v['tier']-3)*42)
        if name.startswith('T-'):v['reverse']=45 if not name.startswith('T-80') else 68
        else:v['reverse']=130
    if name=='M1' or name.startswith('M1A'):v['color']=(170,157,117)
    if name.startswith('Leopard 2'):v['color']=(85,112,74)
def tone(c,f):return tuple(max(0,min(255,int(a*f))) for a in c)
from GroundModels import turret as turret_points, hull as hull_points, details as model_details, family as chassis_family

def draw_model(surface,v,center,scale=3.5,yaw=-15,top=False,turret_yaw=None,color=None):
    if v.get('reward_model') in ('LOSAT','Raketenautomat'):
        from NewRewardVehicles import draw_launcher
        return draw_launcher(surface,v,center,scale,yaw,top,turret_yaw,color)
    if v.get('modern_aa'):
        from ModernAirDefense import draw_model as modern_draw
        return modern_draw(surface,v,center,scale,yaw,top,turret_yaw,color)
    if v.get('split_system'):
        from SplitAirDefense import draw_model as draw_split
        return draw_split(surface,v,center,scale,yaw,top,turret_yaw,color)
    from ModelLayers import Draw,Point
    draw=Draw(top)
    c=color or v['color'];length,width,kind,offset,r,gun=v['model'];a=math.radians(yaw)
    def project(x,y,z=0,rotation=None):
        b=a if rotation is None else math.radians(rotation);rx=x*math.cos(b)-y*math.sin(b);ry=x*math.sin(b)+y*math.cos(b)
        draw.depth=z
        return Point(center[0]+(rx if top else (rx-ry)*.86)*scale,center[1]+(ry if top else (rx+ry)*.36-z*.84)*scale,z)
    def poly(points,z,color):draw.polygon(surface,color,[project(x,y,z) for x,y in points])
    def box(x0,x1,y0,y1,z0,z1,color):
        rotation=ta if z0>=36 else yaw
        points=[(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
        if not top:
            for i in sorted(range(4),key=lambda i:project(*points[i])[1]):
                j=(i+1)%4;draw.polygon(surface,tone(color,.7),[project(*points[i],z0),project(*points[j],z0),project(*points[j],z1),project(*points[i],z1)])
        draw.polygon(surface,color,[project(x,y,z1,rotation) for x,y in points])
    if not top:draw.ellipse(surface,(21,26,23),(center[0]-length*scale*1.5,center[1]-13*scale,length*scale*3,59*scale))
    for side in (-1,1):
        if v.get('wheel',kind=='wheel'):
            for x in (-length*.75,-length*.25,length*.25,length*.75):
                box(x-7,x+7,side*(width+1)-4,side*(width+1)+4,0,14,(35,39,34))
                if not top:
                    wheel=project(x,side*(width+6),7);draw.ellipse(surface,(24,29,28),(wheel[0]-7*scale,wheel[1]-6*scale,14*scale,12*scale));draw.ellipse(surface,tone(c,.73),(wheel[0]-3*scale,wheel[1]-3*scale,6*scale,6*scale))
        else:
            box(-length,length,side*(width+1)-4,side*(width+1)+4,0,13,(35,40,34))
            for x in range(-length,length,8):box(x,x+5,side*(width+1)-4,side*(width+1)+4,13,14,(77,80,66))
            if not top:
                count={'abrams':7,'leopard2':7,'leopard1':7,'tseries':6,'t34':5,'is':6,'panther':8,'pz4':8,'pz3':6,'sherman':6,'bradley':6,'bmp':6,'bmp3':6,'m113':5,'tiger':8}.get(chassis_family(v),6)
                for i in range(count):
                    x=-length+9+i*(length*2-18)/max(1,count-1)
                    wheel=project(x,side*(width+6),7)
                    draw.ellipse(surface,tone(c,.75),(wheel[0]-4*scale,wheel[1]-3*scale,8*scale,6*scale))
                    draw.ellipse(surface,(36,40,34),(wheel[0]-4*scale,wheel[1]-3*scale,8*scale,6*scale),max(1,int(scale*.4)))
    if not top:
        hp=hull_points(v)
        for i in sorted(range(len(hp)),key=lambda i:project(*hp[i])[1]):
            j=(i+1)%len(hp);draw.polygon(surface,tone(c,.72),[project(*hp[i],9),project(*hp[j],9),project(*hp[j],23),project(*hp[i],23)])
    poly(hull_points(v),23,c)
    poly(hull_points(v),26,tone(c,1.1))
    if kind in ('truck','halftrack'):
        box(length-29,length-4,-width+2,width-2,23,42,tone(c,.92))
        box(length-7,length-4,-width+5,width-5,33,39,(58,84,88))
    # Engine decks are drawn by the named chassis profile below.
    if v['tier']>=4:
        for side in (-1,1):box(-length+8,length-7,side*width-2,side*width+2,13,26,tone(c,.83))
    ta=yaw if turret_yaw is None else turret_yaw;points=turret_points(v)
    roof_height=v.get('turret_height',40 if kind not in ('casemate','open') else 37);gun_height=roof_height-7 if v.get('artillery') else 34
    base=[project(x,y,27,ta) for x,y in points];roof=[project(x*.94,y*.94,roof_height,ta) for x,y in points]
    if not top:
        for i in sorted(range(len(points)),key=lambda i:base[i][1]):draw.polygon(surface,tone(c,.72),(base[i],base[(i+1)%len(points)],roof[(i+1)%len(points)],roof[i]))
    draw.polygon(surface,tone(c,1.14),roof);draw.polygon(surface,tone(c,1.4),roof,max(1,int(scale*.25)))
    if kind=='open':draw.polygon(surface,(29,35,28),[project(x*.72,y*.72,38,ta) for x,y in points])
    if v.get('weapon')!='sam':
        count=v.get('barrels',1)
        for barrel in range(count):
            spacing=(barrel-(count-1)/2)*7
            draw.line(surface,(33,38,30),project(offset+12,spacing,gun_height,ta),project(gun,spacing,gun_height,ta),max(2,int(scale*(4 if count==1 else 2.4))))
            draw.line(surface,tone(c,1.2),project(offset+12,spacing,gun_height+1,ta),project(gun,spacing,gun_height+1,ta),max(1,int(scale*1.4)))
    if v.get('independent_missiles') or v.get('weapon')=='sam':
        for side in (-1,1):box(offset-12,offset+18,side*(r+4)-4,side*(r+4)+4,36,46,tone(c,.72))
    if v.get('aps'):
        for side in (-1,1):
            box(offset-17,offset-7,side*(r-2)-4,side*(r-2)+4,40,48,tone(c,.65))
            sensor=project(offset+17,side*(r-3),45,ta);draw.circle(surface,(78,117,123),sensor,max(2,int(scale*2)))
    if v.get('id')=='de_reward_maus':
        draw.line(surface,(45,49,38),project(offset+12,-10,gun_height,ta),project(gun*.63,-10,gun_height,ta),max(2,int(scale*2.3)))
    if v.get('id')=='us_reward_t58':
        draw.line(surface,tone(c,.6),project(offset-r,-r*.8,roof_height+1,ta),project(offset-r,r*.8,roof_height+1,ta),max(1,int(scale)))
        draw.circle(surface,tone(c,.6),project(offset,-r,roof_height*.85,ta),max(2,int(scale*4)))
    if v.get('grenade') and not v.get('id')=='de_reward_maus':
        for side in (-1,1):draw.line(surface,(35,42,31),project(length-16,side*(width-6),27),project(length+5,side*(width-6),27),max(2,int(scale*2)))
    if v.get('radar'):
        pole=project(offset-12,0,47,ta);dish=project(offset-12,0,65,ta)
        draw.line(surface,tone(c,.8),pole,dish,max(1,int(scale*1.4)))
        draw.ellipse(surface,tone(c,.65),(dish[0]-9*scale,dish[1]-4*scale,18*scale,8*scale),max(1,int(scale*1.3)))
    hatch=project(offset-7,-min(7,r*.40),roof_height+2,ta);draw.circle(surface,tone(c,.62),hatch,max(2,int(scale*5)))
    if v['era']:
        for x in range(-5,26,8):
            for side in (-1,1):box(x,x+6,side*(r-4)-3,side*(r-4)+3,41,45,tone(c,.85))
        for x in range(length-22,length-4,7):box(x,x+5,-width+3,width-3,27,30,tone(c,.85))
    if v['thermal']:box(offset-8,offset-1,-r+2,-r+9,40,48,tone(c,.75))
    if v['mg']:draw.line(surface,(25,29,24),project(offset-3,7,roof_height+6,ta),project(offset+20,7,roof_height+6,ta),max(1,int(scale*1.2)))
    if v['name'] in ('M1A2 SEPv2','M1A2 SEPv3'):
        box(offset-9,offset+1,6,14,41,51,tone(c,.85))
        draw.line(surface,(29,32,25),project(offset-3,10,51,ta),project(offset+21,10,51,ta),max(1,int(scale*1.5)))
    if v['name']=='M1A2 SEPv3':box(-36,-26,-r+4,r-4,29,36,tone(c,.78))
    if v['name']=='Leopard 2A7V':box(-length+4,-length+14,-width+4,width-4,26,33,tone(c,.87))
    if v['tier']>=6:draw.line(surface,(32,38,28),project(-12,12,42,ta),project(-12,12,61,ta),max(1,int(scale*.3)))

    model_details(v,poly,box,project,surface,scale,tone,c,ta,draw)

    if v['name'] in ('Pz.IV F2','Tiger H1','Panther D','Panther A','Panther F','IS-2','ISU-122','M4A3 (76) W','M10','M36','M26','T26E1-1'):
        draw.line(surface,tone(c,.78),project(gun-5,-3,35,ta),project(gun-5,3,35,ta),max(2,int(scale*3)))
        draw.line(surface,(35,43,36),project(gun-2,-3,35,ta),project(gun-2,3,35,ta),max(1,int(scale)))
    if kind=='round' and not v['name'].startswith('T-90M'):
        inner=[(offset+(x-offset)*.69,y*.69) for x,y in points]
        draw.polygon(surface,tone(c,1.22),[project(x,y,roof_height+.2,ta) for x,y in inner])

    if v.get('reward_model')=='T-72M2 Moderna':
        box(-12,18,17,22,41,46,tone(c,.75))
        draw.line(surface,(34,39,32),project(18,19,46,ta),project(69,19,46,ta),max(2,round(scale*2)))
        for side in (-1,1):
            for x in (-24,-14,-4,6,16):box(x,x+8,side*22-4,side*22+4,40,46,tone(c,.82))
        box(-16,-8,-10,-3,43,50,(64,102,105))
    draw.flush()
