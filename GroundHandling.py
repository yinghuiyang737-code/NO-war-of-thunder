"""Separate traction acceleration from responsive differential steering."""
def approach(value,target,amount):return value+max(-amount,min(amount,target-value))
def advance(t,goals,factor,dt):
    if not t.vehicle_id:
        largest=max((abs(target-getattr(t,attr)) for attr,target in goals.items()),default=0)
        blend=min(1,t.stats.get('acceleration',160)*dt/largest) if largest else 1
        for attr,target in goals.items():setattr(t,attr,getattr(t,attr)+(target-getattr(t,attr))*blend)
        return
    speed_limit=max(1,t.stats['speed']*factor)
    ratio=min(1,abs(t.speed)/speed_limit)
    acceleration=t.stats.get('acceleration',25)*factor*(1-.75*ratio*ratio)
    if len(goals)==2:
        centre=(t.left_speed+t.right_speed)/2;difference=(t.left_speed-t.right_speed)/2
        target=(goals['left_speed']+goals['right_speed'])/2;turn=(goals['left_speed']-goals['right_speed'])/2
        braking=abs(target)<abs(centre) or target*centre<0
        rate=max(65,speed_limit*.28) if braking else acceleration
        centre=approach(centre,target,rate*dt)
        difference=approach(difference,turn,t.stats.get('steering_acceleration',160)*factor*dt)
        t.left_speed=max(-speed_limit,min(speed_limit,centre+difference));t.right_speed=max(-speed_limit,min(speed_limit,centre-difference))
    else:
        for attr,target in goals.items():
            value=getattr(t,attr);rate=max(65,speed_limit*.28) if abs(target)<abs(value) or target*value<0 else acceleration
            setattr(t,attr,approach(value,target,rate*dt))
