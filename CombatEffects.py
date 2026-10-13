"""Spatial post-penetration fragments, evaluated against actual module geometry."""
import math,re
from pygame.math import Vector2 as V

def external_spall(t,point,normal,rng):
    """An external blast can damage exposed parts, never bypass hull armour."""
    origin=V(point)+V(normal)*3;rays=[];damaged=[]
    for k in ('left_track','right_track','barrel'):
        if t.modules[k]<=0:continue
        end=t.module_world(k);delta=end-origin
        if delta.length()>max(30,t.radius*1.4):continue
        clip=t.module_clip(k,origin,end)
        if not clip:continue
        contact=t.shell_contact(origin,end)
        part_distance=V(clip[0]).distance_to(origin)
        if contact and contact[3] in ('hull','turret') and V(contact[1]).distance_to(origin)+2<part_distance:continue
        rays.append((t.local(origin),t.local(V(clip[0]))))
        if rng.random()<.8:t.damage_module(k,1);damaged.append(k)
    return damaged,rays

def spall(t,entry,direction,ammo,rng,energy_scale=1.):
    typ=(ammo or {}).get('type','AP').upper()
    bursting=('APHE' in typ or 'APCBC' in typ or typ=='HE')
    chemical=not (ammo or {}).get('kinetic_missile') and ('HEAT' in typ or 'ATGM' in typ)
    cone=25 if chemical else 42 if 'APFSDS' in typ else 58
    caliber=float((ammo or {}).get('caliber') or 75.)
    scale=max(.06,min(1.5,caliber/100.))
    count=max(1,round(25*scale))
    fragment_energy=max(.12,1.1*scale)*energy_scale
    length=max(12,max(60,t.radius*2.2)*math.sqrt(scale))*energy_scale
    origin=V(entry)+direction*2
    rays=[];damage={}
    def cast(start,d,reach,energy,bounces=0):
        intended=start+d*reach
        end=intended
        clipped=t.body_rect.inflate(2,2).clipline(start,end)
        if not clipped:return
        start,end=map(V,clipped);reach=start.distance_to(end)
        rays.append((V(start),V(end)))
        contacts=[]
        for k in t.module_rects:
            if k in ('barrel','left_track','right_track'):continue
            clip=t.module_clip(k,t.world(start),t.world(end))
            if clip:contacts.append((V(clip[0]).distance_to(t.world(start)),k,V(clip[0]).distance_to(V(clip[1]))))
        for distance,k,thickness in sorted(contacts):
            if distance>reach or energy<=0:break
            # Modules absorb fragments; later modules receive less energy.
            threshold=.45 if k in ('engine','breech') else .25 if k=='ammo' else .08
            if t.modules[k]>0 and energy>=threshold:damage[k]=max(damage.get(k,0),1 if energy<1.5 else 2)
            density=1.35 if k in ('engine','transmission','breech') else .9 if k in ('ammo','ring') else .3
            absorption=density*(.4+min(1,thickness/18)*.6)*(.65 if t.modules[k]<=0 else 1.)
            energy-=absorption
            if energy<=0:
                rays[-1]=(V(start),start+d*min(reach,distance+thickness));break
        remaining=V(intended).distance_to(start)-reach
        if bounces<2 and remaining>2 and energy>.18 and rng.random()<.32:
            bounds=t.body_rect.inflate(2,2)
            horizontal=min(abs(end.x-bounds.left),abs(end.x-bounds.right))<min(abs(end.y-bounds.top),abs(end.y-bounds.bottom))
            reflected=V(-d.x,d.y) if horizontal else V(d.x,-d.y)
            cast(end+reflected*.8,reflected,remaining*.55,energy*.45,bounces+1)
    for i in range(count):
        spread=-cone+2*cone*(i+rng.random())/count
        cast(origin,direction.rotate(spread),length*(.55+.45*rng.random()),fragment_energy)
    burst=None
    if bursting:
        burst=origin+direction*min(t.half_length*.65,length*.22)
        burst_count=max(2,round(40*scale))
        for i in range(burst_count):
            cast(burst,V(1,0).rotate((i+rng.random())*360/burst_count),length*.55,1.7*scale*energy_scale)
    for k,amount in damage.items():
        t.damage_module(k,amount)
        if k=='engine' and rng.random()<.4:t.fire=15
    return list(damage),rays,burst
