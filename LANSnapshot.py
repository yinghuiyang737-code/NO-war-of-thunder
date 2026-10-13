"""Explicit JSON snapshots; clients render the host's world without simulating hits."""
import pygame
from pygame.math import Vector2 as V
from Aviation import AIRCRAFT
from AircraftPhysics import Plane
from NuclearMission import configure,NuclearExplosion
TANK_FIELDS='ammo_bins ammo_targets secondary_belt_cursor rocket_tube reload_voice_serial reload_voice_events reload_voice_pending ammo_box_used radar_scale split_member split_role shells shell_capacity mg_rounds supply_timer supply_ammo_active supply_crew_active crew_replenished era_spent scout_marks airborne p body aim speed angular_speed left_speed right_speed modules dead fire cd missile_cd mg_cd grenade_cd grenade_count smoke_cd smoke_charges ess_active ess_timer ammo_index missile_index missile_count aps_charges aps_cd trail drowning_age network_owner network_name user_vehicle_name reason premium_mag premium_ammo reload_duration ai_role ai_maneuver ai_focus ai_skill'.split()
PLANE_FIELDS='guided_camera hover hover_anchor hover_altitude p a speed throttle altitude bank sweep phase modules dead cd mcd bcd rcd cdc counter ammo pod_ammo missiles bombs rockets agms flares heat_flares chaff cm_flare_capacity cm_chaff_capacity cm_mode belt missile fuel takeoff_distance nuclear stores loadout pods ground_choice ground_lock airbrake chute_deployed chute_used hook_deployed cable_engaged cable_anchor'.split()
PRIVATE_FIELDS='last_missile_token combat_notice battery_units battery_radar battery_placing drone_heading drone_bank drone_speed drone_throttle drone_orbit drone_orbit_center drone_active drone_pos drone_battery drone_cooldown drone_zoom scout_cooldown scouted_targets abandon_elapsed state score kills daily_kills active_vehicle_slot reserves used_slots deploy_delay deploy_choice deploy_selected deploy_hint vision night_battle xray zoom paused death_wait player_death_handled pending_state pending_deploy_delay feedback_clock personal_kills messages ammo_choices missile_choices death_camera hitview'.split()
class Snapshot:
    def __init__(self,authority):self.a=authority;self.tree_ids={tuple(p):i for i,(p,size) in enumerate(authority.root.terrain.trees)}
    def pack(self,value):
        if isinstance(value,V):return {'v':[round(value.x,3),round(value.y,3)]}
        if isinstance(value,pygame.Rect):return {'r':list(value)}
        if hasattr(value,'_net_uid'):return {'ref':value._net_uid}
        if isinstance(value,dict):
            if '_net_uid' in value:return {'ref':value['_net_uid']}
            return {str(k):self.pack(v) for k,v in value.items() if not callable(v)}
        if isinstance(value,(list,tuple,set)):return [self.pack(v) for v in value]
        if isinstance(value,(str,int,float,bool)) or value is None:return value
        return None
    def tank(self,t):
        return dict(uid=self.a.uid(t),vehicle=t.vehicle_id,enemy=t.enemy,elite=t.elite,ai=t.ai,fields={k:self.pack(getattr(t,k)) for k in TANK_FIELDS if hasattr(t,k)})
    def plane(self,p):return dict(ident=p.ident,fields={k:self.pack(getattr(p,k)) for k in PLANE_FIELDS if hasattr(p,k)})
    def build(self):
        a=self.a;r=a.root;tanks=list({id(t):t for t in r.vehicles()+[g.player for g in a.contexts.values()]}.values())
        for t in tanks:a.uid(t)
        for q in r.air.planes:a.uid(q)
        players={}
        for ident,g in a.contexts.items():
            fields={k:self.pack(getattr(g,k)) for k in PRIVATE_FIELDS if hasattr(g,k)}
            players[str(ident)]=dict(player=a.uid(g.player),fields=fields,plane=self.plane(g.flight.plane) if g.flight.plane else None,record=a.uid(g.flight.record) if g.flight.record else None,radar_state=self.pack({k:getattr(g.flight.radar,k) for k in ('enabled','mode','clock','beam','tracks','stt','selected')}) if hasattr(g.flight,'radar') else None,warning_contacts=self.pack(g.flight.warning.contacts) if hasattr(g.flight,'warning') else [],warning_clock=g.flight.warning.clock if hasattr(g.flight,'warning') else 0.,warning_enabled=g.flight.warning.enabled if hasattr(g.flight,'warning') else True,artillery=g.artillery.enabled,settle=g.artillery.settle,focus=self.pack(g.artillery.focus),nuke_used=g.flight.nuke_used,nuke_pending=g.flight.nuke_pending,nuke_timer=g.flight.nuke_timer,nuke_point=self.pack(g.flight.nuke_point),service_timer=g.flight.service.timer,service_stage=g.flight.service.stage,flight_base=dict(kind=g.flight.base_kind,helipad_enabled=g.flight.helipad_enabled,p=self.pack(g.flight.airport),heading=g.flight.heading),ground_lock=dict(missile=bool(g.air.lock.get('missile')),p=self.pack(g.air.lock['p'])) if isinstance(g.air.lock,dict) else None)
        planes=[]
        for q in r.air.planes:
            if q['dead']:continue
            model=q.get('model',{});record={k:self.pack(q[k]) for k in ('p','v','dead','health','bomb','life','team','bank','sweep','age','ammo','bombs_left') if k in q}
            p=q.get('ai_plane') or (q['controlled'].plane if q.get('controlled') else None)
            if p:record.update(p=self.pack(p.p),bank=p.bank,sweep=p.sweep)
            planes.append(dict(uid=a.uid(q),model=model.get('id'),fields=record))
        projectiles=[b for g in a.contexts.values() for b in g.flight.projectiles]
        animation=r.flight.nuke_animation
        from BattleAudio import nuclear_alarm
        return dict(ammo_boxes=self.pack(r.ammo_boxes),nuclear_alarm=nuclear_alarm(r),nuclear_result=r.nuclear_result,ai_nuclear=r.ai_nuclear,battle_roster=r.battle_roster,type='snapshot',seq=a.sequence,map_id=r.map_id,br=r.battle_br,time=r.time,feedback_clock=r.feedback_clock,state=a.final_state,players=players,members=list(a.members.values()),tanks=[self.tank(t) for t in tanks],enemies=[a.uid(t) for t in r.enemies],allies=[a.uid(t) for t in r.allies],wrecks=[a.uid(t) for t in r.wrecks],planes=planes,bullets=self.pack(r.bullets),missiles=self.pack(r.air.missiles),projectiles=self.pack(projectiles),fx=self.pack(r.fx[-220:]),tracks=self.pack(r.tracks[-500:]),smokes=self.pack(r.smokes),counter_clouds=self.pack(getattr(r,'counter_clouds',[])),mg_tracers=self.pack(r.mg_tracers),trees=[self.tree_ids[tuple(p)] for p,size in r.terrain.trees if tuple(p) in self.tree_ids],fallen=self.pack(r.terrain.fallen),objectives=[dict(owner=p.owner,team=p.team,progress=p.progress,contested=p.contested,owner_since=p.owner_since) for p in r.objectives],tickets=r.tickets,wave=r.wave,ground_kills=r.ground_kills,kill_feed=r.kill_feed,artillery_shells=self.pack(r.artillery.shells),artillery_blasts=self.pack(r.artillery.blasts),nuke_detonated=r.flight.nuke_detonated,nuke_animation=dict(point=self.pack(animation.point),age=animation.age) if animation else None)

