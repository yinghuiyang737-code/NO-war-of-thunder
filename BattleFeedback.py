"""Enemy-only hit analysis, kill feeds and a short post-destruction view."""
import pygame
from pygame.math import Vector2 as V

def install(Game,api):
    previous={k:getattr(Game,k) for k in ('__init__','register_death','update','draw','deploy_player','camera')}
    def init(self,*a,**kw):
        previous['__init__'](self,*a,**kw)
        self.player.is_user=True
        self.player.user_vehicle_name=self.flight.plane.stats['name'] if self.flight.active else self.player.stats.get('name','坦克')
        self.daily_kills=0;self.feedback_clock=0.;self.kill_feed=[];self.personal_kills=[];self.death_wait=0.;self.pending_state=None;self.player_death_handled=False
        old_kill=self.air.kill_plane
        def kill_plane(q,owner=None):
            if q['dead']:return
            attacker=owner if owner is not None else q.get('last_attacker')
            old_kill(q,owner)
            if q['dead'] and not q.get('feedback_announced'):
                q['feedback_announced']=True
                # The controlled plane's death is already announced through its player anchor.
                if not q.get('controlled'):self.announce_kill(attacker,q,q.get('last_weapon',''))
        self.air.kill_plane=kill_plane
    def record_hit(self,target,result,owner,weapon=''):
        if not self.is_player(owner) or not target.enemy or result.get('continue'):return
        result=dict(result,weapon=weapon)
        self.hitview=(target,result,self.time+4.)
    def record_air_hit(self,target,point,owner,weapon=''):
        if not self.is_player(owner) or target.get('team',1)==0:return
        plane=target.get('ai_plane') or (target['controlled'].plane if target.get('controlled') else None)
        result=dict(kind='空中目标命中',weapon=weapon,point=V(point),modules=dict(plane.modules) if plane else None)
        self.hitview=(target,result,self.time+4.)
    def name(self,unit):
        if unit is None:return '环境 / 坠毁'
        if self.is_player(unit):
            model=self.flight.plane.stats if getattr(unit,'airborne',False) and self.flight.plane else unit.stats
            return getattr(unit,'user_vehicle_name',model.get('name','坦克'))
        if isinstance(unit,dict):return unit.get('model',{}).get('name','飞机')
        return unit.stats.get('name','坦克')
    def announce_kill(self,attacker,victim,weapon=''):
        team=victim.get('team',1) if isinstance(victim,dict) else int(victim.enemy)
        attacker_team=attacker.get('team',1) if isinstance(attacker,dict) else int(attacker.enemy) if attacker is not None else -1
        if not weapon:weapon='坠毁 / 环境' if attacker is None else '未知弹药'
        event=dict(attacker=self.unit_name(attacker),victim=self.unit_name(victim),weapon=weapon,team=team,attacker_team=attacker_team,expires=self.feedback_clock+8.)
        self.kill_feed.append(event);self.kill_feed=self.kill_feed[-5:]
        if self.is_player(attacker) and team==1:
            self.daily_kills+=1
            self.personal_kills.append(dict(victim=self.unit_name(victim),expires=self.feedback_clock+3.));self.personal_kills=self.personal_kills[-3:]
    def death(self,t):
        player=t is self.player
        if player and self.player_death_handled:return
        active=player or t in self.allies or t in self.enemies
        attacker=getattr(t,'last_attacker',None);weapon=getattr(t,'last_weapon','')
        previous['register_death'](self,t)
        if not active:return
        self.announce_kill(attacker,t,weapon)
        if player and self.state in ('deploy','lose'):
            self.player_death_handled=True;self.pending_state=self.state;self.pending_deploy_delay=max(0,self.deploy_delay-4.)
            self.death_wait=4.;self.state='wreck';self.paused=False
            self.death_camera=V(self.player.p)-V(api['W']/self.zoom/2,api['VIEW'].h/self.zoom/2+api['VIEW'].top)
            self.cam=V(self.death_camera)
    def camera(self,*a,**kw):
        if getattr(self,'player_death_handled',False) and self.death_wait>0:
            self.cam=V(self.death_camera);return
        previous['camera'](self,*a,**kw)
    def update(self,dt):
        if not self.paused:
            self.feedback_clock+=dt
            self.kill_feed=[e for e in self.kill_feed if e['expires']>self.feedback_clock]
            self.personal_kills=[e for e in self.personal_kills if e['expires']>self.feedback_clock]
        if self.state=='wreck':
            if self.paused:return
            wait_before=self.death_wait
            # Continue the actual battle while the camera stays with the destroyed vehicle.
            self.state='play';previous['update'](self,dt)
            if self.state in ('win','lose'):return
            self.death_wait=max(0,self.death_wait-dt)
            if self.death_wait>0:self.state='wreck'
            else:
                self.state=self.pending_state;self.deploy_delay=max(0,self.pending_deploy_delay-max(0,dt-wait_before))
            return
        previous['update'](self,dt)
    def deploy(self,*a,**kw):
        result=previous['deploy_player'](self,*a,**kw)
        if result:
            self.player.is_user=True;self.player.user_vehicle_name=self.flight.plane.stats['name'] if self.flight.active else self.player.stats.get('name','坦克')
            self.player_death_handled=False;self.pending_state=None;self.death_wait=0.
        return result
    def is_player(self,unit):return unit is self.player or (unit is not None and not isinstance(unit,dict) and getattr(unit,'is_user',False))
    def draw_hit(self):
        if not self.hitview or self.hitview[2]<=self.time:return
        target,hit,_=self.hitview;s=api['screen'];text=api['text'];r=pygame.Rect(s.get_width()-260,530 if self.flight.active else 300,242,205)
        text('命中分析 · '+hit['kind'][:10],(r.x+12,r.y+10),18)
        if isinstance(target,dict):
            from Aviation import draw_aircraft
            if target.get('model'):draw_aircraft(s,target['model'],(r.centerx,r.y+88),.35,0,units=8)
            modules=hit.get('modules') or {};labels={'pilot':'飞行员','engine':'发动机','left_wing':'左机翼','right_wing':'右机翼'}
            text(' / '.join(labels[k] for k,v in modules.items() if v<2) or '命中机体',(r.x+12,r.bottom-48),14,(239,181,118))
        else:
            old=s.get_clip();s.set_clip(r);self.schematic(target,(r.x+96,r.y+111),1.7,hit);s.set_clip(old)
            text((' / '.join(api['LABELS'][k] for k in hit['modules']))[:18] or '装甲阻挡弹丸',(r.x+12,r.bottom-48),14,(239,181,118))
        text(hit.get('weapon','')[:23],(r.x+12,r.bottom-24),14,(163,180,148))
    def draw_battle_feedback(self):
        s=api['screen'];text=api['text']
        if self.state!='deploy':self.draw_hit()
        if self.kill_feed:
            feed=self.kill_feed[-(4 if s.get_height()>=950 else 2):];rect=pygame.Rect(350,280,min(482,s.get_width()-630),32+len(feed)*51)
            text('全局击杀 · 蓝：己方 / 橙：敌方',(rect.x+10,rect.y+6),16,(189,210,192))
            def line(label,pos,color):
                rendered=api['fonts'][14].render(label,True,color)
                if rendered.get_width()>rect.w-20:rendered=pygame.transform.smoothscale(rendered,(rect.w-20,max(11,int(rendered.get_height()*(rect.w-20)/rendered.get_width()))))
                s.blit(rendered,pos)
            for i,e in enumerate(feed):
                color=(239,180,130) if e['attacker_team']==1 else (153,203,235) if e['attacker_team']==0 else (185,190,177)
                line(e['attacker']+' ['+e['weapon']+']',(rect.x+10,rect.y+32+i*51),color)
                line('→ '+e['victim'],(rect.x+24,rect.y+53+i*51),(239,180,130) if e['team'] else (153,203,235))
        if self.personal_kills:
            text('摧毁目标'+(f" ×{len(self.personal_kills)}" if len(self.personal_kills)>1 else ''),(s.get_width()/2,max(150,s.get_height()*.22)),30,(255,220,139),True)
            text(self.personal_kills[-1]['victim'],(s.get_width()/2,max(150,s.get_height()*.22)+39),18,(244,223,188),True)
        if self.state=='wreck':
            rect=pygame.Rect(s.get_width()//2-250,s.get_height()//2-55,500,110);pygame.draw.rect(s,(24,29,26),rect,border_radius=8)
            text('载具被摧毁',(rect.centerx,rect.y+25),30,(244,167,123),True)
            text(f"{self.death_wait:.1f} 秒后"+('进入部署' if self.pending_state=='deploy' else '进入队友观战' if self.pending_state=='spectate' else '显示战斗结果'),(rect.centerx,rect.y+74),18,(218,220,194),True)
    def draw(self,*a,**kw):
        previous['draw'](self,*a,**kw);draw_battle_feedback(self)
    Game.draw_battle_feedback=draw_battle_feedback
    for key,value in [('__init__',init),('is_player',is_player),('record_hit',record_hit),('record_air_hit',record_air_hit),('unit_name',name),('announce_kill',announce_kill),('register_death',death),('update',update),('deploy_player',deploy),('draw_hit',draw_hit),('draw',draw),('camera',camera)]:setattr(Game,key,value)
