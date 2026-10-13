"""Persistent battle roster, authoritative combat credit and AI nuclear sorties."""
import random,pygame
from pygame.math import Vector2 as V
from AircraftPhysics import direction,bearing

WORDS=('苍鹰','灰狼','雪豹','猎隼','赤狐','夜枭','山猫','海燕','铁杉','白桦','松鼠','野牛','雷鸟','雨燕','黑熊','飞鱼','流星','晨风','北斗','霜刃','银翼','远山','疾风','青锋')
def get(unit,key,default=None):return unit.get(key,default) if isinstance(unit,dict) else getattr(unit,key,default)
def put(unit,key,value):
    if isinstance(unit,dict):unit[key]=value
    else:setattr(unit,key,value)
def root(g):return getattr(g,'_lan_world',None) or g

def row(g,u):
    if u is None:return None
    g=root(g);authority=getattr(g,'_lan_authority',None)
    if isinstance(u,dict) and u.get('controlled'):u=u['controlled'].g.player
    if isinstance(u,dict) and u.get('source') and not u.get('managed'):u=u['source']
    owner=get(u,'network_owner')
    human=u is g.player or owner is not None or get(u,'is_user',False)
    ident=('player_'+str(owner if owner is not None else 0)) if human else get(u,'battle_id')
    team=get(u,'team',int(get(u,'enemy',False)))
    if not human and ident and str(ident).startswith('player_'):ident=None
    if not ident:
        g.roster_serial+=1;ident='ai_'+str(g.roster_serial);put(u,'battle_id',ident)
    if ident not in g.battle_roster:
        name=(authority.members.get(owner or 0,{}).get('name','玩家') if authority else '玩家') if human else random.choice(WORDS)+'-'+str(random.randint(10,99))
        if not human:
            while any(v['name']==name for v in g.battle_roster.values()):name=random.choice(WORDS)+'-'+str(random.randint(10,99))
        g.battle_roster[ident]=dict(id=ident,name=name,team=team,human=human,ground=0,air=0,deaths=0,assists=0,score=0,nuke_used=False,vehicle='',alive=True)
    result=g.battle_roster[ident];result['alive']=not get(u,'dead',False)
    model=get(u,'model',{}) if isinstance(u,dict) else u.stats
    result['vehicle']=get(u,'user_vehicle_name') or model.get('name','载具')
    if human:
        ctx=authority.contexts.get(owner or 0,g) if authority else g
        result['score']=ctx.score
    put(u,'battle_id',ident);return result

def scan(g):
    g=root(g)
    for u in [g.player]+g.allies+g.enemies+[q for q in g.air.planes if q.get('managed')]:row(g,u)

def credit_hit(g,target,result,owner):
    r=row(g,owner);v=row(g,target)
    if not r or not v or r['team']==v['team'] or not result:return
    if get(target,'dead',False):return
    marks=get(target,'battle_damage',{})
    now=root(g).time
    if now-marks.get(r['id'],-100)>=1 and not r['human']:r['score']+=15
    marks[r['id']]=now;put(target,'battle_damage',marks)

def credit_kill(g,attacker,victim):
    g=root(g)
    if get(victim,'battle_death_recorded',False):return
    put(victim,'battle_death_recorded',True)
    v=row(g,victim);v['deaths']+=1;v['alive']=False
    a=row(g,attacker)
    if a and a['team']!=v['team']:
        a['air' if isinstance(victim,dict) or get(victim,'airborne',False) else 'ground']+=1
        if not a['human']:a['score']+=150 if isinstance(victim,dict) else 200 if get(victim,'elite',False) else 100
    assistants=set(k for k,t in get(victim,'battle_damage',{}).items() if g.time-t<=30)
    for owner,until in get(victim,'scout_marks',{}).items():
        if until>=g.time:assistants.add('player_'+str(owner))
    for ident in assistants:
        r=g.battle_roster.get(ident)
        if not r or r['team']==v['team'] or a and r['id']==a['id']:continue
        r['assists']+=1
        if not r['human']:r['score']+=50
        elif ident in get(victim,'battle_damage',{}):
            authority=getattr(g,'_lan_authority',None);ctx=authority.contexts.get(int(ident.split('_')[1])) if authority else g
            if ctx:ctx.score+=50;ctx.say('助攻 +50 分')

