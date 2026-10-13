from WindowLayout import preferred_size,fit,blit_scaled,mouse_point

def run(api):
    assert preferred_size((2560,1440))==(1600,1025)
    width,height=preferred_size((1920,1080));assert width>1280 and height>820 and height<=990
    small=preferred_size((1366,768));assert small[0]<1366 and small[1]<768
    rendered=api['fonts'][16].render('Ctrl + Shift + Alt + Mouse Button 1 / custom binding '*4,True,(240,240,240))
    assert fit(rendered,460).get_width()==460
    canvas=api['pygame'].Surface((1280,820));canvas.fill((87,123,154))
    target=api['pygame'].Surface((1600,1025));rect=blit_scaled(canvas,target)
    assert rect.size==(1280,820) and tuple(target.get_at(rect.topleft))[:3]==(87,123,154)
    assert mouse_point((800,512.5),(1600,1025))==(640,410)
    target=api['pygame'].Surface((1700,1000));rect=blit_scaled(canvas,target)
    assert mouse_point(rect.center,target.get_size())==(640,410)
    assert tuple(target.get_at((0,0)))[:3]==(0,0,0)
    g=api['Game']();target=api['Tank']((2000,2000),enemy=True)
    g.hitview=(target,dict(kind='未击穿',modules=[],point=api['V'](target.p),line=(api['V'](-30,0),api['V'](0,0))),g.time+4)
    background=(77,99,123);api['screen'].fill(background);g.draw_hit()
    assert tuple(api['screen'].get_at((1021,301)))[:3]==background
    g.controls.open=True;g.controls.draw(api['screen'],api['text']);g.controls.open=False
    print('PASS: larger monitor-bounded window sizes, long-binding text fitting, transparent hit-replay background and settings drawing')

    import WindowLayout
    from AutoUpdate import Updater
    from DailyRewards import Panel
    garage=api['Garage'](api['screen'],api['text'])
    for size in ((1280,820),(1600,1025)):
        WindowLayout.CANVAS=size
        controls_rect=api['pygame'].Rect(size[0]-135,size[1]-37,125,30)
        utilities=[Updater(frozen=False).button(),Panel.button(),api['pygame'].Rect(510,size[1]-37,285,30),controls_rect]
        navigation=[garage.garage_button(),garage.tech_button(),garage.data_button(),api['pygame'].Rect(790,20,112,40),api['pygame'].Rect(912,20,112,40),garage.start_button()]
        assert all(not a.colliderect(b) for i,a in enumerate(utilities+navigation) for b in (utilities+navigation)[i+1:])
    WindowLayout.CANVAS=api['screen'].get_size()
    print('PASS: menu update, sound, rewards, bindings and ground/air navigation have separate clickable areas')

    saved={k:api[k] for k in ('screen','W','H')}
    try:
        for size in ((1280,820),(1600,1025)):
            api['screen']=api['pygame'].Surface(size);api['W'],api['H']=size;WindowLayout.select(api['screen'])
            garage.screen=api['screen']
            countries=garage.country_buttons();slots=garage.slot_buttons()
            assert countries[0][1].y==size[1]-262
            assert max(r.bottom for _,r in slots)==size[1]-49
            assert all(r.bottom<size[1]-37 for _,r in slots)
            assert all(not a.colliderect(b) for _,a in countries for _,b in slots)
            garage.aviation=False;garage.draw();garage.aviation=True;garage.draw()
            controls=g.controls;controls.open=False;api['screen'].fill((0,0,0));controls.draw(api['screen'],api['text'])
            button=api['pygame'].Rect(size[0]-135,size[1]-37,125,30)
            pixels=api['pygame'].surfarray.array3d(api['screen'].subsurface(button))
            assert ((pixels[:,:,0]>150)&(pixels[:,:,1]>150)).sum()>80,'settings label must have visible full-size glyphs'
            controls.event(api['pygame'].event.Event(api['pygame'].MOUSEBUTTONDOWN,button=1,pos=button.center),'garage')
            assert controls.open;controls.open=False
    finally:
        api.update(saved);WindowLayout.select(api['screen'])
    print('PASS: ground/air national roster bottom anchors, footer clearance and visible clickable settings text at both window sizes')
