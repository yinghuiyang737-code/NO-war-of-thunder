"""Draw the flight view directly at display resolution, including very wide zoom.
Avoids allocating a many-hundred-megabyte world image when zooming out.
"""
import math
import pygame
from pygame.math import Vector2 as V
from VehicleModels import draw_model
from Aviation import draw_aircraft
from AircraftRadar import position,velocity
from BattleRendering import trees,world_bounds,vehicle as draw_ground

def intercept(origin,target,target_velocity,speed):
    r=V(target)-origin;v=V(target_velocity);a=v.length_squared()-speed*speed;b=2*r.dot(v);c=r.length_squared()
    if abs(a)<1e-8:times=[-c/b] if abs(b)>1e-8 else []
    else:
        discriminant=b*b-4*a*c
        times=[(-b-math.sqrt(discriminant))/(2*a),(-b+math.sqrt(discriminant))/(2*a)] if discriminant>=0 else []
    positive=[t for t in times if t>0]
    if not positive:return None
    seconds=min(positive);return V(target)+v*seconds,seconds

def draw(f,mouse=None):
    g=f.g;s=f.api['screen'];text=f.api['text'];view=f.api['VIEW'];z=g.zoom;at=g.world_to_display
    s.fill((69,83,48));s.set_clip(view)
    from Seasons import ground,tree,season
    ground(g,s,view,at,z)
    def rect(r):
        q=at(r.topleft);return pygame.FRect(q.x,q.y,r.w*z,r.h*z)
    for road in g.terrain.roads:pygame.draw.rect(s,(151,163,170) if season(g)=='winter' else (115,102,67),rect(road))
    for pond in g.terrain.ponds:
        pygame.draw.rect(s,(112,109,73),rect(pond.inflate(14,14)),border_radius=max(1,int(12*z)))
        pygame.draw.rect(s,(97,151,144),rect(pond),border_radius=max(1,int(8*z)))
    bounds=world_bounds(g,view)
    for r,kind in g.terrain.nearby_obstacles(bounds):
        rr=rect(r)
        if not rr.colliderect(view) or kind=='tree':continue
        if kind=='deep_water':pygame.draw.rect(s,(39,77,93),rr)
        elif kind=='house':
            pygame.draw.rect(s,(34,40,30),rr.move(5*z,7*z));pygame.draw.rect(s,(223,232,235) if season(g)=='winter' else (145,117,83),rr)
            pygame.draw.line(s,(76,64,45),(rr.centerx,rr.top),(rr.centerx,rr.bottom),max(1,int(3*z)))
        else:pygame.draw.ellipse(s,(120,124,102),rr)
    for p,r in trees(g.terrain,bounds):
        q=at(p)
        if not view.inflate(50,50).collidepoint(q):continue
        pygame.draw.circle(s,(41,51,31),q+V(5,7)*z,max(1,int(r*z)))
        pygame.draw.circle(s,tree(g,p,0),q,max(1,int(r*z)));pygame.draw.circle(s,tree(g,p,2),q-V(6,6)*z,max(1,int(r*z*.5)))
    for p,r,a,progress in g.terrain.fallen:
        q=at(p);tip=at(p+V(math.cos(math.radians(a)),math.sin(math.radians(a)))*r*2*progress)
        if view.inflate(50,50).collidepoint(q):pygame.draw.line(s,(111,83,47),q,tip,max(1,int(7*z)))
    if getattr(g,'objective',None):g.objective.draw_world(s,text,at,z)
    from GroundTraces import draw as draw_traces
    draw_traces(g,s,at,view,z)
    for tank in g.wrecks+g.enemies+g.allies:
        q=at(tank.p)
        if not tank.vehicle_id or not view.inflate(120,120).collidepoint(q):continue
        draw_ground(s,tank.stats,q,.56*z,tank.body,True,tank.aim,(70,72,61) if tank.dead else None)
    for cloud in g.smokes:
        q=at(cloud['p']);radius=max(2,int(cloud['radius']*z))
        if not view.inflate(radius*2,radius*2).collidepoint(q):continue
        from AIRedeployResponse import smoke_image
        image=smoke_image(radius,cloud['kind']);image.set_alpha(180);s.blit(image,q-V(image.get_width()/2,image.get_height()/2))
    for b in g.bullets:
        q=at(b[0]);pygame.draw.line(s,(251,216,140),q-b[1].normalize()*max(2,15*z),q,1)
    for fx in g.fx:
        q=at(fx[0])
        if view.collidepoint(q):pygame.draw.circle(s,fx[3],q,max(1,int(fx[2]*8*z)))
    for p in g.air.planes:
        if p.get('controlled') or p['dead'] or not p.get('model'):continue
        q=at(p['p'])
        if not view.inflate(200,200).collidepoint(q):continue
        heading=math.degrees(math.atan2(p['v'].y,p['v'].x));draw_aircraft(s,p['model'],q,z,heading,units=8,bank=p.get('bank',0))
        if p.get('managed'):text(('敌军' if p['team'] else '队友')+' '+p['model']['name'],q+V(0,45),14,(240,156,117) if p['team'] else (134,211,246),True)
    for missile in g.air.missiles:
        q=at(missile['p']);pygame.draw.line(s,(245,215,136),q-missile['v'].normalize()*max(3,18*z),q,2)
    f.draw_world(s,display=True)
    if g.night_battle and g.vision=='day':
        from VisionRendering import apply
        apply(g,s,view,.56,draw_model)
    s.set_clip(None)
    pygame.draw.rect(s,(15,24,21),(0,0,s.get_width(),68));pygame.draw.rect(s,(15,24,21),(0,s.get_height()-42,s.get_width(),42))
    text('钢铁旷野',(22,15),30);text('STEEL WILDERNESS',(184,27),14,(133,157,123))
    enemy_air=sum(1 for q in g.air.planes if not q['dead'] and q.get('team',1)==1)
    text(f'歼灭 {g.ground_kills}/{g.kill_goal} · 敌车 {len(g.enemies)} / 敌机 {enemy_air}',(390,25),18)
    text(f'飞机广角视野 {z:.2f}× · 滚轮缩放',(390,50),14,(194,230,164))
    for i,m in enumerate(g.messages):text(m[0],(350,575-i*23),16,m[1])
    f.hud()
    if g.state=='play':draw_aim(f,mouse)
    elif g.state=='win' and not f.nuke_detonated:g.overlay('战斗胜利','敌方战场分数耗尽',g.controls.label('common.back')+' 返回机库 · '+g.controls.label('common.restart')+' 重新出战')
    elif g.state=='lose':g.overlay('战斗失败',g.player.reason or '己方战场分数耗尽',g.controls.label('common.back')+' 返回机库 · '+g.controls.label('common.restart')+' 重新出战')
    if g.paused:g.overlay('已暂停',g.controls.label('common.pause')+' 继续战斗')