def nuclear_update(manager,q,dt):
    from FlightDynamics import step
    g=manager.g;p=q['ai_plane'];center=V(g.world_size)/2
    q['age']+=dt;p.throttle=1.;desired=q['heading'] if p.phase=='runway' else bearing(center-p.p)
    if not step(p,dt,desired,q['heading']):manager.killed(q);return
    q.update(p=V(p.p),v=direction(p.a)*p.speed,bank=p.bank,phase=p.phase)
    if p.phase=='airborne':manager.defend(q)
    if p.phase=='airborne' and p.bombs and p.p.distance_to(center)<2400:
        p.bombs=0;g.ai_nuclear=dict(team=q['team'],point=list(center),timer=4.);g.say(('敌方' if q['team'] else '己方')+' AI 已投放核弹！')

def launch_nukes(g):
    from Aviation import AIRCRAFT
    from NuclearMission import select_aircraft,configure
    g=root(g);scan(g)
    active=[t for t in g.allies+g.enemies if not t.dead and not get(t,'is_user',False) and get(t,'network_owner') is None]+[q for q in g.air.planes if q.get('managed') and not q['dead']]
    for u in active:
        r=row(g,u);team=r['team']
        if r['human'] or r['id'].startswith('player_') or get(u,'controlled') or r['score']<2500 or r['nuke_used'] or any(q.get('ai_nuclear') and not q['dead'] and q['team']==team for q in g.air.planes):continue
        country=(g.enemy_country or 'ussr') if team else g.country
        entry=dict(aircraft=select_aircraft(AIRCRAFT,country,g.battle_br),vehicle=get(u,'vehicle_id'),elite=False,battle_id=r['id'])
        if isinstance(u,dict):u['dead']=True;u['ai_plane'].dead=True
        elif u in g.enemies:u.dead=True;g.enemies.remove(u)
        elif u in g.allies:u.dead=True;g.allies.remove(u)
        q=g.ai_flights.spawn(entry,team);q['ai_nuclear']=True;configure(q['ai_plane']);q['battle_id']=r['id'];r['nuke_used']=True
        g.say(r['name']+' 达到 2500 分，出动核弹机 '+q['model']['name'])

