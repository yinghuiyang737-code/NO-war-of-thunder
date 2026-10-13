"""Per-round deployment loadouts, finite ammunition bins and numbered battle HUD."""
import pygame,os,json
from VehicleData import guided

def groups(v):
    primary=[i for i,a in enumerate(v['ammo_options']) if v['weapon']=='sam' or not (v.get('independent_missiles') and guided(a))]
    secondary=[i for i in range(len(v['ammo_options'])) if i not in primary]
    maincap=(v.get('missile_capacity') or 8) if v['weapon']=='sam' else v.get('ammo_capacity',800 if v['branch']==3 or v['weapon']=='auto' else 45)
    return [(primary,int(maincap),'missile_count' if v['weapon']=='sam' else 'shells')]+([(secondary,int(v.get('missile_capacity') or 0),'missile_count')] if secondary else [])

def sanitize(v,values):
    result={str(i):0 for i in range(len(v['ammo_options']))}
    if not isinstance(values,dict):return result
    for indices,capacity,field in groups(v):
        left=capacity
        for i in indices:
            raw=values.get(str(i),values.get(i,0));n=max(0,min(left,raw)) if isinstance(raw,int) and not isinstance(raw,bool) else 0
            result[str(i)]=n;left-=n
    return result

def selected(g):
    from Garage import VEHICLES
    if g.flight.nuke_pending:return None
    ident=g.lineup[g.active_vehicle_slot] if g.lineup else g.player.vehicle_id
    return VEHICLES.get(ident)

def preset(g,v):
    if not hasattr(g,'ammo_packs'):g.ammo_packs={}
    if v['id'] not in g.ammo_packs:
        values={}
        for indices,cap,field in groups(v):
            if not indices:continue
            preferred=(g.missile_choices if indices and guided(v['ammo_options'][indices[0]]) and v.get('independent_missiles') else g.ammo_choices).get(v['id'],indices[0] if indices else 0)
            values[str(preferred if preferred in indices else indices[0])]=cap
        g.ammo_packs[v['id']]=sanitize(v,values)
    g.ammo_packs[v['id']]=sanitize(v,g.ammo_packs[v['id']])
    return g.ammo_packs[v['id']]

def totals(t):
    for indices,cap,field in groups(t.ammo_original_stats):
        setattr(t,field,sum(t.ammo_bins[str(i)] for i in indices))
    if t.ammo_original_stats['weapon']=='sam':t.shells=1
    if hasattr(t,'premium_ammo'):
        t.premium_ammo=t.shells;t.premium_mag=min(t.premium_mag,t.shells)

def sync(t):
    if not hasattr(t,'ammo_bins'):return
    for indices,cap,field in groups(t.ammo_original_stats):
        before=sum(t.ammo_bins[str(i)] for i in indices);after=getattr(t,field) or 0
        difference=after-before
        if difference>0:
            preferred=t.missile_index if field=='missile_count' and t.stats.get('independent_missiles') else t.ammo_index
            order=sorted(indices,key=lambda i:i!=preferred)
            for i in order:
                key=str(i);n=min(difference,max(0,t.ammo_targets[key]-t.ammo_bins[key]));t.ammo_bins[key]+=n;difference-=n
        elif difference<0:
            preferred=t.missile_index if field=='missile_count' and t.stats.get('independent_missiles') else t.ammo_index
            for i in sorted(indices,key=lambda i:i!=preferred):
                key=str(i);n=min(-difference,t.ammo_bins[key]);t.ammo_bins[key]-=n;difference+=n
    totals(t)

def configure(t,values):
    from Garage import VEHICLES
    v=VEHICLES[t.vehicle_id];t.ammo_original_stats=v;t.stats=dict(v)
    t.ammo_targets=sanitize(v,values);t.ammo_bins=dict(t.ammo_targets)
    for indices,cap,field in groups(v):
        amount=sum(t.ammo_bins[str(i)] for i in indices)
        if field=='shells':t.shell_capacity=amount;t.stats['ammo_capacity']=amount
        else:t.stats['missile_capacity']=amount
        available=[i for i in indices if t.ammo_bins[str(i)]>0]
        attr='missile_index' if field=='missile_count' and v.get('independent_missiles') else 'ammo_index'
        if available and getattr(t,attr) not in available:setattr(t,attr,available[0])
    if v['weapon']=='sam':
        t.shell_capacity=1
        if v.get('independent_missiles'):t.ammo_index=t.missile_index
    totals(t)

def slots(t):return [int(i) for i,n in getattr(t,'ammo_targets',{}).items() if n>0]

