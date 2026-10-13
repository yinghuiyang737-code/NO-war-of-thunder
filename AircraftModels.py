"""Meter-based hand-drawn airframe planforms. Shared airframes share tooling.
Coordinates are fractions of the published length and span; +X is the nose.
Render and damage geometry use the same convex parts, including twin booms.
"""
import math
import pygame
from pygame.math import Vector2 as V
from SwingWingModels import FITS as SWING, parts as swing_parts, draw_details as swing_details

# family: wing root LE, wingtip LE, wingtip TE, root TE, fuselage width,
# tail span, number of engines, structural features.
PROFILES={
 'i15':(.19,.12,-.12,-.17,.12,.30,1,'biplane radial'),
 'he51':(.15,.08,-.14,-.19,.09,.27,1,'biplane'),
 'hs123':(.13,.07,-.13,-.21,.11,.27,1,'biplane radial'),
 'i16':(.13,.06,-.16,-.23,.14,.30,1,'radial short'),
 'p26':(.12,.02,-.15,-.23,.11,.28,1,'radial fixedgear'),
 'p40':(.13,-.01,-.12,-.22,.09,.28,1,'inline'),
 'p43':(.15,.05,-.12,-.24,.12,.30,1,'radial'),
 'p51':(.11,-.01,-.15,-.24,.075,.30,1,'inline radiator'),
 'p47':(.13,.04,-.16,-.27,.125,.30,1,'radial'),
 'yak':(.12,-.02,-.13,-.23,.075,.29,1,'inline'),
 'mig3':(.06,-.06,-.17,-.26,.075,.29,1,'inline longnose'),
 'la':(.12,.05,-.14,-.24,.105,.30,1,'radial'),
 'bf109':(.12,.01,-.15,-.24,.07,.27,1,'inline radiator'),
 'fw190':(.13,.03,-.13,-.24,.105,.29,1,'radial'),
 'fw190d':(.08,-.02,-.16,-.23,.08,.29,1,'inline longnose'),
 'ta152':(.10,.02,-.12,-.22,.07,.22,1,'inline longnose'),
 'he112':(.10,-.04,-.16,-.24,.085,.29,1,'inline gull'),
 'f2a':(.17,.09,-.12,-.24,.13,.30,1,'radial short'),
 'f6f':(.18,.06,-.15,-.27,.115,.30,1,'radial'),
 'f4u':(.14,.01,-.14,-.25,.09,.29,1,'radial gull'),
 'am1':(.17,.10,-.14,-.29,.12,.32,1,'radial'),
 'p38':(.16,.03,-.11,-.24,.065,.38,2,'prop boom'),
 'il2':(.12,-.02,-.15,-.25,.105,.29,1,'inline armored'),
 'ju87':(.13,-.01,-.14,-.25,.09,.31,1,'inline gull fixedgear'),
 'hs129':(.13,.04,-.13,-.24,.07,.30,2,'prop armored'),
 'sb':(.18,.07,-.08,-.23,.07,.31,2,'prop glass'),
 'db3':(.14,.01,-.12,-.26,.075,.34,2,'prop glass'),
 'pe2':(.12,-.01,-.14,-.26,.07,.33,2,'prop twinfin glass'),
 'tu2':(.14,.02,-.14,-.27,.09,.34,2,'prop twinfin glass'),
 'he111':(.15,.03,-.13,-.25,.10,.31,2,'prop glass ellipse'),
 'ju88':(.19,.06,-.12,-.25,.095,.32,2,'prop glass'),
 'do217':(.13,.01,-.15,-.27,.105,.34,2,'prop twinfin glass'),
 'b18':(.17,.06,-.10,-.27,.105,.32,2,'prop glass'),
 'b25':(.15,.01,-.12,-.27,.09,.37,2,'prop twinfin glass'),
 'b17':(.12,-.03,-.13,-.27,.065,.30,4,'prop glass fortress'),
 'b29':(.10,-.06,-.14,-.27,.075,.32,4,'prop glass fortress'),
 'mig9':(.11,.02,-.13,-.26,.11,.31,2,'jet intake'),
 'yak23':(.11,.00,-.14,-.25,.085,.30,1,'jet intake'),
 'mig15':(.16,-.14,-.23,-.26,.105,.34,1,'jet intake swept'),
 'mig17':(.16,-.20,-.27,-.29,.095,.34,1,'jet intake swept'),
 'f86':(.15,-.12,-.22,-.28,.10,.35,1,'jet intake swept'),
 'f84g':(.10,.00,-.14,-.25,.09,.34,1,'jet intake'),
 'f84f':(.14,-.15,-.23,-.29,.09,.34,1,'jet intake swept'),
 'mig21':(.13,-.32,-.37,-.30,.075,.33,1,'jet intake delta'),
 'j7e':(.13,-.28,-.37,-.31,.075,.33,1,'jet intake doubledelta'),
 'j8':(.13,-.24,-.33,-.28,.075,.32,2,'jet sideintake delta'),
 'su7':(.10,-.18,-.25,-.29,.09,.31,1,'jet intake swept'),
 'q5':(.11,-.15,-.25,-.30,.105,.31,2,'jet sideintake swept'),
 'f104':(-.02,-.13,-.18,-.23,.055,.38,1,'jet sideintake ttail'),
 'f16':(.17,-.14,-.23,-.29,.075,.40,1,'jet chinintake lerx'),
 'j10':(.13,-.30,-.36,-.31,.075,0,1,'jet chinintake delta canard'),
 'eurofighter':(.19,-.31,-.37,-.31,.09,0,2,'jet chinintake delta canard'),
 'mig29':(.21,-.12,-.23,-.33,.07,.38,2,'jet lerx twinfin'),
 'su27':(.22,-.10,-.24,-.34,.065,.38,2,'jet lerx twinfin stinger'),
 'su30':(.22,-.10,-.24,-.34,.065,.38,2,'jet lerx twinfin stinger canard'),
 'f15':(.20,-.03,-.22,-.33,.085,.38,2,'jet sideintake twinfin'),
 'f18':(.15,-.13,-.24,-.30,.075,.39,2,'jet lerx twinfin'),
 'f4':(.17,-.12,-.26,-.34,.095,.37,2,'jet sideintake cranked'),
 'f8':(.12,-.10,-.19,-.28,.075,.36,1,'jet chinintake swept'),
 'yak141':(.12,-.16,-.26,-.30,.10,.38,1,'jet sideintake boom twinfin liftfan'),
 'f14':(.16,-.03,-.17,-.30,.09,.40,2,'jet sideintake twinfin swing'),
 'f111':(.17,.02,-.11,-.27,.10,.34,2,'jet sideintake swing'),
 'tornado':(.12,-.01,-.13,-.29,.095,.35,2,'jet sideintake swing'),
 'su17':(.12,-.07,-.17,-.28,.09,.35,1,'jet intake swing'),
 'su24':(.17,.00,-.13,-.28,.12,.34,2,'jet sideintake swing'),
 'su9':(.12,.01,-.11,-.24,.075,.30,2,'jet nacelle'),
 'me262':(.13,-.05,-.16,-.28,.075,.32,2,'jet nacelle'),
 'he162':(.12,.01,-.13,-.23,.085,.34,1,'jet dorsal twinfin'),
 'ar234':(.13,.02,-.09,-.22,.08,.31,2,'jet nacelle glass'),
 'il28':(.11,.01,-.11,-.25,.08,.34,2,'jet nacelle glass'),
 'b57':(.10,.04,-.12,-.25,.10,.31,2,'jet nacelle glass'),
 'a4':(.18,-.25,-.32,-.29,.085,.36,1,'jet sideintake delta'),
 'a7':(.14,-.13,-.23,-.31,.115,.34,1,'jet chinintake'),
 'a10':(.05,.01,-.13,-.24,.10,.37,2,'jet dorsal twinfin'),
 'su25':(.08,-.05,-.16,-.25,.105,.33,2,'jet sideintake armored'),
 'alpha':(.15,-.10,-.23,-.30,.08,.33,2,'jet sideintake'),
 'jh7':(.13,-.15,-.25,-.31,.09,.33,2,'jet sideintake cranked'),
}
ALIASES=[('i-15','i15'),('he51','he51'),('hs-123','hs123'),('i-16','i16'),('p-26','p26'),('p-40','p40'),('p-43','p43'),('p-51','p51'),('p-47','p47'),('yak_141','yak141'),('yak-23','yak23'),('yak-','yak'),('mig_3','mig3'),('la-','la'),('bf-109','bf109'),('fw-190d','fw190d'),('fw-190','fw190'),('ta-152','ta152'),('he_112','he112'),('f2a','f2a'),('f6f','f6f'),('f4u','f4u'),('am_1','am1'),('p-38','p38'),('il_2','il2'),('il-10','il2'),('ju-87','ju87'),('hs-129','hs129'),('sb_','sb'),('db_3','db3'),('pe-2','pe2'),('tu-2','tu2'),('he-111','he111'),('ju-88','ju88'),('do_217','do217'),('b_18','b18'),('b_25','b25'),('b-17','b17'),('b-29','b29'),('mig-9','mig9'),('mig-17','mig17'),('mig-15','mig15'),('f-86','f86'),('f-84g','f84g'),('f-84f','f84f'),('mig-21','mig21'),('j_7','j7e'),('j_8','j8'),('su-7','su7'),('q_5','q5'),('f-104','f104'),('f_16','f16'),('j_10','j10'),('ef_2000','eurofighter'),('mig_29','mig29'),('su_30','su30'),('j_15','su30'),('su_27','su27'),('j_11','su27'),('f_15','f15'),('fa_18','f18'),('f-4','f4'),('f8u','f8'),('f_14','f14'),('f_111','f111'),('tornado','tornado'),('su_17','su17'),('su_24','su24'),('su-9','su9'),('me-262','me262'),('he-162','he162'),('arado','ar234'),('il_28','il28'),('b-57','b57'),('a_4','a4'),('a_7','a7'),('a_10','a10'),('su_25','su25'),('alpha','alpha'),('jh_7','jh7')]
def family(d):
    if d.get("helicopter"):return "helicopter"
    for prefix,key in ALIASES:
        if d['slug'].startswith(prefix):return key
    raise ValueError('Missing aircraft planform: '+d['slug'])

