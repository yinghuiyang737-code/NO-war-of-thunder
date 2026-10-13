"""Per-vehicle gameplay response, kept separate from sourced traverse specifications."""
def configure(v):
    reference=v['turret_slew'];modern=v.get('stabilizer')==2 and v.get('br',0)>=8
    factor=(1.85+min(.25,max(0,v.get('br',8)-8)*.055)) if modern else 1.25
    if v['branch']==3:factor=1.30
    if v.get('artillery'):factor=1.5
    if v['model'][2]=='casemate':factor=1.1
    v['aim_response_slew']=round(reference*factor,2)
