"""FMOD event playback with an embedded runtime and optional installed banks."""
import ctypes as C, os, glob, struct,re,sys
from WTEventMap import EVENTS
P=C.c_void_p
class ExInfo(C.Structure):
    _fields_=[('cbsize',C.c_int),('length',C.c_uint),('fileoffset',C.c_uint),('numchannels',C.c_int),('defaultfrequency',C.c_int),('format',C.c_int),('decodebuffersize',C.c_uint),('initialsubsound',C.c_int),('numsubsounds',C.c_int),('inclusionlist',P),('inclusionlistnum',C.c_int),('pcmreadcallback',P),('pcmsetposcallback',P),('nonblockcallback',P),('dlsname',P),('encryptionkey',P),('maxpolyphony',C.c_int),('userdata',P),('suggestedsoundtype',C.c_int),('fileuseropen',P),('fileuserclose',P),('fileuserread',P),('fileuserseek',P),('fileuserasyncread',P),('fileuserasynccancel',P),('fileuserdata',P),('filebuffersize',C.c_int),('channelorder',C.c_int),('initialsoundgroup',P),('initialseekposition',C.c_uint),('initialseekpostype',C.c_uint),('ignoresetfilesystem',C.c_int),('audioqueuepolicy',C.c_uint),('minmidigranularity',C.c_uint),('nonblockthreadid',C.c_int),('fsbguid',P),('resamplermethod',C.c_int)]
class SoundInfo(C.Structure):
    _fields_=[('name_or_data',P),('mode',C.c_uint),('exinfo',ExInfo),('subsoundindex',C.c_int),('keyhash',C.c_ulonglong)]
class ProgrammerSound(C.Structure):
    _fields_=[('name',C.c_char_p),('sound',P),('subsoundIndex',C.c_int)]
class ParameterDescription(C.Structure):
    _fields_=[('name',C.c_char_p),('id1',C.c_uint),('id2',C.c_uint),('minimum',C.c_float),('maximum',C.c_float),('default',C.c_float),('type',C.c_int),('flags',C.c_uint),('guid',C.c_byte*16)]
Callback=C.WINFUNCTYPE(C.c_int,C.c_uint,P,P)

def installations():
    from PortableAudio import discover_installations
    return discover_installations()

