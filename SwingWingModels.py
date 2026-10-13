"""Dedicated simplified planforms with rigid wing panels and aircraft-specific pivots.
Fractions use +X nose, +Y starboard. Rotation is evaluated in metres, never by stretching.
"""
import math
import pygame
from pygame.math import Vector2 as V

# Open/full sweep angles and open-to-swept span targets. Shapes are visual approximations.
FITS={
 'f14':dict(angles=(20,68),pivot=(.085,.170),root_chord=.205,tip_chord=.062,span=(19.55,11.64)),
 'f111':dict(angles=(16,72.5),pivot=(.070,.140),root_chord=.205,tip_chord=.056,span=(19.20,9.74)),
 'tornado':dict(angles=(25,67),pivot=(.035,.163),root_chord=.170,tip_chord=.064,span=(13.91,8.56)),
 'su17':dict(angles=(28,62),pivot=(-.025,.213),root_chord=.168,tip_chord=.057,span=(13.68,10.02)),
 'su24':dict(angles=(16,69),pivot=(.015,.170),root_chord=.200,tip_chord=.058,span=(17.64,10.37)),
}
BODIES={
 'f14':[
  [(.50,0),(.29,-.035),(-.10,-.055),(-.10,.055),(.29,.035)],
  [(.02,-.12),(-.25,-.13),(-.44,-.083),(-.44,.083),(-.25,.13),(.02,.12)]],
 'f111':[
  [(.50,0),(.32,-.045),(.16,-.075),(-.10,-.075),(-.10,.075),(.16,.075),(.32,.045)],
  [(.08,-.095),(-.27,-.087),(-.48,-.058),(-.48,.058),(-.27,.087),(.08,.095)]],
 'tornado':[
  [(.50,0),(.27,-.045),(.12,-.070),(-.13,-.070),(-.13,.070),(.12,.070),(.27,.045)],
  [(.02,-.105),(-.29,-.090),(-.49,-.058),(-.49,.058),(-.29,.090),(.02,.105)]],
 'su17':[
  [(.50,-.022),(.36,-.054),(.04,-.061),(-.28,-.048),(-.49,-.032),(-.49,.032),(-.28,.048),(.04,.061),(.36,.054),(.50,.022)]],
 'su24':[
  [(.50,0),(.36,-.040),(.20,-.064),(.02,-.079),(.02,.079),(.20,.064),(.36,.040)],
  [(.10,-.112),(-.24,-.104),(-.49,-.063),(-.49,.063),(-.24,.104),(.10,.112)]],
}
GLOVES={
 'f14':[(.14,.065),(.085,.19),(-.14,.19),(-.23,.09)],
 'f111':[(.12,.06),(.07,.16),(-.16,.16),(-.23,.065)],
 'tornado':[(.09,.075),(.035,.18),(-.13,.18),(-.23,.08)],
 'su17':[(.13,.047),(-.025,.213),(-.193,.213),(-.27,.053)],
 'su24':[(.11,.075),(.015,.19),(-.18,.19),(-.26,.075)],
}
TAILS={
 'f14':[(-.265,.075),(-.365,.287),(-.495,.255),(-.455,.075)],
 'f111':[(-.315,.050),(-.400,.225),(-.495,.205),(-.455,.050)],
 'tornado':[(-.260,.055),(-.355,.270),(-.465,.245),(-.445,.055)],
 'su17':[(-.290,.033),(-.410,.260),(-.485,.210),(-.440,.033)],
 'su24':[(-.310,.055),(-.405,.240),(-.495,.210),(-.455,.055)],
}

def wing_panel(key,d,side,sweep):
    fit=FITS[key];px,py=fit['pivot'];open_angle,closed_angle=fit['angles'];extent=(.5-py)*d['span']
    hinge=V(px*d['length'],side*py*d['span']);dx=-math.tan(math.radians(open_angle))*extent
    panel=[V(0,0),V(dx,side*extent),V(dx-fit['tip_chord']*d['length'],side*extent),V(-fit['root_chord']*d['length'],0)]
    rotation=side*(closed_angle-open_angle)*max(0,min(1,sweep))
    return [((hinge+v.rotate(rotation)).x/d['length'],(hinge+v.rotate(rotation)).y/d['span']) for v in panel]

def parts(key,d,sweep):
    # The outer panels must precede gloves so trail origins select the true tips.
    out=[('wing',wing_panel(key,d,side,sweep)) for side in (-1,1)]
    out += [('tail',[(x,y*side) for x,y in TAILS[key]]) for side in (-1,1)]
    out += [('glove',[(x,y*side) for x,y in GLOVES[key]]) for side in (-1,1)]
    out += [('body',poly) for poly in BODIES[key]]
    if key=='f14':
        for side in (-1,1):out.append(('engine',[(.00,side*.079),(-.16,side*.142),(-.46,side*.113),(-.48,side*.064)]))
    elif key!='su17':
        for side in (-1,1):out.append(('engine',[(-.10,side*.028),(-.12,side*.082),(-.49,side*.080),(-.49,side*.025)]))
    return out

def wing_point(key,d,x,y,sweep):
    """Move a wing-carried attachment around its pivot; body mounts remain fixed."""
    fit=FITS[key];px,py=fit['pivot'];side=1 if y>=0 else -1
    if abs(y)<=py*d['span']:return V(x,y)
    hinge=V(px*d['length'],side*py*d['span']);rotation=side*(fit['angles'][1]-fit['angles'][0])*max(0,min(1,sweep))
    return hinge+(V(x,y)-hinge).rotate(rotation)

