"""Ground traces follow the rendered undercarriage rather than fixed tank offsets."""
import math,pygame
from collections import OrderedDict
from pygame.math import Vector2 as V
from VehicleGeometry import MODEL_SCALE

def contacts(t,snow=False):
    if not t.vehicle_id:return [('left_track',t.world((0,-22)),4),('right_track',t.world((0,22)),4)]
    v=t.stats
    if v.get('wheel'):
        if not snow:return []
        length,width=v['model'][:2]
        return [(key,t.world((-length*.7*MODEL_SCALE,side*(width+1)*MODEL_SCALE)),5*MODEL_SCALE) for side,key in ((-1,'left_track'),(1,'right_track'))]
    width=v['model'][1]
    # These dedicated models draw the track centre at width; generic/Buk models at width+1.
    offset=width if v.get('modern_aa') or v.get('reward_model') in ('LOSAT','Raketenautomat') else width+1
    return [(key,t.world((0,side*offset*MODEL_SCALE)),8*MODEL_SCALE) for side,key in ((-1,'left_track'),(1,'right_track'))]

LIFETIME=150.
MAX_TRACES=20000

def emit(t,traces,now=None,snow=False):
    current=contacts(t,snow) if not t.dead and not getattr(t,'airborne',False) else []
    previous=getattr(t,'trace_contacts',{})
    latest={}
    for key,point,width in current:
        old=previous.get(key)
        if old is None or old.distance_to(point)>600:latest[key]=V(point);continue
        distance=old.distance_to(point)
        if distance<4:latest[key]=old;continue
        steps=min(24,max(1,math.ceil(distance/5)))
        for i in range(steps):
            mark=(old.lerp(point,i/steps),old.lerp(point,(i+1)/steps),width)
            traces.append(mark+(now+LIFETIME,) if now is not None else mark)
        latest[key]=V(point)
    t.trace_contacts=latest

def draw(g,surface,at,view,zoom=1):
    bounds=pygame.FRect(g.cam.x,g.cam.y+g.render_view.top,g.render_view.w,g.render_view.h) if zoom==1 else pygame.FRect(g.screen_to_world(view.topleft),g.screen_to_world(view.bottomright)-g.screen_to_world(view.topleft))
    signature=(len(g.tracks),id(g.tracks[0]) if g.tracks else 0,id(g.tracks[-1]) if g.tracks else 0,g.map_id)
    # Rebuild at a bounded rate, then draw reusable raster tiles instead of thousands of lines.
    if not hasattr(g,'trace_tiles') or (signature!=getattr(g,'trace_signature',None) and g.time>=getattr(g,'trace_refresh',0)):
        cells=getattr(g,'trace_cells',{});registered=getattr(g,'trace_registered',OrderedDict())
        dirty=set();current_first=id(g.tracks[0]) if g.tracks else None
        # Remove dropped history incrementally, keeping raster tiles that have not changed.
        while registered and next(iter(registered))!=current_first:
            ident,old=registered.popitem(last=False)
            mark,keys=old
            for key in keys:
                cells[key].pop(ident,None);dirty.add(key)
                if not cells[key]:cells.pop(key)
        additions=[]
        for mark in reversed(g.tracks):
            if id(mark) in registered:break
            additions.append(mark)
        for mark in reversed(additions):
            start,end,width=mark[:3];keys=[];ident=id(mark)
            left=math.floor((min(start.x,end.x)-width)/512);right=math.floor((max(start.x,end.x)+width)/512)
            top=math.floor((min(start.y,end.y)-width)/512);bottom=math.floor((max(start.y,end.y)+width)/512)
            for x in range(left,right+1):
                for y in range(top,bottom+1):
                    key=(x,y);cells.setdefault(key,{})[ident]=mark;keys.append(key);dirty.add(key)
            registered[ident]=(mark,keys)
        tiles=getattr(g,'trace_tiles',{})
        for key in dirty:tiles.pop(key,None)
        g.trace_registered=registered;g.trace_cells=cells;g.trace_tiles=tiles;g.trace_scaled={};g.trace_signature=signature;g.trace_refresh=g.time+.35
    for x in range(math.floor(bounds.left/512),math.floor(bounds.right/512)+1):
        for y in range(math.floor(bounds.top/512),math.floor(bounds.bottom/512)+1):
            key=(x,y);marks=g.trace_cells.get(key)
            if not marks:continue
            tile=g.trace_tiles.get(key)
            if tile is None:
                tile=pygame.Surface((512,512),pygame.SRCALPHA);origin=V(x*512,y*512)
                for mark in marks.values():
                    start,end,width=mark[:3]
                    color=(135,157,171) if g.map_id=='urban_front' else (123,171,162) if g.terrain.in_shallow(end) else (52,61,36)
                    pygame.draw.line(tile,color,start-origin,end-origin,max(1,round(width)))
                g.trace_tiles[key]=tile
            point=at(V(x*512,y*512))
            if zoom==1:surface.blit(tile,point)
            else:
                cache=getattr(g,'trace_scaled',{})
                scale_key=(id(tile),round(zoom,5));image=cache.get(scale_key)
                if image is None:
                    if len(cache)>96:cache.clear()
                    image=pygame.transform.scale(tile,(max(1,math.ceil(512*zoom)),max(1,math.ceil(512*zoom))));cache[scale_key]=image
                g.trace_scaled=cache;surface.blit(image,point)
    # Historical tiles may refresh less often; the fresh tail must reach the
    # current track contact on every frame, including at high vehicle speeds.
    for mark in reversed(g.tracks):
        if id(mark) in g.trace_registered:break
        start,end,width=mark[:3]
        if not bounds.inflate(width*2,width*2).clipline(start,end):continue
        color=(135,157,171) if g.map_id=='urban_front' else (123,171,162) if g.terrain.in_shallow(end) else (52,61,36)
        pygame.draw.line(surface,color,at(start),at(end),max(1,round(width*zoom)))


def checks(api):
    widths=set()
    for ident,v in api['VEHICLES'].items():
        t=api['Tank']((2000,2000),vehicle=ident);t.body=37
        pairs=contacts(t)
        if v.get('wheel'):assert not pairs;continue
        assert len(pairs)==2
        widths.add(round(pairs[0][1].distance_to(pairs[1][1]),2))
        expected=(v['model'][1] if v.get('modern_aa') or v.get('reward_model') in ('LOSAT','Raketenautomat') else v['model'][1]+1)*MODEL_SCALE
        for key,p,w in pairs:assert abs(abs(t.local(p).y)-expected)<.0001 and abs(t.local(p).x)<.0001
        traces=[];emit(t,traces);t.p+=V(30,0).rotate(t.body);emit(t,traces)
        assert traces and all(abs(abs(t.local(a).y)-expected)<.0001 for a,b,w in traces)
        traces=[];t.speed=0;t.body+=90;emit(t,traces);assert traces
        t.p+=V(1000,0);traces=[];emit(t,traces);assert not traces
    assert len(widths)>5
    print('PASS all vehicle trace centres/scale/yaw, wheel exclusion, continuous translation/pivot traces and no teleport streaks')


def prune(g):g.tracks=[m for m in g.tracks if len(m)<4 or m[3]>g.time][-MAX_TRACES:]
