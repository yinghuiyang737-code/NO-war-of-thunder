"""Passive radar warning and equipment-gated missile approach display."""
import math
import pygame
from pygame.math import Vector2 as V
from AircraftPhysics import bearing,difference,direction

class Warnings:
    def __init__(self,flight):self.f=flight;self.enabled=True;self.clock=0.;self.contacts=[]
    def toggle(self):
        self.enabled=not self.enabled;self.contacts=[]
        equipment=self.f.plane.stats['warning']
        self.f.g.say('此机没有告警设备' if not (equipment['rwr'] or equipment['maw']) else '告警界面已'+('开启' if self.enabled else '关闭'))
    def update(self,dt):
        self.clock+=dt;f=self.f
        if not f.active or not self.enabled:self.contacts=[];return
        p=f.plane;g=f.g;equipment=p.stats['warning'];rwr=equipment['rwr'];found=[]
        def mine(target):
            return target is f.record or target is p or isinstance(target,dict) and (target.get('controlled') is p or target.get('ai_plane') is p)
        def add(identity,pos,level,label,team=1,hold=1.5):
            contact=next((c for c in self.contacts if c['id']==identity),None)
            data=dict(id=identity,pos=V(pos),level=level,label=label,team=team,until=self.clock+hold)
            if contact:contact.update(data)
            else:self.contacts.append(data)
            found.append(identity)
        if rwr:
            for q in g.air.planes:
                radar=q.get('radar');source=q.get('ai_plane') or q.get('controlled')
                if q is f.record or q['dead'] or not source or not radar or not radar.enabled or radar.kind in ('none','ranging','ground') or radar.mode=='AG':continue
                delta=p.p-source.p
                if delta.length()>min(rwr['range'],radar.maximum*1.3)*8000 or abs(difference(bearing(delta),source.a))>radar.sector:continue
                locked=mine(radar.stt) and radar.mode not in ('TWS','RAM') and radar.has_track(radar.stt)
                az=difference(bearing(delta),source.a)
                if not locked and abs(difference(az,radar.beam))>10:continue
                if radar.stt is not None and radar.mode not in ('TWS','RAM') and not locked:continue
                add(('air',id(q)),source.p,2 if locked and rwr['tracking'] else 1,'空中雷达',q.get('team',1),max(1.5,radar.period*1.2))
            for tank in g.enemies+g.allies:
                from RadarContacts import ground_fit
                if tank.dead or not tank.stats.get('radar') or tank.p.distance_to(p.p)>min(ground_fit(tank)[0]*getattr(tank,'radar_scale',1.),rwr['range'])*8000:continue
                locked=mine(getattr(tank,'ai_air_target',None)) or tank is getattr(g,'player',None) and mine(g.air.lock)
                az=bearing(p.p-tank.p)
                if not locked and abs(difference(az,g.air.scan_clock*120))>12:continue
                add(('ground',id(tank)),tank.p,2 if locked and rwr['tracking'] else 1,'地面雷达',int(tank.enemy),3.2)
        from RadarContacts import missiles
        for m in missiles(g):
            if m.get('life',0)<=0:continue
            if m.get('team',1)==p.team:continue
            if not mine(m.get('target')):
                relative=V(m['v'])-direction(p.a)*p.speed;offset=p.p-m['p']
                if relative.length_squared()<1 or offset.dot(relative)<=0 or abs(offset.cross(relative))/relative.length()>1000:continue
            delta=p.p-m['p'];distance=delta.length();owner=m.get('owner');source=m.get('source')
            from Countermeasures import guidance as seeker_type
            guidance=seeker_type(m)
            radar_command=guidance=='COMMAND' and owner is not None and owner.stats.get('radar') and owner.stats.get('branch')==3
            radar_guided=guidance in ('SARH','ARH','RADAR') or radar_command
            if m.get('kind')=='agm' or any(tag in str((m.get('ammo') or {}).get('type','')).upper() for tag in ('ATGM','AGM')):radar_guided=False
            approaching=(V(m['v'])-direction(p.a)*p.speed).dot(delta)>0
            maw=equipment['maw'] and distance<48000 and approaching
            launch=bool(rwr and rwr['launch'] and radar_guided and distance<rwr['range']*8000)
            if guidance=='SARH':launch=launch and f.illumination(m,m.get('target'))
            if not (maw or launch):continue
            # A passive RWR indicates the illuminating emitter, not a magic missile position.
            pos=m['p'] if maw or guidance=='ARH' else source['p'] if source else owner.p if owner is not None else m['p']
            add(('missile',id(m)),pos,3,'导弹逼近' if maw else '雷达导弹',m.get('team',int(owner.enemy) if owner is not None else 1),.5)
        self.contacts=[c for c in self.contacts if c['until']>self.clock]
        self.contacts.sort(key=lambda c:-c['level'])
    def draw(self,s,text):
        f=self.f
        if not f.active:return
        p=f.plane;e=p.stats['warning'];rwr=e['rwr']
        if not rwr and not e['maw']:return
        dx=s.get_width()-1280
        rect=pygame.Rect(1028+dx,302,235,205);pygame.draw.rect(s,(11,24,24),rect,border_radius=7)
        text((rwr['model'] if rwr else 'MAW')+(' + MAW' if rwr and e['maw'] else ''),(1038+dx,310),14,(181,220,182))
        if not self.enabled:text('告警已关闭',(1064+dx,398),18,(145,166,154));return
        center=V(1145+dx,410);radius=60
        for r in (30,60):pygame.draw.circle(s,(52,91,72),center,r,1)
        pygame.draw.line(s,(65,115,91),center+V(0,-65),center+V(0,65));pygame.draw.line(s,(65,115,91),center+V(-65,0),center+V(65,0))
        pygame.draw.polygon(s,(180,223,179),[center+V(0,-10),center+V(-5,7),center+V(5,7)])
        text('前',(1138+dx,334),14);text('后',(1138+dx,474),14)
        for c in self.contacts[:8]:
            angle=math.radians(bearing(c['pos']-p.p)-p.a-90);offset=V(math.cos(angle),math.sin(angle))
            col=(246,101,79) if c['level']==3 else (247,196,99) if c['level']==2 else (177,211,150)
            if rwr and rwr['iff'] and c['team']==p.team:col=(121,180,238)
            if c['level']>=2 and int(self.clock*5)%2:col=tuple(int(v*.55) for v in col)
            point=center+offset*(43 if c['level']==3 else 60)
            pygame.draw.line(s,col,center+offset*18,point,2 if c['level']>=2 else 1)
            pygame.draw.circle(s,col,point,5,2)
            label='M' if c['level']==3 else 'S' if c['label']=='地面雷达' else 'A'
            text(label,point+V(5,-7),14,col)
        highest=max((c['level'] for c in self.contacts),default=0)
        text(('无告警','雷达搜索','雷达锁定','导弹告警')[highest],(1038+dx,488),14,(247,151,100) if highest>=2 else (160,198,166))
        if highest==3:
            text('导弹告警 · '+f.g.controls.label('air.counter')+' 干扰弹',(640,86),24,(255,115,86),center=True)


