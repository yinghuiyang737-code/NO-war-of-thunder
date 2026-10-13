import os,sys,json,math
import pygame
from Matchmaking import lineup_br
from Aviation import AIRCRAFT

NATIONS={
 'cn':{'name':'中国','code':'CHN','color':(100,131,78),'branches':[['M5A1','Type 62','PTL02'],['T-34-85','Type 59','Type 69'],['SU-76M','ISU-122','IS-2']]},
 'ussr':{'name':'苏联','code':'USSR','color':(94,119,72),'branches':[['BT-5','T-50','PT-76B'],['T-34 (1941)','T-34-85','T-54 (1947)'],['SU-76M','SU-85','IS-2']]},
 'de':{'name':'德国','code':'GER','color':(151,143,109),'branches':[['Pz.II C','Pz.III J','Puma'],['Pz.IV F2','Panther D','Leopard 1'],['StuG III F','Jagdpanzer IV','Tiger H1']]},
 'us':{'name':'美国','code':'USA','color':(112,132,91),'branches':[['M5A1','M24','M41A1'],['M4A1','M4A3 (76) W','M26'],['M10','M36','T26E1-1']]}}
NATIONS['us']['branches'][1] += ['M46','M48A1','M60','M60A1 (AOS)','M60A3 TTS','M1','M1A1','M1A2','M1A2 SEP','M1A2 SEPv2','M1A2 SEPv3']
NATIONS['de']['branches'][1] += ['Leopard A1A1','Leopard 1A5','Leopard 2K','Leopard 2A4','Leopard 2A5','Leopard 2A6','Leopard 2A7V']
NATIONS['ussr']['branches'][1] += ['T-55A','T-62','T-64A','T-72A','T-64B','T-80B','T-80U','T-72B3','T-80BVM']
from VehicleModels import SHAPES
from ExtendedVehicles import install, extend_config
install(NATIONS,SHAPES)
SHAPES.update({'Type 59D1': (47, 24, 'round', 1, 22, 85), 'ZTZ88B': (50, 25, 'round', 0, 23, 89), 'MBT-2000': (54, 27, 'wedge', 0, 26, 95), 'VT4A1': (57, 28, 'wedge', 0, 28, 99), 'T-62M-1': (49, 25, 'round', 0, 24, 84), 'T-72B': (49, 25, 'round', 0, 24, 91), 'T-72B (1989)': (49, 26, 'round', 0, 24, 91), 'T-90A': (50, 26, 'box', 0, 25, 93), 'T-90M': (52, 27, 'wedge', -2, 27, 94), 'T-90M (Arena-M)': (52, 27, 'wedge', -2, 27, 94), 'M4A3E2': (45, 25, 'round', 1, 20, 56), 'M60A1 RISE (P)': (54, 27, 'point', 0, 24, 89), 'IPM1': (57, 27, 'abrams', -1, 26, 89), 'M1A1 HC': (58, 28, 'abrams', -1, 27, 94), 'M1A2 (Trophy-HV)': (59, 29, 'abrams', -1, 29, 95), 'Panther A': (53, 26, 'box', 5, 18, 84), 'Panther F': (53, 26, 'box', 5, 17, 84), 'Leopard 2AV': (57, 28, 'box', 0, 26, 86), 'Leopard 2 PSO': (58, 29, 'wedge', 0, 29, 94), 'Leopard 2A7A1': (59, 29, 'wedge', 0, 29, 108)})
NATIONS['ussr']['branches'].append(['T-62M-1', 'T-72B', 'T-72B (1989)', 'T-90A', 'T-90M', 'T-90M (Arena-M)'])
NATIONS['cn']['branches'].append(['Type 59D1', 'ZTZ88B', 'MBT-2000', 'VT4A1'])
NATIONS['us']['branches'].append(['M4A3E2', 'M60A1 RISE (P)', 'IPM1', 'M1A1 HC', 'M1A2 (Trophy-HV)'])
NATIONS['de']['branches'].append(['Panther A', 'Panther F', 'Leopard 2AV', 'Leopard 2 PSO', 'Leopard 2A7A1'])
NATIONS['ussr']['branches'][2]+=['BMPT-72','BMPT']
SHAPES.update({'BMPT-72':(50,26,'box',-3,16,64),'BMPT':(52,27,'box',-3,17,66)})
from ArtilleryVehicles import register as register_artillery, configure as configure_artillery
register_artillery(NATIONS,SHAPES)
BRANCH_NAMES=('侦察线','主战线','支援线','防空线','主战二线','自行火炮')
VEHICLES={}
for country,nation in NATIONS.items():
    for branch,names in enumerate(nation['branches']):
        for tier,name in enumerate(names,1):
            ident=f'{country}_{branch}_{tier}'
            speed=(160 if branch==0 else 135 if branch==1 else 105)+(tier-1)*7
            reload=(1.45 if branch==0 else 1.65 if branch==1 else 2.05)-(tier-1)*.08
            front=(58 if branch==0 else 85 if branch==1 else 108)+(tier-1)*17
            side=(32 if branch==0 else 48 if branch==1 else 64)+(tier-1)*8
            pen=(112 if branch==0 else 128 if branch==1 else 148)+(tier-1)*18
            if country=='de':front+=7;pen+=5
            if country=='us':reload*=.9
            if country=='cn':speed+=5
            VEHICLES[ident]={'id':ident,'name':name,'country':country,'branch':branch,'tier':tier,
                'parent':f'{country}_{branch}_{tier-1}' if tier>1 else None,'cost':80 if tier==2 else 160+(tier-3)*40 if tier>=3 else 0,
                'speed':speed,'reverse':80 if country=='us' else 60 if country=='ussr' else 72,
                'turn':78 if branch==0 else 65 if branch==1 else 55,'reload':max(.9,reload),
                'armor':(front,side,28+(tier-1)*8),'pen':pen,'color':nation['color']}
