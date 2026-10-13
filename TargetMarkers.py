import pygame
from pygame.math import Vector2 as V

def project(point,rect,origin=None):
    q=V(point);r=pygame.Rect(rect)
    if r.collidepoint(q):return q,False
    start=V(origin or r.center)
    start.x=max(r.left,min(r.right-1,start.x));start.y=max(r.top,min(r.bottom-1,start.y))
    d=q-start;times=[]
    if d.x:times.append(((r.right-1 if d.x>0 else r.left)-start.x)/d.x)
    if d.y:times.append(((r.bottom-1 if d.y>0 else r.top)-start.y)/d.y)
    return start+d*min(x for x in times if x>=0),True

def draw(surface,text,point,rect,label,color,origin=None):
    q,edge=project(point,rect,origin);r=pygame.Rect(rect)
    pygame.draw.rect(surface,color,(q.x-14,q.y-14,28,28),2)
    if edge:
        d=V(point)-q
        if d.length_squared():
            d=d.normalize();side=d.rotate(90)
            pygame.draw.polygon(surface,color,[q+d*12,q-d*6+side*6,q-d*6-side*6])
        label+=' · 视野外'
    x=max(r.left,min(r.right-250,q.x+19 if q.x<r.centerx else q.x-250))
    text(label,(x,max(r.top,min(r.bottom-22,q.y-27))),14,color)
    return {'point':q,'edge':edge,'label':label}