class Replica:
    def __init__(self,api,start,ident):
        self.api=api;self.ident=ident;self.members={m['id']:m for m in start['members']};c=self.members[ident]['config']
        self.g=api['Game'](True,c['country'],c['lineup'],c['slot'],c['ammo'],c['missiles'],map_id=start['map_id']);self.g.battle_br=start['br'];self.g.flight.weapons=c['weapons'];self.objects={};self.sequence=-1;self.last=None;self.tree_base=list(self.g.terrain.trees);self.static_obstacles=[q for q in self.g.terrain.obstacles if q[1]!='tree'];self.tree_signature=None;self.view_id=ident
        self.g.spawn_allies=lambda *args,**kwargs:None
    def unpack(self,value):
        if isinstance(value,list):return [self.unpack(v) for v in value]
        if isinstance(value,dict):
            if set(value)=={'v'}:return V(value['v'])
            if set(value)=={'r'}:return pygame.Rect(value['r'])
            if set(value)=={'ref'}:return self.objects.get(value['ref'])
            return {k:self.unpack(v) for k,v in value.items()}
        return value
    def apply(self,message,view_id=None):
        if message['seq']<self.sequence:return
        self.sequence=message['seq'];self.last=message;g=self.g;self.members={m['id']:m for m in message['members']};self.view_id=self.ident if view_id is None else view_id
        if str(self.view_id) not in message['players']:self.view_id=self.ident
        own=message['players'][str(self.ident)];view=message['players'][str(self.view_id)]
        for record in message['tanks']:
            uid=record['uid'];t=self.objects.get(uid)
            if t is None:t=self.api['Tank']((0,0),record['enemy'],record['elite'],vehicle=record['vehicle']);t._net_uid=uid;self.objects[uid]=t
            t.ai=record['ai']
        for record in message['planes']:
            if record['uid'] not in self.objects:self.objects[record['uid']]={'_net_uid':record['uid']}
        for record in message['tanks']:
            t=self.objects[record['uid']]
            for key,value in record['fields'].items():setattr(t,key,self.unpack(value))
            if getattr(t,'split_role',None)=='launcher':
                import copy
                t.stats=copy.deepcopy(t.stats);t.stats['split_role']='launcher';t.stats['name']=t.stats['split_system']+' 发射车'
        own_state=own['fields']['state']
        for key,value in own['fields'].items():
            preserve_deployment=own_state=='deploy' and g.state=='deploy' and key in ('deploy_choice','deploy_selected','active_vehicle_slot')
            if key not in ('zoom','paused') and not preserve_deployment:setattr(g,key,self.unpack(value))
        g.battery.units=getattr(g,'battery_units',[]);g.battery.radar=getattr(g,'battery_radar',None);g.battery.placing=getattr(g,'battery_placing',False)
        g.used_slots=set(g.used_slots);g.player=self.objects[view['player']];g.player.is_user=True
        g.enemies=[self.objects[k] for k in message['enemies']];g.allies=[self.objects[k] for k in message['allies'] if k!=view['player']]
        host_player=message['players']['0']['player']
        if self.view_id!=0 and host_player!=view['player'] and not self.objects[host_player].dead:g.allies.append(self.objects[host_player])
        # Other-client replicas also need the viewer's actual local tank visible while spectating.
        if own['player']!=view['player'] and not self.objects[own['player']].dead and self.objects[own['player']] not in g.allies:g.allies.append(self.objects[own['player']])
        g.wrecks=[self.objects[k] for k in message['wrecks'] if k in self.objects]
        g.air.planes=[]
        for record in message['planes']:
            q=self.objects[record['uid']];q.clear();q.update(self.unpack(record['fields']));q['_net_uid']=record['uid'];q['model']=AIRCRAFT.get(record['model']);g.air.planes.append(q)
        plane_data=view['plane'];f=g.flight
        if plane_data is not None:
            p=f.plane
            if p is None or p.ident!=plane_data['ident'] or getattr(p,'_view_player',None)!=view['player']:
                f.start(plane_data['ident'],bool(plane_data['fields'].get('nuclear')));p=f.plane;p._view_player=view['player'];g.player=self.objects[view['player']]
                g.air.planes=[self.objects[r['uid']] for r in message['planes']]
            for key,value in plane_data['fields'].items():setattr(p,key,self.unpack(value))
            if p.nuclear:configure(p,p.bombs)
            # Restore finite mission countermeasures after local configuration.
            for key in ('heat_flares','chaff','flares'):setattr(p,key,plane_data['fields'].get(key,getattr(p,key)))
            p._view_player=view['player'];f.record=self.objects.get(view['record'])
            if f.record:f.record['controlled']=f
        else:f.plane=None;f.record=None
        g.player=self.objects[view['player']]
        g.ammo_boxes=self.unpack(message.get('ammo_boxes',[]))
        g._nuclear_alarm_remote=bool(message.get('nuclear_alarm',False))
        g.nuclear_result=message.get('nuclear_result');g.ai_nuclear=message.get('ai_nuclear');g.battle_roster=message.get('battle_roster',{});g.time=message['time'];g.feedback_clock=message['feedback_clock'];g.battle_br=message['br'];g.tickets=list(message['tickets']);g.wave=message['wave'];g.ground_kills=message['ground_kills'];g.kill_feed=message['kill_feed'];g.paused=False
        g.state=message['state'] or ('play' if own_state=='spectate' and self.view_id!=self.ident else own_state)
        for key in ('bullets','fx','smokes','counter_clouds','mg_tracers'):setattr(g,key,self.unpack(message[key]))
        cache=getattr(self,'trace_cache',{})
        for mark in self.unpack(message.get('tracks',[])):
            start,end,width=mark[:3];key=(start.x,start.y,end.x,end.y,width,mark[3] if len(mark)>3 else 0)
            cache.setdefault(key,mark)
        cache={k:m for k,m in cache.items() if len(m)<4 or m[3]>g.time}
        if len(cache)>20000:cache=dict(list(cache.items())[-20000:])
        self.trace_cache=cache;g.tracks=list(cache.values())
        base=view.get('flight_base')
        if base:f.helipad_enabled=bool(base.get('helipad_enabled'));f.base_kind=base['kind'];f.airport=self.unpack(base['p']);f.heading=base['heading']
        g.air.missiles=self.unpack(message['missiles']);f.projectiles=self.unpack(message['projectiles'])
        descriptor=view.get('ground_lock');g.air.lock=None
        if descriptor:
            from RadarContacts import missiles
            candidates=missiles(g) if descriptor['missile'] else g.air.planes
            point=self.unpack(descriptor['p'])
            g.air.lock=min(candidates,key=lambda q:q['p'].distance_squared_to(point),default=None)
        signature=tuple(message['trees'])
        if self.tree_signature!=signature:
            self.tree_signature=signature;g.terrain.trees=[self.tree_base[i] for i in signature]
            g.terrain.obstacles=self.static_obstacles+[(pygame.Rect(p.x-9,p.y-9,18,18),'tree') for p,size in g.terrain.trees]
        g.terrain.fallen=self.unpack(message['fallen'])
        for p,state in zip(g.objectives,message['objectives']):
            for key,value in state.items():setattr(p,key,value)
        g.artillery.shells=self.unpack(message['artillery_shells']);g.artillery.blasts=self.unpack(message['artillery_blasts']);g.artillery.enabled=view['artillery'] and own_state!='spectate';g.artillery.settle=view['settle']
        f.nuke_timer=view['nuke_timer'];f.nuke_point=self.unpack(view['nuke_point']);f.nuke_used=own['nuke_used'];f.nuke_pending=own['nuke_pending'];f.nuke_detonated=message['nuke_detonated'];f.service.timer=view['service_timer'];f.service.stage=view['service_stage']
        anim=message['nuke_animation']
        if anim:
            if not f.nuke_animation:f.nuke_animation=NuclearExplosion(self.unpack(anim['point']))
            f.nuke_animation.age=anim['age']
        if g.flight.active and not g.artillery.enabled and g.zoom>=.65:g.zoom=.38
        if g.artillery.enabled and g.zoom>.5:g.zoom=.2;g.artillery.focus=self.unpack(view['focus'])
        if not g.artillery.enabled and not g.flight.active and g.zoom<.5:g.zoom=1.
        if g.flight.active:
            for key,value in (view.get('radar_state') or {}).items():setattr(g.flight.radar,key,self.unpack(value))
            g.flight.radar.tracks=[t for t in g.flight.radar.tracks if t.get('target') is not None]
            g.flight.warning.contacts=self.unpack(view.get('warning_contacts',[]));g.flight.warning.clock=view.get('warning_clock',0.);g.flight.warning.enabled=view.get('warning_enabled',True)
        g.camera()
        alive_ids={r['uid'] for r in message['tanks']}|{r['uid'] for r in message['planes']}
        self.objects={key:value for key,value in self.objects.items() if key in alive_ids}
    def render_update(self,dt):
        g=self.g
        if g.flight.active:
            radar=g.flight.radar;radar.clock+=dt
            if radar.stt is None:
                phase=(radar.clock/radar.period)%2;radar.beam=(-radar.sector+2*radar.sector*phase) if phase<1 else (3*radar.sector-2*radar.sector*phase)
            g.flight.warning.clock+=dt
            g.flight.warning.contacts=[c for c in g.flight.warning.contacts if c['until']>g.flight.warning.clock]
        if g.artillery.enabled:
            mouse=pygame.mouse.get_pos();view=self.api['VIEW']
            if view.collidepoint(mouse):
                edge=55;dx=(int(mouse[0]>view.right-edge)-int(mouse[0]<view.left+edge));dy=(int(mouse[1]>view.bottom-edge)-int(mouse[1]<view.top+edge));g.artillery.focus+=V(dx,dy)*1800*dt;g.camera()
