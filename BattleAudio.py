"""World-wide nuclear alert; local first-deployment voice remains per player."""
def nuclear_alarm(g):
    if g is None or getattr(g,'state',None) in ('win','lose'):return False
    if hasattr(g,'_nuclear_alarm_remote'):return bool(g._nuclear_alarm_remote)
    world=getattr(g,'_lan_world',None) or g
    if getattr(world,'nuclear_result',None) or getattr(getattr(world,'flight',None),'nuke_detonated',False):return False
    authority=getattr(world,'_lan_authority',None)
    contexts=list(authority.contexts.values()) if authority else [world]
    for ctx in contexts:
        flight=getattr(ctx,'flight',None);plane=getattr(flight,'plane',None)
        if plane and getattr(plane,'nuclear',False) and not plane.dead:return True
        if getattr(flight,'nuke_timer',None) is not None:return True
    if getattr(world,'ai_nuclear',None):return True
    for q in getattr(getattr(world,'air',None),'planes',[]):
        if not q.get('dead',False) and (q.get('ai_nuclear') or q.get('nuclear') or getattr(q.get('ai_plane'),'nuclear',False)):return True
    return False


def alarm_playing(settings,g):
    """Continuously loop the alert while the nuclear threat remains active."""
    return bool(g and not g.paused and not settings.config['muted'] and nuclear_alarm(g))
