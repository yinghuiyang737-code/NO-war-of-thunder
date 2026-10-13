"""One defended capture zone and symmetric vehicle-loss tickets."""
import pygame
from pygame.math import Vector2 as V
from AITactics import objective_goal

class Objective:
    def __init__(self,g,name='A',position=None):
        self.name=name;self.g=g;self.p=V(position) if position is not None else V(g.world_size)/2;self.radius=320;self.owner=None;self.team=None;self.progress=0.;self.contested=False;self.owner_since=0.
    def occupants(self):
        units=[self.g.player]+self.g.allies+self.g.enemies
        return [[t for t in units if not t.dead and not getattr(t,'airborne',False) and int(t.enemy)==team and t.p.distance_to(self.p)<=self.radius] for team in (0,1)]
    def update(self,dt,drain=True):
        occupied=self.occupants();self.contested=bool(occupied[0] and occupied[1])
        remaining=dt
        while remaining>1e-8:
            step=min(.1,remaining);remaining-=step
            if drain and self.owner is not None:self.g.tickets[1-self.owner]=max(0,self.g.tickets[1-self.owner]-4*step)
            # Presence of any surviving ground vehicle of the owner protects ownership.
            if self.owner is not None and occupied[self.owner]:self.team=None;self.progress=0.;continue
            contenders=[team for team in (0,1) if occupied[team]]
            if len(contenders)!=1:
                if not contenders:self.progress=max(0,self.progress-step)
                continue
            team=contenders[0]
            if team==self.owner:self.team=None;self.progress=0.;continue
            if self.team!=team:self.team=team;self.progress=0.
            self.progress+=step;required=12 if self.owner is None else 6
            if self.progress+1e-6>=required:
                if self.owner is None:self.owner=team;self.owner_since=self.g.time;self.g.say(('己方' if team==0 else '敌方')+'占领 '+self.name+' 点')
                else:self.owner=None;self.g.say(self.name+' 点已中立化')
                self.progress=0.
    def ai_goal(self,t):
        return objective_goal(self,t)
    def label(self):
        label=self.name+' 中立' if self.owner is None else self.name+' '+('己方控制' if self.owner==0 else '敌方控制')
        if self.contested:label+=' · 双方争夺' if self.owner is None else ' · 驻守保护'
        elif self.team is not None and self.progress>0:label+=f' · {"己方" if self.team==0 else "敌方"}{"占领" if self.owner is None else "中立化"} {self.progress/(12 if self.owner is None else 6)*100:.0f}%'
        return label
    def draw_world(self,screen,text,at,factor=1):
        color=(168,186,157) if self.owner is None else (113,207,238) if self.owner==0 else (238,132,91)
        pos=at(self.p);radius=max(5,int(self.radius*factor))
        pygame.draw.circle(screen,color,pos,radius,2);text(self.name+' 占领区',pos+V(0,-radius-22),18,color,True)
    def draw(self,screen,text,api,header=True):
        g=self.g;color=(168,186,157) if self.owner is None else (113,207,238) if self.owner==0 else (238,132,91)
        def mark(rect):
            pos=V(rect.x+self.p.x/g.world_size[0]*rect.w,rect.y+self.p.y/g.world_size[1]*rect.h)
            pygame.draw.circle(screen,color,pos,max(5,int(self.radius/g.world_size[0]*rect.w)),2);text(self.name,pos+V(0,-21),16,color,True)
        if g.state=='deploy':mark(g.deployment_map())
        else:
            if not g.flight.active:mark(pygame.Rect(api['W']-218,85,200,156))
            else:
                f=g.flight;lo=V(min(-1000,f.airport.x-13000),-2000);extent=V(g.world_size[0]+2000,f.airport.y+14000)-lo
                pos=V(1028,85)+V((self.p.x-lo.x)/extent.x*235,(self.p.y-lo.y)/extent.y*175)
                pygame.draw.circle(screen,color,pos,4,1);text(self.name,pos+V(-4,-19),14,color)
        if not header:return
        pygame.draw.rect(screen,(15,28,26),(386,0,405,68))
        text(f'己方 {g.tickets[0]:.0f}  :  {g.tickets[1]:.0f} 敌方',(398,12),20,(200,224,207));text(self.label(),(398,39),14,color)