for c in NATIONS:
    root=VEHICLES[f'{c}_4_1'];root['parent']=f'{c}_1_1' if c=='us' else f'{c}_1_3';root['cost']=240
    for vehicle in VEHICLES.values():
        if vehicle['country']==c and vehicle['branch']==4:vehicle['cost']=240+(vehicle['tier']-1)*160
# Keep support-equipped vehicles in their original research chains.
# M3A3 follows M3 before HSTV-L; PUMA VJTF follows PUMA.
from VehicleModels import configure_vehicle, draw_model
from VehicleData import configure as configure_data, default_ammo, ammo_name, guided
for vehicle in VEHICLES.values():configure_vehicle(vehicle);extend_config(vehicle);configure_data(vehicle);configure_artillery(vehicle)
for ident in ('ussr_2_10','ussr_2_11','us_0_6','de_0_9','cn_2_7'):VEHICLES[ident]['equipment'].append('步战火力支援')

from GroundModels import fit as fit_ground_model
for vehicle in VEHICLES.values():fit_ground_model(vehicle)
from ModernVehicles import register as register_modern
register_modern(VEHICLES,NATIONS)
from PremiumVehicles import register as register_premiums
register_premiums(VEHICLES)
from JapaneseVehicles import register as register_japan
register_japan(VEHICLES,NATIONS,AIRCRAFT)
from NewRewardVehicles import register as register_extra_rewards
register_extra_rewards(VEHICLES)
from SplitAirDefense import register as register_split_sam
register_split_sam(VEHICLES,NATIONS)
from Helicopters import register as register_helicopters
register_helicopters(AIRCRAFT)
from NewAircraft import register as register_new_aircraft
register_new_aircraft(AIRCRAFT)
from T80M import register as register_t80m
register_t80m(VEHICLES,NATIONS)
from TechExpansion import register as register_expansion
register_expansion(VEHICLES,NATIONS,AIRCRAFT)
from ModernAirDefense import register as register_modern_aa
register_modern_aa(VEHICLES,NATIONS)
from TechTreeLayout import normalize as normalize_research
normalize_research(VEHICLES);normalize_research(AIRCRAFT)
CATALOG={**VEHICLES,**AIRCRAFT}
from ResearchRebalance import configure as rebalance_research
rebalance_research(CATALOG)
from Reconnaissance import configure as configure_recon
configure_recon(VEHICLES)
from AmmoCapacityData import configure as configure_ammo_capacities
configure_ammo_capacities(VEHICLES)
def combined_br(lineup):
    return min(max(v['br'] for v in VEHICLES.values()),max((CATALOG[k].get('ground_br',CATALOG[k]['br']) for k in lineup if k),default=1.))

def starter_lineup(country):return [next(k for k,d in VEHICLES.items() if d['country']==country and d['branch']==b and d['parent'] is None and not d.get('premium')) for b in (1,0,2)]+[None]*9
def default_save_path():
    root=os.path.dirname(sys.executable if getattr(sys,'frozen',False) else os.path.abspath(__file__))
    return os.path.join(root,'玩家进度.json')
