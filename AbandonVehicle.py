"""Authoritative held-key abandonment, shared by solo and LAN contexts."""
import pygame

def step(g,dt):
    active=g.state=='play' and not g.paused and not g.player.dead
    held=active and g.controls.keys(g.input_context())[pygame.K_F6]
    g.abandon_elapsed=min(3.,getattr(g,'abandon_elapsed',0.)+dt) if held else 0.
    if g.abandon_elapsed<3:return False
    g.abandon_elapsed=0.;g.player.last_attacker=None;g.player.last_weapon='主动弃机' if g.flight.active else '主动弃车'
    if g.flight.active:g.flight.destroy()
    else:
        g.player.dead=True;g.player.reason='主动弃车';g.register_death(g.player)
    return True

def install(Game,api):
    old=Game.update;draw=Game.draw
    def update(g,dt):
        step(g,dt);old(g,dt)
    def render(g,*args,**kwargs):
        draw(g,*args,**kwargs)
        elapsed=getattr(g,'abandon_elapsed',0.)
        if elapsed>0 and g.state=='play':api['text']('弃机' if g.flight.active else '弃车',(570,200),24);api['text'](f'{3-elapsed:.1f} 秒 · 松开取消',(520,235),18)
        elif g.state=='play':api['text'](g.controls.label('common.abandon')+' 按住 3 秒弃车 / 弃机',(470,760),16)
    Game.update=update;Game.draw=render