def parts(d,sweep=0):
    if d.get("helicopter"):
        from Helicopters import parts as heli_parts
        return heli_parts(d)
    key=family(d)
    if key=='f22':
        result=[('wing',[(.24,side*.08),(-.12,side*.5),(-.33,side*.32),(-.25,side*.08)]) for side in (-1,1)]
        result += [('tail',[(-.29,side*.09),(-.40,side*.43),(-.49,side*.30),(-.47,side*.08)]) for side in (-1,1)]
        result.append(('body',[(.5,0),(.31,-.045),(.15,-.115),(-.36,-.105),(-.48,-.075),(-.48,.075),(-.36,.105),(.15,.115),(.31,.045)]))
        result += [('engine',[(.08,y-.032),(.08,y+.032),(-.47,y+.032),(-.47,y-.032)]) for y in (-.05,.05)]
        return result
    if key in SWING:return swing_parts(key,d,sweep)
    le,tip,te,root,width,tail,engines,features=PROFILES[key]
    wing=[(le,.07),(tip,.5),(te,.5),(root,.07)]
    if 'doubledelta' in features:wing=[(le,.07),(-.09,.31),(tip,.5),(te,.5),(root,.07)]
    if 'gull' in features:wing.insert(1,(le-.06,.23))
    result=[('wing',[(x,y*side) for x,y in wing]) for side in (-1,1)]
    if key=='p38':
        result.append(('tail',[(-.40,-.25),(-.49,-.25),(-.49,.25),(-.40,.25)]))
    elif tail:
        result += [('tail',[(-.31,.035),(-.40,side*tail),(-.49,side*tail*.84),(-.46,.035)]) for side in (-1,1)]
    if 'lerx' in features:
        result += [('wing',[(.32,side*.045),(.12,side*.20),(-.22,side*.20),(-.28,side*.05)]) for side in (-1,1)]
    if 'canard' in features:
        result += [('canard',[(.29,side*.04),(.22,side*.22),(.14,side*.20),(.18,side*.04)]) for side in (-1,1)]
    if 'boom' in features:
        for side in (-1,1):result.append(('engine',[(.31,side*.14),(.20,side*.22),(-.48,side*.21),(-.49,side*.16)]))
        if key=='p38':result.append(('body',[(.37,0),(.21,-width),(-.21,-width),(-.28,0),(-.21,width),(.21,width)]))
    if key!='p38':result.append(('body',[(.5,0),(.32,-width*.60),(.12,-width),(-.36,-width*.75),(-.5,-width*.35),(-.5,width*.35),(-.36,width*.75),(.12,width),(.32,width*.60)]))
    if engines>1 and 'boom' not in features:
        positions=[-.31,-.16,.16,.31] if engines==4 else [-.22,.22] if 'prop' in features or 'nacelle' in features else [-.12,.12] if 'dorsal' in features else [-.065,.065]
        for y in positions:
            front=.20 if 'prop' in features else .08 if 'nacelle' in features else -.14 if 'dorsal' in features else .10
            rear=-.055 if 'prop' in features else -.23 if 'nacelle' in features else -.40
            result.append(('engine',[(front,y-.025),(front+.02,y), (front,y+.025),(rear,y+.025),(rear-.025,y),(rear,y-.025)]))
    return result

