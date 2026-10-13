"""Background GitHub Releases updater; only the fixed executable is replaced."""
import base64, hashlib, json, os, re, shutil, subprocess, sys, tempfile, threading,ctypes,time
from datetime import datetime,timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError

VERSION='2026.10.13.6'
BUILD_UTC='2026-10-13T19:13:24.931396+00:00'
REPOSITORY='yinghuiyang737-code/NO-war-of-thunder'
API='https://api.github.com/repos/'+REPOSITORY+'/releases/latest'
MAX_SIZE=256*1024*1024

def version(value):
    match=re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?',value or '')
    return tuple(int(x or 0) for x in match.groups()) if match else None

def release_asset(data,current=VERSION):
    newest=version(data.get('tag_name'))
    if newest is None:
        match=re.search(r'(?<![0-9])v?(\d+\.\d+\.\d+(?:\.\d+)?)(?![0-9.])',data.get('name','')+' '+data.get('body',''))
        if match:newest=version(match[1])
    if data.get('draft') or data.get('prerelease') or newest is not None and newest<=version(current):return None
    asset=next((a for a in data.get('assets',[]) if a.get('name')=='SteelWilderness.exe' and a.get('state')=='uploaded'),None)
    if asset is None:raise ValueError('新版尚未上传游戏 EXE')
    url=asset.get('browser_download_url','')
    if not url.startswith('https://github.com/'+REPOSITORY+'/releases/download/'):raise ValueError('更新文件来源不匹配')
    digest=asset.get('digest') or ''
    if not re.fullmatch(r'sha256:[0-9a-fA-F]{64}',digest):raise ValueError('新版缺少 SHA-256 校验，暂不安装')
    size=asset.get('size')
    if not isinstance(size,int) or not 1024<=size<=MAX_SIZE:raise ValueError('更新文件大小异常')
    return dict(url=url,size=size,digest=digest[7:].lower(),version='.'.join(map(str,newest)) if newest else data.get('tag_name','正式版'),unversioned=newest is None,updated=asset.get('updated_at'))

def request(url):return Request(url,headers={'User-Agent':'SteelWilderness/'+VERSION,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})

def verify(path,digest,size):
    if os.path.getsize(path)!=size:raise ValueError('更新下载不完整')
    sha=hashlib.sha256()
    with open(path,'rb') as f:
        head=f.read(64)
        if len(head)<64 or head[:2]!=b'MZ':raise ValueError('更新文件不是 Windows 程序')
        offset=int.from_bytes(head[60:64],'little')
        if not 64<=offset<=size-4:raise ValueError('更新程序格式异常')
        f.seek(offset)
        if f.read(4)!=b'PE\0\0':raise ValueError('更新程序格式异常')
        f.seek(0)
        for block in iter(lambda:f.read(1024*1024),b''):sha.update(block)
    if sha.hexdigest()!=digest:raise ValueError('更新校验失败，已保留当前版本')

def executable_version(path):
    if os.name!='nt':return None
    class Info(ctypes.Structure):
        _fields_=[(name,ctypes.c_uint32) for name in ('signature','structure','ms','ls','flags_mask','flags','os','type','subtype','date_ms','date_ls')]
    lib=ctypes.WinDLL('version',use_last_error=True)
    lib.GetFileVersionInfoSizeW.argtypes=[ctypes.c_wchar_p,ctypes.c_void_p];lib.GetFileVersionInfoSizeW.restype=ctypes.c_uint32
    lib.GetFileVersionInfoW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p]
    lib.VerQueryValueW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(ctypes.c_uint32)]
    size=lib.GetFileVersionInfoSizeW(path,None)
    if not size:return None
    data=ctypes.create_string_buffer(size)
    if not lib.GetFileVersionInfoW(path,0,size,data):return None
    pointer=ctypes.c_void_p();length=ctypes.c_uint32()
    if not lib.VerQueryValueW(data,'\\',ctypes.byref(pointer),ctypes.byref(length)) or length.value<ctypes.sizeof(Info):return None
    info=ctypes.cast(pointer,ctypes.POINTER(Info)).contents
    if info.signature!=0xfeef04bd:return None
    return (info.ms>>16,info.ms&65535,info.ls>>16,info.ls&65535)

