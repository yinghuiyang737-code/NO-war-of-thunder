"""Spatial queries and a geometry-preserving distant ground vehicle detail level."""
import math,pygame
from pygame.math import Vector2 as V
from VehicleModels import draw_model,hull_points,turret_points

def world_bounds(g,view,margin=90):
    a=g.screen_to_world(view.topleft);b=g.screen_to_world(view.bottomright)
    return pygame.FRect(a,b-a).inflate(margin*2,margin*2)

def trees(terrain,bounds):
    signature=(id(terrain.trees),len(terrain.trees))
    if getattr(terrain,'tree_signature',None)!=signature:
        chunks={}
        for item in terrain.trees:chunks.setdefault((math.floor(item[0].x/512),math.floor(item[0].y/512)),[]).append(item)
        terrain.tree_chunks=chunks;terrain.tree_signature=signature
    for x in range(math.floor(bounds.left/512),math.floor(bounds.right/512)+1):
        for y in range(math.floor(bounds.top/512),math.floor(bounds.bottom/512)+1):
            yield from terrain.tree_chunks.get((x,y),())

def vehicle(surface,stats,point,scale,body,top=True,turret_yaw=None,color=None):
    # Close views retain every model detail. At under ~30 px, tiny tread plates
    # and engine grilles cost much more than their contribution to the image.
    if scale>=.20:return draw_model(surface,stats,point,scale,body,top,turret_yaw,color)
    point=V(point);col=color or stats['color'];length,width,kind,offset,radius,gun=stats['model']
    def project(points,angle,origin):
        a=math.radians(angle);c=math.cos(a)*scale;s=math.sin(a)*scale
        return [(origin.x+x*c-y*s,origin.y+x*s+y*c) for x,y in points]
    for side in (-1,1):
        pygame.draw.line(surface,(35,40,34),*project([(-length,side*(width+1)),(length,side*(width+1))],body,point),max(1,round(8*scale)))
    pygame.draw.polygon(surface,col,project(hull_points(stats),body,point))
    aim=body if turret_yaw is None else turret_yaw
    pygame.draw.polygon(surface,tuple(round(c*.85) for c in col),project(turret_points(stats),aim,point))
    pygame.draw.line(surface,col,*project([(offset+12,0),(gun,0)],aim,point),max(1,round(4*scale)))

def cached_vehicle(surface,tank,point,scale,color):
    stats=tank.stats;length,width,kind,offset,radius,gun=stats['model']
    half=math.ceil((max(length,width,gun+abs(offset),32)*scale+32)/16)*16
    key=(tank.vehicle_id,stats['name'],stats['model'],scale,tank.body,tank.aim,color)
    cached=getattr(tank,'rendered_pose',None)
    if cached and cached[0]==key:sprite=cached[1]
    else:
        sprite=cached[1] if cached and cached[1].get_size()==(half*2,half*2) else pygame.Surface((half*2,half*2),pygame.SRCALPHA)
        sprite.fill((0,0,0,0));draw_model(sprite,stats,(half,half),scale,tank.body,True,tank.aim,color)
        tank.rendered_pose=(key,sprite)
    surface.blit(sprite,V(point)-V(half,half))
