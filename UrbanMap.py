"""Deterministic city districts with connected wide streets and open capture squares."""
import pygame
from pygame.math import Vector2 as V

def prepare(terrain,layout):
    terrain.city_regions=[pygame.Rect(2100,1100,2400,2200),pygame.Rect(3900,2800,1200,1400),pygame.Rect(4500,3700,2400,2200)]
    terrain.ponds=[pygame.Rect(1400,3000,520,360),pygame.Rect(7080,3640,520,360),pygame.Rect(6200,900,600,360),pygame.Rect(2200,5740,600,360)]
    # One coordinated street grid; local streets never duplicate or offset a main road.
    terrain.roads=[pygame.Rect(0,y-100,9000,200) for y in (2400,3500,4800)]+[pygame.Rect(x-100,0,200,7000) for x in (3600,4500,5400)]
    terrain.roads.extend(pygame.Rect(x-80,1100,160,2200) for x in (2400,3000))
    terrain.roads.extend(pygame.Rect(x-80,3700,160,2200) for x in (6000,6600))
    terrain.roads.extend(pygame.Rect(2100,y-80,2400,160) for y in (1400,1900,2900))
    terrain.roads.extend(pygame.Rect(4500,y-80,2400,160) for y in (4100,5300,5800))
    for region in terrain.city_regions:
        for x in range(region.left+35,region.right-110,120):
            for y in range(region.top+35,region.bottom-110,125):
                building=pygame.Rect(x,y,100,105)
                if any(building.inflate(24,24).colliderect(road) for road in terrain.roads):continue
                if any(building.colliderect(pygame.Rect(point[0]-360,point[1]-360,720,720)) for _,point in layout['points']):continue
                if any(building.inflate(12,12).colliderect(r) for r,k in terrain.obstacles if k=='house'):continue
                terrain.obstacles.append((building,'house'))

def draw_ground(terrain,screen,camera,view):
    winter=getattr(terrain,"map_id",None)=="urban_front"
    for region in terrain.city_regions:
        r=region.move(-camera.x,-camera.y)
        if r.colliderect(view):pygame.draw.rect(screen,(205,218,224) if winter else (99,103,96),r)
    visible=[road for road in terrain.roads if road.move(-camera.x,-camera.y).inflate(30,30).colliderect(view)]
    # Draw the complete pavement union before markings: intersections have no curb through their center.
    for road in visible:pygame.draw.rect(screen,(230,237,240) if winter else (137,133,120),road.move(-camera.x,-camera.y).inflate(24,24))
    for road in visible:pygame.draw.rect(screen,(105,116,122) if winter else (71,76,77),road.move(-camera.x,-camera.y))
    for road in visible:
        horizontal=road.w>road.h
        perpendicular=[other.inflate(24,24) for other in terrain.roads if (other.w>other.h)!=horizontal]
        first=max(road.left,int(camera.x+view.left)) if horizontal else max(road.top,int(camera.y+view.top))
        last=min(road.right,int(camera.x+view.right)) if horizontal else min(road.bottom,int(camera.y+view.bottom))
        for along in range(first//100*100,last,100):
            stripe=pygame.Rect(along,road.centery-1,40,3) if horizontal else pygame.Rect(road.centerx-1,along,3,40)
            if not road.contains(stripe) or any(stripe.colliderect(other) for other in perpendicular):continue
            pygame.draw.rect(screen,(179,173,137),stripe.move(-camera.x,-camera.y))
