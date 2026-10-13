"""Named aircraft sensors and a deliberately simplified 2D radar simulation.
Hardware identities follow the unit's official WT sensor fit; scan timing,
tracking limits, notch widths and detection ranges below are gameplay values.
"""
import math
import pygame
from pygame.math import Vector2 as V

TYPES={'aesa':'AESA 有源相控阵','pesa':'PESA 无源相控阵','cassegrain':'倒卡 / 扭转卡塞格林',
       'mechanical':'机械扫描平板阵列','pulse':'机械扫描脉冲雷达','ranging':'测距雷达','ground':'对地 / 地形雷达','none':'无搜索雷达'}
# radar model, antenna category, usable modes, game maximum km, sector half-angle,
# full-sector revisit seconds, retained tracks, simulated Doppler notch m/s.
RADARS={
 'KLJ-10A':('aesa',('RWS','PD','TWS','ACM'),160,60,.35,16,12),
 'CAPTOR ECRS Mk.1':('aesa',('RWS','PD','TWS','ACM'),160,70,.35,16,12),
 'AN/APG-63(V)3':('aesa',('RWS','PD','TWS','ACM'),160,60,.35,16,12),
 'N035E':('pesa',('RWS','PD','TWS','ACM'),160,70,.5,12,18),
 'N001':('cassegrain',('PD','RWS','ACM'),80,60,2.8,1,45),
 'N001VEP':('cassegrain',('PD','TWS','RWS','ACM'),100,60,2.4,4,35),
 'N019/OEPS-29':('cassegrain',('PD','RWS','ACM'),60,60,3.,1,45),
 'N019E/OEPS-29E':('cassegrain',('PD','RWS','ACM'),60,60,3.,1,45),
 'Type 1493':('mechanical',('PD','TWS','RWS','ACM'),100,60,2.,8,26),
 'N010 Zhuk':('mechanical',('PD','TWS','RWS','ACM'),80,60,2.,8,28),
 'N010M Zhuk-M':('mechanical',('PD','TWS','RWS','ACM'),100,60,1.8,8,24),
 'AN/APG-63 PSP':('mechanical',('PD','RAM','RWS','ACM'),120,60,1.6,4,24),
 'AN/APG-70':('mechanical',('PD','TWS','RWS','ACM'),120,60,1.5,8,22),
 'AN/APG-66(V)3':('mechanical',('PD','TWS','RWS','ACM'),80,60,1.8,8,28),
 'AN/APG-68(V)7':('mechanical',('PD','TWS','RWS','ACM'),100,60,1.6,8,24),
 'AN/APG-73':('mechanical',('PD','TWS','RWS','ACM'),100,60,1.5,8,22),
 'AN/APG-65G':('mechanical',('PD','TWS','RWS','ACM'),100,60,1.8,8,28),
 'CAPTOR-M':('mechanical',('PD','TWS','RWS','ACM'),120,60,1.5,8,22),
 'AN/AWG-9':('mechanical',('PD','TWS','RWS','ACM'),160,65,2.4,12,30),
 'AN/APQ-120':('pulse',('RWS','ACM'),60,60,2.8,1,0),
 'Type 208A':('pulse',('RWS','ACM'),40,60,3.2,1,0),
 'RP-22S':('pulse',('RWS','ACM'),20,30,3.4,1,0),
 'RP-21':('pulse',('RWS','ACM'),20,30,3.4,1,0),
 'AN/ASG-14':('pulse',('RWS','ACM'),30,40,3.,1,0),
 'AN/APQ-83':('pulse',('RWS','ACM'),30,45,3.,1,0),
 'JL-10A':('mechanical',('RWS','PD','AG','ACM'),80,60,2.4,4,32),
 'Orion':('ground',('AG',),40,50,3.,1,0),
 'ARI 23274':('ground',('AG',),40,50,3.,1,0),
 'AN/APQ-159':('ground',('AG',),40,50,3.,1,0),
 'AN/APG-30':('ranging',('RNG',),2,8,.4,1,0),
 'AN/APG-33':('ranging',('RNG',),2,8,.4,1,0),
 'Type 226':('ranging',('RNG',),2,8,.4,1,0),
}
FITS={'J-10C':'KLJ-10A','J-11':'N001','J-11B':'Type 1493','J-15T':'KLJ-10A',
 'J-8B':'Type 208A','J-7E':'Type 226','F-16A MLU (China)':'AN/APG-66(V)3','JH-7A':'JL-10A',
 'Yak-141':'N010 Zhuk','MiG-29 (9-13)':'N019/OEPS-29','MiG-29SMT (9-19)':'N010M Zhuk-M',
 'MiG-29 (9-12A) (Germany)':'N019E/OEPS-29E','MiG-21bis':'RP-22S','MiG-21MF (Germany)':'RP-21',
 'Su-27':'N001','Su-27SM':'N001VEP','Su-30SM2':'N035E','Su-24M':'Orion',
 'EF-2000 (Germany)':'CAPTOR-M','EF-2000 (AESA) (Germany)':'CAPTOR ECRS Mk.1',
 'Tornado IDS ASSTA1 (Germany)':'ARI 23274','Tornado IDS SLE (Germany)':'ARI 23274',
 'F-16CM':'AN/APG-68(V)7','F-15A':'AN/APG-63 PSP','F-15C MSIP II':'AN/APG-63 PSP',
 'F-15C Golden Eagle':'AN/APG-63(V)3','F-15E':'AN/APG-70','F-14B':'AN/AWG-9',
 'F/A-18C Late':'AN/APG-73','F-4E Phantom II':'AN/APQ-120','F-4F Early (Germany)':'AN/APQ-120',
 'F-4F KWS LV (Germany)':'AN/APG-65G','F-111F':'AN/APQ-159',
 'F-104G (China)':'AN/ASG-14','F-104G (Germany)':'AN/ASG-14','F8U-2':'AN/APQ-83',
 'F-86F-25':'AN/APG-30','F-84G-21-RE (China)':'AN/APG-30','F-84F (Germany)':'AN/APG-30'}