class Objectives:
    def __init__(self,g,points):
        self.g=g;self.points=points;self.p=V(g.world_size)/2;self.radius=320;self.assignments={}
    def assign(self,team):
        units=[u for u in (self.g.enemies if team else self.g.allies) if not u.dead and not getattr(u,'airborne',False)]
        alive={id(u) for u in units}
        self.assignments={key:value for key,value in self.assignments.items() if key in alive or value[0]!=team}
        counts={p.name:sum(value==(team,p.name) for value in self.assignments.values()) for p in self.points}
        for u in units:
            if id(u) not in self.assignments:
                p=min(self.points,key=lambda p:(counts[p.name],u.p.distance_squared_to(p.p)))
                self.assignments[id(u)]=(team,p.name);counts[p.name]+=1
            u.ai_objective=next(p for p in self.points if p.name==self.assignments[id(u)][1])
        return units
    def ai_goal(self,t):
        self.assign(int(t.enemy));return objective_goal(t.ai_objective,t)
    def update(self,dt):
        remaining=dt
        while remaining>1e-8:
            step=min(.1,remaining);remaining-=step
            for team in (0,1):
                count=sum(p.owner==team for p in self.points)
                if count>=2:self.g.tickets[1-team]=max(0,self.g.tickets[1-team]-4*step)
            for p in self.points:p.update(step,drain=False)
    def draw_world(self,screen,text,at,factor=1):
        for p in self.points:p.draw_world(screen,text,at,factor)
    def draw(self,screen,text,api):
        for p in self.points:p.draw(screen,text,api,header=False)
        pygame.draw.rect(screen,(15,28,26),(386,0,405,68))
        text(f'己方 {self.g.tickets[0]:.0f}  :  {self.g.tickets[1]:.0f} 敌方',(398,12),20,(200,224,207))
        for i,p in enumerate(self.points):
            color=(168,186,157) if p.owner is None else (113,207,238) if p.owner==0 else (238,132,91)
            label=p.name+' '+('中立' if p.owner is None else '己方' if p.owner==0 else '敌方')
            if p.contested:label+=' 争夺'
            elif p.progress>0:label+=f' {p.progress/(12 if p.owner is None else 6)*100:.0f}%'
            text(label,(398+i*128,39),14,color)

def install(Game,api):
    init=Game.__init__;update=Game.update;draw=Game.draw;announce=Game.announce_kill
    def wrapped_init(self,*a,**kw):
        init(self,*a,**kw);self.tickets=[5000.,5000.]
        self.objectives=[Objective(self,name,position) for name,position in self.map_layout['points']]
        self.objective=self.objectives[0] if len(self.objectives)==1 else Objectives(self,self.objectives)
        clearance=360 if self.map_id=='urban_front' else 520
        zones=[pygame.Rect(p.p.x-clearance,p.p.y-clearance,clearance*2,clearance*2) for p in self.objectives]
        self.terrain.obstacles=[(r,k) for r,k in self.terrain.obstacles if not any(zone.colliderect(r) for zone in zones)]
        self.terrain.trees=[(p,size) for p,size in self.terrain.trees if not any(zone.collidepoint(p) for zone in zones)]
        self.terrain.ponds=[r for r in self.terrain.ponds if not any(zone.colliderect(r) for zone in zones)]
    def wrapped_announce(self,attacker,victim,weapon=''):
        announce(self,attacker,victim,weapon)
        recorded=victim.get('ticket_loss_recorded',False) if isinstance(victim,dict) else getattr(victim,'ticket_loss_recorded',False)
        if recorded:return
        team=victim.get('team',1) if isinstance(victim,dict) else int(victim.enemy)
        if isinstance(victim,dict):victim['ticket_loss_recorded']=True
        else:
            victim.ticket_loss_recorded=True
            victim.wreck_age=0.
        self.tickets[team]=max(0,self.tickets[team]-60)
    def wrapped_update(self,dt):
        if not self.paused and self.state in ('play','deploy','wreck'):
            for t in self.wrecks:t.wreck_age=getattr(t,'wreck_age',0.)+dt
            self.wrecks=[t for t in self.wrecks if t.wreck_age<api['WRECK_LIFETIME']]
        update(self,dt)
        if self.paused or self.state not in ('play','deploy','wreck'):return
        self.objective.update(dt)
        if min(self.tickets)<=0:
            self.state='win' if self.tickets[1]<=0 and self.tickets[0]>0 else 'lose';self.enemy_queue.clear();self.ally_queue.clear()
            self.player.reason='双方战场分数耗尽' if max(self.tickets)<=0 else '己方战场分数耗尽' if self.state=='lose' else '敌方战场分数耗尽'
    def wrapped_draw(self,*a,**kw):
        draw(self,*a,**kw);self.objective.draw(api['screen'],api['text'],api)
        api['text'](self.map_name,(18,48),14,(178,207,202))
        counts=[]
        for team,units in ((0,self.allies),(1,self.enemies)):
            ground=sum(not t.dead for t in units)
            air=sum(not q['dead'] and q.get('team',1)==team for q in self.air.planes)
            player=int(team==0 and not self.player.dead and not getattr(self.player,'airborne',False) and self.state!='deploy')
            counts.append(ground+air+player)
        api['text'](f'己方 {counts[0]}/16 · 敌方 {counts[1]}/16',(800,48),14,(178,207,202))
    Game.__init__=wrapped_init;Game.update=wrapped_update;Game.draw=wrapped_draw;Game.announce_kill=wrapped_announce

