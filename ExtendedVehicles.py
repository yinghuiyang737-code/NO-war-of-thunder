# Extensions preserve every existing vehicle ID and save-game reference.
ADDITIONS={
 'us':{0:['M551','M3 Bradley','M3A3 Bradley','HSTV-L','M1128'],2:['M50','M56','M901','M113 TOW','M10 Booker'],3:['M13 MGMC','M16 MGMC','M19A1','M42','M163','M247','LAV-AD','ADATS']},
 'de':{0:['Marder 1A1','Begleitpanzer 57','TAM','Radkampfwagen 90','PUMA','PUMA VJTF'],2:['Jagdpanther','Kanonenjagdpanzer','Raketenjagdpanzer 2','Jaguar 1','Wiesel 1A2'],3:['Flakpanzer I','Wirbelwind','Ostwind II','ZSU-57-2 (GER)','Gepard','Gepard 1A2','FlaRakPz 1','FlaRakRad']},
 'ussr':{0:['BMP-1','BMP-2','BMP-3','BMP-2M','2S38'],2:['IS-3','SU-100','ASU-85','Object 120','2S25','2S25M'],3:['GAZ-AAA (4M)','ZSU-37','ZSU-57-2','ZSU-23-4','Strela-10M','2S6 Tunguska','Pantsir-S1']},
 'cn':{0:['Type 63','ZBD86','ZBD04A','ZLT11'],1:['ZTZ88A','ZTZ96','ZTZ96A','ZTZ99-II','ZTZ99-III','ZTZ99A'],2:['Type 60','PTZ89','AFT09','QN506'],3:['ZSD63','PGZ80','PGZ88','PGZ04A','PGZ09','Tor-M1']}}
# name: half length, half width, turret silhouette, offset, radius, gun length;
# traits N night, T thermal, S stabilized, D dual drive, R radar, M missile; primary gun type.
DETAILS={
'M551':((43,23,'round',1,19,69),'NS','gun'),'M3 Bradley':((48,24,'box',4,18,58),'NTSDM','auto'),
'M3A3 Bradley':((49,25,'box',4,19,59),'NTSDM','auto'),'HSTV-L':((43,22,'box',1,17,73),'NTSD','auto'),
'M1128':((54,25,'wheel',-1,15,88),'NTS','gun'),'M50':((34,17,'open',1,14,42),'','gun'),
'M56':((34,17,'open',8,12,67),'','gun'),'M901':((44,22,'launcher',0,17,31),'NTDM','sam'),
'M113 TOW':((43,22,'launcher',2,13,31),'NDM','sam'),'M10 Booker':((52,25,'box',-1,24,82),'NTSD','gun'),
'M13 MGMC':((45,20,'halftrack',-15,12,38),'','auto'),'M16 MGMC':((45,20,'halftrack',-15,14,38),'','auto'),
'M19A1':((43,22,'open',-12,18,57),'','auto'),'M42':((46,23,'open',-5,19,58),'','auto'),
'M163':((43,22,'open',2,14,39),'R','auto'),'M247':((54,26,'box',0,24,69),'NRD','auto'),
'LAV-AD':((49,23,'wheel',-3,18,53),'NTSRM','auto'),'ADATS':((49,25,'launcher',-1,20,52),'NTRDM','auto'),
'Marder 1A1':((49,25,'box',7,12,46),'ND','auto'),'Begleitpanzer 57':((49,25,'open',4,17,64),'NTDM','auto'),
'TAM':((50,24,'box',2,20,80),'NSD','gun'),'Radkampfwagen 90':((55,26,'wheel',0,22,88),'NS','gun'),
'PUMA':((52,26,'box',2,15,61),'NTSD','auto'),'PUMA VJTF':((53,27,'box',2,16,62),'NTSDM','auto'),
'Jagdpanther':((54,26,'casemate',10,23,91),'','gun'),'Kanonenjagdpanzer':((48,24,'casemate',6,21,76),'ND','gun'),
'Raketenjagdpanzer 2':((47,24,'launcher',-1,15,26),'NDM','sam'),'Jaguar 1':((48,24,'launcher',-2,16,27),'NTDM','sam'),
'Wiesel 1A2':((29,15,'launcher',1,9,29),'NTM','sam'),'Flakpanzer I':((34,18,'open',-4,12,35),'','auto'),
'Wirbelwind':((45,24,'open',0,20,47),'','auto'),'Ostwind II':((45,24,'open',0,20,57),'','auto'),
'ZSU-57-2 (GER)':((49,25,'open',0,25,76),'','auto'),'Gepard':((51,25,'box',0,22,74),'NRD','auto'),
'Gepard 1A2':((52,25,'box',0,22,75),'NTRDM','auto'),'FlaRakPz 1':((49,25,'launcher',0,20,35),'NRDM','sam'),
'FlaRakRad':((65,26,'truck',-10,23,36),'NTRM','sam'),
'BMP-1':((48,23,'round',6,13,46),'N','gun'),'BMP-2':((49,23,'round',3,15,58),'NS','auto'),
'BMP-3':((50,24,'round',1,17,67),'NTS','gun'),'BMP-2M':((49,24,'round',3,16,59),'NTSM','auto'),
'2S38':((50,24,'box',1,18,78),'NTS','auto'),'IS-3':((53,26,'round',0,22,88),'','gun'),
'SU-100':((48,24,'casemate',8,22,82),'','gun'),'ASU-85':((44,22,'casemate',4,19,73),'N','gun'),
'Object 120':((57,25,'round',-12,23,113),'N','gun'),'2S25':((53,24,'round',-3,21,96),'NS','gun'),
'2S25M':((54,25,'round',-3,22,97),'NTS','gun'),'GAZ-AAA (4M)':((44,18,'truck',-14,12,33),'','auto'),
'ZSU-37':((41,20,'open',-6,16,49),'','auto'),'ZSU-57-2':((49,25,'open',0,25,76),'','auto'),
'ZSU-23-4':((46,24,'box',4,21,54),'NR','auto'),'Strela-10M':((45,22,'launcher',-3,17,31),'NM','sam'),
'2S6 Tunguska':((57,26,'box',0,24,73),'NSRM','auto'),'Pantsir-S1':((67,27,'truck',-14,24,63),'NTRM','auto'),
'Type 63':((49,24,'round',1,17,64),'N','gun'),'ZBD86':((48,23,'round',6,13,47),'N','gun'),
'ZBD04A':((52,25,'round',0,18,69),'NTS','gun'),'ZLT11':((56,26,'wheel',0,21,90),'NTS','gun'),
'ZTZ88A':((50,25,'round',0,23,88),'NS','gun'),'ZTZ96':((51,25,'box',0,24,93),'NS','gun'),
'ZTZ96A':((52,26,'wedge',0,25,94),'NTS','gun'),'ZTZ99-II':((55,27,'wedge',0,26,96),'NTS','gun'),
'ZTZ99-III':((56,27,'wedge',0,27,97),'NTS','gun'),'ZTZ99A':((58,28,'wedge',0,28,99),'NTSD','gun'),
'Type 60':((39,20,'casemate',7,16,61),'','gun'),'PTZ89':((53,25,'box',-7,22,99),'NS','gun'),
'AFT09':((47,23,'launcher',-3,17,36),'NTM','sam'),'QN506':((49,25,'box',0,17,58),'NTSDM','auto'),
'ZSD63':((43,21,'open',-9,15,43),'','auto'),'PGZ80':((49,25,'open',0,24,76),'','auto'),
'PGZ88':((52,25,'box',0,23,73),'NR','auto'),'PGZ04A':((50,24,'box',1,21,58),'NTRM','auto'),
'PGZ09':((55,26,'box',0,24,78),'NTSRD','auto'),'Tor-M1':((55,26,'launcher',-3,25,32),'NRM','sam')}
def install(nations,shapes):
    for country,branches in ADDITIONS.items():
        for branch,names in branches.items():
            if branch==3:nations[country]['branches'].append(names)
            else:nations[country]['branches'][branch]+=names
    for name,(shape,traits,weapon) in DETAILS.items():shapes[name]=shape

