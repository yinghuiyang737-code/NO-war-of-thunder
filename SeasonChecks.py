"""Season visuals, compressed snow, lifetime bounds and automatic night selection."""
import pygame,random
from pygame.math import Vector2 as V
from Seasons import season,ground,tree,night,NIGHT_CHANCE,PALETTES
from GroundTraces import emit,prune,LIFETIME,MAX_TRACES,contacts

def run(api):
    from InputBindings import ACTIONS
    assert 'ground.night_battle' not in ACTIONS and 0<NIGHT_CHANCE<.2
    rng=random.Random(77);fraction=sum(night(rng) for _ in range(5000))/5000;assert .08<fraction<.12
    colors=[]
    for name,mode in [('wilderness','summer'),('three_fronts','autumn'),('urban_front','winter')]:
        g=api['Game'](False,'ussr',['ussr_1_7']+[None]*11,map_id=name);assert season(g)==mode
        g.player.p=V(3000,3000);g.camera();g.vision='day';g.night_battle=False
        s=pygame.Surface((600,400));view=s.get_rect();ground(g,s,view,lambda p:p-V(3000,3000),1)
        pixels={s.get_at((x,y))[:3] for x in range(0,600,40) for y in range(0,400,40)};assert len(pixels)>1
        colors.append(PALETTES[mode][0]);g.draw();g.state='deploy';g.draw_deployment()
        g.state='play';g.night_battle=True;g.draw()
    assert len(set(colors))==3
    g=api['Game'](False,'ussr',['ussr_1_7']+[None]*11,map_id='urban_front');t=g.player;g.tracks=[];emit(t,g.tracks,0,True);t.p+=V(20,0);emit(t,g.tracks,1,True)
    assert g.tracks and all(len(m)==4 for m in g.tracks)
    g.time=100;prune(g);assert g.tracks
    g.time=LIFETIME+2;prune(g);assert not g.tracks
    wheeled=next(k for k,v in api['VEHICLES'].items() if v.get('wheel'));t=api['Tank']((2000,2000),vehicle=wheeled)
    assert not contacts(t) and len(contacts(t,True))==2
    g.tracks=[(V(),V(1,0),4,999)]*(MAX_TRACES+1);g.time=1;prune(g);assert len(g.tracks)==MAX_TRACES
    print('PASS three seasonal palettes/spatial variation, winter tyre and track compression, extended bounded trace lifetime, automatic 10% night chance and no manual day/night action')