def panel(g,api):
    # Held action works with custom chords and local controls on LAN clients.
    if not g.controls.keys(g.input_context())[pygame.K_BACKQUOTE]:return
    s=api['screen'];text=api['text'];w,h=s.get_size();r=pygame.Rect(50,85,w-100,h-140)
    layer=pygame.Surface(r.size,pygame.SRCALPHA);layer.fill((13,23,24,240));s.blit(layer,r)
    text('战绩 · '+g.controls.label('common.scoreboard')+' 按住查看',(r.centerx,r.y+20),24,center=True)
    for team in (0,1):
        x=r.x+20+team*(r.w//2);width=r.w//2-35
        text('己方' if team==0 else '敌方',(x,r.y+62),20,(145,212,241) if team==0 else (241,170,124))
        cols=[x,x+width*.28,x+width*.56,x+width*.66,x+width*.76,x+width*.86]
        for label,cx in zip(('名称 / 载具','分数','地面击毁','死亡','空军击毁','助攻'),cols):text(label,(cx,r.y+94),14)
        entries=sorted((v for v in g.battle_roster.values() if v['team']==team),key=lambda v:(-v['score'],v['id']))[:16]
        stride=min(43,max(25,(r.h-135)//16))
        for i,v in enumerate(entries):
            y=r.y+120+i*stride;color=(224,230,214) if v['alive'] else (132,144,138)
            text(v['name']+(' [AI]' if not v['human'] else ''),(x,y),14,color,max_width=width*.27)
            if stride>=35:text(v['vehicle'],(x,y+17),14,(145,167,145),max_width=width*.27)
            for value,cx in zip((v['score'],v['ground'],v['deaths'],v['air'],v['assists']),cols[1:]):text(str(value),(cx,y),14,color)

def install(Game,api):
    from AIFlight import AIFlights
    old={k:getattr(Game,k) for k in ('__init__','announce_kill','record_hit','record_air_hit','register_death','deploy_player','spawn_allies','draw','update')}
    def init(g,*a,**kw):
        old['__init__'](g,*a,**kw);g.battle_roster={};g.roster_serial=0;g.ai_nuclear=None;scan(g)
    def announce(g,a,v,weapon=''):
        credit_kill(g,a,v);old['announce_kill'](g,a,v,weapon)
    def hit(g,t,result,owner,weapon=''):
        if result.get('modules') and not result.get('continue'):credit_hit(g,t,result,owner)
        old['record_hit'](g,t,result,owner,weapon)
    def air_hit(g,t,point,owner,weapon=''):
        credit_hit(g,t,True,owner);old['record_air_hit'](g,t,point,owner,weapon)
    def death(g,t):
        active=t is g.player or t in g.allies or t in g.enemies;r=row(g,t);old['register_death'](g,t)
        queue=g.enemy_queue if t.enemy else g.ally_queue
        if active and t is not g.player and queue and isinstance(queue[-1],dict):queue[-1]['battle_id']=r['id']
    def deploy(g,*a,**kw):
        result=old['deploy_player'](g,*a,**kw)
        if result:row(g,g.player)
        return result
    def spawn(g,*a,**kw):
        before={id(t) for t in g.allies};old['spawn_allies'](g,*a,**kw)
        for t in g.allies:
            if id(t) not in before:
                if getattr(g,'pending_battle_id',None):t.battle_id=g.pending_battle_id;g.pending_battle_id=None
                if hasattr(root(g),'battle_roster'):row(g,t)
    def update(g,dt):
        old['update'](g,dt)
        if g.paused or g.state not in ('play','deploy','wreck'):return
        launch_nukes(g)
        if g.ai_nuclear:
            g.ai_nuclear['timer']-=dt
            if g.ai_nuclear['timer']<=0:
                from NuclearMission import NuclearExplosion
                team=g.ai_nuclear['team'];g.flight.nuke_animation=NuclearExplosion(g.ai_nuclear['point']);g.flight.nuke_detonated=True;g.nuclear_result='lose' if team else 'win';g.ai_nuclear=None
                authority=getattr(g,'_lan_authority',None)
                if authority:authority.root.nuclear_result=g.nuclear_result
    def draw(g,*a,**kw):old['draw'](g,*a,**kw);panel(g,api)
    for k,v in [('__init__',init),('announce_kill',announce),('record_hit',hit),('record_air_hit',air_hit),('register_death',death),('deploy_player',deploy),('spawn_allies',spawn),('update',update),('draw',draw)]:setattr(Game,k,v)
    original_spawn=AIFlights.spawn;original_decide=AIFlights.decide;original_killed=AIFlights.killed;original_update=AIFlights.update
    def ai_spawn(manager,entry,team):
        q=original_spawn(manager,entry,team)
        if entry.get('battle_id'):q['battle_id']=entry['battle_id'];q['replacement']['battle_id']=entry['battle_id']
        row(manager.g,q);return q
    def decide(manager,entry,team):
        manager.g.pending_battle_id=entry.get('battle_id') if team==0 else None;result=original_decide(manager,entry,team)
        if result:manager.g.pending_battle_id=None
        return result
    def killed(manager,q,owner=None):
        row(manager.g,q);q['replacement']['battle_id']=q['battle_id'];original_killed(manager,q,owner)
        if q['dead'] and not q.get('feedback_announced'):
            q['feedback_announced']=True;manager.g.announce_kill(owner if owner is not None else q.get('last_attacker'),q,q.get('last_weapon',''))
    def flight_update(manager,q,dt):
        if q.get('ai_nuclear'):nuclear_update(manager,q,dt)
        else:original_update(manager,q,dt)
    AIFlights.spawn=ai_spawn;AIFlights.decide=decide;AIFlights.killed=killed;AIFlights.update=flight_update