def extend_config(v):
    name=v['name'];entry=DETAILS.get(name)
    v['weapon']='gun';v['radar']=False;v['missile']=False;v['missile_ground']=False;v['barrels']=1;v['wheel']=v['model'][2] in ('wheel','truck','halftrack')
    if not entry:return
    shape,traits,weapon=entry;v['weapon']=weapon;v['night']='N' in traits;v['thermal']='T' in traits;v['stabilizer']=2 if 'S' in traits else 0;v['dual']='D' in traits
    v['radar']='R' in traits;v['missile']='M' in traits;v['missile_ground']=v['missile'] and v['branch']!=3
    v['mg']=v['branch']!=3 and name not in {'M50','M56','M901','M113 TOW','Raketenjagdpanzer 2','Jaguar 1','Wiesel 1A2','AFT09'}
    v['barrels']=4 if name in {'M16 MGMC','Wirbelwind','ZSU-23-4','PGZ04A','GAZ-AAA (4M)'} else 2 if name in {'M19A1','M42','Ostwind II','ZSU-57-2','ZSU-57-2 (GER)','PGZ80','Gepard','Gepard 1A2','PGZ88','PGZ09','2S6 Tunguska','Pantsir-S1'} else 1
    if v['branch']!=1:
        v['armor']=(22 if v['branch']==3 else 50,16 if v['branch']==3 else 25,12)
        v['speed']=min(255,165+v['tier']*8);v['reverse']=90;v['turn']=82
        if name in {'IS-3','Jagdpanther'}:v['armor']=(120,80,40);v['speed']=115
    if weapon=='auto':v['reload']=.12 if v['branch']==3 else .2;v['pen']=min(155,40+v['tier']*10)
    elif weapon=='sam':v['reload']=3.5;v['pen']=0
    else:v['reload']=1.25;v['pen']=min(620,150+v['tier']*38)
    v['equipment']=[label for key,label in [('mg','机枪'),('night','夜视'),('thermal','热成像'),('dual','双流传动'),('radar','搜索雷达'),('missile','反坦克导弹' if v['missile_ground'] else '防空导弹')] if v[key]]
    if v['stabilizer']:v['equipment'].append('双向稳定')
    if weapon=='auto':v['equipment'].append('连发机关炮')
