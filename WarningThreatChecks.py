"""Threat detection checks, including untracked and remotely controlled weapons."""
from types import SimpleNamespace as N
from pygame.math import Vector2 as V
from AircraftWarnings import Warnings

def run():
    equipment={'rwr':dict(range=70,tracking=True,launch=True,iff=True),'maw':True}
    p=N(p=V(0,0),a=0,speed=100,team=0,stats={'warning':equipment})
    record=dict(p=p.p,team=0,controlled=p,dead=False)
    air=N(planes=[record],missiles=[],scan_clock=0,lock=None)
    g=N(air=air,enemies=[],allies=[],player=N(dead=False),_lan_authority=None)
    f=N(active=True,plane=p,record=record,g=g,projectiles=[],illumination=lambda m,t:t is record)
    g.flight=f;warning=Warnings(f)
    def reset():warning.contacts=[];air.missiles=[];f.projectiles=[];g.enemies=[];air.planes=[record]
    # A seeker losing its target must not erase the MAW threat.
    m=dict(p=V(-10000,0),v=V(5000,0),life=10,kind='missile',guidance='IR',team=1,target=None)
    f.projectiles=[m];warning.update(.1);assert any(c['level']==3 for c in warning.contacts)
    reset();m['v']=V(-5000,0);f.projectiles=[m];warning.update(.1);assert not warning.contacts
    reset();m.update(v=V(5000,0),team=0);f.projectiles=[m];warning.update(.1);assert not warning.contacts
    reset();m['team']=1;equipment['maw']=False;f.projectiles=[m];warning.update(.1);assert not warning.contacts
    # Incoming SARH can warn through RWR, even without MAW.
    reset();m.update(guidance='SARH',target=record);f.projectiles=[m];warning.update(.1);assert any(c['level']==3 for c in warning.contacts)
    # Long-range ground radars use their own range and accept aircraft aliases.
    reset();tank=N(dead=False,enemy=True,p=V(-96000,0),stats={'radar':True,'name':'Pantsir-S1'},ai_air_target={'controlled':p})
    g.enemies=[tank];warning.update(.1);assert any(c['level']==2 for c in warning.contacts)
    # Radar-command SAMs have no radar seeker but their emitter still warns RWR.
    reset();tank.stats['branch']=3
    m.update(p=V(-20000,0),guidance='COMMAND',target=record,owner=tank)
    air.missiles=[m];warning.update(.1);assert any(c['level']==3 for c in warning.contacts)
    reset();source=N(p=V(-20000,0),a=0)
    target={'controlled':p};radar=N(enabled=True,kind='mechanical',mode='PD',maximum=70,sector=60,stt=target,beam=0,period=1,has_track=lambda t:t is target)
    air.planes.append(dict(controlled=source,dead=False,radar=radar,team=1));warning.update(.1);assert any(c['level']==2 for c in warning.contacts)
    # Shared LAN projectile lists must be examined too.
    reset();equipment['maw']=True;m.update(guidance='IR',target=None,owner=None)
    remote=N(flight=N(projectiles=[m]),air=N(missiles=[]));g._lan_authority=N(contexts={1:remote})
    warning.update(.1);assert any(c['level']==3 for c in warning.contacts)
    print('PASS: coasting missile approach, friendly/receding rejection, equipment gate, SARH, long-range SAM radar, player radar locks and LAN missile warnings')
