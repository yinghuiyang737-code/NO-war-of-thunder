"""Configurable keyboard, mouse and wheel bindings with contextual actions."""
import os,sys,json,time
import pygame

def key(k):return 'key:'+str(k)
def mouse(n):return 'mouse:'+str(n)
MODIFIER_KEYS=(pygame.K_LCTRL,pygame.K_RCTRL,pygame.K_LSHIFT,pygame.K_RSHIFT,pygame.K_LALT,pygame.K_RALT,pygame.K_LGUI,pygame.K_RGUI)
def chord(*tokens):
    parts=set(part for token in tokens for part in token.split('+'))
    order={key(k):i for i,k in enumerate(MODIFIER_KEYS)}
    return '+'.join(sorted(parts,key=lambda part:(order.get(part,100),part)))
GROUPS=[('common','通用'),('ground','地面'),('air','飞机'),('deploy','部署'),('garage','机库')]
ACTIONS={}
def add(group,ident,label,canonical,tokens,contexts=None):
    ACTIONS[group+'.'+ident]=dict(group=group,label=label,canonical=canonical,defaults=tokens,contexts=contexts or ([group] if group!='common' else ['ground','air','deploy','wreck','garage','result']))
add('common','scoreboard','按住查看战绩',pygame.K_BACKQUOTE,[key(pygame.K_TAB)],['ground','air','deploy','wreck','result','spectate'])
add('common','abandon','按住三秒弃车 / 弃机',pygame.K_F6,[key(pygame.K_j)],['ground','air'])
add('common','settings','按键设置',None,[key(pygame.K_F10)])
for ident,label,k in [('back','返回机库 / 退出',pygame.K_ESCAPE),('restart','重新开始战斗',pygame.K_r),('pause','暂停 / 继续',pygame.K_p),('nuke','部署核弹机',pygame.K_k)]:
    add('common',ident,label,k,[key(k)],None if ident=='back' else ['ground','air','deploy','wreck','result'])
for ident,label,wheel in [('zoom_in','放大视野',1),('zoom_out','缩小视野',-1)]:add('common',ident,label,('wheel',wheel),['wheel:'+str(wheel)],['ground','air','wreck','result'])
for ident,label,k in [('forward','前进',pygame.K_w),('reverse','后退',pygame.K_s),('left','向左转向',pygame.K_a),('right','向右转向',pygame.K_d),('repair','停车修理',pygame.K_f),('grenade','副炮 / 榴弹发射器',pygame.K_g),('ammo','切换炮弹',pygame.K_b),('missile_ammo','切换地面导弹',pygame.K_m),('smoke','烟雾弹',pygame.K_z),('ess','引擎烟雾',pygame.K_h),('lock','锁定目标',pygame.K_q),('missile','发射地面导弹',pygame.K_j),('night','夜视仪',pygame.K_n),('thermal','热成像',pygame.K_v),('xray','查看模块',pygame.K_x),('extinguish','灭火',pygame.K_e)]:add('ground',ident,label,k,[key(pygame.K_F5 if ident=='missile' else k)])
add('ground','mg','机枪',pygame.K_LCTRL,[key(pygame.K_LCTRL),key(pygame.K_RCTRL)])
for group in ('ground','air'):
    add(group,'fire','主武器开火',pygame.K_SPACE,[mouse(1)])
    add(group,'fire_alt','主武器备用开火',pygame.K_SPACE,[key(pygame.K_SPACE)])
