"""Keep the entire battle update chain active behind a dead player's deployment UI."""
def install(Game):
    previous=Game.update
    def update(g,dt):
        waiting=g.state=='deploy' and g.player.dead and getattr(g,'player_death_handled',False)
        if not waiting:return previous(g,dt)
        if g.paused:return
        g.deploy_delay=max(0,g.deploy_delay-dt)
        controls=g.controls
        from Reconnaissance import MaskControls
        g.controls=MaskControls(controls);g.state='play'
        try:previous(g,dt)
        finally:
            g.controls=controls
            if g.state=='play':g.state='deploy'
    Game.update=update