def store_mount(key,d,x,y,sweep):
    fit=FITS[key];px,py=fit['pivot'];span=d['span'];side=1 if y>=0 else -1
    if abs(y)<=py*span:return V(x,y)
    extent=(.5-py)*span;fraction=max(0,min(1,(abs(y)-py*span)/extent))
    chord=(fit['root_chord']*(1-fraction)+fit['tip_chord']*fraction)*d['length']
    longitudinal=px*d['length']-math.tan(math.radians(fit['angles'][0]))*(abs(y)-py*span)-chord*.5
    return wing_point(key,d,longitudinal,y,sweep)

def draw_details(surface,key,d,center,scale,yaw,col,units,bank,sweep):
    origin=V(center);projection=max(.08,abs(math.cos(math.radians(bank))))
    def pt(x,y):return origin+V(x*d['length']*units,y*d['span']*units*projection).rotate(yaw)*scale
    def line(p,q,color=(70,84,91),width=1):pygame.draw.line(surface,color,pt(*p),pt(*q),max(1,round(width*scale)))
    def poly(shape,color):pygame.draw.polygon(surface,color,[pt(*p) for p in shape])
    # Hinges and flap seams use the exact moving wing polygon, not a stationary generic line.
    for side in (-1,1):
        panel=wing_panel(key,d,side,sweep)
        a,b,c,e=map(V,panel)
        line(a.lerp(e,.65),b.lerp(c,.65),(90,103,108));line(b.lerp(c,.12),b.lerp(c,.86),(187,196,190))
        hinge=FITS[key]['pivot'];pygame.draw.circle(surface,(62,74,81),pt(hinge[0],side*hinge[1]),max(1,round(units*.11*scale)),1)
        if key in ('f111','tornado','su24'):
            intake={'f111':(.10,.067,.105),'tornado':(.10,.072,.12),'su24':(.13,.090,.14)}[key]
            x,y,outer=intake;poly([(x,side*y),(x-.025,side*outer),(x-.14,side*outer),(x-.14,side*y)],(37,47,53))
        if key=='f14':
            poly([(.08,side*.073),(.015,side*.140),(-.135,side*.140),(-.06,side*.083)],(35,47,55))
            poly([(-.275,side*.083),(-.435,side*.137),(-.49,side*.137),(-.45,side*.090)],tuple(max(0,v-40) for v in col))
            line((-.455,side*.065),(-.455,side*.112),(34,41,47),3)
        elif key!='su17':line((-.472,side*.028),(-.472,side*.075),(32,40,46),3)
    if key in ('f111','su24'):
        # Broad side-by-side cockpit and a central divider.
        front=.29 if key=='f111' else .25;rear=.14 if key=='f111' else .115
        poly([(front,0),(front-.03,-.047),(rear,-.046),(rear-.03,0),(rear,.046),(front-.03,.047)],(43,87,110))
        line((rear-.01,0),(front,0),(155,177,181))
        line((rear,-.043),(rear,.043),(165,187,184))
    else:
        positions={'f14':(.31,.11,.024),'tornado':(.29,.085,.027),'su17':(.30,.13,.028)}
        front,rear,width=positions[key]
        poly([(front,0),(front-.04,-width),(rear,-width),(rear-.025,0),(rear,width),(front-.04,width)],(43,87,110))
        line(((front+rear)*.5,-width),((front+rear)*.5,width),(163,188,186))
    if key!='f14':
        spine={'f111':(-.26,-.49,.016),'tornado':(-.19,-.47,.026),'su17':(-.23,-.49,.015),'su24':(-.20,-.49,.024)}[key]
        front,rear,width=spine;poly([(front,0),(rear+.045,-width),(rear,-width),(rear,width),(rear+.045,width)],tuple(max(0,v-32) for v in col))
        line((front,0),(rear,0),(61,74,83),2)
    if key=='su17':
        line((.485,-.020),(.485,.020),(30,42,46),3);poly([(.49,0),(.42,-.010),(.42,.010)],(111,131,138))
        line((-.474,-.025),(-.474,.025),(31,40,43),3)
        # Dorsal avionics hump makes the M4 recognisable from the plain Su-7.
        line((.10,-.007),(-.21,-.007),(105,124,130),3)
    if key=='tornado' and 'SLE' in d['name']:
        for side in (-1,1):poly([(-.04,side*.032),(-.14,side*.043),(-.30,side*.037),(-.30,side*.025)],(110,126,131))
    # National marking is attached to a moving panel instead of floating off the swept wing.
    panel=wing_panel(key,d,-1,sweep);p=sum((V(v) for v in panel),V())/4;m=pt(p.x,p.y);radius=max(1,round(scale*units*.22))
    if d['country']=='de':
        pygame.draw.line(surface,(237,237,231),m-V(radius,0),m+V(radius,0),max(1,radius));pygame.draw.line(surface,(237,237,231),m-V(0,radius),m+V(0,radius),max(1,radius))
    elif d['country']=='ussr':pygame.draw.polygon(surface,(190,61,54),[m+V(math.cos(i*math.pi/5-math.pi/2),math.sin(i*math.pi/5-math.pi/2))*(radius if i%2==0 else radius*.45) for i in range(10)])
    else:pygame.draw.circle(surface,(215,223,223),m,radius);pygame.draw.circle(surface,(48,91,135),m,max(1,radius//2))