class BankPlayer:
    def __init__(self,installation=None):
        roots=installations();self.root=installation or (roots[0] if roots else None)
        bundled=os.path.join(getattr(sys,'_MEIPASS',os.path.dirname(os.path.abspath(__file__))),'fmod')
        if not os.path.isfile(os.path.join(bundled,'fmod.dll')):bundled=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','work','portable_fmod'))
        self.bundled=bundled
        self.root=self.root or os.path.dirname(bundled)
        sdks=[sdk for base in dict.fromkeys((os.environ.get('ProgramFiles(x86)',r'C:\Program Files (x86)'),os.environ.get('ProgramFiles',r'C:\Program Files'))) for sdk in glob.glob(os.path.join(base,'FMOD SoundSystem','*'))]
        sdk=next((x for x in sdks if os.path.isfile(os.path.join(x,'api','studio','lib','x64','fmodstudio.dll')) and os.path.isfile(os.path.join(x,'api','core','lib','x64','fmod.dll'))),None)
        self.dll_dirs=[]
        if os.path.isfile(os.path.join(bundled,'fmod.dll')) and os.path.isfile(os.path.join(bundled,'fmodstudio.dll')):
            self.dll_dirs=[os.add_dll_directory(bundled)]
            self.core=C.WinDLL(os.path.join(bundled,'fmod.dll'));self.lib=C.WinDLL(os.path.join(bundled,'fmodstudio.dll'))
            with open(os.path.join(bundled,'version.txt')) as source:header=int(source.read())
            self.runtime=bundled
        elif sdk:
            core_dir=os.path.join(sdk,'api','core','lib','x64');studio_dir=os.path.join(sdk,'api','studio','lib','x64')
            self.dll_dirs=[os.add_dll_directory(core_dir),os.add_dll_directory(studio_dir)]
            self.core=C.WinDLL(os.path.join(core_dir,'fmod.dll'));self.lib=C.WinDLL(os.path.join(studio_dir,'fmodstudio.dll'))
            with open(os.path.join(sdk,'api','core','inc','fmod_common.h'),encoding='utf-8') as f:header=int(re.search(r'#define\s+FMOD_VERSION\s+(0x[0-9a-fA-F]+)',f.read())[1],16)
            self.runtime=sdk
        else:
            self.dll_dirs=[os.add_dll_directory(os.path.join(self.root,'win64'))]
            self.core=C.WinDLL(os.path.join(self.root,'win64','fmod64.dll'));self.lib=C.WinDLL(os.path.join(self.root,'win64','fmodstudio64.dll'));header=None;self.runtime=self.root
        self.system=P();self.banks=[];self.events={};self.instance=None;self.deployment_queue=[];self.deployment_active=False;self.alarm_instance=None;self.loaded_paths=set();self.catalog={};self.event_banks={};self.language='zh';self.load_errors={}
        version=P();self.core.FMOD_System_Create.argtypes=[C.POINTER(P),C.c_uint] if header else [C.POINTER(P)]
        self.check(self.core.FMOD_System_Create(C.byref(version),header) if header else self.core.FMOD_System_Create(C.byref(version)))
        v=C.c_uint();modern=bool(header and header>=0x20400)
        self.core.FMOD_System_GetVersion.argtypes=[P,C.POINTER(C.c_uint),C.POINTER(C.c_uint)] if modern else [P,C.POINTER(C.c_uint)]
        self.check(self.core.FMOD_System_GetVersion(version,C.byref(v),None) if modern else self.core.FMOD_System_GetVersion(version,C.byref(v)))
        self.core.FMOD_System_Release.argtypes=[P];self.core.FMOD_System_Release(version)
        self.call('System_Create',[C.POINTER(P),C.c_uint],C.byref(self.system),v.value)
        self.call('System_Initialize',[P,C.c_int,C.c_uint,C.c_uint,P],self.system,64,4,0,None)
        self.core_system=P();self.call('System_GetCoreSystem',[P,C.POINTER(P)],self.system,C.byref(self.core_system))
        self.resolved_samples=[];self.last_error='';self.effect_instance=None;self.callback=Callback(self.programmer_sound)
    def programmer_sound(self,kind,event,parameters):
        props=C.cast(parameters,C.POINTER(ProgrammerSound)).contents
        try:
            if kind==0x80:
                info=SoundInfo();info.exinfo.cbsize=C.sizeof(ExInfo)
                self.call('System_GetSoundInfo',[P,C.c_char_p,C.POINTER(SoundInfo)],self.system,props.name,C.byref(info))
                sound=P();f=self.core.FMOD_System_CreateSound;f.argtypes=[P,P,C.c_uint,C.POINTER(ExInfo),C.POINTER(P)]
                self.check(f(self.core_system,info.name_or_data,info.mode|0x200,C.byref(info.exinfo),C.byref(sound)))
                props.sound=sound;props.subsoundIndex=info.subsoundindex;self.resolved_samples.append(props.name.decode('utf-8'));self.resolved_samples=self.resolved_samples[-32:]
            elif kind==0x100 and props.sound:
                f=self.core.FMOD_Sound_Release;f.argtypes=[P];self.check(f(props.sound))
            return 0
        except (ValueError,OSError) as e:self.last_error=str(e);return 0
    @staticmethod
    def check(result):
        if result:raise ValueError('FMOD 错误 '+str(result)+'（音效包或播放库版本可能不匹配）')
    def call(self,name,types,*args):
        f=getattr(self.lib,'FMOD_Studio_'+name);f.argtypes=types;f.restype=C.c_int;self.check(f(*args))
    def load(self,path):
        normalized=os.path.normcase(os.path.abspath(path))
        if normalized in self.loaded_paths:return
        b=P();self.call('System_LoadBankFile',[P,C.c_char_p,C.c_uint,C.POINTER(P)],self.system,os.fsencode(path),0,C.byref(b))
        self.banks.append(b);self.loaded_paths.add(normalized)
        count=C.c_int();self.call('Bank_GetEventCount',[P,C.POINTER(C.c_int)],b,C.byref(count))
        array=(P*max(1,count.value))();self.call('Bank_GetEventList',[P,C.POINTER(P),C.c_int,C.POINTER(C.c_int)],b,array,len(array),C.byref(count))
        for event in array[:count.value]:
            buffer=C.create_string_buffer(4096);n=C.c_int()
            try:self.call('EventDescription_GetPath',[P,C.c_char_p,C.c_int,C.POINTER(C.c_int)],event,buffer,len(buffer),C.byref(n))
            except ValueError:continue
            key=buffer.value.decode('utf-8');self.events[key]=event
            self.event_banks[key]=next((name for name,file in self.catalog.items() if os.path.normcase(os.path.abspath(file))==normalized),os.path.basename(path).lower())
    def import_pack(self,path):
        folder=path if os.path.isdir(path) else os.path.dirname(path)
        custom=sorted(glob.glob(os.path.join(folder,'**','*.bank'),recursive=True))
        if not custom:raise ValueError('文件夹中没有 .bank')
        # Some VWS packs ship alternative copies of the same bank with a
        # language prefix. They share event GUIDs and must replace the original,
        # rather than loading together with it (FMOD ERR_EVENT_ALREADY_LOADED).
        variants={}
        for file in custom:
            match=re.match(r'^(Chinese|English|Japanese)_(aircraft_gui\.(?:assets\.)?bank)$',os.path.basename(file),re.I)
            if match:
                code={'chinese':'zh','english':'en','japanese':'jp'}[match[1].lower()]
                variants.setdefault(code,{})[match[2].lower()]=file
        complete={code:files for code,files in variants.items() if len(files)==2}
        selected=next((code for code in (self.language,'jp' if self.language=='ja' else self.language,'zh','en','jp') if code in complete),None)
        custom=[file for file in custom if not re.match(r'^(Chinese|English|Japanese)_aircraft_gui\.',os.path.basename(file),re.I)]
        baseline=sorted(glob.glob(os.path.join(self.bundled,'banks','*.bank')))
        original=sorted(glob.glob(os.path.join(self.root,'sound','*.bank')))
        # Register every bank, including all language/sample variants. Only event
        # metadata is loaded now; large sample banks are loaded when used.
        self.catalog={os.path.basename(f).lower():f for f in baseline}
        self.catalog.update({os.path.basename(f).lower():f for f in original})
        self.catalog.update({os.path.basename(f).lower():f for f in custom})
        if selected:self.catalog.update(complete[selected])
        custom_paths={os.path.normcase(os.path.abspath(file)) for file in custom}
        if selected:custom_paths.update(os.path.normcase(os.path.abspath(file)) for file in complete[selected].values())
        self.custom_names={name for name,file in self.catalog.items() if os.path.normcase(os.path.abspath(file)) in custom_paths}
        self.languages=sorted({m.group(1) for name in self.catalog if (m:=re.match(r'^_(?:crew_dialogs_(?:ground|common|naval)|dialogs|infantry_voices_narrator)_(.+?)\.(?:assets\.)?bank$',name))})
        self.languages=sorted(set(self.languages)|set(complete))
        names=sorted(self.catalog,key=lambda n:(not n.endswith('.strings.bank'),n!='masterbank.bank',n))
        for name in names:
            if '.assets.bank' in name or '.asset.bank' in name or name.startswith('_'):continue
            try:self.load(self.catalog[name])
            except ValueError as e:self.load_errors[name]=str(e)
        for event_path,(guid,key) in EVENTS.items():
            event=P()
            try:self.call('System_GetEvent',[P,C.c_char_p,C.POINTER(P)],self.system,guid.encode(),C.byref(event))
            except ValueError:continue
            self.events.setdefault(event_path,event)
        self.update();return len(self.events)
    def prepare_samples(self,event_path):
        name=self.event_banks.get(event_path,'crew_dialogs_ground.bank' if '/dialogs_crew_ground/' in event_path else 'aircraft_gui.bank')
        family=name[:-5]
        needed=['masterbank.assets.bank',family+'.assets.bank']
        families=[family] if family in ('crew_dialogs_ground','crew_dialogs_common','crew_dialogs_naval','dialogs','infantry_voices_narrator') else []
        if 'crew' in family and 'crew_dialogs_common' not in families:families.append('crew_dialogs_common')
        for localized in families:
            language=next((code for code in (self.language,'en','zh') if '_'+localized+'_'+code+'.bank' in self.catalog),None)
            if language:needed+=['_'+localized+'_'+language+'.bank','_'+localized+'_'+language+'.assets.bank']
        for item in needed:
            file=self.catalog.get(item)
            if file:self.load(file)
    @property
    def busy(self):
        if not self.instance:return False
        state=C.c_int();self.call('EventInstance_GetPlaybackState',[P,C.POINTER(C.c_int)],self.instance,C.byref(state))
        return state.value!=2
    def play(self,key,volume=.55):
        if self.deployment_active:
            if key=='voice_missile_warning':self.stop()
            else:return False
        matches=[p for p,(guid,eventkey) in EVENTS.items() if eventkey==key and p in self.events]
        aliases={'battle_start':('voice_message_commander_battle_start',),'ground_hit':('voice_message_driver_correction_hit',),'ground_destroyed':('voice_message_driver_correction_target_hit','voice_message_commander_correction_target_destroyed_nice_shot'),'voice_missile_warning':('vws_missile',)}
        aliases['ground_reload_start']=('voice_message_commander_reload',)
        aliases['voice_radar_warning']=('vws_lock',)
        for kind in ('AP','HE','HEAT','HESH','sabot','smoke','missile'):
            aliases['ground_load_'+kind]=('voice_message_commander_load_'+kind,)
            aliases['ground_ready_'+kind]=('voice_message_loader_load_'+kind,)
        matches+= [p for p in self.events if p.rsplit('/',1)[-1] in aliases.get(key,()) and p not in matches]
        if not matches:return False
        # Medium crew urgency; aircraft warning voice follows aircraft country.
        matches.sort(key=lambda p:(self.event_banks.get(p) not in self.custom_names,'/'+getattr(self,'voice_family','betty')+'/' not in p if key in ('voice_missile_warning','voice_radar_warning') else '/med/' not in p,p))
        return self.play_path(matches[0],volume)
    def play_effect(self,key,volume=.55):
        paths={'radar_scan':'alarm_spin_scan','rwr_search':'alarm_con_scan','rwr_lock':'alarm_radar','radar_lock':'alarm_radar','missile_warning':'alarm_radar'}
        path='event:/aircraft/gui/'+paths.get(key,'')
        event=self.events.get(path)
        if not event:return False
        family=self.event_banks.get(path,'').removesuffix('.bank')
        if family+'.assets.bank' not in self.catalog:return False
        self.prepare_samples(path);self.stop_effect();instance=P()
        self.call('EventDescription_CreateInstance',[P,C.POINTER(P)],event,C.byref(instance))
        self.effect_instance=instance
        # WT sets these event parameters in-game. FMOD's event volume does
        # not replace the bank's own 'volume' parameter (default: silence).
        values={'volume':1.,'track':1. if key in ('rwr_lock','radar_lock','missile_warning') else 0.,'launch':1. if key in ('radar_lock','missile_warning') else 0.}
        count=C.c_int()
        self.call('EventDescription_GetParameterDescriptionCount',[P,C.POINTER(C.c_int)],event,C.byref(count))
        for index in range(count.value):
            parameter=ParameterDescription()
            self.call('EventDescription_GetParameterDescriptionByIndex',[P,C.c_int,C.POINTER(ParameterDescription)],event,index,C.byref(parameter))
            name=parameter.name.decode()
            if name in values:
                value=max(parameter.minimum,min(parameter.maximum,values[name]))
                self.call('EventInstance_SetParameterByName',[P,C.c_char_p,C.c_float,C.c_int],instance,parameter.name,value,1)
        self.call('EventInstance_SetVolume',[P,C.c_float],instance,volume)
        self.call('EventInstance_Start',[P],instance);self.update();return True
    def stop_effect(self):
        if self.effect_instance:
            self.call('EventInstance_Stop',[P,C.c_int],self.effect_instance,1)
            self.call('EventInstance_Release',[P],self.effect_instance);self.effect_instance=None
    def play_path(self,path,volume=.55):
        effects={'alarm_spin_scan':'radar_scan','alarm_con_scan':'rwr_search','alarm_radar':'rwr_lock','alarm_launch_detected':'radar_lock'}
        if path.startswith('event:/aircraft/gui/') and path.rsplit('/',1)[-1] in effects:
            return self.play_effect(effects[path.rsplit('/',1)[-1]],volume)
        event=self.events.get(path)
        if not event:return False
        family=self.event_banks.get(path,'').removesuffix('.bank')
        if family.startswith('aircraft_') and family+'.assets.bank' not in self.catalog:return False
        self.last_error=''
        self.prepare_samples(path)
        self.stop(cancel_sequence=False);instance=P()
        self.call('EventDescription_CreateInstance',[P,C.POINTER(P)],event,C.byref(instance));self.instance=instance
        self.call('EventInstance_SetCallback',[P,Callback,C.c_uint],instance,self.callback,0x180)
        self.call('EventInstance_SetVolume',[P,C.c_float],instance,volume)
        self.call('EventInstance_Start',[P],instance);self.update();return True
    @property
    def can_alarm(self):return 'aircraft_ambient.assets.bank' in self.catalog
    def set_alarm(self,active,volume=.55):
        active=bool(active and self.can_alarm)
        if not active:
            if self.alarm_instance:
                self.call('EventInstance_Stop',[P,C.c_int],self.alarm_instance,1)
                self.call('EventInstance_Release',[P],self.alarm_instance);self.alarm_instance=None
            return
        if not self.alarm_instance:
            path='event:/aircraft/ambient/air_defence_alarm';event=self.events.get(path)
            if not event:return
            self.prepare_samples(path);instance=P()
            self.call('EventDescription_CreateInstance',[P,C.POINTER(P)],event,C.byref(instance))
            # Keep the emitter at the listener so every player hears the alert,
            # regardless of vehicle position, camera, or distance from the bomber.
            class Vector(C.Structure):_fields_=[('x',C.c_float),('y',C.c_float),('z',C.c_float)]
            class Attributes(C.Structure):_fields_=[('position',Vector),('velocity',Vector),('forward',Vector),('up',Vector)]
            attributes=Attributes();attributes.forward.z=1;attributes.up.y=1
            try:
                self.call('EventInstance_Set3DAttributes',[P,C.POINTER(Attributes)],instance,C.byref(attributes))
                self.call('EventInstance_SetCallback',[P,Callback,C.c_uint],instance,self.callback,0x180)
                self.call('EventInstance_Start',[P],instance)
            except (ValueError,OSError):
                self.call('EventInstance_Release',[P],instance);raise
            self.alarm_instance=instance
        self.call('EventInstance_SetVolume',[P,C.c_float],self.alarm_instance,volume)
        state=C.c_int();self.call('EventInstance_GetPlaybackState',[P,C.POINTER(C.c_int)],self.alarm_instance,C.byref(state))
        if state.value==2:self.call('EventInstance_Start',[P],self.alarm_instance)
    def play_deployment(self,volume=.55):
        names=('voice_message_chief_battle_start','voice_message_driver_battle_ready','voice_message_gunner_battle_ready','voice_message_loader_battle_ready','voice_message_commander_battle_start')
        paths=[]
        for name in names:
            matches=sorted((p for p in self.events if p.rsplit('/',1)[-1]==name),key=lambda p:('/med/' not in p,p))
            if matches:paths.append(matches[0])
        self.stop();self.deployment_queue=[(p,volume) for p in paths[1:]];self.deployment_active=bool(paths)
        return bool(paths and self.play_path(paths[0],volume))
    def update(self):
        self.call('System_Update',[P],self.system)
        if self.instance and self.deployment_active:
            state=C.c_int();self.call('EventInstance_GetPlaybackState',[P,C.POINTER(C.c_int)],self.instance,C.byref(state))
            if state.value==2:
                if self.deployment_queue:
                    path,volume=self.deployment_queue.pop(0);self.play_path(path,volume)
                else:self.deployment_active=False
    def stop(self,cancel_sequence=True):
        if cancel_sequence:self.deployment_queue=[];self.deployment_active=False
        if self.instance:
            self.call('EventInstance_Stop',[P,C.c_int],self.instance,1)
            self.call('EventInstance_Release',[P],self.instance);self.instance=None
    def close(self):
        if self.system:self.call('System_Release',[P],self.system);self.system=None