def select(g,slot):
    t=g.player
    if g.state!='play' or g.paused or t.dead or g.flight.active:return False
    sync(t);available=slots(t)
    if not 0<=slot<len(available):return False
    i=available[slot]
    if t.ammo_bins[str(i)]<=0:g.say('该弹种已耗尽');return False
    independent=t.stats.get('independent_missiles') and guided(t.stats['ammo_options'][i])
    attr='missile_index' if independent else 'ammo_index'
    if getattr(t,attr)==i:return True
    setattr(t,attr,i)
    if t.stats['weapon']=='sam':t.ammo_index=t.missile_index=i
    if independent:t.missile_cd=max(t.missile_cd,t.stats['missile_reload']);g.missile_choices[t.vehicle_id]=i
    else:t.cd=max(t.cd,t.stats['ammo_reload']);g.ammo_choices[t.vehicle_id]=i
    if not independent:
        from ReloadVoice import event,ammo_kind
        kind=ammo_kind(t.ammo);event(t,'ground_load_'+kind);t.reload_voice_pending=kind
    g.say('换装：'+t.stats['ammo_options'][i]['name']);return True

def panel(g):return pygame.Rect(g.flight.api['W']-207,425,190,max(100,g.flight.api['H']-475))
def row(g,i):
    r=panel(g);return pygame.Rect(r.x+4,r.y+70+(i-getattr(g,'ammo_scroll',0))*49,r.w-8,47)

def adjust(g,pos):
    if g.state!='deploy' or not panel(g).collidepoint(pos):return False
    v=selected(g)
    if not v:return True
    values=preset(g,v)
    for i in range(len(v['ammo_options'])):
        r=row(g,i)
        if r.top<panel(g).y+68 or r.bottom>panel(g).bottom:continue
        if slider(g,i).inflate(12,12).collidepoint(pos):g.ammo_edit=None;g.ammo_drag=(v['id'],i);drag_to(g,pos[0]);return True
        if pygame.Rect(r.right-60,r.y+22,32,24).collidepoint(pos):g.ammo_edit=(v['id'],i,'');return True
        n=100 if pygame.key.get_mods()&pygame.KMOD_CTRL else 10 if pygame.key.get_mods()&pygame.KMOD_SHIFT else 1
        for sign,button in [(-1,pygame.Rect(r.right-87,r.y+23,25,22)),(1,pygame.Rect(r.right-27,r.y+23,25,22))]:
            if not button.collidepoint(pos):continue
            inds,cap,field=next(x for x in groups(v) if i in x[0]);used=sum(values[str(j)] for j in inds)
            amount=min(n,cap-used) if sign>0 else -min(n,values[str(i)])
            values[str(i)]+=amount;save_packs(g)
            if sign>0 and amount==0:g.deploy_hint='该武器弹药已达容量上限，请先减少其他弹种'
            return True
    return True

def draw_panel(g,api):
    v=selected(g);r=panel(g);s=api['screen'];text=api['text'];pygame.draw.rect(s,(22,34,29),r,border_radius=5)
    if not v:text('飞机挂载在机库配置',r.topleft,14);return
    values=preset(g,v);text('弹药配载 · 机枪独立',(r.x+6,r.y+6),16)
    for n,(inds,cap,field) in enumerate(groups(v)):
        text(('主武器' if n==0 else '独立导弹')+f' {sum(values[str(i)] for i in inds)}/{cap}',(r.x+6,r.y+30+n*18),14)
    clip=s.get_clip();s.set_clip(pygame.Rect(r.x,r.y+68,r.w,r.h-68))
    for i,a in enumerate(v['ammo_options']):
        rr=row(g,i)
        if not rr.colliderect(s.get_clip()):continue
        indices,capacity,field=next(x for x in groups(v) if i in x[0])
        bar=slider(g,i);pygame.draw.rect(s,(52,70,58),bar,border_radius=3)
        fill=round(bar.w*values[str(i)]/max(1,capacity));pygame.draw.rect(s,(159,189,117),pygame.Rect(bar.x,bar.y,fill,bar.h),border_radius=3)
        pygame.draw.circle(s,(227,222,166),(bar.x+fill,bar.centery),5)
        text(a['name'],(rr.x+2,rr.y+2),14,max_width=rr.w-4)
        editing=getattr(g,'ammo_edit',None)
        value='['+editing[2]+']' if editing and editing[:2]==(v['id'],i) else str(values[str(i)])
        text(value,(rr.right-59,rr.y+25),14,max_width=31)
        for sign,x in [('-',rr.right-87),('+',rr.right-27)]:
            button=pygame.Rect(x,rr.y+23,25,22);pygame.draw.rect(s,(58,77,61),button,border_radius=3);text(sign,button.center,14,center=True)
    s.set_clip(clip)

