"""Station compatibility and fixed presets from the actual unit WT tables."""
import math,copy
from functools import lru_cache
import pygame
from AircraftLoadoutData import DATA

LABELS={'aam':'空空导弹','agm':'对地导弹','bomb':'炸弹','rocket':'火箭','gunpod':'机炮吊舱','tank':'副油箱','pod':'设备吊舱'}

def guidance_label(w):
    value=str(w.get('guidance','')).upper()
    if 'SARH' in value:return '半主动雷达'
    if 'ARH' in value or 'ACTIVE RADAR' in value:return '主动雷达'
    if 'IIR' in value:return '成像红外自导'
    if 'SALH' in value or 'SEMI-ACTIVE LASER' in value:return '半主动激光'
    if 'BEAM' in value and 'LASER' in value:return '激光驾束'
    if 'LASER' in value:return '激光制导'
    if 'WIRE' in value:return '有线指令'
    if 'RADIO' in value:return '无线指令'
    if 'SACLOS' in value or 'COMMAND' in value:return '指令制导'
    if 'TV' in value or 'TELEVISION' in value:return '电视制导'
    if 'GPS' in value or 'INS' in value or 'INERTIAL' in value:return '惯性 / 卫星'
    if 'IR' in value:return '红外自导'
    if 'RADAR' in value:return '雷达制导'
    return '无制导' if w.get('kind')=='rocket' else '制导未标注'

def type_label(w):
    kind=w['kind'];name=w['name'].lower()
    if kind in ('aam','agm'):return LABELS[kind]+' · '+guidance_label(w)
    if kind=='bomb':return '制导炸弹' if w.get('guidance') else '普通炸弹'
    if kind=='rocket':return '火箭弹'
    if kind=='pod':
        if 'torpedo' in name:return '鱼雷'
        if 'countermeasure' in name or 'chaff' in name:return '干扰弹吊舱'
        if 'data link' in name:return '数据链吊舱'
        if 'targeting' in name:return '瞄准吊舱'
    return LABELS.get(kind,'设备挂载')

def preset_type_label(preset):
    return ' / '.join(dict.fromkeys(type_label(w) for w in preset['items']))

@lru_cache(maxsize=2048)
def fitted_label(label,width):
    font=pygame.font.Font(pygame.font.match_font('microsoftyahei,simhei,segoeui'),14)
    if font.size(label)[0]<=width:return label
    while label and font.size(label+'…')[0]>width:label=label[:-1]
    return label+'…'
def configure(aircraft):
    for ident,d in aircraft.items():
        d['loadout']=DATA[ident];d['station_count']=len(DATA[ident]['slots'])
        d['weapon_station_count']=len({i for w in DATA[ident]['weapons'] if w['kind'] in ('aam','agm','bomb','rocket','gunpod') for i in w['slots']})
        for w in DATA[ident]['weapons']:
            if w['kind']=='aam' and w['short'].split()[0] not in d['missile_types']:d['missile_types'].append(w['short'].split()[0])

def totals(d,config):
    fit=d['loadout'];mass=left=right=0
    for i,w in items(d,config):
        mass+=w['mass'];side=fit['slots'][i]['side'] if fit['slots'] else 0
        if side<0:left+=w['mass']
        if side>0:right+=w['mass']
    return mass,left,right

def valid(d,config):
    fit=d['loadout']
    if not isinstance(config,dict):return False
    if not fit['slots']:return isinstance(config.get('preset'),int) and -1<=config['preset']<len(fit['presets'])
    slots=config.get('stations')
    if d.get('helicopter') and isinstance(slots,list) and len(slots)==4 and len(fit['slots'])==6:slots=slots+[-1,-1];config=dict(config,stations=slots)
    if not isinstance(slots,list) or len(slots)!=len(fit['slots']):return False
    for i,index in enumerate(slots):
        if not isinstance(index,int) or index<-1 or index>=len(fit['weapons']):return False
        if index>=0 and i not in fit['weapons'][index]['slots']:return False
    mass,left,right=totals(d,config)
    return (not fit['maximum'] or mass<=fit['maximum']+.01) and (not fit['wing_max'] or max(left,right)<=fit['wing_max']+.01) and (not fit['imbalance'] or abs(left-right)<=fit['imbalance']+.01)

def items(d,config):
    fit=d['loadout']
    if fit['slots']:return [(i,fit['weapons'][w]) for i,w in enumerate(config['stations']) if w>=0]
    index=config.get('preset',-1)
    return list(enumerate(fit['presets'][index]['items'])) if 0<=index<len(fit['presets']) else []

