"""LAN lobby, validated national loadouts and unanimous ready gate."""
import socket,pygame
from LANTransport import Transport,PORT,PROTOCOL,local_addresses
from Garage import CATALOG,NATIONS,combined_br
from BattleMaps import choose_map

def configuration(profile):
    country=profile.country
    return dict(late_join=bool(getattr(profile,'late_join',False)),country=country,lineup=list(profile.lineups[country]),slot=profile.active[country],ammo=dict(profile.ammo_choices),missiles=dict(profile.missile_choices),weapons=profile.aviation.weapons)

def validate_config(data):
    if not isinstance(data,dict):raise ValueError('编成无效')
    country=data.get('country');lineup=data.get('lineup');slot=data.get('slot',0)
    if not isinstance(country,str) or country not in NATIONS or not isinstance(lineup,list) or len(lineup) not in (8,12):raise ValueError('编成无效')
    equipped=[k for k in lineup if k is not None]
    if any(not isinstance(k,str) for k in equipped):raise ValueError("载具编成无效")
    if not equipped or len(set(equipped))!=len(equipped) or any(k not in CATALOG or CATALOG[k]['country']!=country for k in equipped):raise ValueError('国家或载具编成无效')
    if not isinstance(slot,int) or not 0<=slot<len(lineup) or lineup[slot] is None:slot=next(i for i,k in enumerate(lineup) if k)
    return dict(late_join=data.get('late_join') is True,country=country,lineup=lineup,slot=slot,ammo=data.get('ammo',{}) if isinstance(data.get('ammo'),dict) else {},missiles=data.get('missiles',{}) if isinstance(data.get('missiles'),dict) else {},weapons=data.get('weapons',{}) if isinstance(data.get('weapons'),dict) else {})

