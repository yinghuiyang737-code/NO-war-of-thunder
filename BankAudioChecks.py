"""Check real FMOD mixer output; playback state alone cannot detect silence."""
import ctypes as C,time
from WTBank import P

class Meter(C.Structure):
    _fields_=[('samples',C.c_int),('peak',C.c_float*32),('rms',C.c_float*32),('channels',C.c_short)]

def check_output(bank):
    def core(name,types,*args):
        function=getattr(bank.core,'FMOD_'+name);function.argtypes=types
        bank.check(function(*args))
    group=P();dsp=P()
    core('System_GetMasterChannelGroup',[P,C.POINTER(P)],bank.core_system,C.byref(group))
    core('ChannelGroup_GetDSP',[P,C.c_int,C.POINTER(P)],group,-1,C.byref(dsp))
    core('DSP_SetMeteringEnabled',[P,C.c_int,C.c_int],dsp,0,1)
    for key in ('radar_scan','rwr_search','rwr_lock','radar_lock','voice_radar_warning','voice_missile_warning'):
        bank.stop();bank.stop_effect()
        for _ in range(10):bank.update();time.sleep(.02)
        if key.startswith('voice'):assert bank.play(key,.05)
        else:assert bank.play_effect(key,.05)
        peak=0.
        for _ in range(40):
            bank.update();time.sleep(.02);meter=Meter()
            core('DSP_GetMeteringInfo',[P,P,C.POINTER(Meter)],dsp,None,C.byref(meter))
            peak=max(peak,max(meter.peak))
        assert peak>0.00001,(bank.language,key,'silent mixer output',peak)
    bank.stop();bank.stop_effect()
