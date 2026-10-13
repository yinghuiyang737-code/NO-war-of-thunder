"""Separate infrared flares and radar chaff with real local decoys."""
import random,math
import pygame
from pygame.math import Vector2 as V
from AircraftPhysics import direction,bearing,difference

def prepare(p):
    equipment=p.stats.get('warning',{}).get('cm',{'flare':True,'chaff':True})
    pod=any(w.get('countermeasures',0) for w in p.stores)
    flare=equipment['flare'] or pod;chaff=equipment['chaff'] or pod;total=p.flares
    p.heat_flares=(total+1)//2 if flare and chaff else total if flare else 0
    p.chaff=total//2 if flare and chaff else total if chaff else 0
    p.flares=p.heat_flares+p.chaff;p.cm_flare_capacity=p.heat_flares;p.cm_chaff_capacity=p.chaff
    options=modes(p);p.cm_mode=getattr(p,'cm_mode','mixed')
    if p.cm_mode not in options:p.cm_mode=options[0] if options else 'mixed'

def modes(p):return (['mixed'] if p.cm_flare_capacity and p.cm_chaff_capacity else [])+(['flare'] if p.cm_flare_capacity else [])+(['chaff'] if p.cm_chaff_capacity else [])
LABELS={'mixed':'热诱 + 箔条','flare':'热诱弹','chaff':'箔条'}
def release(g,p,kind=None):
    kind=kind or p.cm_mode
    if p.cdc or p.dead:return False
    available=[]
    if kind in ('mixed','flare') and p.heat_flares:available.append('flare');p.heat_flares-=1
    if kind in ('mixed','chaff') and p.chaff:available.append('chaff');p.chaff-=1
    if not available:return False
    p.flares=p.heat_flares+p.chaff;p.cdc=.4;p.counter=1.8
    if not hasattr(g,'counter_clouds'):g.counter_clouds=[]
    for type_ in available:
        color=(255,195,90) if type_=='flare' else (178,209,224);g.burst(p.p,color,8)
        offset=direction(p.a)*(-p.stats['length']*3)+direction(p.a+(90 if type_=='flare' else -90))*p.stats['span']*3
        g.counter_clouds.append(dict(kind=type_,p=V(p.p)+offset,v=direction(p.a)*p.speed*.2+direction(p.a+random.choice((-90,90)))*80,life=2.4 if type_=='flare' else 3.5,team=p.team))
    return True

def guidance(m):
    if m.get('guidance'):return m['guidance']
    name=(m.get('ammo') or {}).get('name','').lower();owner=m.get('owner')
    if (m.get('ammo') or {}).get('type')=='AAM' or any(s in name for s in ('stinger','igla','mistral','fim-92','9m39','9m336','9m37','hn-6')):return 'IR'
    if any(s in name for s in ('mim146','mim-146','9m133','kornet')):return 'OPTICAL'
    return 'RADAR' if owner is not None and getattr(owner,'stats',{}).get('radar') else 'OPTICAL'

def distracted(g,m,target,dt,rng=random):
    kind=guidance(m);wanted='flare' if kind=='IR' else 'chaff' if kind in ('SARH','ARH','RADAR') else None
    if wanted is None:return False
    source=m.get('source');radar=source.get('radar') if isinstance(source,dict) else None
    resistance=.35 if wanted=='chaff' and (kind=='ARH' or radar and radar.mode in ('PD','TWS','RAM')) else 1.
    for cloud in getattr(g,'counter_clouds',[]):
        if cloud['kind']!=wanted or cloud['life']<=0 or cloud['team']!=target.get('team',1) or cloud['p'].distance_to(target['p'])>1600:continue
        delta=cloud['p']-m['p']
        if delta.length()>24000 or abs(difference(bearing(delta),bearing(m['v'])))>35:continue
        if rng.random()<min(.8,dt*2.2*resistance):return True
    return False

def update_clouds(g,dt):
    if getattr(g,"_lan_id",0)!=0:return
    for c in getattr(g,'counter_clouds',[]):c['life']-=dt;c['p']+=c['v']*dt;c['v']*=max(0,1-dt*.7)
    g.counter_clouds=[c for c in getattr(g,'counter_clouds',[]) if c['life']>0]

def draw_clouds(g,s,at,factor=1):
    for c in getattr(g,'counter_clouds',[]):
        pos=at(c['p']);age=(2.4 if c['kind']=='flare' else 3.5)-c['life']
        if c['kind']=='flare':
            pygame.draw.circle(s,(255,117,43),pos,max(2,int(7*factor)));pygame.draw.circle(s,(255,237,155),pos,max(1,int(3*factor)))
            pygame.draw.line(s,(252,164,80),pos,pos-c['v']*.09,2)
        else:
            for i in range(8):
                offset=direction(i*45+age*15)*max(2,(15+age*25)*factor)
                pygame.draw.line(s,(174,200,216),pos+offset,pos+offset+V(3,1),1)