class Room:
    def __init__(self,profile):
        self.profile=profile;self.net=None;self.host=False;self.my_id=None;self.members={};self.open=False;self.ip='';self.notice='先在机库选择编成，再创建或加入小队';self.started=None;self.heartbeat=0.;self.pending_start=None;self.ip_focused=False;self.ip_selected=False;self.ip_cursor=0
        self.name=('玩家 '+socket.gethostname())[:24]
    def create(self,port=PORT,address=''):
        self.close();self.net=Transport(True,address,port);self.host=True;self.my_id=0
        self.members={0:dict(id=0,name=self.name,config=validate_config(configuration(self.profile)),ready=False,connected=True)}
        self.open=True;self.notice='房间已创建 · 主机也需要准备';self.ips=local_addresses();self.publish()
    def join(self,address,port=PORT):
        self.close();self.net=Transport(False,address,port);self.host=False;self.open=True;self.notice='正在加入小队…'
        self.net.send(0,dict(type='hello',protocol=PROTOCOL,name=self.name,config=configuration(self.profile)))
    def public(self):return [self.members[k] for k in sorted(self.members)]
    @property
    def all_ready(self):return bool(self.members) and len(self.members)<=4 and all(m['ready'] and m.get('connected',True) for m in self.members.values())
    @property
    def battle_br(self):return max((combined_br(m['config']['lineup']) for m in self.members.values()),default=1.)
    def publish(self):
        if self.net:self.net.broadcast(dict(type='lobby',members=self.public(),br=self.battle_br))
    def ready(self):
        if self.my_id not in self.members:return
        value=not self.members[self.my_id]['ready']
        if self.host:self.members[self.my_id]['ready']=value;self.publish()
        else:self.net.send(0,dict(type='ready',ready=value))
    def start(self):
        if not self.host or not self.all_ready:return False
        self.started=dict(late_join=bool(getattr(self.profile,'late_join',False)),type='start',protocol=PROTOCOL,map_id=choose_map(),br=self.battle_br,members=self.public());self.net.broadcast(self.started);self.open=False;return True
    def handle(self,peer,msg):
        kind=msg.get('type')
        if self.host:
            if kind=='hello':
                if self.started or len(self.members)>=4 or msg.get('protocol')!=PROTOCOL:
                    self.net.send(peer,dict(type='error',message='房间已开战、已满，或游戏版本不一致'));self.net.peers[peer]['closing']=True;return
                try:config=validate_config(msg.get('config'))
                except ValueError as e:self.net.send(peer,dict(type='error',message=str(e)));self.net.peers[peer]['closing']=True;return
                if peer in self.members:return
                self.members[peer]=dict(id=peer,name=str(msg.get('name','玩家'))[:24],config=config,ready=False,connected=True)
                for m in self.members.values():m['ready']=False
                self.net.send(peer,dict(type='welcome',id=peer));self.publish()
            elif kind=='ready' and peer in self.members:self.members[peer]['ready']=bool(msg.get('ready'));self.publish()
            elif kind=='disconnected' and peer in self.members:
                self.members.pop(peer)
                for m in self.members.values():m['ready']=False
                self.notice='有成员离开，请重新准备';self.publish()
        else:
            if kind=='welcome':self.my_id=msg['id']
            elif kind=='lobby':self.members={m['id']:m for m in msg['members']};self.notice='等待所有成员准备，再由主机开始'
            elif kind=='start':self.started=msg;self.open=False
            elif kind in ('error','disconnected'):
                self.notice=msg.get('message',msg.get('reason','主机连接已断开'));self.close(keep_notice=True);self.open=True
    def update(self,dt):
        if not self.net:return
        self.heartbeat+=dt
        if self.heartbeat>2:
            self.heartbeat=0
            if self.host:self.net.broadcast(dict(type='ping'))
            else:self.net.send(0,dict(type='ping'))
        for peer,msg in self.net.pump():self.handle(peer,msg)
    def close(self,keep_notice=False):
        if self.net:self.net.close()
        self.net=None;self.members={};self.my_id=None;self.started=None;self.host=False
        if not keep_notice:self.notice='先在机库选择编成，再创建或加入小队'
    @staticmethod
    def ip_box():return pygame.Rect(680,176,350,42)
    def insert_ip(self,value):
        value=''.join(c for c in value if c in '0123456789.')
        if not value:return
        if self.ip_selected:self.ip='';self.ip_cursor=0;self.ip_selected=False
        value=value[:max(0,45-len(self.ip))]
        self.ip=self.ip[:self.ip_cursor]+value+self.ip[self.ip_cursor:];self.ip_cursor+=len(value)
    def event(self,event):
        if event.type==pygame.KEYDOWN:
            if event.key==pygame.K_ESCAPE:self.close();self.open=False;return
            if not self.net:
                if event.key==pygame.K_TAB:self.ip_focused=True;self.ip_cursor=len(self.ip);return
                if not self.ip_focused:return
                mods=getattr(event,'mod',pygame.key.get_mods())
                if event.key==pygame.K_RETURN:
                    try:self.join(self.ip)
                    except (OSError,ValueError) as e:self.notice='连接失败：'+str(e)[:75]
                    return
                if mods & pygame.KMOD_CTRL:
                    if event.key==pygame.K_a:self.ip_selected=True
                    elif event.key==pygame.K_v:
                        try:self.insert_ip(pygame.scrap.get_text().strip())
                        except pygame.error:self.notice='无法读取剪贴板，请直接输入主机 IP'
                    return
                if event.key in (pygame.K_BACKSPACE,pygame.K_DELETE):
                    if self.ip_selected:self.ip='';self.ip_cursor=0
                    elif event.key==pygame.K_BACKSPACE and self.ip_cursor>0:
                        self.ip=self.ip[:self.ip_cursor-1]+self.ip[self.ip_cursor:];self.ip_cursor-=1
                    elif event.key==pygame.K_DELETE:self.ip=self.ip[:self.ip_cursor]+self.ip[self.ip_cursor+1:]
                    self.ip_selected=False
                elif event.key in (pygame.K_LEFT,pygame.K_RIGHT,pygame.K_HOME,pygame.K_END):
                    self.ip_cursor=0 if event.key==pygame.K_HOME else len(self.ip) if event.key==pygame.K_END else max(0,min(len(self.ip),self.ip_cursor+(-1 if event.key==pygame.K_LEFT else 1)));self.ip_selected=False
                else:
                    # Physical digit keys also work while gameplay disables IME/text input.
                    digits={getattr(pygame,'K_KP'+str(i)):str(i) for i in range(10)}
                    digits.update({pygame.K_0+i:str(i) for i in range(10)})
                    digits.update({pygame.K_PERIOD:'.',pygame.K_KP_PERIOD:'.'})
                    self.insert_ip(digits.get(event.key,getattr(event,'unicode','')))
            elif event.key==pygame.K_RETURN:
                if self.host and self.all_ready:self.start()
                else:self.ready()
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            pos=event.pos
            if not self.net:
                self.ip_focused=self.ip_box().collidepoint(pos);self.ip_selected=False;self.ip_cursor=len(self.ip)
                if self.ip_focused:return
            if pygame.Rect(20,740,160,45).collidepoint(pos):self.close();self.open=False;return
            try:
                if not self.net:
                    if pygame.Rect(230,230,350,65).collidepoint(pos):self.create()
                    elif pygame.Rect(680,230,350,65).collidepoint(pos):self.join(self.ip)
                else:
                    if pygame.Rect(440,710,190,50).collidepoint(pos):self.ready()
                    elif pygame.Rect(680,710,190,50).collidepoint(pos):self.start()
            except (OSError,ValueError) as e:self.notice='连接失败：'+str(e)[:75]
    def draw(self,screen,text):
        screen.fill((18,28,28));text('局域网小队 · 最多 4 人',(640,45),30,(211,230,205),True)
        text(self.notice,(640,95),18,(235,208,148),True)
        def button(rect,label,enabled=True):
            pygame.draw.rect(screen,(66,104,84) if enabled else (37,47,43),rect,border_radius=7);text(label,rect.center,20,(227,236,218) if enabled else (128,142,128),True)
        button(pygame.Rect(20,740,160,45),'返回机库')
        if not self.net:
            text('主机：创建房间，告诉队友本机 IP',(230,180),18)
            text('队友：输入主机的局域网 IPv4 地址',(680,145),18)
            box=self.ip_box();pygame.draw.rect(screen,(48,66,58),box,border_radius=5)
            pygame.draw.rect(screen,(164,219,171) if self.ip_focused else (87,112,98),box,2,border_radius=5)
            if self.ip_selected:pygame.draw.rect(screen,(68,107,122),(688,183,max(10,len(self.ip)*11),28),border_radius=3)
            text(self.ip or '点击输入主机 IP，可 Ctrl+V 粘贴',(690,187),18)
            if self.ip_focused and pygame.time.get_ticks()%1000<550:
                font=pygame.font.Font(pygame.font.match_font('microsoftyahei,simhei,segoeui'),18)
                x=690+font.size(self.ip[:self.ip_cursor])[0];pygame.draw.line(screen,(220,235,214),(x,184),(x,207),2)
            button(pygame.Rect(230,230,350,65),'创建小队 / 成为主机');button(pygame.Rect(680,230,350,65),'加入小队')
            text('当前编成：'+NATIONS[self.profile.country]['name']+f' · BR {combined_br(self.profile.lineups[self.profile.country]):.1f}',(230,345),20)
            text('所有人准备后开局 · 分房取成员最高权重 · 载具耗尽后观战队友',(230,399),18)
            return
        if self.host:text('主机 IP：'+' / '.join(self.ips)+'  ·  端口 '+str(self.net.port),(230,139),20,(160,220,229))
        else:text('已连接主机 · 小队最高 BR '+f'{self.battle_br:.1f}',(230,139),20,(160,220,229))
        for row,m in enumerate(self.public()):
            rect=pygame.Rect(230,195+row*115,820,100);pygame.draw.rect(screen,(36,55,48),rect,border_radius=8)
            c=m['config'];text(('主机 · ' if m['id']==0 else '队友 · ')+m['name']+('（你）' if m['id']==self.my_id else ''),(245,rect.y+12),20)
            text(NATIONS[c['country']]['name']+f" · 编成 BR {combined_br(c['lineup']):.1f} · {sum(k is not None for k in c['lineup'])}/12 辆",(245,rect.y+47),18,(181,209,184))
            text('已准备' if m['ready'] else '未准备',(985,rect.y+40),20,(151,234,154) if m['ready'] else (239,176,112),True)
        own=self.members.get(self.my_id,{})
        button(pygame.Rect(440,710,190,50),'取消准备' if own.get('ready') else '准备')
        button(pygame.Rect(680,710,190,50),'主机开始' if self.host else '等待主机',self.host and self.all_ready)
        text(f'小队最高 BR {self.battle_br:.1f} · {len(self.members)}/4 人 · 全员准备才可开始',(640,675),18,(224,211,166),True)