def draw_aim(f,mouse=None):
    p=f.plane;g=f.g;s=f.api['screen'];text=f.api['text'];view=f.api['VIEW'];at=g.world_to_display
    mouse=V(pygame.mouse.get_pos() if mouse is None else mouse)
    guided=f.guided_missile()
    if guided:
        center=at(guided['p']);col=(172,246,211)
        pygame.draw.circle(s,col,mouse,16,2)
        pygame.draw.line(s,col,mouse-V(26,0),mouse+V(26,0),1)
        pygame.draw.line(s,col,mouse-V(0,26),mouse+V(0,26),1)
        pygame.draw.line(s,col,center,center+guided['v'].normalize()*45,2)
        text('导弹视角 · '+guided['weapon']['short']+' · 鼠标引导',(view.centerx,view.top+45),20,col,True)
        draw_locks(f,guided['p'])
        return

    pool=[q for q in g.air.planes if q.get('team',1)==1 and not q['dead']]+[q for q in g.enemies if not q.dead]
    selected=f.lock if f.lock is not None and not (f.lock.get('dead',False) if isinstance(f.lock,dict) else f.lock.dead) else f.radar.selected
    ground=p.ground_lock if p.ground_lock is not None and not p.ground_lock.dead else None
    if selected is None and ground is not None:selected=ground
    if selected is None:
        visible=[q for q in pool if view.collidepoint(at(position(q))) and at(position(q)).distance_to(mouse)<160]
        selected=min(visible,key=lambda q:at(position(q)).distance_to(mouse),default=None)
    def marker(point,col,label,shape='circle'):
        q=at(point);safe=pygame.Rect(345,160,660,455);inside=safe.collidepoint(q)
        end=V(max(safe.left,min(safe.right,q.x)),max(safe.top,min(safe.bottom,q.y)))
        if inside:
            pygame.draw.circle(s,col,end,10,2);pygame.draw.line(s,col,end-V(16,0),end+V(16,0),1);pygame.draw.line(s,col,end-V(0,16),end+V(0,16),1)
        else:
            delta=q-end
            if delta.length_squared():
                d=delta.normalize();side=d.rotate(90);pygame.draw.polygon(s,col,[end+d*8,end-d*6+side*6,end-d*6-side*6],2)
            label+=' · 视野外'
        text(label,(end.x+15 if end.x<safe.centerx else end.x-155,end.y-22),14,col)
        return end
    # Visible gun impact reference even without a selected target.
    forward=V(math.cos(math.radians(p.a)),math.sin(math.radians(p.a)))
    marker(p.p+forward*(2400+p.speed)*.55,(156,209,234),'机炮指向 / 0.55s')
    if selected is not None:
        result=intercept(p.p,position(selected),velocity(selected),2400+p.speed)
        if result and (selected is not ground or result[1]<=1.1):
            point,seconds=result;col=(247,219,119) if seconds<=1.1 else (236,157,101)
            a=marker(point,col,f'提前量 {seconds:.2f}s'+(' · 超射程' if seconds>1.1 else ''))
            target=at(position(selected));s.set_clip(pygame.Rect(340,130,675,488));pygame.draw.line(s,col,target,a,1)
            if view.collidepoint(target):pygame.draw.rect(s,col,(target.x-16,target.y-16,32,32),1)
            s.set_clip(None)
    draw_locks(f,p.p)
    f.last_lead=selected

def draw_locks(f,origin):
    from TargetMarkers import draw as draw_target
    p=f.plane;g=f.g;s=f.api['screen'];text=f.api['text'];at=g.world_to_display;view=f.api['VIEW']
    ground=p.ground_lock if p.ground_lock is not None and not p.ground_lock.dead else None
    safe=pygame.Rect(view.left+24,view.top+90,max(280,view.width-48),max(80,view.height-145))
    f.last_target_markers=[]
    for target,label,col in ((ground,'地面自动锁定',(126,250,168)),(f.lock,'空中锁定',(247,211,104))):
        if target is None or (target.get('dead',False) if isinstance(target,dict) else target.dead):continue
        distance=position(target).distance_to(origin)/8000
        f.last_target_markers.append(draw_target(s,text,at(position(target)),safe,f'{label} {distance:.2f} km',col,at(origin)))