def configure(aircraft):
    for d in aircraft.values():
        name=FITS.get(d['name']);d['radar_model']=name
        d['radar']=bool(name and RADARS[name][0] not in ('ranging','ground'))
        d['radar_type']=TYPES[RADARS[name][0]] if name else TYPES['none']
        if name:d['sensor_note']=name

def position(target):return V(target['p'] if isinstance(target,dict) else target.p)
def velocity(target):
    if isinstance(target,dict):return V(target.get('v',(0,0)))
    return V(math.cos(math.radians(target.body)),math.sin(math.radians(target.body)))*target.speed
def dead(target):return target.get('dead',False) if isinstance(target,dict) else target.dead

class Radar:
    def __init__(self,flight):
        self.f=flight;d=flight.plane.stats;self.name=d.get('radar_model');self.kind,self.modes,self.maximum,self.sector,self.period,self.capacity,self.notch=RADARS.get(self.name,('none',('VIS',),0,60,1,0,0))
        self.mode=self.modes[0];self.enabled=self.kind!='none';self.clock=0.;self.beam=-self.sector;self.tracks=[];self.selected=None;self.display_km=min(5.,self.maximum) if self.maximum else 2.;self.notice='';self.stt=None
    def toggle(self):
        if self.kind=='none':self.notice='此机没有雷达';return
        self.enabled=not self.enabled;self.tracks=[];self.selected=self.stt=None
        self.notice='雷达开启' if self.enabled else '雷达关闭'
    def cycle_mode(self):
        self.mode=self.modes[(self.modes.index(self.mode)+1)%len(self.modes)];self.tracks=[];self.stt=None;self.notice='模式 '+self.mode
    def cycle_range(self):
        ranges=[r for r in (.5,1,2,5,10,20,40,80,160) if r<=max(.5,self.maximum)]
        self.display_km=next((r for r in ranges if r>self.display_km),ranges[0]);self.notice=f'显示量程 {self.display_km:g} km'
    def candidate(self,target):
        p=self.f.plane;delta=position(target)-p.p
        if delta.length_squared()<1:return None
        az=(math.degrees(math.atan2(delta.y,delta.x))-p.a+180)%360-180
        sector=10 if self.mode in ('ACM','RNG') else self.sector
        limit=min(self.maximum,2) if self.mode in ('ACM','RNG') else self.maximum
        if abs(az)>sector or delta.length()>limit*8000:return None
        radial=velocity(target).dot(delta.normalize())/8
        if self.mode in ('PD','TWS','RAM') and abs(radial)<self.notch:return None
        if self.kind=='pulse' and isinstance(target,dict) and target.get('controlled') and target['controlled'].plane.altitude<60 and delta.length()>4000:return None
        return az,delta.length()/8000,radial
    def update(self,dt):
        if not self.enabled or self.kind=='none':return
        previous=self.clock;self.clock+=dt;phase=(self.clock/self.period)%2
        self.beam=(-self.sector+phase*2*self.sector) if phase<1 else (3*self.sector-phase*2*self.sector)
        if self.stt is not None and self.mode not in ('TWS','RAM'):
            fit=self.candidate(self.stt)
            if fit:self.beam=fit[0]
        p=self.f.plane;g=self.f.g;ground=self.mode=='AG'
        candidates=g.enemies+g.allies if ground else [q for q in g.air.planes if q is not self.f.record]
        for target in candidates:
            if dead(target):continue
            fit=self.candidate(target)
            if not fit:continue
            if self.stt is not None and self.mode not in ('TWS','RAM') and target is not self.stt:continue
            az,km,radial=fit
            # Electronic arrays revisit freely; mechanical antennas sweep a raster.
            electronic_revisit=self.kind in ('aesa','pesa','ranging') and int(previous/self.period)!=int(self.clock/self.period)
            swept=electronic_revisit if self.kind in ('aesa','pesa','ranging') else self.mode=='ACM' or target is self.stt or abs(az-self.beam)<max(5,dt*self.sector*4/self.period) or dt>=self.period
            if not swept:continue
            existing=next((t for t in self.tracks if t['target'] is target),None)
            snapshot={'target':target,'seen':self.clock,'az':az,'km':km,'radial':radial,'p':position(target),'v':velocity(target)}
            if existing:existing.update(snapshot)
            else:self.tracks.append(snapshot)
        hold=max(.8,self.period*2.2)
        self.tracks=[t for t in self.tracks if not dead(t['target']) and self.clock-t['seen']<hold and self.candidate(t['target']) is not None]
        self.tracks.sort(key=lambda t:(t['target'] is not self.stt,t['km']))
        self.tracks=self.tracks[:self.capacity if self.mode in ('TWS','RAM') else max(16,self.capacity)]
        if self.stt is not None and not any(t['target'] is self.stt for t in self.tracks):self.stt=None;self.notice='丢失锁定'
        if self.selected is not None and not any(t['target'] is self.selected for t in self.tracks):self.selected=None
    def enemies(self):
        team=getattr(self.f.plane,'team',0)
        return [t['target'] for t in self.tracks if (t['target'].get('team',1) if isinstance(t['target'],dict) else int(t['target'].enemy))!=team]
    def cycle_target(self):
        pool=self.enemies()
        if not pool:self.selected=None;self.notice='没有探测到敌方目标';return
        index=next((i for i,q in enumerate(pool) if q is self.selected),-1);self.selected=pool[(index+1)%len(pool)]
    def lock(self):
        pool=self.enemies()
        self.stt=self.selected if any(q is self.selected for q in pool) else min(pool,key=lambda q:position(q).distance_squared_to(self.f.plane.p),default=None)
        self.selected=self.stt;self.notice=('TWS 目标跟踪' if self.mode in ('TWS','RAM') else 'STT 单目标跟踪') if self.stt is not None else '未发现可锁定目标'
        return self.stt
    def has_track(self,target):return self.enabled and any(t['target'] is target for t in self.tracks)
    def draw(self,s,text):
        r=pygame.Rect(16,148,320,310);pygame.draw.rect(s,(10,24,23),r,border_radius=7)
        text(self.name or '目视瞄准 / 无雷达',(28,159),18,(155,226,183));text(TYPES[self.kind],(28,187),14,(137,181,163))
        # An antenna symbol distinguishes the hardware without replacing the
        # standard azimuth/range scope with a decorative circular minimap.
        icon=pygame.Rect(295,181,24,24)
        if self.kind in ('aesa','pesa'):
            pygame.draw.rect(s,(123,181,141) if self.kind=='aesa' else (213,180,104),icon,1)
            for x in range(4):
                for y in range(4):pygame.draw.rect(s,(111,161,132),(icon.x+3+x*5,icon.y+3+y*5,3,3))
        elif self.kind=='cassegrain':
            pygame.draw.circle(s,(167,194,137),icon.center,11,1);pygame.draw.circle(s,(167,194,137),icon.center,4,1)
            pygame.draw.line(s,(167,194,137),icon.midleft,icon.midright,1)
        elif self.kind!='none':
            pygame.draw.rect(s,(143,178,161),icon,1)
            for y in range(4):pygame.draw.line(s,(143,178,161),(icon.x+3,icon.y+4+y*5),(icon.right-3,icon.y+4+y*5))
        plot=pygame.Rect(32,216,287,165);pygame.draw.rect(s,(16,42,34),plot);pygame.draw.rect(s,(65,111,80),plot,1)
        for i in range(1,4):
            pygame.draw.line(s,(35,72,47),(plot.x+i*plot.w/4,plot.y),(plot.x+i*plot.w/4,plot.bottom));pygame.draw.line(s,(35,72,47),(plot.x,plot.y+i*plot.h/4),(plot.right,plot.y+i*plot.h/4))
        tracking='TRK' if self.mode in ('TWS','RAM') else 'STT'
        text(f'{self.mode}  {self.display_km:g} km  '+(tracking if self.stt is not None else '扫描' if self.enabled else '关闭'),(36,222),14,(173,224,169))
        if self.enabled:
            from RadarContacts import radar_missiles as missiles
            for m in missiles(self.f.g):
                fit=self.candidate(m)
                if fit and fit[1]<=self.display_km:
                    az,km,_=fit;q=V(plot.centerx+az/self.sector*(plot.w/2-7),plot.bottom-5-km/self.display_km*(plot.h-30))
                    pygame.draw.polygon(s,(246,221,104),[q+V(0,-4),q+V(4,0),q+V(0,4),q+V(-4,0)],1)
            x=plot.centerx+self.beam/self.sector*plot.w/2
            old_clip=s.get_clip();s.set_clip(plot)
            for offset in range(0,31,3):
                glow=max(25,155-offset*4)
                pygame.draw.line(s,(15,glow,55),(x-offset,plot.y+25),(x-offset,plot.bottom),3)
            pygame.draw.line(s,(125,242,147),(x,plot.y+25),(x,plot.bottom),2)
            if self.kind in ('aesa','pesa'):
                row=plot.y+28+(self.clock/self.period%1)*(plot.h-28)
                pygame.draw.line(s,(69,130,89),(plot.x,row),(plot.right,row),1)
            s.set_clip(old_clip)
            for index,track in enumerate(self.tracks):
                if track['km']>self.display_km:continue
                q=V(plot.centerx+track['az']/self.sector*(plot.w/2-7),plot.bottom-5-track['km']/self.display_km*(plot.h-30))
                target=track['target'];friendly=target.get('team',1)==0 if isinstance(target,dict) else not target.enemy
                fade=max(.35,1-(self.clock-track['seen'])/max(.8,self.period*2.2))
                col=tuple(int(c*fade) for c in ((122,177,241) if friendly else (255,116,83)))
                if friendly:pygame.draw.circle(s,col,q,4,1)
                else:pygame.draw.polygon(s,col,[q+V(0,-6),q+V(-5,4),q+V(5,4)],2)
                old_clip=s.get_clip();s.set_clip(plot)
                text(('友' if friendly else '敌')+str(index+1)+f" {track['km']:.1f}",(min(plot.right-80,q.x+8),max(plot.y+27,q.y-19)),14,col)
                s.set_clip(old_clip)
                if target is self.selected:pygame.draw.rect(s,(244,221,111),(q.x-8,q.y-7,16,14),1)
                if target is self.stt:pygame.draw.rect(s,(251,163,84),(q.x-10,q.y-9,20,18),2)
        status='目视引导 · 无雷达航迹' if self.kind=='none' else f'航迹 {len(self.tracks)} · '+('测距' if self.kind=='ranging' else '对地回波' if self.mode=='AG' else f'多目标 {self.capacity if self.mode in ("TWS","RAM") else 1}')
        text(status,(28,389),14,(156,193,160))
        text('敌▲',(238,390),14,(255,116,83));text('友○',(285,390),14,(122,177,241))
        controls=getattr(self.f.g,'controls',None)
        label=lambda action,default:controls.label('air.'+action) if controls else default
        text(label('radar','Tab')+' 开关 · '+label('radar_mode','T')+' 模式 · '+label('radar_range','F')+' 量程',(28,414),14);text(label('radar_target','Y')+' 选目标 · '+label('lock','Q')+' 锁定 / 解锁',(28,435),14)