add('air','cm_mode','切换热诱 / 箔条 / 混合模式',pygame.K_i,[key(pygame.K_i)])
add('air','flare','单独释放热诱弹',pygame.K_F7,[key(pygame.K_F7)])
add('ground','drone','侦察无人机 / 返回坦克',pygame.K_u,[key(pygame.K_u)])
add('ground','scout','侦察目标',pygame.K_t,[key(pygame.K_t)])
add('ground','launcher_deploy','部署 / 取消发射车',pygame.K_F11,[key(pygame.K_F11)])
add('ground','battery_switch','切换雷达车 / 发射车',pygame.K_F12,[key(pygame.K_F12)])
add('ground','ammo_box','部署个人弹药箱',pygame.K_F3,[key(pygame.K_F3)])
add('ground','artillery','切换火炮模式',pygame.K_o,[key(pygame.K_o)])
add('air','chaff','单独释放箔条',pygame.K_F8,[key(pygame.K_F8)])
add('air','warning','告警界面开关',pygame.K_F9,[key(pygame.K_F9)])
add('air','hover','直升机悬停模式',pygame.K_F4,[key(pygame.K_F4)])
for ident,label,k,physical in [('heli_forward','直升机向上位移',pygame.K_KP8,pygame.K_w),('heli_reverse','直升机向下位移',pygame.K_KP2,pygame.K_s),('heli_left','直升机向左位移',pygame.K_KP4,pygame.K_a),('heli_right','直升机向右位移',pygame.K_KP6,pygame.K_d)]:add('air',ident,label,k,[key(physical)])
add('air','throttle_up','增加油门',pygame.K_LSHIFT,[key(pygame.K_LSHIFT),key(pygame.K_RSHIFT)])
add('air','throttle_down','减少油门',pygame.K_LCTRL,[key(pygame.K_LCTRL),key(pygame.K_RCTRL)])
for ident,label,k in [('roll_left','向左滚转',pygame.K_a),('roll_right','向右滚转',pygame.K_d),('radar','雷达开关',pygame.K_TAB),('radar_mode','雷达模式',pygame.K_t),('radar_range','雷达显示量程',pygame.K_f),('radar_target','选择雷达目标',pygame.K_y),('ground_target','切换地面目标',pygame.K_e),('ground_store','切换对地挂载',pygame.K_u),('agm','发射对地导弹',pygame.K_h),('lock','空中锁定 / 解锁',pygame.K_q),('aam','发射空空导弹',pygame.K_j),('counter','释放干扰弹',pygame.K_c),('bomb','投放炸弹',pygame.K_b),('rocket','发射火箭',pygame.K_g),('missile_ammo','切换空空导弹',pygame.K_m),('belt','切换机炮弹带',pygame.K_n),('land','友方机场自动降落',pygame.K_l)]:add('air',ident,label,k,[key(pygame.K_BACKSLASH if ident=='radar' else pygame.K_F5 if ident=='aam' else k)])
add('deploy','confirm','确认部署',pygame.K_RETURN,[key(pygame.K_RETURN)])
add('deploy','select','选择鼠标处的部署项',('mouse',1),[mouse(1)])
add('garage','start','开始出战',pygame.K_RETURN,[key(pygame.K_RETURN)])
add('garage','tech','打开科技树',pygame.K_t,[key(pygame.K_t)])
add('garage','select','选择鼠标处的界面项目',('mouse',1),[mouse(1)])
add('garage','remove','移除鼠标处的出战载具',('mouse',3),[mouse(3)])
add('garage','scroll_up','科技树向上滚动',('wheel',1),['wheel:1'])
add('garage','scroll_down','科技树向下滚动',('wheel',-1),['wheel:-1'])

add('common','spectate_next','观战下一位队友',pygame.K_RIGHT,[key(pygame.K_RIGHT)],['spectate'])
add('common','spectate_prev','观战上一位队友',pygame.K_LEFT,[key(pygame.K_LEFT)],['spectate'])
for ident,d in ACTIONS.items():
    if ident.startswith('common.') and 'spectate' not in d['contexts']:d['contexts'].append('spectate')

for group in ('ground','air'):add(group,'radar_unlock','取消雷达锁定',pygame.K_BACKSPACE,[key(pygame.K_BACKSPACE)])

add('common','missile_camera','最后发射的导弹视角 / 返回',pygame.K_F1,[key(pygame.K_F1)],['ground','air'])

