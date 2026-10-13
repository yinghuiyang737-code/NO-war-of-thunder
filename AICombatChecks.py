from pygame.math import Vector2 as V
from types import SimpleNamespace as N

def run(api):
    from AICombatAwareness import observe,observe_air,emit
    g=api['Game'](True,'us',['us_1_1']+[None]*11);g.time=10;g.state='play';g.bullets=[];g.visible=lambda *a:True;g.smoke_blocks=lambda *a:False
    def crew(skill=1):
        t=api['Tank']((1000,1000),vehicle='us_1_1');t.ai=True;t.aim=0;t.ai_skill=skill;return t
    a=api['Tank']((1600,1000),True,vehicle='ussr_1_1');friend=crew();friend.p=V(1200,1000);g.enemies=[a];g.allies=[friend]
    def reset():g.ai_incidents=[];g._ai_incident_cache=None;g.bullets=[];g.time+=10
    def shell():g.bullets=[[V(1100,1000),V(-900,0),True,4,0,a]]
    t=crew();shell();observe(g,t,.05);assert t.ai_incident_pending and not hasattr(t,'retaliation_attacker')
    strong_delay=t.ai_incident_pending['ready']-g.time
    weak=crew(0);weak.ai_attention=1;observe(g,weak,.05);assert weak.ai_incident_pending['ready']-g.time>strong_delay
    g.time+=strong_delay+.01;observe(g,t,.05);assert t.retaliation_attacker is a and t.ai_alert_kind=='projectile'
    reset();t=crew();t.aim=180;shell();g.bullets[0][0]=V(1550,1000);observe(g,t,.05);assert getattr(t,'ai_incident_pending',None) is None
    reset();t=crew();shell();g.visible=lambda *a:False;observe(g,t,.05);assert getattr(t,'ai_incident_pending',None) is None
    reset();g.visible=lambda *a:True;t=crew();shell();g.bullets[0][5]=friend;observe(g,t,.05);assert getattr(t,'ai_incident_pending',None) is None
    reset();t=crew();emit(g,'tracer',V(1050,1000),a,velocity=V(-2000,0));observe(g,t,.05);assert t.ai_incident_pending['kind']=='tracer'
    reset();t=crew();g.visible=lambda *a:False;friend.p=V(1200,1000);emit(g,'destroyed',friend.p,a,friend);observe(g,t,.05);assert t.ai_incident_pending
    g.time=t.ai_incident_pending['ready']+.01;observe(g,t,.05);assert t.ai_recent_hit>0 and not hasattr(t,'retaliation_attacker')
    reset();t=crew();friend.p=V(4000,1000);emit(g,'hit',friend.p,a,friend);observe(g,t,.05);assert getattr(t,'ai_incident_pending',None) is None
    reset();g.visible=lambda *a:True;t=crew();friend.p=V(1300,1000);emit(g,'hit',friend.p,a,friend);observe(g,t,.05);g.time=t.ai_incident_pending['ready']+.01;observe(g,t,.05);assert t.retaliation_attacker is a
    for _ in range(200):emit(g,'hit',friend.p,a,friend)
    assert len(g.ai_incidents)==128
    reset();shell();p=N(phase='airborne',p=V(1000,1000),a=0);q=dict(ai_plane=p,dead=False,team=0,skill=1,age=1,attention=.5)
    observe_air(g,q,.05);assert q['incident_pending'];g.time=q['incident_pending']['ready']+.01;observe_air(g,q,.05);assert q['egress']>0 and q['attention']==0
    print('PASS optical shell/tracer sensing, FOV/occlusion/friendly/distance exclusions, delayed skill/attention reactions, teammate incident support, hidden shooter exclusion, bounded cues and aircraft evasion')
