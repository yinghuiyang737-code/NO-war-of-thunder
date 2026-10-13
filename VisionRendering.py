"""Display-resolution, native grayscale vision filters with reusable surfaces."""
import pygame,math
from pygame.math import Vector2 as V

def apply(g,screen,view,model_scale,draw_model):
    mode=g.vision
    if mode not in ('night','thermal') and not g.night_battle:return
    if getattr(g,'vision_buffer',None) is None or g.vision_buffer.get_size()!=view.size:
        g.vision_buffer=pygame.Surface(view.size).convert()
        g.darkness_buffer=pygame.Surface(view.size,pygame.SRCALPHA);g.darkness_buffer.fill((1,5,15,185))
    if mode not in ('night','thermal'):
        screen.blit(g.darkness_buffer,view.topleft);return
    image=g.vision_buffer
    pygame.transform.grayscale(screen.subsurface(view),image)
    if mode=='night':
        image.fill((64,255,51),special_flags=pygame.BLEND_RGB_MULT)
        image.fill((0,20,0),special_flags=pygame.BLEND_RGB_ADD)
    else:
        image.fill((128,128,128),special_flags=pygame.BLEND_RGB_MULT)
        image.fill((20,20,20),special_flags=pygame.BLEND_RGB_ADD)
    screen.blit(image,view.topleft)
    if mode!='thermal':return
    model_cache=getattr(g,'thermal_models',{});next_cache={}
    visible_bounds=view.inflate(140,140)
    for target in g.enemies+g.allies+[g.player]+g.wrecks:
        point=g.world_to_display(target.p)
        if not visible_bounds.collidepoint(point):continue
        heat=(245,245,245) if not target.dead else (99,99,99)
        if target.vehicle_id:
            length,width,kind,offset,r,gun=target.stats['model']
            half=math.ceil((max(length,width,gun+abs(offset),32)*model_scale*g.zoom+16)/16)*16
            key=(target.vehicle_id,target.stats.get('name'),half,round(model_scale*g.zoom,4),target.body,target.aim,target.dead)
            cached=model_cache.get(target)
            if cached and cached[0]==key:sprite=cached[1]
            else:
                sprite=cached[1] if cached and cached[1].get_size()==(half*2,half*2) else pygame.Surface((half*2,half*2),pygame.SRCALPHA)
                sprite.fill((0,0,0,0))
                draw_model(sprite,target.stats,(half,half),model_scale*g.zoom,target.body,True,target.aim,heat)
                if target.dead:sprite.fill((99,99,99,255),special_flags=pygame.BLEND_RGB_MIN)
                else:sprite.fill((215,215,215,255),special_flags=pygame.BLEND_RGB_MAX)
            next_cache[target]=(key,sprite)
            screen.blit(sprite,point-V(half,half))
        else:pygame.draw.rect(screen,heat,pygame.Rect(point-V(25,20)*g.zoom,V(50,40)*g.zoom),border_radius=4)
    g.thermal_models=next_cache
    # Shells and machine-gun tracers remain luminous after the native grayscale pass.
    for b in g.bullets:
        q=g.world_to_display(b[0])
        if view.inflate(20,20).collidepoint(q):
            v=V(b[1]);tail=v.normalize()*max(3,15*g.zoom) if v.length_squared() else V()
            pygame.draw.line(screen,(255,255,255),q-tail,q,max(1,round(2*g.zoom)))
    for start,end,life in g.mg_tracers:
        a=g.world_to_display(start);b=g.world_to_display(end)
        if view.clipline(a,b):pygame.draw.line(screen,(255,255,255),a,b,2)
    for cloud in g.smokes:
        if cloud['kind']=='ess' or (cloud['kind']!='grenade' and not cloud.get('thermal_heat')):continue
        radius=max(2,round(cloud['radius']*g.zoom));q=g.world_to_display(cloud['p'])
        if not view.inflate(radius*2,radius*2).collidepoint(q):continue
        from AIRedeployResponse import smoke_image
        source=smoke_image(radius,'thermal')
        fade=min(1,cloud['age']/.25,max(0,(cloud['life']-cloud['age'])/4))
        source.set_alpha(round(255*fade));screen.blit(source,q-V(source.get_width()/2,source.get_height()/2))