class MappedKeys:
    def __init__(self,controls,context):self.c=controls;self.context=context
    def __getitem__(self,k):
        return any(not a.endswith('.fire') and d['canonical']==k and self.context in d['contexts'] and self.c.held_action(a) for a,d in ACTIONS.items())

class Bindings:
    def __init__(self,path=None):
        self.modes={a:'single' for a in ACTIONS};self.gestures={};self.clicks={};self.armed=set();self.ready=[]
        self.path=path;self.binds={a:list(d['defaults']) for a,d in ACTIONS.items()};self.pressed=set();self.pulses={};self.open=False;self.waiting=None;self.capture=set();self.group='ground';self.scroll=0;self.notice='';self.old_paused=False;self.game=None
        if path and os.path.exists(path):
            try:
                data=json.load(open(path,encoding='utf8'))
                self.modes.update({a:v for a,v in data.get('trigger_modes',{}).items() if a in ACTIONS and v in ('single','double','hold')})
                for a,tokens in data.get('bindings',{}).items():
                    if a in ACTIONS and isinstance(tokens,list) and all(self.valid_token(t) for t in tokens):self.binds[a]=[chord(t) for t in tokens]
            except (OSError,ValueError):self.notice='按键文件无法读取，已使用默认设置'
        if self.binds['air.radar']==[key(pygame.K_TAB)]:self.binds['air.radar']=[key(pygame.K_BACKSLASH)]
        for action in ('ground.missile','air.aam'):
            if key(pygame.K_j) in self.binds[action]:self.binds[action]=[key(pygame.K_F5) if t==key(pygame.K_j) else t for t in self.binds[action]]
    def valid_token(self,t):
        if not isinstance(t,str):return False
        try:
            parts=t.split('+')
            return bool(parts) and len(set(parts))==len(parts) and all(len(part.split(':'))==2 and part.split(':')[0] in ('key','mouse','wheel') and int(part.split(':')[1])!=0 for part in parts)
        except (ValueError,TypeError):return False
        except IndexError:return False
    def save(self):
        if self.path:
            with open(self.path,'w',encoding='utf8') as f:json.dump({'bindings':self.binds,'trigger_modes':self.modes},f,ensure_ascii=False,indent=2)
    def bind(self,action,token):
        assert action in ACTIONS and self.valid_token(token)
        token=chord(token)
        d=ACTIONS[action]
        self.binds[action]=[token];self.save()
        self.notice='已绑定 '+d['label']+'：'+self.token_name(token)+'；允许与其他操作重复'
    def token_name(self,t):
        if '+' in t:return ' + '.join(self.token_name(part) for part in t.split('+'))
        kind,n=t.split(':');n=int(n)
        if kind=='mouse':return {1:'鼠标左键',2:'鼠标中键',3:'鼠标右键'}.get(n,f'鼠标键 {n}')
        if kind=='wheel':return '滚轮向上' if n>0 else '滚轮向下'
        return {pygame.K_LSHIFT:'左Shift',pygame.K_RSHIFT:'右Shift',pygame.K_LCTRL:'左Ctrl',pygame.K_RCTRL:'右Ctrl',pygame.K_LALT:'左Alt',pygame.K_RALT:'右Alt'}.get(n,pygame.key.name(n).upper() or str(n))
    def label(self,action):return ' / '.join(self.token_name(t) for t in self.binds[action]) or '未绑定'
    def held_token(self,t):
        if '+' in t:return all(self.held_token(part) for part in t.split('+'))
        if t in self.pressed or self.pulses.get(t,0)>time.monotonic():return True
        kind,n=t.split(':');n=int(n)
        if kind=='key':
            try:return bool(pygame.key.get_pressed()[n])
            except (IndexError,KeyError):return False
        if kind=='mouse':
            buttons=pygame.mouse.get_pressed(5);return 0<n<=len(buttons) and buttons[n-1]
        return False
    def binding_active(self,a,token):
        if not self.held_token(token):return False
        parts=set(token.split('+'));contexts=set(ACTIONS[a]['contexts'])
        # A more specific chord takes priority over its single-key components.
        return not any(parts<set(other.split('+')) and self.held_token(other) for ident,tokens in self.binds.items() if contexts&set(ACTIONS[ident]['contexts']) for other in tokens if '+' in other)
    def held_action(self,a):
        active=any(self.binding_active(a,t) for t in self.binds[a])
        mode=self.modes.get(a,'single')
        return active and (mode=='single' or mode=='double' and a in self.armed or mode=='hold' and a in self.gestures and time.monotonic()-self.gestures[a][0]>=.5)
    def poll_events(self,context):
        events=[ev for a,ev in self.ready if context in ACTIONS[a]['contexts'] and not self.open];self.ready=[];now=time.monotonic()
        for a,(started,token,ev) in list(self.gestures.items()):
            if self.open or context not in ACTIONS[a]['contexts'] or not self.binding_active(a,token):
                self.gestures.pop(a,None);self.armed.discard(a);continue
            if self.modes[a]=='hold' and now-started>=.5 and a not in self.armed:
                self.armed.add(a);events.append(pygame.event.Event(ev.type,dict(ev.dict,_binding_action=a)))
        return events
    def keys(self,context):return MappedKeys(self,context)
    def buttons(self,context):return (self.held_action(context+'.fire') if context in ('ground','air') else False,False,False)
    def toggle(self,g=None):
        self.open=not self.open;self.waiting=None;self.capture.clear()
        if self.open:self.game=g;self.old_paused=bool(g and g.paused)
        if self.game:self.game.paused=True if self.open else self.old_paused
    def rows(self):return [a for a,d in ACTIONS.items() if d['group']==self.group]
    def event(self,ev,context,g=None):
        if getattr(ev,'_binding_action',None):return ev
        if ev.type==pygame.WINDOWFOCUSLOST:self.gestures.clear();self.armed.clear();self.clicks.clear()
        if ev.type==pygame.WINDOWFOCUSLOST:self.pressed.clear();self.capture.clear();self.pulses.clear()
        token=None
        if ev.type in (pygame.KEYDOWN,pygame.KEYUP):token=key(ev.key)
        elif ev.type in (pygame.MOUSEBUTTONDOWN,pygame.MOUSEBUTTONUP):token=mouse(ev.button)
        elif ev.type==pygame.MOUSEWHEEL and ev.y:token='wheel:'+str(1 if ev.y>0 else -1);self.pulses[token]=time.monotonic()+.12
        repeated=token in self.pressed
        if token and ev.type in (pygame.KEYUP,pygame.MOUSEBUTTONUP):
            self.pressed.discard(token)
            for a,(_,ch,_) in list(self.gestures.items()):
                if token in ch.split('+'):self.gestures.pop(a,None);self.armed.discard(a)
        elif token and ev.type in (pygame.KEYDOWN,pygame.MOUSEBUTTONDOWN):self.pressed.add(token)
        down=ev.type in (pygame.KEYDOWN,pygame.MOUSEBUTTONDOWN,pygame.MOUSEWHEEL)
        if self.open:
            if self.waiting and token:
                # Clickable cancel/clear remain available; Escape itself is a bindable key.
                if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1 and pygame.Rect(1080,716,140,36).collidepoint(ev.pos):self.waiting=None;self.capture.clear();return None
                if down:
                    self.capture.add(token)
                    if ev.type in (pygame.MOUSEBUTTONDOWN,pygame.MOUSEWHEEL):self.bind(self.waiting,chord(*self.capture));self.waiting=None;self.capture.clear()
                elif token in self.capture:
                    self.bind(self.waiting,chord(*self.capture));self.waiting=None;self.capture.clear()
                return None
            if ev.type==pygame.MOUSEWHEEL:self.scroll=max(0,min(max(0,len(self.rows())-12),self.scroll-ev.y*3))
            if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                x,y=ev.pos
                if pygame.Rect(1090,75,130,38).collidepoint(ev.pos):self.toggle();return None
                if pygame.Rect(100,716,170,36).collidepoint(ev.pos):self.binds={a:list(d['defaults']) for a,d in ACTIONS.items()};self.modes={a:'single' for a in ACTIONS};self.save();self.notice='已恢复全部默认按键';return None
                for i,(group,_) in enumerate(GROUPS):
                    if pygame.Rect(100+i*220,142,205,40).collidepoint(ev.pos):self.group=group;self.scroll=0;return None
                index=int((y-205)//40)+self.scroll
                if 100<=x<=1218 and 205<=y<685 and 0<=index<len(self.rows()):
                    action=self.rows()[index]
                    if 970<=x<=1100:
                        choices=('single','double','hold');self.modes[action]=choices[(choices.index(self.modes[action])+1)%3];self.gestures.clear();self.armed.clear();self.save();return None
                    if x>1100:self.binds[action]=[];self.save();self.notice='已清除 '+ACTIONS[action]['label']
                    else:self.waiting=action;self.capture={t for t in self.pressed if t.startswith('key:')}
            elif down and any(token in t.split('+') and self.held_token(t) for t in self.binds['common.settings']):self.toggle()
            return None
        if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1 and pygame.Rect(__import__("WindowLayout").CANVAS[0]-135,__import__("WindowLayout").CANVAS[1]-37,125,30).collidepoint(ev.pos):self.toggle(g);return None
        if context=='garage' and any(token in t.split('+') and all(part==token or self.held_token(part) for part in t.split('+')) for t in self.binds['garage.select']) and ev.type in (pygame.KEYUP,pygame.MOUSEBUTTONUP):
            return pygame.event.Event(pygame.MOUSEBUTTONUP,{'button':1,'pos':getattr(ev,'pos',pygame.mouse.get_pos())})
        if not down or not token:return ev
        matches=[(len(t.split('+')),a) for a,d in ACTIONS.items() if context in d['contexts'] for t in self.binds[a] if token in t.split('+') and self.binding_active(a,t)]
        if not matches:return None if ev.type in (pygame.KEYDOWN,pygame.MOUSEWHEEL,pygame.MOUSEBUTTONDOWN) else ev
        emitted=[]
        # Dispatch every matching action; each keeps its own click/hold state.
        for action in dict.fromkeys(a for _,a in sorted(matches,key=lambda match:-match[0])):
            canonical=ACTIONS[action]['canonical']
            if action=='common.settings':
                self.toggle(g);continue
            if isinstance(canonical,tuple):
                kind,n=canonical
                mapped=pygame.event.Event(pygame.MOUSEWHEEL,{'y':n,'x':0}) if kind=='wheel' else pygame.event.Event(pygame.MOUSEBUTTONDOWN,{'button':n,'pos':getattr(ev,'pos',pygame.mouse.get_pos())})
            else:
                data=dict(ev.dict);data['key']=canonical
                mapped=pygame.event.Event(pygame.KEYDOWN,data)
            result=self.trigger(action,ev,mapped,repeated)
            if result is not None:emitted.append((action,pygame.event.Event(result.type,dict(result.dict,_binding_action=action))))
        if not emitted:return None
        self.ready.extend(emitted[1:])
        return emitted[0][1]
    def trigger(self,a,ev,mapped,repeated):
        mode=self.modes[a]
        if mode=='single':return mapped
        if repeated:return None
        now=time.monotonic();token=next((t for t in self.binds[a] if self.binding_active(a,t)),None)
        if token is None:return None
        self.gestures[a]=(now,token,mapped)
        if mode=='hold':return None
        previous=self.clicks.get(a,-100);self.clicks[a]=now
        if now-previous<=.35:self.clicks.pop(a,None);self.armed.add(a);return mapped
        return None
    def draw(self,s,text):
        pygame.draw.rect(s,(25,43,41),(s.get_width()-135,s.get_height()-37,125,30),border_radius=5);text('按键设置',(s.get_width()-120,s.get_height()-32),16)
        if not self.open:return
        shade=pygame.Surface(s.get_size(),pygame.SRCALPHA);shade.fill((5,12,12,235));s.blit(shade,(0,0))
        text('按键绑定',(100,73),30);text('点击操作，按住组合键后松开确认；也可组合鼠标按钮或滚轮。',(100,115),16,(180,206,192))
        pygame.draw.rect(s,(51,75,63),(1090,75,130,38),border_radius=5);text('关闭设置',(1105,83),18)
        for i,(group,label) in enumerate(GROUPS):
            r=pygame.Rect(100+i*220,142,205,40);pygame.draw.rect(s,(80,112,79) if self.group==group else (32,51,43),r,border_radius=5);text(label,(r.x+15,r.y+9),18)
        for i,action in enumerate(self.rows()[self.scroll:self.scroll+12]):
            r=pygame.Rect(100,205+i*40,1120,36);pygame.draw.rect(s,(80,78,43) if action==self.waiting else (26,43,39),r,border_radius=4)
            label=('按住后松开：'+self.token_name(chord(*self.capture)) if self.capture else '等待输入，松开确认…') if action==self.waiting else self.label(action)
            text(ACTIONS[action]['label'],(115,r.y+7),18,max_width=510);text(label,(650,r.y+8),16,(235,217,147),max_width=310);text({'single':'单击','double':'双击','hold':'长按'}[self.modes[action]],(990,r.y+8),16,(170,220,200));text('清除',(1130,r.y+8),16)
        text(self.notice[:76] or '允许重复绑定；相同按键按各操作的单击、双击或长按方式触发。设置自动保存。',(100,685),14,(187,211,181))
        pygame.draw.rect(s,(61,77,57),(100,716,170,36),border_radius=5);text('恢复默认',(115,724),18)
        if self.waiting:pygame.draw.rect(s,(77,62,46),(1080,716,140,36),border_radius=5);text('取消选择',(1095,724),18)

_controls=None
def get_controls():
    global _controls
    if _controls is None:
        root=os.path.dirname(sys.executable if getattr(sys,'frozen',False) else os.path.abspath(__file__))
        _controls=Bindings(None if '--test' in sys.argv else os.path.join(root,'按键设置.json'))
    return _controls

def install(Game):
    init=Game.__init__
    def wrapped(self,*a,**kw):self.controls=get_controls();init(self,*a,**kw)
    def context(self):
        if self.state in ('deploy','wreck'):return self.state
        if self.state in ('win','lose'):return 'result'
        return 'drone' if self.drone_active else 'air' if self.flight.active else 'ground'
    Game.__init__=wrapped;Game.input_context=context


add('ground','radar_range','防空雷达量程',pygame.K_F2,[key(pygame.K_F2)])
add('ground','radar_target','防空切换锁定目标',pygame.K_y,[key(pygame.K_y)])

# Drone uses existing aircraft throttle/roll bindings and ground scout/return bindings.
add('ground','drone_orbit','无人机自动盘旋 / 手动飞行',pygame.K_F6,[key(pygame.K_F6)],['ground','drone'])
for ident in ('ground.drone','ground.scout','air.throttle_up','air.throttle_down','air.roll_left','air.roll_right'):
    ACTIONS[ident]['contexts'].append('drone')
for ident,d in ACTIONS.items():
    if ident.startswith('common.') and 'ground' in d['contexts']:d['contexts'].append('drone')

for i in range(10):
    k=pygame.K_1+i if i<9 else pygame.K_0
    add("ground","ammo_"+str(i+1),"选择携带弹药 "+str(i+1),k,[key(k)])

for ident,wheel in (("ammo_up",1),("ammo_down",-1)):add("deploy",ident,"滚动配载列表",("wheel",wheel),["wheel:"+str(wheel)])
