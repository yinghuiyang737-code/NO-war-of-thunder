"""Deep water, laser illumination and impact-triggered attention."""
import math
import pygame
from pygame.math import Vector2 as V
from GroundEquipment import EQUIPMENT

def missile_guidance(ammo):
    if (ammo or {}).get('guidance'):return ammo['guidance']
    name=(ammo or {}).get('name','').lower();typ=(ammo or {}).get('type','').upper()
    if any(x in name for x in ('stinger','igla','mistral','fim-92','9m39','9m336','9m37','hn-6','qn201')) or typ=='AAM':return 'IR'
    if 'spike' in name or '长钉' in name:return 'TOP_ATTACK'
    if 'qn502' in name:return 'IR'
    if any(x in name for x in ('9m119','9m133','kornet','mim146','mim-146','9m120-1')):return 'LASER_BEAM'
    return 'COMMAND'

def submerged(t,terrain):
    points=[p for poly in t.footprint()[:len(t.collision_parts)] for p in poly] if t.vehicle_id else [t.p+V(x,y).rotate(t.body) for x,y in ((-30,-27),(30,-27),(30,27),(-30,27))]
    # Requiring the complete footprint inside one basin avoids premature centre-point deaths.
    return any(k=='deep_water' and all(r.collidepoint(p) for p in points) for r,k in terrain.nearby_obstacles(pygame.FRect(t.p.x-t.radius,t.p.y-t.radius,t.radius*2,t.radius*2)))

def install(Game,Tank,api):
    old_update=Game.update;old_draw=Game.draw;old_hit=Game.record_hit;old_air_hit=Game.record_air_hit
    def note_attack(g,victim,attacker):
        if attacker is None:return
        if isinstance(victim,dict):
            victim['retaliation_attacker']=attacker;victim['retaliation_until']=g.time+6.;return
        victim.retaliation_attacker=attacker;victim.retaliation_until=g.time+6.;victim.ai_recent_hit=4.
        p=attacker.get('p') if isinstance(attacker,dict) else attacker.p
        victim.ai_threat_heading=math.degrees(math.atan2((p-victim.p).y,(p-victim.p).x));victim.ai_scan_timer=0.
    def record_hit(g,target,result,owner,weapon=''):
        if not result.get('continue'):note_attack(g,target,owner)
        old_hit(g,target,result,owner,weapon)
    def record_air_hit(g,target,point,owner,weapon=''):
        note_attack(g,target,owner);old_air_hit(g,target,point,owner,weapon)
    def illuminate(g,emitter,target):
        if target is None or isinstance(target,dict) or target.dead or not EQUIPMENT.get(target.vehicle_id,{}).get('lws'):return False
        p=emitter.get('p') if isinstance(emitter,dict) else emitter.p
        if not g.visible(p,target.p,False):return False
        target.laser_warning=(math.degrees(math.atan2((p-target.p).y,(p-target.p).x)),g.time+2.5)
        return True
    def update(g,dt):
        active=not g.paused and g.state in ('play','deploy','wreck')
        old_update(g,dt)
        if not active or g.paused or g.state not in ('play','deploy','wreck'):return
        for t in g.vehicles()[:]:
            if t.dead or getattr(t,'airborne',False) or (t is g.player and g.state=='deploy'):continue
            age=getattr(t,'drowning_age',0.)
            t.drowning_age=0. if EQUIPMENT.get(t.vehicle_id,{}).get('amphibious') or not submerged(t,g.terrain) else age+dt
            if t.drowning_age>=3.-1e-7:
                t.dead=True;t.reason='深水溺亡';t.last_attacker=None;t.player_credit=False;t.last_weapon='深水溺亡';g.register_death(t)
        target=g.air.lock
        if target is not None and EQUIPMENT.get(g.player.vehicle_id,{}).get('laser'):illuminate(g,g.player,target)
        # AI laser ranging occurs only while aiming at a currently observed target.
        for t in g.allies+g.enemies:
            target=t.ai_target
            if not t.dead and target is not None and t.ai_focus=='aim' and EQUIPMENT.get(t.vehicle_id,{}).get('laser') and abs(api['diff'](api['angle'](target.p-t.p),t.aim))<4:illuminate(g,t,target)
    def draw(g,*a,**kw):
        old_draw(g,*a,**kw)
        t=g.player
        if g.state not in ('play','wreck') or getattr(t,'airborne',False):return
        age=getattr(t,'drowning_age',0.)
        if age>0 and not t.dead:
            pygame.draw.rect(api['screen'],(75,30,26),(420,110,440,66),border_radius=8)
            api['text'](f'深水溺亡：{max(0,3-age):.1f} 秒',(640,128),24,(255,164,108),True)
            api['text']('立即退出深水区',(640,157),16,(248,211,182),True)
        warning=getattr(t,'laser_warning',None)
        if warning and warning[1]>g.time and not t.dead:
            screen=api['screen'];center=g.world_to_display(t.p)
            radius=max(76,t.radius*g.zoom+25)
            direction=V(1,0).rotate(warning[0]);edge=center+direction*radius
            clip=screen.get_clip();screen.set_clip(api['VIEW'])
            pygame.draw.circle(screen,(125,86,45),center,round(radius),1)
            # The illuminated sector is fixed to the source's world bearing, not hull heading.
            points=[center+V(radius,0).rotate(warning[0]+a) for a in range(-13,14,2)]
            pygame.draw.lines(screen,(255,171,62),False,points,5)
            tip=edge-direction*8;side=direction.rotate(90)
            pygame.draw.polygon(screen,(255,217,113),[tip,edge+direction*10+side*7,edge+direction*10-side*7])
            api['text']('激光',edge+direction*29-V(0,8),16,(255,197,91),True)
            screen.set_clip(clip)
    Game.update=update;Game.draw=draw;Game.record_hit=record_hit;Game.record_air_hit=record_air_hit;Game.note_attack=note_attack;Game.illuminate=illuminate
