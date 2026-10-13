from types import SimpleNamespace as N
import tempfile,os
def run(api):
    from BattleAudio import nuclear_alarm
    from PresentationSettings import Settings
    plane=N(nuclear=True,dead=False)
    g=N(state='play',paused=False,flight=N(plane=None,nuke_timer=None,nuke_detonated=False),air=N(planes=[]),nuclear_result=None,ai_nuclear=None,used_slots=set(),player=N(dead=False))
    assert not nuclear_alarm(g)
    g.flight.plane=plane;assert nuclear_alarm(g)
    plane.dead=True;assert not nuclear_alarm(g)
    g.flight.nuke_timer=4;assert nuclear_alarm(g);g.flight.nuke_timer=None
    g.flight.plane=None;g.air.planes=[dict(ai_nuclear=True,dead=False)];assert nuclear_alarm(g)
    g.air.planes[0]['dead']=True;assert not nuclear_alarm(g)
    g.ai_nuclear={'timer':4};assert nuclear_alarm(g);g.ai_nuclear=None;g.air.planes=[]
    plane.dead=False;g._lan_authority=N(contexts={0:g,1:N(flight=N(plane=plane,nuke_timer=None))});assert nuclear_alarm(g)
    del g._lan_authority;g._nuclear_alarm_remote=True
    for state in ('play','deploy','wreck','spectate'):g.state=state;assert nuclear_alarm(g)
    g.state='win';assert not nuclear_alarm(g)
    g.state='play';g._nuclear_alarm_remote=False;assert not nuclear_alarm(g)
    class Bank:
        def __init__(self):self.keys=[];self.alarms=[]
        def set_alarm(self,active,volume):self.alarms.append(active)
        def play(self,key,volume):self.keys.append(key);return True
    with tempfile.TemporaryDirectory() as temp:
        settings=Settings(os.path.join(temp,'settings.json'));settings.bank=Bank()
        settings.update_battle_bank(g);assert settings.bank.keys==[]
        g.used_slots={0};settings.update_battle_bank(g);assert settings.bank.keys==['battle_start']
        g.state='deploy';settings.update_battle_bank(g);g.state='play';g.used_slots.add(1);settings.update_battle_bank(g);assert settings.bank.keys==['battle_start']
        g._nuclear_alarm_remote=True;settings.update_battle_bank(g);assert settings.bank.alarms[-1]
        settings.clock+=5.1;settings.update_battle_bank(g);assert settings.bank.alarms[-1]
        settings.clock+=3.;settings.update_battle_bank(g);assert settings.bank.alarms[-1]
        settings.config['muted']=True;settings.update_battle_bank(g);assert not settings.bank.alarms[-1]
        settings.config['muted']=False;settings.update_battle_bank(None);assert not settings.bank.alarms[-1]
    print('PASS nuclear alert for human/AI/remote/observer, bomb countdown, death/end/mute stop and once-per-battle deployment voice')