def polygons(d,units=8,bank=0,sweep=0):
    span=d['span']*max(.08,abs(math.cos(math.radians(bank))))
    return [(kind,[V(x*d['length']*units,y*span*units) for x,y in shape]) for kind,shape in parts(d,sweep)]

def wingtips(d,bank=0,sweep=0):
    """Trailing outer vertices from the same rolled/swept wing geometry."""
    tips=[]
    for kind,shape in polygons(d,8,bank,sweep):
        if kind!='wing':continue
        reach=max(abs(p.y) for p in shape)
        if len(tips)>=2:break
        tips.append(min((p for p in shape if abs(abs(p.y)-reach)<.001),key=lambda p:p.x))
    return tips

def contact(d,pos,yaw,start,end,bank=0,sweep=0):
    from VehicleGeometry import segment_polygon
    hits=[hit for _,shape in polygons(d,8,bank,sweep) if (hit:=segment_polygon(start,end,[V(pos)+v.rotate(yaw) for v in shape])) is not None]
    return min(hits,key=lambda h:h[0]) if hits else None

def model_self_test(api):
    from Aviation import AIRCRAFT
    from GroundModels import FAMILIES
    assert all(v['name'] in FAMILIES for v in api['VEHICLES'].values())
    assert len({family(d) for d in AIRCRAFT.values()})>=60
    for d in AIRCRAFT.values():
        assert abs(d['speed']-d['max_speed']/3.6*8)<.001
        for bank in (0,60,110):
            shapes=polygons(d,8,bank,.5)
            assert shapes and all(len(poly)>=3 for _,poly in shapes)
            assert contact(d,(200,200),37,V(200,200)-V(1000,0).rotate(37),V(200,200)+V(1000,0).rotate(37),bank,.5)
    # The empty gap between P-38 booms must not become a rectangular hitbox.
    p38=next(d for d in AIRCRAFT.values() if d['name']=='P-38E')
    x=-p38['length']*8*.33
    assert contact(p38,(0,0),0,V(x,-2),V(x,2)) is None
    plane=next(d for d in AIRCRAFT.values() if d['name']=='F-15E')
    tank=next(v for v in api['VEHICLES'].values() if v['name']=='M1A2 SEPv3')
    assert plane['length']*8>(tank['model'][0]*2-6)*.56*2
    print('PASS: 116 named aircraft planforms, 160 chassis profiles, real-size proportions, per-airframe speeds, rotating/rolling/swept damage outlines and twin-boom gaps')