def default(d):
    fit=d['loadout']
    if not fit['slots']:return {'preset':0 if fit['presets'] else -1}
    config={'stations':[-1]*len(fit['slots'])}
    if fit.get('revision'):config['fit_revision']=fit['revision']
    # Fit symmetric pairs first, so a heavy rack never gets rejected merely
    # because its balancing rack has not yet been fitted on the other wing.
    for kind in (('agm','aam','rocket','pod','gunpod') if d.get('helicopter') else ('aam','bomb','rocket','pod','gunpod')):
        for wi,w in sorted(enumerate(fit['weapons']),key=lambda q:bool(q[1]['guidance']) if kind=='bomb' else False):
            if w['kind']!=kind:continue
            if kind=='aam' and w['count']>1:continue
            free=[i for i in w['slots'] if config['stations'][i]<0]
            pairs=[];left=[i for i in free if fit['slots'][i]['side']<0];right=[i for i in free if fit['slots'][i]['side']>0]
            pairs.extend(zip(left,reversed(right)));pairs.extend((i,) for i in free if fit['slots'][i]['side']==0)
            for pair in pairs:
                if kind=='aam' and sum(w['count'] for _,w in items(d,config) if w['kind']=='aam')>=4:continue
                candidate=copy.deepcopy(config)
                for i in pair:candidate['stations'][i]=wi
                if valid(d,candidate):config=candidate
    return config

def selected(d,choices=None):
    config=copy.deepcopy((choices or {}).get('loadout'))
    fit=d['loadout']
    if d.get('helicopter') and isinstance(config,dict) and 'stations' in config and config.get('fit_revision')!=fit.get('revision'):
        previous=config['stations'];config={'stations':[-1]*len(fit['slots']),'fit_revision':fit.get('revision')}
        for old_station,index in enumerate(previous):
            if not isinstance(index,int) or index<0 or index>=len(fit['weapons']):continue
            candidates=[slot for slot in fit['weapons'][index]['slots'] if config['stations'][slot]<0]
            if candidates:config['stations'][old_station if old_station in candidates else candidates[0]]=index

    if d.get('helicopter') and isinstance(config,dict) and isinstance(config.get('stations'),list) and len(config['stations'])==4 and len(d['loadout']['slots'])==6:config['stations']+= [-1,-1]
    return copy.deepcopy(config) if valid(d,config) else default(d)

def install_plane(p,choices):
    p.loadout=selected(p.stats,choices);p.stores=[]
    for station,w in items(p.stats,p.loadout):
        store=copy.deepcopy(w);store.update(station=station,remaining=w['count']);p.stores.append(store)
        if w.get('attached_rockets'):
            attached=copy.deepcopy(w);attached.update(kind='rocket',name='FFAR Mighty Mouse rockets',short='FFAR Mighty Mouse',count=w['attached_rockets'],remaining=w['attached_rockets'],station=station,caliber=70,guidance='',mass=0);p.stores.append(attached)

    p.pod_ammo=sum(max(150,int(w.get('params',{}).get('Ammunition','150').split()[0].replace(',','')))*w['count'] for w in p.stores if w['kind']=='gunpod')
    p.pods=any(w['kind']=='pod' and 'target' in w['name'].lower() for w in p.stores)
    p.flares=(30 if p.stats.get('countermeasures') else 0)+sum(w.get('countermeasures',0) for w in p.stores)
    from Countermeasures import prepare
    prepare(p)
    p.fuel=2700.+sum(w['mass']*.5 for w in p.stores if w['kind']=='tank');p.ground_choice=0;p.ground_lock=None
    refresh(p)

def refresh(p):
    p.missiles=sum(w['remaining'] for w in p.stores if w['kind']=='aam')
    p.bombs=sum(w['remaining'] for w in p.stores if w['kind']=='bomb')
    p.rockets=sum(w['remaining'] for w in p.stores if w['kind']=='rocket')
    p.agms=sum(w['remaining'] for w in p.stores if w['kind']=='agm')

def available(p,kind):return [w for w in p.stores if w['kind']==kind and w['remaining']>0]
def consume(p,kind,name=None):
    pool=available(p,kind)
    if name:pool=[w for w in pool if w['short'].split()[0]==name]
    if not pool:return None
    w=pool[0];w['remaining']-=1;refresh(p);return w

def concise(w):
    short=w['short'];import re
    short=re.sub(r'^\d+ (?:kg|lb) ','',short)
    short=short.replace('LDGP ','').replace('air-to-air missiles','').replace('air-to-ground missile','')
    short=re.sub(r'^\d+ mm ','',short)
    match=re.search(r'Mk \d+|AN-[A-Z]\d+|[A-Za-zА-Яа-я][A-Za-z0-9./-]*|\d+-\d+',short)
    code=match[0] if match else short.split()[0]
    return (str(w['count'])+'× ' if w['count']>1 else '')+code[:13]