def file_digest(path):
    sha=hashlib.sha256()
    with open(path,'rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):sha.update(chunk)
    return sha.hexdigest()

def wait_for_game(pid):
    if os.name!='nt' or pid<=0:return
    lib=ctypes.WinDLL('kernel32',use_last_error=True)
    lib.OpenProcess.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32];lib.OpenProcess.restype=ctypes.c_void_p
    lib.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint32];lib.WaitForSingleObject.restype=ctypes.c_uint32
    lib.CloseHandle.argtypes=[ctypes.c_void_p]
    handle=lib.OpenProcess(0x100000,False,pid)
    if not handle:return
    try:
        if lib.WaitForSingleObject(handle,120000)!=0:raise ValueError('游戏仍在运行，更新未替换')
    finally:lib.CloseHandle(handle)

def save_status(target,phase,digest,message=''):
    with open(target+'.update-state.json','w',encoding='utf-8') as out:
        json.dump(dict(phase=phase,digest=digest,message=message),out,ensure_ascii=False)

def retry_copy(source,target):
    for attempt in range(60):
        try:shutil.copy2(source,target);return
        except PermissionError:
            if attempt==59:raise
            time.sleep(.5)

def apply_update(target,payload,digest,size,parent_pid):
    """The temporary copy of this EXE handles replacement after the game exits."""
    target=os.path.abspath(target);payload=os.path.abspath(payload);backup=target+'.rollback.tmp'
    backed_up=False;replaced=False
    try:
        if os.path.basename(target).lower()!='steelwilderness.exe':raise ValueError('更新目标名称不匹配')
        verify(payload,digest,int(size));wait_for_game(int(parent_pid))
        shutil.copy2(target,backup);backed_up=True
        replaced=True;retry_copy(payload,target);verify(target,digest,int(size))
        save_status(target,'installed',digest)
        subprocess.Popen([target],cwd=os.path.dirname(target),creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        try:os.remove(backup);backed_up=False
        except OSError:pass
        return 0
    except Exception as error:
        if replaced and backed_up:
            try:retry_copy(backup,target);os.remove(backup);backed_up=False
            except OSError:pass
        try:save_status(target,'failed',digest,str(error))
        except OSError:pass
        try:subprocess.Popen([target],cwd=os.path.dirname(target),creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        except OSError:pass
        return 1
    finally:
        try:os.remove(payload)
        except OSError:pass

def run_update_helper():
    if len(sys.argv)!=7:return 2
    return apply_update(*sys.argv[2:])

class Updater:
    def __init__(self,frozen=None,opener=urlopen):
        self.enabled=getattr(sys,'frozen',False) if frozen is None else frozen
        self.opener=opener;self.state='idle';self.message='';self.progress=0.;self.new_version='';self.directory=None;self.payload=None;self.asset=None;self.lock=threading.Lock();self.cancelled=threading.Event()
        self.status_path=os.path.abspath(sys.executable)+'.update-state.json'
        status=self.read_status() if self.enabled else None
        if status and (status.get('phase')=='failed' or status.get('phase') in ('ready','pending') and file_digest(sys.executable)!=status.get('digest')):
            self.state='error';self.message='更新替换失败，已保留旧版；点击重试'
        elif self.enabled:self.check()
    def read_status(self):
        try:
            with open(self.status_path,encoding='utf-8-sig') as source:value=json.load(source)
            return value if isinstance(value,dict) else None
        except (OSError,ValueError):return None
    def check(self):
        with self.lock:
            if self.state in ('checking','downloading','installing','ready'):return False
            self.state='checking';self.message='正在检查更新'
        threading.Thread(target=self.worker,name='game-updater',daemon=True).start();return True
    def worker(self):
        try:
            with self.opener(request(API),timeout=12) as response:
                body=response.read(2*1024*1024+1)
                if len(body)>2*1024*1024:raise ValueError('更新信息过大')
            if self.cancelled.is_set():return
            self.asset=release_asset(json.loads(body))
            if not self.asset:self.state='current';self.message='当前已是最新版本';return
            if self.enabled:
                # Release tags can describe a different build than the attached EXE.
                # An identical installed asset must never be downloaded again.
                if file_digest(sys.executable)==self.asset['digest']:self.state='current';self.message='与仓库发布的 EXE 相同';return
            if self.asset['unversioned'] and self.enabled:
                if file_digest(sys.executable)==self.asset['digest']:self.state='current';self.message='与仓库发布的 EXE 相同';return
                updated=self.asset.get('updated')
                if updated and datetime.fromisoformat(updated.replace('Z','+00:00'))<=datetime.fromisoformat(BUILD_UTC):
                    self.state='current';self.message='本地版本较仓库发布更新';return
            self.new_version=self.asset['version'];self.state='downloading';self.message='正在下载 '+self.new_version
            self.directory=tempfile.mkdtemp(prefix='SteelWilderness-update-');self.payload=os.path.join(self.directory,'payload.bin')
            size=0
            with self.opener(request(self.asset['url']),timeout=20) as response,open(self.payload,'wb') as out:
                while True:
                    if self.cancelled.is_set():raise ValueError('更新已取消')
                    block=response.read(256*1024)
                    if not block:break
                    size+=len(block)
                    if size>self.asset['size']:raise ValueError('更新文件大小不匹配')
                    out.write(block);self.progress=size/self.asset['size']
            verify(self.payload,self.asset['digest'],self.asset['size'])
            if self.asset['unversioned'] or self.enabled:
                actual=executable_version(self.payload)
                if actual is None:raise ValueError('发布的 EXE 缺少版本信息，无法确认更新')
                current=max(version(VERSION),executable_version(sys.executable) or version(VERSION)) if self.enabled else version(VERSION)
                if actual<=current:
                    shutil.rmtree(self.directory,ignore_errors=True);self.directory=None;self.payload=None;self.state='current';self.message='本地版本不低于仓库 EXE';return
                self.new_version='.'.join(map(str,actual));self.asset['version']=self.new_version
            self.state='ready';self.message=self.new_version+' 已下载并校验完成，重启即可完成替换'
        except HTTPError as error:
            self.fail('仓库暂无正式版本' if error.code==404 else '更新服务暂不可用，点击重试')
        except json.JSONDecodeError:self.fail('更新信息格式异常，点击重试')
        except ValueError as error:self.fail(str(error))
        except Exception:self.fail('检查或下载失败，联网后点击重试')
    def fail(self,message):
        if self.directory:shutil.rmtree(self.directory,ignore_errors=True)
        self.directory=None;self.payload=None;self.state='error';self.message=message
    def install(self):
        if self.state!='ready' or not self.enabled:return False
        try:
            target=os.path.abspath(sys.executable)
            if os.path.basename(target).lower()!='steelwilderness.exe':raise ValueError('请使用固定名称 SteelWilderness.exe')
            verify(self.payload,self.asset['digest'],self.asset['size'])
            # Use a temporary copy of the game itself; no shell, scripts or readiness timeout.
            helper=os.path.join(self.directory,'update-helper.exe')
            shutil.copy2(target,helper)
            save_status(target,'pending',self.asset['digest'])
            flags=(subprocess.CREATE_NO_WINDOW|subprocess.DETACHED_PROCESS) if os.name=='nt' else 0
            subprocess.Popen([helper,'--apply-update',target,self.payload,self.asset['digest'],str(self.asset['size']),str(os.getpid())],creationflags=flags,close_fds=True)
            self.state='installing';return True
        except ValueError as error:self.fail(str(error))
        except Exception:self.state='ready';self.message='无法启动更新，点击重试'
        return False
    def close(self):
        if self.state=='installing':return
        self.cancelled.set()
        if self.state!='downloading' and self.directory:shutil.rmtree(self.directory,ignore_errors=True)
    def button(self):
        import pygame
        return pygame.Rect(260,__import__("WindowLayout").CANVAS[1]-37,237,30)
    def click(self,pos):
        if not self.button().collidepoint(pos):return False,False
        return True,self.install() if self.state=='ready' else self.check() and False
    def draw(self,garage):
        label='重启更新 '+self.new_version if self.state=='ready' else f'下载更新 {self.progress:.0%}' if self.state=='downloading' else '检查中…' if self.state=='checking' else '检查更新'
        garage.button(self.button(),label,self.state=='ready')
        garage.text('版本 '+VERSION,(835,730+garage.bottom_offset()),14,(172,198,184))
        garage.text(self.message[:26],(835,754+garage.bottom_offset()),14,(172,198,184))