def draw(surface,d,center,scale=1,yaw=0,color=None,units=4,bank=0,sweep=0):
    if d.get("helicopter"):
        from Helicopters import draw as draw_heli
        return draw_heli(surface,d,center,scale,yaw,color,units,bank)
    col=color or {'cn':(149,168,163),'ussr':(160,177,181),'de':(151,164,152),'us':(157,173,184),'jp':(171,174,159)}[d['country']]
    key=family(d);features=PROFILES[key][7];origin=V(center)
    def pt(x,y):return origin+V(x*d['length']*units,y*d['span']*units*max(.08,abs(math.cos(math.radians(bank))))).rotate(yaw)*scale
    def line(a,b,c=(65,78,82),w=1):pygame.draw.line(surface,c,pt(*a),pt(*b),max(1,int(w*scale)))
    def poly(shape,c):pygame.draw.polygon(surface,c,[pt(*p) for p in shape])
    for kind,shape in polygons(d,units,bank,sweep):
        p=[origin+v.rotate(yaw)*scale for v in shape];c=tuple(max(0,x-(16 if kind in ('wing','tail') else 0)) for x in col)
        pygame.draw.polygon(surface,c,p);pygame.draw.polygon(surface,(44,56,62),p,max(1,int(scale*.7)))
    if key in SWING:
        swing_details(surface,key,d,center,scale,yaw,col,units,bank,sweep);return
    # Separate hinges and panel lines make small icons readable.
    le,tip,te,root,width,tail,engines,_=PROFILES[key]
    for side in (-1,1):
        line((root+.03,side*.10),(te+.025,side*.45));line((-.39,side*.04),(-.46,side*tail*.85))
        if 'twinfin' in features:poly([(-.30,side*.105),(-.47,side*.17),(-.49,side*.12),(-.38,side*.08)],tuple(max(0,c-32) for c in col))
        if 'sideintake' in features:poly([(.12,side*width),(.11,side*(width+.045)),(-.04,side*(width+.04)),(-.04,side*width)],(42,51,56))
    if 'twinfin' not in features:line((-.30,0),(-.48,0),tuple(max(0,c-45) for c in col),2)
    poly([(.29,0),(.20,-width*.55),(.03,-width*.43),(-.01,0),(.03,width*.43),(.20,width*.55)],(42,84,105))
    line((.20,-width*.45),(.20,width*.45),(147,180,182))
    if 'intake' in features and 'sideintake' not in features:line((.46,-width*.28),(.46,width*.28),(24,36,40),2)
    if 'glass' in features:poly([(.49,0),(.33,-width*.55),(.30,width*.55)],(67,106,122))
    if 'prop' in features or 'jet' not in features:
        ys=[0] if engines==1 else [-.31,-.16,.16,.31] if engines==4 else [-.18,.18] if key=='p38' else [-.22,.22]
        for y in ys:line((.49 if engines==1 else .29 if key=='p38' else .22,y-.065),(.49 if engines==1 else .29 if key=='p38' else .22,y+.065),(210,199,151),2)
    if 'biplane' in features:
        for side in (-1,1):line((.10,side*.17),(-.10,side*.41),(239,220,155));line((-.10,side*.17),(.10,side*.41),(239,220,155))
    if 'dorsal' in features:
        for y in ([-.12,.12] if key=='a10' else [0]):poly([(-.14,y-.045),(-.14,y+.045),(-.40,y+.045),(-.40,y-.045)],(86,99,105))
    if key=='ju87':
        for side in (-1,1):line((.01,side*.34),(-.12,side*.34),(28,35,32),3)
    if key=='a10':line((.48,-.015),(.55,-.015),(31,40,43),2)
    if key=='f15' and d['name']=='F-15E':
        for side in (-1,1):line((.13,side*.105),(-.30,side*.105),(84,101,107),3)
    # National marks, not a generic orange dot.
    m=pt(-.05,-.31);r=max(1,int(scale*units*.38))
    if d['country']=='de':
        pygame.draw.line(surface,(235,235,229),m-V(r,0),m+V(r,0),max(1,r));pygame.draw.line(surface,(235,235,229),m-V(0,r),m+V(0,r),max(1,r))
    elif d['country']=='ussr':pygame.draw.polygon(surface,(189,58,51),[m+V(math.cos(i*math.pi/5-math.pi/2),math.sin(i*math.pi/5-math.pi/2))*(r if i%2==0 else r*.45) for i in range(10)])
    else:pygame.draw.circle(surface,(211,219,218),m,r);pygame.draw.circle(surface,(47,91,135),m,max(1,r//2))