def draw_stores(surface,d,pos,scale,yaw,config=None,stores=None,bank=0,units=8,sweep=0):
    from pygame.math import Vector2 as V
    fit=d['loadout']
    if not fit['slots']:return
    payload=[(w['station'],w) for w in stores if w['remaining']>0] if stores is not None else items(d,config or default(d))
    n=len(fit['slots']);projection=max(.08,abs(math.cos(math.radians(bank))))
    for station,w in payload:
        side=fit['slots'][station]['side'];rank=sum(1 for s in fit['slots'][:station] if s['side']==side);count=sum(1 for s in fit['slots'] if s['side']==side)
        lateral=side*d['span']*4*(.15+.70*(rank/(max(1,count-1)) if side>0 else 1-rank/max(1,count-1))) if side else 0
        longitudinal=(-.02*d['length']*8 if side else -d['length']*1.0+rank*6)
        mount=V(longitudinal/8,lateral/8)
        if d.get('model_family') in ('f14','f111','tornado','su17','su24'):
            from SwingWingModels import store_mount
            mount=store_mount(d['model_family'],d,mount.x,mount.y,sweep)
        point=V(pos)+V(mount.x,mount.y*projection).rotate(yaw)*scale*units
        color=(234,220,156) if w['kind'] in ('aam','agm') else (115,140,91) if w['kind']=='bomb' else (151,173,186)
        length=max(2,10*scale*units/8);delta=V(length,0).rotate(yaw);pygame.draw.line(surface,color,point-delta,point+delta,max(1,round(3*scale*units/8)))

