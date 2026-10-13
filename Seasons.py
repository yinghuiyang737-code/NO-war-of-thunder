"""Deterministic seasonal terrain variation and a low-probability night battle roll."""
import math,pygame,random
from pygame.math import Vector2 as V
NIGHT_CHANCE=.10
PALETTES={'winter':[(213,225,231),(224,233,237),(200,216,224),(218,228,231)],'autumn':[(118,107,60),(133,112,58),(103,110,61),(144,119,66)],'summer':[(69,83,48),(78,94,53),(62,80,45),(87,99,57)]}
def season(g):return 'winter' if g.map_id=='urban_front' else 'autumn' if g.map_id=='three_fronts' else 'summer'
def tree(g,p,layer=1):
    mode=season(g);n=(int(p.x)//17+int(p.y)//23)%4
    colors=[(157,105,46),(178,126,45),(149,77,38),(117,115,54)] if mode=='autumn' else [(129,151,143),(157,178,174),(175,194,190),(143,165,158)] if mode=='winter' else [(43,70,40),(60,91,46),(76,106,53),(62,86,44)]
    c=colors[n];return tuple(min(255,int(v*(.8+layer*.12))) for v in c)
def ground(g,s,view,at,z=1):
    mode=season(g);colors=PALETTES[mode];pygame.draw.rect(s,colors[0],view)
    a=g.screen_to_world(view.topleft) if z!=1 else g.cam+V(view.topleft)
    b=g.screen_to_world(view.bottomright) if z!=1 else g.cam+V(view.bottomright)
    cell=280
    for x in range(math.floor(a.x/cell)-1,math.floor(b.x/cell)+2):
        for y in range(math.floor(a.y/cell)-1,math.floor(b.y/cell)+2):
            n=(x*73856093^y*19349663^getattr(g.terrain,"seed",7182))&65535
            p=at(V(x*cell,y*cell));r=pygame.FRect(p.x,p.y,cell*z+1,cell*z+1)

            q=at(V(x*cell+n%50,y*cell+(n//50)%50));pygame.draw.ellipse(s,colors[(n+1)%4],pygame.FRect(q.x,q.y,(100+n%170)*z,(75+n%180)*z))
def night(rng=random):return rng.random()<NIGHT_CHANCE
