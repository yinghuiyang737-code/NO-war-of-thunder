"""Host-owned multi-player contexts sharing one ground/air battlefield."""
import math,random,types,time
import pygame
from pygame.math import Vector2 as V
from Aviation import AIRCRAFT
from InputBindings import ACTIONS
WORLD_FIELDS=set('ammo_boxes nuclear_result battle_roster roster_serial ai_nuclear terrain enemies allies wrecks bullets fx tracks smokes counter_clouds mg_tracers ally_queue enemy_queue time wave wait ground_kills tickets kill_goal objective objectives battle_br enemy_country kill_feed'.split())
HELD_KEYS=tuple(sorted(set(d['canonical'] for d in ACTIONS.values() if isinstance(d['canonical'],int))))
class RemoteControls:
    def __init__(self,display):self.display=display;self.input={};self.age=0.
    def keys(self,context):
        active=set(self.input.get('keys',())) if self.age<.5 else set()
        return Keys(active)
    def buttons(self,context):return (bool(self.input.get('fire')) and self.age<.5,False,False)
    def label(self,action):return self.display.label(action)
class Keys:
    def __init__(self,keys):self.values=set(keys)
    def __getitem__(self,key):return key in self.values

def make_shared_class(Game):
    class SharedGame(Game):
        def __getattribute__(self,key):
            if key in WORLD_FIELDS:
                root=object.__getattribute__(self,'__dict__').get('_lan_world')
                if root is not None:return getattr(root,key)
            return super().__getattribute__(key)
        def __setattr__(self,key,value):
            root=self.__dict__.get('_lan_world')
            if root is not None and key in WORLD_FIELDS:setattr(root,key,value)
            else:super().__setattr__(key,value)
    return SharedGame