def map_self_test(api):
    import random
    from BattleMaps import choose_map,MAPS
    Game=api['Game'];V=api['V']
    assert set(choose_map(random.Random(i)) for i in range(50))==set(MAPS)
    old=Game(True,map_id='wilderness');g=Game(True,map_id='three_fronts')
    assert len(old.objectives)==1 and len(g.objectives)==3
    assert old.map_name!=g.map_name and old.terrain.roads!=g.terrain.roads
    assert all(len(bases)==2 for bases in api['DEPLOY_BASES'].values())
    for point in g.objectives:
        assert g.terrain.free(point.p,320)
        assert not any(r.collidepoint(point.p) for r in g.terrain.ponds)
    g.allies=[];g.enemies=[];g.player.p=V(1000,3500)
    a,b,c=g.objectives
    a.owner=0;g.objective.update(1);assert g.tickets==[5000.,5000.]
    b.owner=0;g.objective.update(1);assert abs(g.tickets[1]-4996)<.001
    c.owner=1;g.objective.update(1);assert abs(g.tickets[1]-4992)<.001 and g.tickets[0]==5000
    a.owner=None;g.player.p=V(a.p);g.objective.update(12.1);assert a.owner==0
    foe=api['Tank'](a.p,enemy=True);g.enemies=[foe]
    g.objective.update(20);assert a.owner==0 and a.contested
    g.player.p=V(1000,3500);g.objective.update(6.1);assert a.owner is None
    g.objective.update(12.1);assert a.owner==1
    g.spawn_allies(15)
    units=g.objective.assign(0)
    counts=[sum(u.ai_objective is p for u in units) for p in g.objectives]
    assert max(counts)-min(counts)<=1 and min(counts)>0
    for u in units:g.objective.ai_goal(u)
    assert len({id(u.ai_objective) for u in units})==3
    city=Game(True,map_id='urban_front')
    assert len(city.objectives)==3 and len(city.terrain.city_regions)==3
    assert sum(k=='house' for r,k in city.terrain.obstacles)>140
    from UrbanMap import draw_ground
    canvas=api['pygame'].Surface((800,800));draw_ground(city.terrain,canvas,V(3200,2000),canvas.get_rect())
    for pixel in ((400,400),(290,400),(400,290)):assert tuple(canvas.get_at(pixel))[:3]==(105,116,122)
    houses=[r for r,k in city.terrain.obstacles if k=='house']
    assert all(not house.inflate(24,24).colliderect(road) for house in houses for road in city.terrain.roads)
    for point in city.objectives:assert city.terrain.free(point.p,320)
    for x in (3600,4500,5400):
        for y in range(300,6700,150):assert city.terrain.free(V(x,y),60),('blocked city artery',x,y)
    for y in (2400,3500,4800):
        for x in range(300,8700,150):assert city.terrain.free(V(x,y),60),('blocked city avenue',x,y)
    assert city.deploy_player(api['DEPLOY_BASES'][False][0]) is False
    city.deploy_selected=True;assert city.deploy_player(api['DEPLOY_BASES'][False][0])
    city.player.p=V(4500,3500);city.camera();city.draw()
    g.draw();old.draw()
    print('Map tests passed: random layouts, four deployment zones, three independent defended objectives, majority tickets and distributed AI.')