def radar_self_test(api):
    from types import SimpleNamespace
    from Aviation import AIRCRAFT
    from AircraftModels import wingtips,polygons
    from FlightView import intercept
    for d in AIRCRAFT.values():
        assert d.get('radar_model')==FITS.get(d['name'])
        if d['radar_model']:assert d['radar_model'] in RADARS
    for name,kind in [('J-10C','aesa'),('Su-30SM2','pesa'),('MiG-29 (9-13)','cassegrain'),('F-16CM','mechanical')]:
        d=next(d for d in AIRCRAFT.values() if d['name']==name)
        plane=SimpleNamespace(stats=d,p=V(0,0),a=0)
        enemy={'p':V(3000,0),'v':V(-1600,0),'team':1,'dead':False};friend={'p':V(4000,200),'v':V(-1600,0),'team':0,'dead':False}
        behind={'p':V(-2000,0),'v':V(1600,0),'team':1,'dead':False}
        game=SimpleNamespace(air=SimpleNamespace(planes=[enemy,friend,behind]),enemies=[],allies=[])
        radar=Radar(SimpleNamespace(plane=plane,g=game,record=None));assert radar.kind==kind
        for _ in range(360):radar.update(1/60)
        assert enemy in radar.enemies() and friend not in radar.enemies() and behind not in radar.enemies()
        assert radar.lock() is enemy;radar.toggle();assert not radar.tracks
        radar.toggle();radar.mode='PD';enemy['v']=V(0,1600)
        for _ in range(360):radar.update(1/60)
        assert not radar.has_track(enemy)
    d=next(d for d in AIRCRAFT.values() if d['name']=='F-14B')
    for bank in (0,60,90,140,270):
        for sweep in (0,.5,1):
            wings=[poly for part,poly in polygons(d,8,bank,sweep) if part=='wing'][:2]
            assert all(any(tip.distance_to(vertex)<.001 for vertex in wing) for tip,wing in zip(wingtips(d,bank,sweep),wings))
    point,seconds=intercept(V(0,0),V(2000,0),V(0,500),4000)
    assert abs(point.length()-seconds*4000)<.001
    tank=next(d for d in api['VEHICLES'].values() if d['name']=='M1A2 SEPv3')
    assert tank['model'][1]>=20
    print('PASS: named radar hardware, electronic/mechanical search, sector and IFF, locking, Doppler rejection, rolled/swept trail origins, gun lead and wider tank hull')