class Profile:
    def __init__(self,path=None):
        self.path=path or default_save_path();self.country='cn';self.internal_premium_claim=False;self.late_join=False;self.research=360;self.ammo_choices={};self.missile_choices={}
        self.unlocked={k for k,v in VEHICLES.items() if v['tier']==1 and v['branch'] not in (4,5) and not v.get('premium')}
        self.lineups={k:starter_lineup(k) for k in NATIONS};self.active={k:0 for k in NATIONS}
        try:
            with open(self.path,'r',encoding='utf-8') as f:data=json.load(f)
            self.country=data.get('country','cn') if data.get('country') in NATIONS else 'cn'
            self.late_join=data.get('late_join') is True
            self.internal_premium_claim=data.get('internal_premium_claim') is True
            self.research=max(0,int(data.get('research',360)))
            self.ammo_choices={k:int(i) for k,i in data.get('ammo_choices',{}).items() if k in VEHICLES and isinstance(i,int) and 0<=i<len(VEHICLES[k]['ammo_options'])}
            self.missile_choices={k:int(i) for k,i in data.get('missile_choices',{}).items() if k in VEHICLES and isinstance(i,int) and 0<=i<len(VEHICLES[k]['ammo_options']) and guided(VEHICLES[k]['ammo_options'][i])}
            self.unlocked.update(k for k in data.get('unlocked',[]) if k in CATALOG)
            for country in NATIONS:
                lineup=data.get('lineups',{}).get(country,[])
                equipped=[k for k in lineup if k is not None]
                if len(lineup) in (3,8,12) and len(set(equipped))==len(equipped) and all(k in self.unlocked and CATALOG[k]['country']==country for k in equipped):self.lineups[country]=(lineup+[None]*12)[:12]
                self.active[country]=max(0,min(11,int(data.get('active',{}).get(country,0))))
        except (OSError,ValueError,TypeError):pass
        from Aviation import AirProfile
        self.aviation=AirProfile(self)
        from DailyRewards import Daily
        self.daily=Daily(self,data.get("daily") if "data" in locals() else None)
        from ResearchRebalance import migrate
        migrate(self,data if "data" in locals() else {})
    @property
    def selected(self):return self.lineups[self.country][self.active[self.country]] or next((v for v in self.lineups[self.country] if v is not None),f'{self.country}_1_1')
    def save(self):
        data={'internal_premium_claim':self.internal_premium_claim,'late_join':self.late_join,'country':self.country,'research':self.research,'unlocked':sorted(self.unlocked),'lineups':self.lineups,'active':self.active,'ammo_choices':self.ammo_choices,'missile_choices':self.missile_choices,'aviation':self.aviation.to_dict(),'combined_arms':True,'daily':self.daily.to_dict(),'refunds':self.refunds}
        try:
            with open(self.path+'.tmp','w',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
            os.replace(self.path+'.tmp',self.path);return True
        except OSError:return False
    def ammo_index(self,ident):
        index=self.ammo_choices.get(ident,default_ammo(VEHICLES[ident]))
        return index if isinstance(index,int) and 0<=index<len(VEHICLES[ident]['ammo_options']) and not (VEHICLES[ident]['independent_missiles'] and guided(VEHICLES[ident]['ammo_options'][index])) else default_ammo(VEHICLES[ident])
    def missile_index(self,ident):
        options=VEHICLES[ident]["ammo_options"];valid=[i for i,a in enumerate(options) if guided(a)]
        index=self.missile_choices.get(ident,valid[0] if valid else 0)
        return index if index in valid else valid[0] if valid else 0
    def choose_ammo(self,ident,index):
        if ident not in VEHICLES or not 0<=index<len(VEHICLES[ident]['ammo_options']):return False
        if VEHICLES[ident]['independent_missiles'] and guided(VEHICLES[ident]['ammo_options'][index]):self.missile_choices[ident]=index
        else:self.ammo_choices[ident]=index
        self.save();return True
    def select_country(self,country):
        if country not in NATIONS:return False
        self.country=country;self.save();return True
    def can_research(self,ident):
        if ident not in VEHICLES:return False
        v=VEHICLES[ident]
        return v['country']==self.country and ident not in self.unlocked and not v.get('premium') and (v['parent'] is None or v['parent'] in self.unlocked) and self.research>=v['cost']
    def unlock(self,ident):
        if not self.can_research(ident):return False
        self.research-=VEHICLES[ident]['cost'];self.unlocked.add(ident);self.save();return True
    def equip(self,ident):
        if ident not in self.unlocked or ident not in CATALOG or CATALOG[ident]['country']!=self.country:return False
        slot=self.active[self.country];lineup=self.lineups[self.country];lineup.extend([None]*max(0,12-len(lineup)))
        if ident in lineup:
            other=lineup.index(ident);lineup[other],lineup[slot]=lineup[slot],lineup[other]
        else:lineup[slot]=ident
        self.save();return True

def shade(col,f):return tuple(max(0,min(255,int(c*f))) for c in col)
def draw_tank_art(surface,vehicle,center,scale=3.5,yaw=-15):
    draw_model(surface,vehicle,center,scale,yaw,top=True)

class Garage:
    def __init__(self,screen,text,profile=None):
        self.screen=screen;self.text=text;self.profile=profile or Profile();self.tab='garage';self.preview=self.profile.selected if self.profile.selected in VEHICLES else f'{self.profile.country}_1_1'
        self.notice=(f'日系研发降价返还：{self.profile.research_refund} 研发点' if self.profile.research_refund else '选择国家、编成出战栏，再点击右上角出战');self.yaw=-15.;self.dragging=False;self.last_x=0;self.time=0.;self.tech_row=0
    def current(self):return VEHICLES[self.preview] if self.preview in VEHICLES else VEHICLES[f'{self.profile.country}_1_1']
    def start_button(self):return pygame.Rect(1045,18,205,45)
    def tech_button(self):return pygame.Rect(472,20,136,40)
    def garage_button(self):return pygame.Rect(330,20,120,40)
    def data_button(self):return pygame.Rect(621,20,155,40)
    def ammo_buttons(self):return [(i,pygame.Rect(640+(i%2)*300,160+(i//2)*61,287,54)) for i in range(len(self.current()['ammo_options']))]
    def bottom_offset(self):return self.screen.get_height()-850
    def country_buttons(self):return [(k,pygame.Rect(32+i*155,588+self.bottom_offset(),145,42)) for i,k in enumerate(NATIONS)]
    def slot_buttons(self):return [(i,pygame.Rect(32+(i%6)*130,669+self.bottom_offset()+(i//6)*70,124,62)) for i in range(12)]
    def tech_view(self):return pygame.Rect(280,174,self.screen.get_width()-316,max(240,self.screen.get_height()-501))
    def tech_column(self,branch,count):
        view=self.tech_view();step=(view.w-50)/count
        return round(view.x+50+branch*step),max(100,round(step)-6)
    def rank_rows(self):
        from TechTreeLayout import rows
        country=self.profile.country
        return rows(VEHICLES,country,len(NATIONS[country]['branches']),ranks=('I','II','III','IV','V','VI','VII','VIII'),owned=self.profile.unlocked)
    def max_scroll(self):
        return max(0,sum(row[2] for row in self.rank_rows())-self.tech_view().h)
    def nodes(self):
        view=self.tech_view();nodes=[];offset=max(0,min(self.max_scroll(),self.tech_row))
        for rank,y,height,groups in self.rank_rows():
            for branch,identifiers in enumerate(groups):
                for index,ident in enumerate(identifiers):
                    if ident is None:continue
                    x,width=self.tech_column(branch,len(groups))
                    r=pygame.Rect(x,view.y+y-offset+26+index*60,width,56)
                    if r.colliderect(view):nodes.append((ident,r))
        return nodes
    def scroll(self,delta):
        self.tech_row=max(0,min(self.max_scroll(),self.tech_row-delta*72))

    def unlock_button(self):return pygame.Rect(33,433,238,44)
    def equip_button(self):return pygame.Rect(33,487,238,44)
    def click(self,pos):
        if self.start_button().collidepoint(pos) and not any(self.profile.lineups[self.profile.country]):self.notice='请先装备至少一辆载具';return None
        if self.start_button().collidepoint(pos):return 'battle'
        if self.garage_button().collidepoint(pos):self.tab='garage';self.preview=self.profile.selected if self.profile.selected in VEHICLES else f'{self.profile.country}_1_1';return None
        if self.data_button().collidepoint(pos):self.tab='data';return None
        if self.tab=='data':
            for i,r in self.ammo_buttons():
                if r.collidepoint(pos):self.profile.choose_ammo(self.preview,i);self.notice='已保存 '+ammo_name(self.current()['ammo_options'][i]);return None
        if self.tech_button().collidepoint(pos):self.tab='tech';return None
        for country,r in self.country_buttons():
            if r.collidepoint(pos):
                self.tech_row=0;self.profile.select_country(country);self.preview=self.profile.selected;self.notice='已切换国家，出战栏仅包含该国科技线载具';return None
        for slot,r in self.slot_buttons():
            if r.collidepoint(pos):
                self.profile.active[self.profile.country]=slot;self.profile.save();self.preview=self.profile.selected
                self.notice=f'已选择出战栏 {slot+1}，科技树中可更换该栏载具';return None
        if self.tab=='tech':
            for ident,r in self.nodes():
                if self.tech_view().collidepoint(pos) and r.collidepoint(pos):self.preview=ident;return None
            if self.unlock_button().collidepoint(pos):
                if self.profile.unlock(self.preview):self.notice='研究完成！点击“加入出战栏”装备载具'
                else:self.notice='需要先研究前置载具，并有足够研究点'
            if self.equip_button().collidepoint(pos):
                if self.profile.equip(self.preview):self.notice='载具已加入当前出战栏'
                else:self.notice='该载具尚未研究，或不属于当前国家'
        elif pygame.Rect(300,90,max(1,self.screen.get_width()-560),max(1,461+self.bottom_offset())).collidepoint(pos):self.dragging=True;self.last_x=pos[0]
        return None
    def remove_slot(self,pos):
        for slot,r in self.slot_buttons():
            if not r.collidepoint(pos):continue
            lineup=self.profile.lineups[self.profile.country]
            if lineup[slot] is None:return False
            lineup[slot]=None;self.profile.save();self.preview=self.profile.selected
            self.notice=f'已移除出战栏 {slot+1} 的载具，编成 BR 已重新计算';return True
        return False
    def motion(self,pos):
        if self.dragging:self.yaw+=(pos[0]-self.last_x)*.45;self.last_x=pos[0]
    def collect_game(self,game):
        self.profile.daily.report(game)
        if getattr(game,'reward_paid',False):return 0
        reward=game.kills*20+max(0,game.wave-1)*30+(120 if game.state=='win' else 20 if game.state=='lose' else 0)
        game.reward_paid=True
        if reward:self.profile.research+=reward;self.profile.save();self.notice=f'战斗结算：获得 {reward} 研究点'
        return reward
    def button(self,r,label,selected=False,enabled=True):
        pygame.draw.rect(self.screen,(77,92,77) if selected else (35,43,42),r,border_radius=5)
        pygame.draw.rect(self.screen,(218,185,109) if selected else (78,89,82),r,2 if selected else 1,border_radius=5)
        self.text(label,r.center,18,(240,229,194) if enabled else (120,130,122),True)
    def draw(self):
        s=self.screen;t=self.text;p=self.profile;v=self.current();dy=self.bottom_offset();s.fill((20,27,27))
        width=s.get_width();bottom=551+dy
        horizon=round(76+(bottom-76)*.66)
        pygame.draw.rect(s,(29,39,37),(0,76,width,bottom-76))
        for x in range(0,width,80):pygame.draw.line(s,(39,51,47),(x,76),(x,bottom))
        for y in range(76,bottom,80):pygame.draw.line(s,(39,51,47),(0,y),(width,y))
        pygame.draw.rect(s,(17,23,25),(0,0,s.get_width(),76));t('钢铁旷野',(32,17),30);t('STEEL WILDERNESS',(34,51),14,(129,151,142))
        self.button(self.garage_button(),'车库',self.tab=='garage');self.button(self.tech_button(),'科技树',self.tab=='tech')
        self.button(self.start_button(),'出 战  →',True)
        self.button(self.data_button(),'资料 / 弹药',self.tab=='data')
        if self.tab=='data':
            self.draw_data()
        elif self.tab=='garage':
            draw_tank_art(s,v,((s.get_width()+50)/2,76+(bottom-76)*.50),min(3.65,(bottom-145)/(2*max(v['model'][0],v['model'][5],v['model'][4]+12)),(width-570)/(2*max(v['model'][0],v['model'][5],v['model'][4]+12))),self.yaw)
            pygame.draw.rect(s,(24,32,31),(25,105,260,388),border_radius=7)
            t(NATIONS[p.country]['name']+' · '+BRANCH_NAMES[v['branch']],(42,123),18,(174,197,165));t(v['name'],(42,160),24)
            t(f'{v["rank"]} 级 · BR {v["br"]:.1f} / 出战栏 {p.active[p.country]+1}',(42,201),16,(193,185,151))
            for i,(label,val,limit,unit) in enumerate([('前进速度',v['speed']*.2,40,'km/h'),('正面动能等效≈' if 'hull' in v['front_profile'] else '车体正面钢甲',v['front_profile'].get('hull',v['armor'])[0],900 if 'hull' in v['front_profile'] else 180,'mm'),('穿甲能力',v['pen'],200,'mm'),('装填时间',v['reload'],3,'s')]):
                y=251+i*53;t(label,(42,y),16,(159,179,165));t(f'{val:.1f} {unit}',(155,y),16)
                pygame.draw.rect(s,(50,61,53),(42,y+28,218,5));pygame.draw.rect(s,(174,189,131),(42,y+28,int(218*min(1,val/limit)),5))
            t('按住左键拖动 · 旋转 2D 载具',((s.get_width()+50)/2,bottom-40),16,(197,207,184),True)
            pygame.draw.rect(s,(25,33,32),(s.get_width()-240,126,213,230),border_radius=7)
            for i,line in enumerate(['野外协同作战','每方 16 人 · 双部署点','机枪 / 夜视 / 热成像','稳定器 / 双流传动','被击毁后选择下一辆','浅水 / 撞树 / 模块损伤']):t(line,(s.get_width()-226,145+i*32),18 if i==0 else 16,(222,224,191) if i==0 else (162,185,165))
        else:
            pygame.draw.rect(s,(23,31,31),(20,94,s.get_width()-40,self.tech_view().bottom-94+23),border_radius=7)
            t(NATIONS[p.country]['name']+' 科技树',(34,109),24);t(v['name'],(34,152),20)
            draw_tank_art(s,v,(149,270),1.2,-15)
            protection=f'正面 KE≈{v["front_profile"]["hull"][0]:g} / CE≈{v["front_profile"]["hull"][1]:g}' if 'hull' in v['front_profile'] else f'钢甲 {v["armor"][0]:g} mm  穿甲 {v["pen"]:g} mm'
            for i,line in enumerate([f'{v["rank"]} 级 · BR {v["br"]:.1f} · {BRANCH_NAMES[v["branch"]]}',f'速度 {v["speed"]*.2:.1f} km/h  装填 {v["reload"]:.2f}s',protection,f'研究费用：{v["cost"]} 点']):t(line,(33,323+i*22),16,(181,195,171))
            if v['parent']:t('前置：'+VEHICLES[v['parent']]['name'],(33,407),14,(157,181,161))
            columns=len(self.rank_rows()[0][3])
            for branch in range(columns):t(BRANCH_NAMES[branch] if branch<len(BRANCH_NAMES) else "已获得高级载具",(self.tech_column(branch,columns)[0]+self.tech_column(branch,columns)[1]/2,132),16,(214,214,175),True)
            view=self.tech_view();offset=max(0,min(self.max_scroll(),self.tech_row));previous_clip=s.get_clip();s.set_clip(view)
            visible=self.nodes();positions=dict(visible)
            for index,(rank,y,height,groups) in enumerate(self.rank_rows()):
                top=view.y+y-offset;band=pygame.Rect(view.x,top,view.w,height)
                if not band.colliderect(view):continue
                pygame.draw.rect(s,(28,39,37) if index%2==0 else (24,34,33),band)
                pygame.draw.line(s,(79,98,83),(view.left,top),(view.right,top),1)
                t(rank+' 级',(304,top+12),16,(217,197,141),True)
                for branch,identifiers in enumerate(groups):
                    if not identifiers:t('—',(self.tech_column(branch,len(groups))[0]+self.tech_column(branch,len(groups))[1]/2,top+48),16,(86,106,96),True)
            # Research links use actual parent IDs, including parents in another branch.
            for ident,r in visible:
                parent=VEHICLES[ident]['parent'];pr=positions.get(parent)
                if pr:
                    color=(145,166,117) if parent in p.unlocked else (70,90,77)
                    start=(pr.centerx,pr.bottom);end=(r.centerx,r.top)
                    if pr.x==r.x:pygame.draw.line(s,color,start,end,2)
                    else:
                        lane=r.top-5;pygame.draw.lines(s,color,False,[start,(start[0],lane),(end[0],lane),end],2)
            for ident,r in visible:
                node=VEHICLES[ident];owned=ident in p.unlocked;eligible=p.can_research(ident)
                pygame.draw.rect(s,(53,69,55) if owned else (38,47,45),r,border_radius=5)
                pygame.draw.rect(s,(235,196,112) if ident==self.preview else (133,168,128) if eligible else (82,104,87),r,2,border_radius=5)
                t(node['name'],(r.x+7,r.y+5),14 if len(node['name'])>16 else 16)
                t(f'{node["rank"]} · BR {node["br"]:.1f} · '+('已获得' if node.get('premium') else '已研究' if owned else f'{node["cost"]} 点'),(r.x+8,r.y+32),14,(169,216,154) if owned else (208,181,115))
            s.set_clip(previous_clip)
            self.button(self.unlock_button(),'已研究' if self.preview in p.unlocked else '研究载具',p.can_research(self.preview),p.can_research(self.preview))
            self.button(self.equip_button(),f'加入出战栏 {p.active[p.country]+1}',False,self.preview in p.unlocked)
            t('前置在上 · 后继在下 · 滚轮浏览',(s.get_width()-240,109),14,(173,189,167),True)
            track=pygame.Rect(view.right+4,view.y,4,view.h);pygame.draw.rect(s,(52,67,59),track)
            total=self.max_scroll()+view.h;thumb=max(25,int(view.h*view.h/total));pygame.draw.rect(s,(155,178,133),(track.x,track.y+int(offset/max(1,self.max_scroll())*(track.h-thumb)),4,thumb))
        equipment=' · '.join(v['equipment']) or '无附加设备'
        t(equipment,(320,bottom-21),14,(188,209,170))
        pygame.draw.rect(s,(17,24,25),(0,551+dy,s.get_width(),s.get_height()-551-dy));t(self.notice,(32,558+dy),16,(206,193,148))
        for country,r in self.country_buttons():self.button(r,NATIONS[country]['name']+'  '+NATIONS[country]['code'],country==p.country)
        t(f'陆战研发点  {p.research}',(830,601+dy),20,(226,203,135))
        t('出战载具  ·  共用 12 栏 / 坦克 + 飞机 + 直升机',(32,641+dy),18,(200,213,184))
        lineup=(p.lineups[p.country]+[None]*12)[:12]
        for slot,r in self.slot_buttons():
            ident=lineup[slot];active=slot==p.active[p.country]
            pygame.draw.rect(s,(45,58,48) if active else (30,39,37),r,border_radius=6)
            pygame.draw.rect(s,(224,189,111) if active else (71,91,77),r,2,border_radius=6)
            if ident:
                vehicle=CATALOG[ident]
                if ident in AIRCRAFT:
                    from Aviation import draw_aircraft
                    draw_aircraft(s,vehicle,(r.right-29,r.y+45),.3,-15)
                else:draw_tank_art(s,vehicle,(r.right-29,r.y+45),.29,-15)
                t(f'{slot+1}  {vehicle["name"]}',(r.x+10,r.y+8),14,max_width=r.w-18)
                t(('飞机 · 陆战 BR '+str(vehicle['ground_br'])) if ident in AIRCRAFT else f'{vehicle["rank"]} 级 · BR {vehicle["br"]:.1f}',(r.x+10,r.y+35),14,(174,192,157),max_width=r.w-16)
            else:
                t(f'{slot+1}  未装备',(r.x+10,r.y+8),16,(137,152,133))
                t('科技树中选择载具',(r.x+10,r.y+35),14,(119,140,125),max_width=r.w-16)
        rating=combined_br(lineup);low=min((CATALOG[k].get('ground_br',CATALOG[k]['br']) for k in lineup if k is not None),default=1.)
        t(f'编成 BR {rating:.1f} · 敌军 {max(1,rating-1):.1f}—{rating+1:.1f}',(830,641+dy),16,(225,203,139))
        if rating-low>1:t('低 BR 载具会被带入高等级战斗',(830,665+dy),14,(242,155,109))
        from InputBindings import get_controls
        controls=get_controls()

    def draw_data(self):
        from InputBindings import get_controls
        controls=get_controls()
        s=self.screen;t=self.text;v=self.current();d=v['research_data'];p=self.profile
        pygame.draw.rect(s,(23,31,31),(20,94,1240,432),border_radius=7)
        t(v['name']+' · 载具资料',(36,105),24)
        armor=lambda a:' / '.join(f'{x:g}' for x in a)
        profile=v['front_profile']
        front_lines=[f"车体 前 / 侧 / 后：{armor(v['armor'])} mm",f"炮塔 前 / 侧 / 后：{armor(v['turret_armor'])} mm"]
        if 'hull' in profile:
            front_lines=['正面整体防护 · 动能 / 化学弹（mm RHAe）',f"车体主防护区 ≈ {profile['hull'][0]:g} / {profile['hull'][1]:g}",f"炮塔主防护区 ≈ {profile['turret'][0]:g} / {profile['turret'][1]:g}",'首下 / 炮盾 / 座圈等弱区不等于主区防护']
        lines=[f"重量 {v['weight']:g} t · {v['horsepower']:g} hp · {v['power_weight']:.1f} hp/t",
               f"前进 {v['forward_kph']:g} / 倒车 {v['reverse_kph']:g} km/h",
               f"方向机 {v['turret_slew']:g} °/s · 游戏 {v['aim_response_slew']:g} · "+('WT 满改 / 满熟练' if '满熟练' in v['turret_slew_basis'] else v['turret_slew_basis'])]+front_lines+[
               f"装填 {v['reload']:.2f} s" if v['weapon']!='auto' else f"单管射速 {d.get('rpm',0):g} 发/分",
               '车体转向：'+v['steering'],
               ('钢板 + 复合包 / 间隙 / 附加甲' if v['composite'] else '均质 / 铸造钢装甲')+(' + 正面反应装甲' if max(profile.get('hull_era',(0,0))) or max(profile.get('turret_era',(0,0))) else '')]
        for i,line in enumerate(lines):t(line,(36,151+i*27),16,(197,211,183))
        t(d['source_note'][:43] if d.get('status') in ('mixed','simulation') else 'A7A1 未公开参数借用 A7V 的 WT 数据' if d.get('status')=='proxy' else '公开实车资料优先，其余采用 WT RB 满改规格',(36,447),14,(218,197,139))
        t(v['armor_note'] if d.get('status')=='mixed' else '≈ 为 WT 层材与布局折算估算；完整三维防护随命中点变化' if 'hull' in profile else '钢甲为 WT 资料厚度；角度会影响等效防护',(36,470),14,(178,194,170))
        t((controls.label('ground.smoke')+' 烟雾弹  ' if v['smoke_grenades'] else '')+(controls.label('ground.ess')+' 发动机烟幕' if v['ess'] else '') or '未装备烟雾设备',(36,493),14,(156,181,170))
        t('选择出战弹药 · 每辆车单独保存',(640,110),20,(225,213,169))
        t(controls.label('ground.ammo')+' 换炮弹 / '+controls.label('ground.missile_ammo')+' 换导弹 · '+controls.label('ground.lock')+' 锁定 / '+controls.label('ground.missile')+' 发射',(640,139),14,(185,204,175))
        for i,r in self.ammo_buttons():
            a=v['ammo_options'][i];selected=i==p.ammo_index(v['id']) or (v['independent_missiles'] and i==p.missile_index(v['id']))
            pygame.draw.rect(s,(62,76,55) if selected else (36,46,43),r,border_radius=5)
            pygame.draw.rect(s,(233,195,108) if selected else (82,105,87),r,2 if selected else 1,border_radius=5)
            t(('导弹：' if v['independent_missiles'] and guided(a) else '')+a['name'],(r.x+10,r.y+7),16,(241,230,196))
            t(f"{a['type']} · 近距穿深 {a['penetration'][0]:g} mm",(r.x+10,r.y+29),14,(166,191,164))
        a=v['ammo_options'][p.ammo_index(v['id'])]
        t(f"选中：{a['name']} · 1000 m 穿深 {a['penetration'][3]:g} mm",(640,442),16,(229,210,157))
        t(f"初速 {a['velocity']:g} m/s" if a.get('velocity') else '弹带初速：未在规格表列出，飞行速度采用模拟值',(640,470),14,(173,196,173))
        t(('独立导弹：'+v['ammo_options'][p.missile_index(v['id'])]['name']+' · 与机炮分别装填') if v['independent_missiles'] else '动能弹随距离衰减；破甲弹由装甲结构防护；榴弹产生破片',(640,495),14,(173,196,173))

from Aviation import install_garage
install_garage(Garage)
