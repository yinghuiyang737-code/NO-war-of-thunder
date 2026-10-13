"""LAN battle controller, semantic inputs and teammate spectating."""
import pygame
from pygame.math import Vector2 as V
from LANBattle import Authority,HELD_KEYS
from LANSnapshot import Snapshot,Replica

class Session:
    def __init__(self,room,api,start):
        self.room=room;self.api=api;self.controls=api['get_controls']() if 'get_controls' in api else __import__('InputBindings').get_controls();self.my_id=room.my_id;self.host=room.host;self.exit=False;self.to_lobby=False;self.notice='';self.spectator=None;self.send_time=0.;self.snapshot_time=0.;self.latest=None;self.last_seq=-1
        if self.host:
            self.authority=Authority(api,start,self.controls);self.snapshot=Snapshot(self.authority);self.replica=None;self.g=self.authority.root
        else:self.authority=None;self.snapshot=None;self.replica=Replica(api,start,self.my_id);self.g=self.replica.g
    def own_state(self):
        if self.host:return self.authority.contexts[self.my_id].state
        if self.latest:return self.latest['players'][str(self.my_id)]['fields']['state']
        return 'deploy'
    def input_context(self):
        state=self.own_state()
        if state=='spectate':return 'spectate'
        if state in ('deploy','wreck'):return state
        if state in ('win','lose'):return 'result'
        return 'drone' if self.g.drone_active else 'air' if self.g.flight.active else 'ground'
    def issue(self,action,**kwargs):
        message=dict(type='action',action=action,**kwargs)
        if self.host:self.authority.action(self.my_id,message)
        else:self.room.net.send(0,message)
    def confirm_deploy(self):
        g=self.g
        if not g.deploy_selected or g.deploy_delay>0:return
        base=min(range(2),key=lambda i:g.deploy_choice.distance_squared_to(self.api['DEPLOY_BASES'][False][i]))
        from AmmoLoadout import selected,preset
        v=selected(g)
        self.issue('deploy',slot=g.active_vehicle_slot,base=base,ammo_loadout=dict(preset(g,v)) if v else {})
    def candidates(self):
        if self.host:return [i for i,g in self.authority.contexts.items() if i!=self.my_id and not g.player.dead and g.state=='play' and self.authority.members[i].get('connected',True)]
        if not self.latest:return []
        ids=[]
        for i,packet in self.latest['players'].items():
            if int(i)==self.my_id or packet['fields']['state']!='play':continue
            t=self.replica.objects.get(packet['player'])
            if t is not None and not t.dead:ids.append(int(i))
        return ids
    def cycle_spectator(self,delta=1):
        pool=self.candidates()
        if not pool:self.spectator=None;return
        if self.spectator not in pool:self.spectator=pool[0]
        else:self.spectator=pool[(pool.index(self.spectator)+delta)%len(pool)]
        if self.replica and self.latest:self.replica.apply(self.latest,self.spectator)
    def restart(self):
        if not self.host:self.notice='由主机返回小队大厅，再全员准备开局';return
        for member in self.room.members.values():member['ready']=False
        self.room.members={i:m for i,m in self.room.members.items() if m.get('connected',True)}
        self.room.started=None;self.room.open=True;self.room.net.broadcast(dict(type='return_lobby',members=self.room.public()));self.room.publish();self.to_lobby=True
    def event(self,event):
        state=self.own_state();g=self.g
        if event.type==pygame.KEYDOWN:
            key=event.key
            if key==pygame.K_ESCAPE:self.exit=True;return
            if key==pygame.K_r:self.restart();return
            if key==pygame.K_p:self.notice='局域网战斗持续进行，不能单独暂停';return
            if state=='spectate':
                if key in (pygame.K_RIGHT,pygame.K_LEFT):self.cycle_spectator(1 if key==pygame.K_RIGHT else -1)
                return
            if key==pygame.K_RETURN and state=='deploy':self.confirm_deploy();return
            if key==pygame.K_k:self.issue('nuke');return
            if state!='play':return
            if g.flight.active:self.issue('air_key',key=key);return
            if pygame.K_1<=key<=pygame.K_9 or key==pygame.K_0:self.issue('ammo_select',slot=9 if key==pygame.K_0 else key-pygame.K_1);return
            if key==pygame.K_u:self.issue('drone');return
            if key==pygame.K_t:self.issue('scout',point=list(g.screen_to_world(pygame.mouse.get_pos())));return
            if key==pygame.K_F6 and g.drone_active:self.issue('drone_orbit');return
            if g.drone_active:return
            actions={pygame.K_BACKSPACE:'radar_unlock',pygame.K_F3:'ammo_box',pygame.K_F2:'radar_range',pygame.K_y:'radar_target',pygame.K_F11:'launcher_deploy',pygame.K_F12:'battery_switch',pygame.K_b:'ammo',pygame.K_m:'missile_ammo',pygame.K_o:'artillery',pygame.K_z:'smoke',pygame.K_h:'ess',pygame.K_q:'lock',pygame.K_j:'missile',pygame.K_n:'night',pygame.K_v:'thermal',pygame.K_e:'extinguish',pygame.K_x:'xray'}
            if key in actions:self.issue(actions[key])
        elif event.type==pygame.MOUSEWHEEL:
            if self.host:
                view=self.authority.contexts.get(self.spectator,self.g) if state=='spectate' else self.g;view.change_zoom(event.y)
            else:g.change_zoom(event.y)
        elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1 and state=='play' and not g.player.dead and g.battery.placing:
            self.issue('launcher_place',point=list(g.screen_to_world(event.pos)))
        elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1 and state=='deploy':
            if g.flight.nuke_button().collidepoint(event.pos):self.issue('nuke')
            elif g.deployment_button().collidepoint(event.pos):self.confirm_deploy()
            else:g.choose_deployment(event.pos)
    def capture_input(self):
        context=self.input_context();g=self.g
        if self.controls.open or context not in ('ground','air'):return dict(keys=[],mouse=list(g.player.p),fire=False)
        keys=self.controls.keys(context);value=dict(keys=[k for k in HELD_KEYS if keys[k]],mouse=list(g.screen_to_world(pygame.mouse.get_pos())),fire=bool(self.controls.buttons(context)[0]))
        if g.artillery.enabled:value['focus']=list(g.artillery.focus)
        return value
    def handle(self,peer,msg):
        kind=msg.get('type')
        if self.host:
            if kind=='input':self.authority.accept_input(peer,msg.get('input'))
            elif kind=='action':self.authority.action(peer,msg)
            elif kind=='disconnected':
                self.authority.disconnect(peer)
                if peer in self.room.members:self.room.members[peer]['connected']=False
            elif kind=='hello':self.room.handle(peer,msg)
        else:
            if kind=='snapshot':
                if msg.get('seq',-1)<self.last_seq:return
                self.last_seq=msg['seq'];self.latest=msg
                state=msg['players'][str(self.my_id)]['fields']['state']
                self.replica.apply(msg,self.spectator if state=='spectate' else None)
                if state=='spectate' and self.spectator not in self.candidates():self.cycle_spectator()
            elif kind=='return_lobby':
                self.room.members={m['id']:m for m in msg['members']};self.room.started=None;self.room.open=True;self.to_lobby=True
            elif kind=='lobby':self.room.handle(peer,msg)
            elif kind in ('disconnected','error'):
                self.notice='主机连接已断开，已结束本地联机';self.room.notice=self.notice;self.exit=True
    def update(self,dt):
        if not self.room.net:self.exit=True;return
        for peer,msg in self.room.net.pump():self.handle(peer,msg)
        if self.exit or self.to_lobby:return
        value=self.capture_input()
        if self.host:
            self.authority.accept_input(self.my_id,value);self.authority.tick(dt)
            if self.own_state()=='spectate' and self.spectator not in self.candidates():self.cycle_spectator()
            self.snapshot_time+=dt
            if self.snapshot_time>=.05:
                self.snapshot_time=0.;self.room.net.broadcast(self.snapshot.build())
        else:
            self.send_time+=dt
            if self.send_time>=1/30:self.send_time=0.;self.room.net.send(0,dict(type='input',input=value))
            self.replica.render_update(dt)
    def draw(self):
        if self.host:self.authority.draw(self.my_id,self.spectator)
        else:self.g.draw()
        s=self.api['screen'];text=self.api['text'];members=self.authority.members if self.host else self.replica.members
        active=sum(m.get('connected',True) for m in members.values())
        text(f'局域网小队 {active}/4 · '+('你是主机' if self.host else '主机同步')+f' · BR {self.g.battle_br:.1f}',(18,121),14,(164,226,238))
        if self.own_state()=='spectate':
            target=members.get(self.spectator,{}).get('name','暂无存活队友，等待战斗结束')
            pygame.draw.rect(s,(19,31,30),(350,68,660,49),border_radius=5)
            text('载具已耗尽 · 观战 '+target,(680,82),20,(219,232,177),True)
            text(self.controls.label('common.spectate_prev')+' / '+self.controls.label('common.spectate_next')+' 切换队友',(680,105),14,(180,214,191),True)
        if self.notice:text(self.notice,(640,766),16,(243,201,129),True)