class Authority:
    def __init__(self,api,start,display_controls):
        self.api=api;Game=api['Game'];self.members={m['id']:m for m in start['members']};self.contexts={};self.inputs={};self.sequence=0;self.uid_counter=0;self.team_nuke=False;self.final_state=None
        SharedGame=make_shared_class(Game)
        for ident,member in self.members.items():
            c=member['config'];cls=Game if ident==0 else SharedGame
            g=cls(True,c['country'],c['lineup'],c['slot'],c['ammo'],c['missiles'],map_id=start['map_id']);g.flight.weapons=c['weapons'];g.battle_br=start['br'];g._lan_id=ident;g._lan_authority=self
            if ident==0:
                self.root=g
                if not hasattr(g,"counter_clouds"):g.counter_clouds=[]
                if not hasattr(g,"mg_tracers"):g.mg_tracers=[]
            else:
                g._lan_world=self.root;g.air.planes=self.root.air.planes;g.air.missiles=self.root.air.missiles;g.artillery.shells=self.root.artillery.shells;g.artillery.blasts=self.root.artillery.blasts
            g.controls=RemoteControls(display_controls);g.player.dead=True;self.contexts[ident]=g;self.bind_player(ident)
        for g in self.contexts.values():g.night_battle=self.root.night_battle
        self.root.battle_br=start['br']
        for ident,g in self.contexts.items():self.install_hooks(g)
        self.root.spawn_allies(max(0,16-len(self.members)))
        if start.get('late_join'):
            from LateJoin import seed_battle
            seed_battle(self.root)
    def bind_player(self,ident):
        g=self.contexts.get(ident)
        if g is None:return
        t=g.player;t.network_owner=ident;t.network_name=self.members[ident]['name'];t.is_user=True;t.ai=False
        t.user_vehicle_name=g.flight.plane.stats['name'] if g.flight.active else t.stats['name'];self.uid(t)
        from BattleRoster import row
        row(g,t)
        if ident and not t.dead and t not in self.root.allies:self.root.allies.append(t)
    def uid(self,obj):
        if isinstance(obj,dict):
            if '_net_uid' not in obj:self.uid_counter+=1;obj['_net_uid']='a'+str(self.uid_counter)
            return obj['_net_uid']
        if not hasattr(obj,'_net_uid'):self.uid_counter+=1;obj._net_uid='t'+str(self.uid_counter)
        return obj._net_uid
    def owner_context(self,owner):
        if owner is None:return None
        ident=getattr(owner,'network_owner',None)
        return self.contexts.get(ident)
    def install_hooks(self,g):
        Game=self.api['Game'];authority=self
        g.is_player=types.MethodType(lambda ctx,u:u is ctx.player,g)
        def unit_name(ctx,u):return getattr(u,'user_vehicle_name',None) or Game.unit_name(ctx,u)
        g.unit_name=types.MethodType(unit_name,g)
        def ai_step(ctx,t,dt):
            if getattr(t,'network_owner',None) is not None:return
            Game.ai_step(ctx,t,dt)
        g.ai_step=types.MethodType(ai_step,g)
        def vehicles(ctx):
            if ctx is not authority.root:return authority.root.vehicles()
            units=Game.vehicles(ctx);return list({id(t):t for t in units}.values())
        g.vehicles=types.MethodType(vehicles,g)
        def spawn(ctx,count,vehicle=None):
            npc=sum(not t.dead and getattr(t,'network_owner',None) is None for t in ctx.allies)
            npc+=sum(1 for q in ctx.air.planes if not q['dead'] and q.get('managed',False) and q.get('team')==0)+len(ctx.ally_queue)
            Game.spawn_allies(ctx,min(count,max(0,16-len(authority.members)-npc)),vehicle)
        g.spawn_allies=types.MethodType(spawn,g)
        def hit(ctx,t,result,owner,weapon=''):
            receiver=authority.owner_context(owner)
            Game.record_hit(receiver or ctx,t,result,owner,weapon)
        g.record_hit=types.MethodType(hit,g)
        def air_hit(ctx,t,point,owner,weapon=''):
            receiver=authority.owner_context(owner);Game.record_air_hit(receiver or ctx,t,point,owner,weapon)
        g.record_air_hit=types.MethodType(air_hit,g)
        def announce(ctx,attacker,victim,weapon=''):
            # One authoritative feed/ticket event; personal credit goes to the actual squad member.
            if isinstance(victim,dict):already=victim.get('ticket_loss_recorded',False)
            else:already=getattr(victim,'ticket_loss_recorded',False)
            if already:return
            Game.announce_kill(authority.root,attacker,victim,weapon)
            receiver=authority.owner_context(attacker);enemy=victim.get('team',1) if isinstance(victim,dict) else int(victim.enemy)
            if receiver is not None and receiver is not authority.root and enemy==1:
                receiver.daily_kills+=1
                receiver.score+=150 if isinstance(victim,dict) else 200 if getattr(victim,'elite',False) else 100;receiver.kills+=1
                receiver.personal_kills.append(dict(victim=authority.root.unit_name(victim),expires=authority.root.feedback_clock+3.))
        g.announce_kill=types.MethodType(announce,g)
        def death(ctx,t):
            ident=getattr(t,'network_owner',None)
            if ident is not None and ident in authority.contexts:
                receiver=authority.contexts[ident]
                if getattr(t,'_lan_death_recorded',False):return
                t._lan_death_recorded=True
                if t in authority.root.allies:authority.root.allies.remove(t)
                Game.register_death(receiver,t)
                if receiver.pending_state=='lose':receiver.pending_state='spectate'
                if receiver.state=='lose':receiver.state='spectate'
                return
            if getattr(t,'last_attacker',None) is not None and authority.owner_context(t.last_attacker) not in (None,authority.root):t.player_credit=False
            Game.register_death(authority.root,t)
        g.register_death=types.MethodType(death,g)
    def accept_input(self,ident,data):
        if ident not in self.contexts or not isinstance(data,dict):return
        keys=data.get('keys',[]);mouse=data.get('mouse',[0,0])
        if not isinstance(keys,list) or len(keys)>64 or not isinstance(mouse,list) or len(mouse)!=2:return
        try:point=[max(-200000,min(200000,float(x))) for x in mouse]
        except (TypeError,ValueError):return
        if not all(math.isfinite(x) for x in point):return
        value=dict(keys=[k for k in keys if k in HELD_KEYS],mouse=point,fire=bool(data.get('fire')))
        g=self.contexts[ident];g.controls.input=value;g.controls.age=0.;self.inputs[ident]=value
        if g.artillery.enabled and isinstance(data.get('focus'),list) and len(data['focus'])==2:
            try:g.artillery.focus=V(*(max(0,min(9000,float(x))) for x in data['focus']))
            except (TypeError,ValueError):pass
    def action(self,ident,message):
        if ident not in self.contexts:return
        g=self.contexts[ident];action=message.get('action');Game=self.api['Game']
        if action=='deploy' and g.state=='deploy':
            slot=message.get('slot',g.active_vehicle_slot);base=message.get('base',0)
            if isinstance(slot,int) and 0<=slot<len(g.lineup) and g.lineup[slot] is not None and (slot not in g.used_slots or g.flight.nuke_pending):g.active_vehicle_slot=slot
            else:return
            if not isinstance(base,int) or base not in (0,1):return
            g.deploy_selected=True;g.deploy_choice=V(self.api['DEPLOY_BASES'][False][base])
            from AmmoLoadout import selected,sanitize
            v=selected(g)
            if v and isinstance(message.get('ammo_loadout'),dict):g.ammo_packs[v['id']]=sanitize(v,message['ammo_loadout'])
            previous=g.player
            if g.deploy_player(g.deploy_choice):
                if previous in self.root.allies:self.root.allies.remove(previous)
                self.bind_player(ident)
            if g.flight.nuke_used:self.team_nuke=True
            if self.team_nuke:
                for ctx in self.contexts.values():ctx.flight.nuke_used=True
            return
        if action=='nuke':
            if not self.team_nuke:g.flight.request_nuke()
            return
        if g.state!='play' or g.player.dead:return
        from Reconnaissance import toggle,mark,orbit
        if action=='ammo_select':
            slot=message.get('slot')
            if isinstance(slot,int):g.select_carried_ammo(slot)
            return
        if action=='ammo_box':g.deploy_ammo_box();return
        if action=='drone':toggle(g);return
        if action=='drone_orbit':orbit(g);return
        if action=='scout':
            point=message.get('point')
            if isinstance(point,list) and len(point)==2:
                try:
                    point=V(float(point[0]),float(point[1]))
                    if all(math.isfinite(x) for x in point):mark(g,point)
                except (TypeError,ValueError):pass
            return
        if g.drone_active:return
        if action=='radar_range':g.air.cycle_range();return
        if action=='radar_unlock':g.air.lock=None;return
        if action=='radar_target':g.air.cycle_target();return
        if action=='launcher_deploy':g.battery.toggle();g.battery.sync();return
        if action=='battery_switch':g.battery.switch();g.battery.sync();return
        if action=='launcher_place':
            point=message.get('point')
            if isinstance(point,list) and len(point)==2:
                try:
                    point=V(float(point[0]),float(point[1]))
                    if all(math.isfinite(x) for x in point):g.battery.place(point);g.battery.sync()
                except (ValueError,TypeError):pass
            return
        if action=='lock':g.air.lock_target();return
        if action=='missile':g.air.launch();return
        if action=='artillery':g.artillery.toggle();return
        methods={'ammo':g.switch_ammo,'missile_ammo':g.switch_missile,'smoke':g.deploy_smoke,'ess':g.toggle_ess,'night':lambda:g.toggle_vision('night'),'thermal':lambda:g.toggle_vision('thermal'),'xray':lambda:setattr(g,'xray',not g.xray),'extinguish':g.player.extinguish}
        if action in methods:methods[action]();return
        if action=='air_key' and g.flight.active:
            key=message.get('key')
            allowed={d['canonical'] for name,d in ACTIONS.items() if name.startswith('air.') and isinstance(d['canonical'],int)}
            if key in allowed:g.flight.event(pygame.event.Event(pygame.KEYDOWN,key=key))
    def tick_remote(self,ident,dt):
        g=self.contexts[ident];g.controls.age+=dt;g.feedback_clock=self.root.feedback_clock;g.personal_kills=[e for e in g.personal_kills if e['expires']>g.feedback_clock]
        for entry in g.messages[:]:
            entry[2]-=dt
            if entry[2]<=0:g.messages.remove(entry)
        if g.state=='wreck':
            g.death_wait=max(0,g.death_wait-dt)
            if g.death_wait<=0:g.state=g.pending_state;g.deploy_delay=g.pending_deploy_delay
        if g.state=='deploy':g.deploy_delay=max(0,g.deploy_delay-dt)
        from AbandonVehicle import step
        step(g,dt)
        from Reconnaissance import step as recon_step
        recon_step(g,dt)
        if g.drone_active:
            g.player.drive(0,0,dt,g.terrain,g.vehicles());g.player.service(dt,False);g.camera();return
        if g.state!='play' or g.player.dead:return
        g.battery.step(dt);g.battery.sync()
        keys=g.controls.keys(g.input_context());mouse=V(g.controls.input.get('mouse',g.player.p))
        if g.flight.active:g.camera();g.flight.update_controls(dt,keys,g.world_to_display(mouse),g.controls.buttons('air'));return
        p=g.player;repair=keys[pygame.K_f];p.drive(0 if repair else int(keys[pygame.K_w])-int(keys[pygame.K_s]),0 if repair else int(keys[pygame.K_d])-int(keys[pygame.K_a]),dt,g.terrain,g.vehicles())
        p.mg_cd=max(0,p.mg_cd-dt);p.service(dt,repair);p.aim_at(mouse,dt,g.terrain,g.vehicles())
        if keys[pygame.K_LCTRL] and not repair:g.machine_gun(p)
        if keys[pygame.K_g] and not repair:g.grenade_launcher(p)
        if (g.controls.buttons('ground')[0] or keys[pygame.K_SPACE]) and not repair:
            if g.artillery.enabled:g.artillery.shoot(p,mouse)
            else:g.shoot(p)
        if g.artillery.enabled:g.artillery.settle=min(1,g.artillery.settle+dt*.25)
    def tick(self,dt):
        root=self.root
        if self.final_state:
            if root.flight.nuke_animation:root.flight.nuke_animation.update(dt)
            self.sequence+=1;return
        for ident in self.contexts:
            if ident:self.tick_remote(ident,dt)
        before=root.state;root.controls.age+=dt;root.paused=False
        if before in ('deploy','spectate'):root.state='play'
        if before=='deploy':root.deploy_delay=max(0,root.deploy_delay-dt)
        root.update(dt)
        if root.state not in ('win','lose','wreck') and before in ('deploy','spectate'):root.state=before
        if root.state=='lose' and root.tickets[0]>0:root.state='spectate'
        for ident,g in self.contexts.items():
            if ident:
                g.flight.update_ordnance(dt)
                if g.flight.nuke_detonated:
                    root.flight.nuke_animation=g.flight.nuke_animation;root.flight.nuke_detonated=True;root.nuclear_result='win'
        if root.state in ('win','lose') and (min(root.tickets)<=0 or root.flight.nuke_detonated):
            self.final_state=root.state
            for g in self.contexts.values():g.state=self.final_state
        self.sequence+=1
    def disconnect(self,ident):
        if ident not in self.contexts:return
        g=self.contexts[ident];self.members[ident]['connected']=False;g.controls.input={};g.reserves=0
        if not g.player.dead:g.player.dead=True;g.player.reason='队友断开连接';self.root.register_death(g.player)
        g.state='spectate';self.root.say(self.members[ident]['name']+' 已断开连接')
    def draw(self,ident,spectator=None):
        g=self.contexts[ident]
        if g.state=='spectate' and spectator in self.contexts:g=self.contexts[spectator]
        root=self.root;old=(root.player,root.flight,root.state,root.allies)
        if g is not root:
            root.player=g.player;root.flight=g.flight;root.state=g.state
            root.allies=[u for u in old[3] if u is not g.player]+([old[0]] if not old[0].dead and not getattr(old[0],'airborne',False) else [])
        try:g.camera();g.draw()
        finally:root.player,root.flight,root.state,root.allies=old
