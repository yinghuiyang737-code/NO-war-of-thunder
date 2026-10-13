"""Daily completion and one persistent random unowned vehicle reward."""
import datetime,random,pygame
from PremiumVehicles import IDS
TASKS=(('kills','摧毁 5 辆敌方载具',5),('score','累计获得 1500 个人战斗分',1500),('battles','完成 2 场战斗',2))
class Daily:
    def __init__(self,profile,state=None):self.p=profile;self.state=state if isinstance(state,dict) else {};self.refresh()
    def refresh(self):
        today=datetime.date.today().isoformat()
        if self.state.get('date')!=today:self.state=dict(date=today,kills=0,score=0,battles=0,claimed=False,reward=None)
    def to_dict(self):self.refresh();return dict(self.state)
    @property
    def complete(self):self.refresh();return all(self.state.get(k,0)>=n for k,label,n in TASKS)
    def report(self,g):
        self.refresh()
        if getattr(g,'daily_reported',False) or g.state not in ('win','lose'):return
        g.daily_reported=True
        for k,value in [('kills',getattr(g,'daily_kills',0)),('score',max(0,g.score)),('battles',1)]:self.state[k]=self.state.get(k,0)+value
        self.p.save()
    def claim(self):
        if not self.complete or self.state.get('claimed'):return None
        pool=[k for k in IDS if k not in self.p.unlocked]
        if not pool:return None
        prior=dict(self.state);reward=random.SystemRandom().choice(pool);self.p.unlocked.add(reward);self.state.update(claimed=True,reward=reward)
        if not self.p.save():self.p.unlocked.remove(reward);self.state=prior;return None
        return reward
    def claim_selected(self,ident):
        if not getattr(self.p,'internal_premium_claim',False) or ident not in IDS or ident in self.p.unlocked:return None
        self.p.unlocked.add(ident)
        if not self.p.save():self.p.unlocked.remove(ident);return None
        return ident
class Panel:
    def __init__(self,garage):self.g=garage;self.open=False;self.selected=IDS[0];self.notice='完成全部每日任务后，随机领取一辆未拥有的高级载具'
    def card(self,i):
        width=max(300,(self.g.screen.get_width()-465)//2)
        return pygame.Rect(430+(i%2)*(width+10),115+(i//2)*140,width,125)
    @staticmethod
    def button():return pygame.Rect(945,__import__("WindowLayout").CANVAS[1]-37,190,30)
    def event(self,e):
        if e.type==pygame.KEYDOWN and e.key==pygame.K_ESCAPE:self.open=False
        if e.type!=pygame.MOUSEBUTTONDOWN or e.button!=1:return
        pos=e.pos;p=self.g.profile
        if pygame.Rect(35,735,250,45).collidepoint(pos):self.open=False;return
        if pygame.Rect(35,360,355,50).collidepoint(pos):
            reward=p.daily.claim_selected(self.selected) if getattr(p,'internal_premium_claim',False) else p.daily.claim()
            from Garage import VEHICLES
            self.notice='已获得 '+VEHICLES[reward]['name'] if reward else '此载具已拥有，或保存失败' if getattr(p,'internal_premium_claim',False) else '尚未完成全部任务、今天已领取，或已集齐全部载具'
        for i,k in enumerate(IDS):
            if self.card(i).collidepoint(pos):self.selected=k
        if pygame.Rect(35,675,355,45).collidepoint(pos):
            from Garage import VEHICLES
            if self.selected not in p.unlocked:self.notice='先完成每日任务并获得此载具';return
            p.select_country(VEHICLES[self.selected]['country']);p.equip(self.selected);self.g.aviation=False;self.g.preview=self.selected;self.notice='已加入该国当前出战槽位'
    def draw(self):
        from Garage import VEHICLES,NATIONS,draw_tank_art
        g=self.g;s=g.screen;t=g.text;p=g.profile;daily=p.daily;daily.refresh();s.fill((22,29,27))
        t('每日任务 · 高级载具',(35,30),30);t('独立于普通科技线 · 每天一次 · 随机未拥有载具',(35,78),18,(222,199,134))
        for i,(key,label,total) in enumerate(TASKS):
            y=135+i*65;value=min(total,daily.state.get(key,0));t(label,(35,y),18);t(f'{value}/{total}',(35,y+25),16,(146,215,166))
            pygame.draw.rect(s,(50,63,51),(150,y+31,235,7));pygame.draw.rect(s,(160,194,124),(150,y+31,int(235*value/total),7))
        claim_label=('已拥有所选载具' if self.selected in p.unlocked else '内部领取 · '+VEHICLES[self.selected]['name']) if getattr(p,'internal_premium_claim',False) else '已集齐全部高级载具' if all(k in p.unlocked for k in IDS) else '今天已领取' if daily.state.get('claimed') else '领取随机高级载具'
        g.button(pygame.Rect(35,360,355,50),claim_label,getattr(p,'internal_premium_claim',False) or daily.complete)
        t('高级载具只可加入所属国家编成',(35,430),16,(184,202,183))
        chosen=VEHICLES[self.selected]
        for i,k in enumerate(IDS):
            v=VEHICLES[k];r=self.card(i);g.button(r,'',k==self.selected)
            draw_tank_art(s,v,(r.x+50,r.y+67),.55,-15)
            t(NATIONS[v['country']]['name']+' · '+v['name'],(r.x+110,r.y+12),18,(228,202,130),max_width=r.w-118)
            t(f"{v['rank']} 级 · BR {v['br']:.1f} · "+('已拥有' if k in p.unlocked else '每日任务随机获得'),(r.x+110,r.y+47),14,max_width=r.w-118)
            t(f"速度 {v['forward_kph']:g} km/h · 正面 {v['armor'][0]:g} mm · 装填 {v['reload']:g}s",(r.x+110,r.y+77),14,max_width=r.w-118)
        for i,line in enumerate([chosen['name'],chosen['research_data']['primary_weapon_name'],' / '.join(a['name'] for a in chosen['ammo_options']),f"正面车体 {chosen['armor'][0]:g} mm / 炮塔 {chosen['turret_armor'][0]:g} mm",'所有模型与操控采用 2D 简化']):
            t(line[:35],(35,475+i*32),16,(193,209,184))
        g.button(pygame.Rect(35,675,355,45),'加入所属国家当前出战槽位',self.selected in p.unlocked)
        g.button(pygame.Rect(35,735,250,45),'返回机库')
        t(self.notice[:68],(430,733),16,(222,202,135))
