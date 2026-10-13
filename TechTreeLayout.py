"""BR-ordered national research chains and rank-banded, BR-aligned cards."""
RANKS=('I','II','III','IV','V','VI','VII','VIII','IX')
def rating(d):return float(d.get('ground_br',d['br']))
def normalize(catalog):
    countries={d['country'] for d in catalog.values()}
    for country in countries:
        branches={d['branch'] for d in catalog.values() if d['country']==country and not d.get('premium')}
        for branch in branches:
            chain=sorted((d for d in catalog.values() if d['country']==country and d['branch']==branch and not d.get('premium')),key=lambda d:(rating(d),d.get('tier',0),d['id']))
            for i,d in enumerate(chain):
                d['parent']=chain[i-1]['id'] if i else None;d['tier']=i+1

def rows(catalog,country,branches,step=60,padding=34,ranks=RANKS,owned=()):
    entries={k:d for k,d in catalog.items() if d['country']==country and (not d.get('premium') or k in owned)}
    premium=any(d.get('premium') for d in entries.values());count=branches+int(premium)
    # Globally increasing BR keeps a low-rated card above every higher-rated card.
    by_br={}
    for k,d in entries.items():
        if not d.get('premium'):by_br.setdefault(rating(d),[]).append(k)
    bands={};level=0
    for br,ids in sorted(by_br.items()):
        ordinary=[entries[k] for k in ids if not entries[k].get('premium')]
        reference=ordinary or [entries[k] for k in ids]
        level=max(level,min(len(ranks)-1,min(RANKS.index(d['rank']) for d in reference)))
        bands.setdefault(level,[]).append((br,ids))
    for k,d in entries.items():
        if not d.get('premium'):continue
        band=min(len(ranks)-1,RANKS.index(d['rank']));br=rating(d)
        match=next((ids for value,ids in bands.get(band,[]) if value==br),None)
        if match is None:bands.setdefault(band,[]).append((br,[k]))
        else:match.append(k)
    result=[];y=0
    for index,rank in enumerate(ranks):
        groups=[[] for _ in range(count)];slot=0
        for br,ids in sorted(bands.get(index,[])):
            local=[[] for _ in range(count)]
            for k in sorted(ids,key=lambda k:(entries[k].get('tier',0),k)):
                d=entries[k];local[branches if d.get('premium') else d['branch']].append(k)
            height=max(map(len,local))
            for b in range(count):groups[b].extend(local[b]+[None]*(height-len(local[b])))
            slot+=height
        height=max(1,slot)*step+padding
        result.append((rank,y,height,groups));y+=height
    return result

def checks(api):
    from Aviation import AIRCRAFT
    for catalog,branches in ((api['VEHICLES'],6),(AIRCRAFT,None)):
        for country in api['NATIONS']:
            entries=[d for d in catalog.values() if d['country']==country and not d.get('premium')]
            for branch in {d['branch'] for d in entries}:
                chain=sorted((d for d in entries if d['branch']==branch),key=lambda d:d['tier'])
                for i,d in enumerate(chain):
                    assert d['parent']==(chain[i-1]['id'] if i else None),(country,d['name'])
                    if i:assert rating(chain[i-1])<=rating(d)
            count=branches or max(d['branch'] for d in entries)+1
            positions={k:y+i*60 for rank,y,h,groups in rows(catalog,country,count) for ids in groups for i,k in enumerate(ids) if k}
            for a in entries:
                if a['parent']:assert positions[a['parent']]<positions[a['id']]
                for b in entries:
                    if rating(a)<rating(b):assert positions[a['id']]<positions[b['id']],(a['name'],b['name'])
    from PremiumVehicles import IDS
    for k in IDS:
        d=api['VEHICLES'][k];assert not any(k in ids for _,__,___,groups in rows(api['VEHICLES'],d['country'],6) for ids in groups)
        r=rows(api['VEHICLES'],d['country'],6,owned={k});assert any(k in groups[-1] for rank,__,___,groups in r if rank==d['rank']) and all(len(groups)==7 for _,__,___,groups in r)
    import tempfile,os
    from Garage import Garage,Profile
    with tempfile.TemporaryDirectory() as tmp:
        profile=Profile(os.path.join(tmp,'progress.json'))
        garage=Garage(api['screen'],api['text'],profile);garage.tab='tech'
        for k in IDS:
            profile.country=api['VEHICLES'][k]['country'];profile.unlocked.add(k)
            for rank,y,h,groups in garage.rank_rows():
                if k in groups[-1]:garage.tech_row=min(garage.max_scroll(),y);break
            garage.draw();rect=dict(garage.nodes())[k];garage.click(rect.center);assert garage.preview==k
            assert profile.equip(k)
    print('PASS all nations ground/air/heli ascending BR, immediate predecessor research, global visual order, owned-only right-side rewards')