class Editor:
    def __init__(self,garage):self.a=garage;self.station=0;self.page=0;self.buttons=[];self.ident=None;self.symmetric=True
    def sync(self):
        if self.ident!=self.a.preview:self.ident=self.a.preview;self.station=0;self.page=0
    def config(self):
        from Aviation import AIRCRAFT
        return selected(AIRCRAFT[self.a.preview],self.a.profile.weapons.get(self.a.preview))
    def save(self,config):
        from Aviation import AIRCRAFT
        if not valid(AIRCRAFT[self.a.preview],config):self.a.notice='超过总挂载、单侧重量或左右重量差限制';return False
        self.a.profile.weapons.setdefault(self.a.preview,{})['loadout']=config;self.a.profile.profile.save();self.a.notice='挂载已保存，下次部署按此配置携带';return True
    def click(self,pos):
        self.sync()
        for kind,value,r in self.buttons:
            if not r.collidepoint(pos):continue
            if kind=='station':self.station=value;self.page=0
            elif kind=='page':self.page=max(0,self.page+value)
            elif kind=='symmetric':self.symmetric=not self.symmetric
            else:
                config=self.config()
                if kind=='preset':config={'preset':value}
                elif kind=='clear':
                    config={'stations':[-1]*len(config['stations'])} if 'stations' in config else {'preset':-1}
                elif kind=='default':
                    from Aviation import AIRCRAFT
                    config=default(AIRCRAFT[self.a.preview])
                else:
                    config['stations'][self.station]=value
                    if self.symmetric:
                        from Aviation import AIRCRAFT
                        fit=AIRCRAFT[self.a.preview]['loadout'];other=len(fit['slots'])-1-self.station
                        if other!=self.station and fit['slots'][other]['side']==-fit['slots'][self.station]['side'] and fit['slots'][self.station]['side'] and (value<0 or other in fit['weapons'][value]['slots']):config['stations'][other]=value
                self.save(config)
            return True
        return False
    def scroll(self,delta):self.page=max(0,self.page-int(delta))
    def draw(self):
        from Aviation import AIRCRAFT,draw_aircraft
        self.sync();a=self.a;g=a.g;s=g.screen;t=g.text;d=AIRCRAFT[a.preview];fit=d['loadout'];config=self.config();self.buttons=[]
        t(d['name']+' · 挂载编辑',(32,96),24)
        draw_aircraft(s,d,(178,282),min(2.2,210/(d['span']*4)),-90)
        draw_stores(s,d,(178,282),min(2.2,210/(d['span']*4)),-90,config,units=4)
        mass,left,right=totals(d,config)
        t(f"挂载重量 {mass:.0f}"+(f" / {fit['maximum']:.0f} kg" if fit['maximum'] else ' kg'),(32,421),16)
        t(f'左翼 {left:.0f} / 右翼 {right:.0f} kg',(32,449),14)
        t('仅显示该位置兼容的挂载',(32,477),14)
        for label,kind,x in [('清空','clear',32),('推荐配置','default',154)]:
            r=pygame.Rect(x,507,112,33);g.button(r,label);self.buttons.append((kind,None,r))
        if fit['slots']:
            t(f"挂载表 {len(fit['slots'])} 个位置（含设备位）",(331,139),16)
            for i,slot in enumerate(fit['slots']):
                r=pygame.Rect(330+(i%2)*173,171+(i//2)*48,166,42);index=config['stations'][i];label=f'{i+1:02d} '+('空' if index<0 else concise(fit['weapons'][index]))
                g.button(r,'',self.station==i)
                t(fitted_label(label,r.width-16),(r.x+8,r.y+3),14)
                if index>=0:t(fitted_label(type_label(fit['weapons'][index]),r.w-16),(r.x+8,r.y+23),14,(169,205,221))
                self.buttons.append(('station',i,r))
            options=[(-1,'空挂点','')]+[(i,w['name'],type_label(w)) for i,w in enumerate(fit['weapons']) if self.station in w['slots']]
            t(f'位置 {self.station+1} 可安装的挂载',(700,139),18)
        else:
            t('固定武器方案 / 弹舱组合',(390,139),18)
            t('选择整套方案后，下次部署生效',(390,167),14)
            options=[(-1,'空载','')]+[(i,p['name'],preset_type_label(p)) for i,p in enumerate(fit['presets'])]
        startx=700 if fit['slots'] else 390;width=548 if fit['slots'] else 858
        pages=max(1,math.ceil(len(options)/8));self.page=min(self.page,pages-1)
        for row,(index,label,category) in enumerate(options[self.page*8:self.page*8+8]):
            r=pygame.Rect(startx,194+row*37,width,32);current=config['stations'][self.station] if fit['slots'] else config['preset']
            g.button(r,'',current==index)
            category_width=240 if fit['slots'] else 300
            t(fitted_label(label,width-category_width-26),(r.x+10,r.y+7),14)
            t(fitted_label(category,category_width-12),(r.right-category_width,r.y+7),14,(169,205,221))
            self.buttons.append(('weapon' if fit['slots'] else 'preset',index,r))
        for delta,x,label in [(-1,startx,'上一页'),(1,startx+115,'下一页')]:
            r=pygame.Rect(x,500,104,34);g.button(r,label);self.buttons.append(('page',delta,r))
        t(f'{self.page+1}/{pages} 页',(startx+240,508),16)
        if fit['slots']:
            r=pygame.Rect(1055,500,193,34);g.button(r,'对称安装：'+('开' if self.symmetric else '关'),self.symmetric);self.buttons.append(('symmetric',None,r))

def loadout_self_test(api):
    from Aviation import AIRCRAFT
    from AircraftPhysics import Plane
    from pygame.math import Vector2 as V
    for ident,d in AIRCRAFT.items():
        config=default(d);assert valid(d,config),d['name']
        plane=Plane(ident,0,V(),{'loadout':config})
        assert plane.missiles==sum(w['count'] for _,w in items(d,config) if w['kind']=='aam')
        assert plane.bombs==sum(w['count'] for _,w in items(d,config) if w['kind']=='bomb')
        assert plane.rockets==sum(w['count'] for _,w in items(d,config) if w['kind']=='rocket')
    d=next(d for d in AIRCRAFT.values() if d['name']=='F-16CM')
    assert d['station_count']==11 and d['weapon_station_count']==8
    config={'stations':[-1]*11};wi=next(i for i,w in enumerate(d['loadout']['weapons']) if w['short'].startswith('AIM-9M'));config['stations'][0]=wi
    assert valid(d,config);p=Plane(d['id'],0,V(),{'loadout':config});assert p.missiles==1
    assert consume(p,'aam','AIM-9M') and p.missiles==0 and consume(p,'aam','AIM-9M') is None
    config['stations'][5]=wi;assert not valid(d,config)
    terrain=api['Terrain']();terrain.obstacles=[(pygame.Rect(551,491,18,18),'tree')];terrain.trees=[(V(560,500),25)];terrain.fallen=[]
    for _ in range(3):terrain.strike_tree(V(500,500),V(620,500),1)
    assert terrain.trees;terrain.strike_tree(V(500,500),V(620,500),1);assert not terrain.trees and len(terrain.fallen)==1
    assert next(d for d in api['VEHICLES'].values() if d['name']=='Pantsir-S1')['visual_length_m']==9
    print('PASS: 116 unit-specific station/preset fits, weight and compatibility limits, actual loaded ammunition and expenditure, bullet-damaged trees and shortened truck geometry')
