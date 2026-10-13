import os,sys,json,tempfile,time
sys.path.insert(0,os.path.abspath('outputs'))
from types import SimpleNamespace
from LANSquad import Room
from LANBattle import Authority
from LANSnapshot import Snapshot,Replica
from InputBindings import get_controls

def run(api):
 game=SimpleNamespace(**api)
 with tempfile.TemporaryDirectory() as tmp:
  rooms=[]
  try:
   for i in range(4):rooms.append(Room(game.Profile(os.path.join(tmp,str(i)+'.json'))))
   from Garage import CATALOG,combined_br
   country=rooms[3].profile.country
   modern=max((k for k,d in CATALOG.items() if d['country']==country),key=lambda k:CATALOG[k].get('ground_br',CATALOG[k]['br']))
   rooms[3].profile.lineups[country]=[modern]+[None]*7;rooms[3].profile.active[country]=0
   rooms[0].create(port=0)
   port=rooms[0].net.listener.getsockname()[1]
   for r in rooms[1:]:r.join('127.0.0.1',port)
   def pump():
    for _ in range(25):
     for r in rooms:r.update(.01)
     time.sleep(.002)
   pump();assert len(rooms[0].members)==4
   assert not rooms[0].start()
   for r in rooms:r.ready()
   pump();assert rooms[0].all_ready;assert rooms[0].start();pump()
   start=rooms[0].started;assert start['br']==combined_br([modern]+[None]*7);assert all(r.started['br']==start['br'] for r in rooms)
   a=Authority(api,start,get_controls());snapshot=Snapshot(a);clients=[Replica(api,start,r.my_id) for r in rooms[1:]]
   for ident,g in a.contexts.items():a.action(ident,dict(action='deploy',slot=g.active_vehicle_slot,base=ident%2))
   assert all(not g.player.dead for g in a.contexts.values())
   # Player aircraft omit the AI managed marker. Exercise the actual replacement
   # update with those records present, including an explicitly empty marker.
   from Aviation import AIRCRAFT
   aircraft=a.contexts[3]
   if not aircraft.flight.active:
    aircraft.player.dead=True
    aircraft.flight.start(next(k for k,d in AIRCRAFT.items() if d['country']==aircraft.country));a.bind_player(3)
   aircraft.flight.record.pop('managed',None)
   for marker in ('missing',None,False):
    if marker=='missing':aircraft.flight.record.pop('managed',None)
    else:aircraft.flight.record['managed']=marker
    victim=next(t for t in a.root.allies if getattr(t,'network_owner',None) is None)
    victim.dead=True;victim.reason='LAN replacement regression';a.root.register_death(victim)
    entry=a.root.ally_queue[-1]
    if isinstance(entry,dict):entry.update(delay=0.,aircraft=None)
    else:a.root.ally_queue[-1]=dict(delay=0.,aircraft=None)
    before=sum(not t.dead and getattr(t,'network_owner',None) is None for t in a.root.allies)
    a.tick(1/60)
    after=sum(not t.dead and getattr(t,'network_owner',None) is None for t in a.root.allies)
    assert after==before+1 or any(isinstance(e,dict) and e.get('vehicle_selected') and e.get('aircraft') is None for e in a.root.ally_queue),(marker,before,after)
   aircraft.flight.radar.stt=a.root.air.planes[0]
   aircraft.flight.radar.tracks=[dict(target=aircraft.flight.radar.stt,seen=aircraft.flight.radar.clock,az=0.,km=1.,radial=10.,p=game.V(aircraft.player.p),v=game.V(0,0))]
   aircraft.flight.warning.contacts=[dict(id=['test',1],pos=game.V(aircraft.player.p),level=3,label='导弹逼近',team=1,until=aircraft.flight.warning.clock+5)]
   old_nuclear=getattr(aircraft.flight.plane,'nuclear',False);aircraft.flight.plane.nuclear=True
   assert snapshot.build()['nuclear_alarm'];aircraft.flight.plane.nuclear=old_nuclear
   alert=snapshot.build();alert['nuclear_alarm']=True
   from BattleAudio import nuclear_alarm
   for client in clients:client.apply(json.loads(json.dumps(alert,allow_nan=False)));assert nuclear_alarm(client.g)
   packet=json.loads(json.dumps(snapshot.build(),allow_nan=False));assert all('player_'+str(i) in packet['battle_roster'] for i in range(4));clients[0].apply(packet,3)
   assert clients[0].g.battle_roster==packet['battle_roster']
   clients[0].render_update(.1);assert clients[0].g.flight.warning.contacts[0]['level']==3 and clients[0].g.flight.radar.stt is not None
   clients[0].apply(packet,1)
   print('PASS: authoritative warning contacts replicated for spectated aircraft; player aircraft without AI marker and AI teammate death/ground replacement')

   from Reconnaissance import toggle,mark
   scout=a.contexts[1];original=scout.player
   recon_id=next(k for k,v in api['VEHICLES'].items() if v.get('scout_drone'))
   scout.player=game.Tank((2000,2000),vehicle=recon_id);a.bind_player(1)
   assert toggle(scout);position=game.V(scout.player.p);drone=game.V(scout.drone_pos)
   a.accept_input(1,dict(keys=[game.pygame.K_LSHIFT],mouse=list(scout.drone_pos+game.V(0,-1000)),fire=False));a.tick_remote(1,.1)
   assert scout.player.p==position and scout.drone_pos.distance_to(drone)>0 and scout.drone_throttle>.65
   target=game.Tank(scout.drone_pos+game.V(100,0),enemy=True);a.root.enemies.append(target)
   assert mark(scout,target.p)
   packet=json.loads(json.dumps(snapshot.build(),allow_nan=False));clients[0].apply(packet);clients[0].g.draw()
   assert clients[0].g.drone_active and clients[0].g.drone_pos.distance_to(scout.drone_pos)<.01
   before=scout.score;host_before=a.root.score
   result=dict(kind='未击穿',modules=[],point=game.V(target.p),line=(game.V(scout.player.p),game.V(target.p)))
   a.root.record_hit(target,result,scout.player,'炮弹');assert scout.score==before+5 and a.root.score==host_before
   a.root.announce_kill(a.root.player,target,'炮弹');assert scout.score==before+80
   a.root.announce_kill(a.root.player,target,'炮弹');assert scout.score==before+80
   toggle(scout);a.root.enemies.remove(target);a.root.allies.remove(scout.player);scout.player=original;a.bind_player(1)
   print('PASS: remote drone movement and JSON camera/mark replicas, authoritative hit ownership and scout assist once')

   for _ in range(60):
    for ident,g in a.contexts.items():a.accept_input(ident,dict(keys=[game.pygame.K_w],mouse=list(g.player.p+game.V(500,0)),fire=False))
    a.tick(1/60)
   packet=json.loads(json.dumps(snapshot.build(),allow_nan=False))
   for c in clients:c.apply(packet);c.g.draw()
   for g in a.contexts.values():assert g.state=='play'
   air=a.contexts[3]
   for _ in range(62):a.accept_input(3,dict(keys=[game.pygame.K_F6],mouse=list(air.player.p),fire=False));a.tick(.05)
   assert air.player.dead and air.flight.plane.dead and air.state=='wreck'
   g=a.contexts[1];g.reserves=0;g.used_slots=set(range(8))
   for _ in range(58):a.accept_input(1,dict(keys=[game.pygame.K_F6],mouse=list(g.player.p),fire=False));a.tick(.05)
   assert not g.player.dead
   for _ in range(4):a.accept_input(1,dict(keys=[game.pygame.K_F6],mouse=list(g.player.p),fire=False));a.tick(.05)
   assert g.player.dead and g.state=='wreck'
   for _ in range(260):a.tick(1/60)
   assert g.state=='spectate',g.state
   packet=json.loads(json.dumps(snapshot.build(),allow_nan=False));clients[0].apply(packet,0);clients[0].g.draw()
   a.draw(0);rooms[0].draw(game.screen,game.text);print('LAN: 4 players, ready gate, highest BR, deploy, authoritative movement, JSON replicas, death delay and spectating passed')
  finally:
   for r in rooms:r.close()
if __name__=='__main__':
 sys.argv.append('--test')
 import SteelWilderness as game
 run(vars(game))