def install(Game,api):
    old={k:getattr(Game,k) for k in ('__init__','deploy_player','choose_deployment','draw_deployment','draw','shoot','update','change_zoom','switch_ammo','switch_missile')}
    def init(g,*a,**kw):
        old['__init__'](g,*a,**kw);g.ammo_packs={};g.ammo_scroll=0;g.ammo_edit=None;g.ammo_drag=None
        g.ammo_save_path=None if api.get('TEST') else os.path.join(os.path.dirname(__import__('Garage').default_save_path()),'弹药配载.json')
        if g.ammo_save_path:
            try:
                with open(g.ammo_save_path,encoding='utf-8') as file:loaded=json.load(file)
                if isinstance(loaded,dict):g.ammo_packs=loaded
            except (OSError,ValueError):pass
    def deploy(g,*a,**kw):
        v=selected(g)
        values=dict(preset(g,v)) if v else None
        if v and not any(values.values()):g.deploy_hint='至少携带一种武器弹药';return False
        result=old['deploy_player'](g,*a,**kw)
        if result and v and not g.flight.active:configure(g.player,values)
        if result:g.ammo_edit=None;g.ammo_drag=None
        return result
    def choose(g,pos):
        if adjust(g,pos):return
        before=g.active_vehicle_slot;old['choose_deployment'](g,pos)
        if g.active_vehicle_slot!=before:g.ammo_scroll=0;g.ammo_edit=None;g.ammo_drag=None
    def depdraw(g):old['draw_deployment'](g);draw_panel(g,api)
    def zoom(g,delta):
        if g.state=='deploy' and panel(g).collidepoint(pygame.mouse.get_pos()):
            v=selected(g);maxscroll=max(0,len(v['ammo_options'])-(panel(g).h-70)//49) if v else 0;g.ammo_scroll=max(0,min(maxscroll,g.ammo_scroll-delta));return
        return old['change_zoom'](g,delta)
    def shoot(g,t):
        if not hasattr(t,'ammo_bins'):return old['shoot'](g,t)
        sync(t);key=str(t.ammo_index)
        if t.ammo_bins[key]<=0:return False
        if guided(t.ammo):return old['shoot'](g,t)
        start=len(g.bullets);result=old['shoot'](g,t)
        if result:
            fired=max(1,len(g.bullets)-start);count=min(fired,t.ammo_bins[key])
            if fired>count:del g.bullets[start+count:]
            t.ammo_bins[key]-=count;totals(t)
        return result
    def update(g,dt):
        for t in g.vehicles():sync(t)
        old['update'](g,dt)
        for t in g.vehicles():sync(t)
    def cycle(g,step=1,missile=False):
        t=g.player
        if not hasattr(t,'ammo_bins'):return old['switch_missile'](g) if missile else old['switch_ammo'](g,step)
        sync(t);avail=slots(t);which=[n for n,i in enumerate(avail) if bool(t.stats.get('independent_missiles') and guided(t.stats['ammo_options'][i]))==missile and t.ammo_bins[str(i)]>0]
        current=t.missile_index if missile else t.ammo_index
        ordered=[avail[n] for n in which]
        if not ordered:return False
        pos=ordered.index(current) if current in ordered else -1
        return select(g,which[(pos+step)%len(which)])
    def draw(g,*a,**kw):
        old['draw'](g,*a,**kw)
        t=g.player
        if g.state!='play' or g.flight.active or g.drone_active or not hasattr(t,'ammo_bins'):return
        available=slots(t);width=max(1,(api['W']-370)//max(1,len(available)))
        for n,i in enumerate(available):
            r=pygame.Rect(350+n*width,api['H']-94,width-4,38);selected_index=t.missile_index if t.stats.get('independent_missiles') and guided(t.stats['ammo_options'][i]) else t.ammo_index
            pygame.draw.rect(api['screen'],(67,80,54) if i==selected_index else (25,38,31),r,border_radius=4)
            label=g.controls.label('ground.ammo_'+str(n+1));api['text'](label+' '+t.stats['ammo_options'][i]['name'],(r.x+4,r.y+2),14,max_width=r.w-8)
            api['text']('剩余 '+str(t.ammo_bins[str(i)]),(r.x+4,r.y+20),14)
    Game.__init__=init;Game.deploy_player=deploy;Game.choose_deployment=choose;Game.draw_deployment=depdraw;Game.change_zoom=zoom;Game.shoot=shoot;Game.update=update;Game.draw=draw
    Game.select_carried_ammo=select;Game.switch_ammo=lambda g,step=1:cycle(g,step);Game.switch_missile=lambda g:cycle(g,1,True)
    from AirDefense import AirDefense
    launch=AirDefense.launch
    def fire(air,t=None,target=None,ammo=None):
        t=t or air.g.player
        if not hasattr(t,'ammo_bins'):return launch(air,t,target,ammo)
        sync(t);i=t.missile_index if t.stats.get('independent_missiles') else t.ammo_index;key=str(i)
        if t.ammo_bins[key]<=0:return False
        success=launch(air,t,target,t.stats['ammo_options'][i])
        if success:t.ammo_bins[key]-=1;totals(t)
        return success
    AirDefense.launch=fire
    from Artillery import Artillery
    shoot_art=Artillery.shoot
    def fire_art(self,t,*args,**kw):
        if not hasattr(t,'ammo_bins'):return shoot_art(self,t,*args,**kw)
        sync(t);key=str(t.ammo_index)
        if t.ammo_bins[key]<=0:return False
        result=shoot_art(self,t,*args,**kw)
        if result:t.ammo_bins[key]-=1;totals(t)
        return result
    Artillery.shoot=fire_art
    from SplitAirDefense import Battery
    place=Battery.place
    def place_launcher(b,*args,**kwargs):
        count=len(b.units);result=place(b,*args,**kwargs)
        if len(b.units)>count and b.radar and hasattr(b.radar,'ammo_targets'):
            unit=b.units[-1];appearance=dict(unit.stats)
            configure(unit,b.radar.ammo_targets)
            for key in ('name','split_role'): 
                if key in appearance:unit.stats[key]=appearance[key]
        return result
    Battery.place=place_launcher


def edit_event(g,e):
    if g.state=='deploy' and getattr(g,'ammo_drag',None):
        if e.type==pygame.WINDOWFOCUSLOST:g.ammo_drag=None;save_packs(g);return False
        if e.type==pygame.MOUSEMOTION:
            if not getattr(e,'buttons',(False,))[0]:g.ammo_drag=None;save_packs(g);return True
            drag_to(g,e.pos[0]);return True
        if e.type==pygame.MOUSEBUTTONUP and e.button==1:drag_to(g,e.pos[0]);g.ammo_drag=None;save_packs(g);return True
    editing=getattr(g,'ammo_edit',None)
    if g.state!='deploy' or not editing:return False
    if e.type!=pygame.KEYDOWN:return e.type==pygame.TEXTINPUT
    ident,i,value=editing
    if e.key==pygame.K_ESCAPE:g.ammo_edit=None;return True
    if e.key in (pygame.K_RETURN,pygame.K_KP_ENTER):
        from Garage import VEHICLES
        v=VEHICLES[ident];values=preset(g,v);indices,cap,field=next(x for x in groups(v) if i in x[0])
        maximum=cap-sum(values[str(j)] for j in indices if j!=i)
        values[str(i)]=min(maximum,int(value or '0'));g.ammo_edit=None;save_packs(g);return True
    if e.key==pygame.K_BACKSPACE:g.ammo_edit=(ident,i,value[:-1]);return True
    text=getattr(e,'unicode','')
    if text and text in '0123456789' and len(value)<5:g.ammo_edit=(ident,i,value+text)
    return True


def slider(g,i):
    r=row(g,i);return pygame.Rect(r.x+3,r.y+30,max(30,r.w-100),8)

def drag_to(g,x):
    ident,i=g.ammo_drag
    from Garage import VEHICLES
    v=VEHICLES[ident];values=preset(g,v);inds,cap,field=next(group for group in groups(v) if i in group[0])
    bar=slider(g,i);desired=round(cap*max(0,min(1,(x-bar.x)/max(1,bar.w))))
    left=cap-sum(values[str(j)] for j in inds if j!=i)
    values[str(i)]=min(left,desired)

def save_packs(g):
    path=getattr(g,'ammo_save_path',None)
    if not path or (getattr(g,'_lan_authority',None) and getattr(g,'_lan_id',0)!=0):return
    try:
        with open(path+'.tmp','w',encoding='utf-8') as file:json.dump(g.ammo_packs,file,ensure_ascii=False,indent=2)
        os.replace(path+'.tmp',path)
    except OSError:g.deploy_hint='弹药配载保存失败，本场配置仍可使用'
