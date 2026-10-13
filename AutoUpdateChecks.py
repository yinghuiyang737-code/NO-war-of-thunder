import base64, hashlib, io, json, os, subprocess, tempfile
from urllib.error import HTTPError
from AutoUpdate import API,REPOSITORY,VERSION,Updater,apply_update,release_asset,verify,version

def run():
    newest='.'.join(map(str,(*version(VERSION)[:3],version(VERSION)[3]+1)))
    payload=bytearray(2048);payload[:2]=b'MZ';payload[60:64]=(128).to_bytes(4,'little');payload[128:132]=b'PE\0\0';payload=bytes(payload)
    digest=hashlib.sha256(payload).hexdigest()
    asset=dict(name='SteelWilderness.exe',state='uploaded',size=len(payload),digest='sha256:'+digest,browser_download_url='https://github.com/'+REPOSITORY+'/releases/download/v'+newest+'/SteelWilderness.exe')
    release=dict(tag_name='v'+newest,assets=[asset])
    assert version('v'+newest)>version(VERSION) and version('bad') is None
    assert release_asset(dict(release,tag_name='v2026.10.11.3')) is None
    assert release_asset(dict(release,prerelease=True)) is None
    for changed in (dict(asset,digest=None),dict(asset,browser_download_url='https://bad.example/file.exe'),dict(asset,size=999)):
        try:release_asset(dict(release,assets=[changed]));raise AssertionError('Unsafe release accepted')
        except ValueError:pass
    assert release_asset(dict(release,tag_name='正式版',name='正式版 '+newest))['version']==newest
    assert release_asset(dict(release,tag_name='正式版',name='正式版',body=''))['unversioned']
    import AutoUpdate
    original_reader=AutoUpdate.executable_version
    formal=dict(release,tag_name='正式版',name='正式版',body='')
    formal_opener=lambda req,timeout:io.BytesIO(json.dumps(formal).encode() if req.full_url==API else payload)
    try:
        AutoUpdate.executable_version=lambda path:version(newest)
        named=Updater(False,formal_opener);named.worker();assert named.state=='ready' and named.new_version==newest
        __import__('shutil').rmtree(named.directory)
        AutoUpdate.executable_version=lambda path:None
        invalid=Updater(False,formal_opener);invalid.worker();assert invalid.state=='error' and '缺少版本信息' in invalid.message
    finally:AutoUpdate.executable_version=original_reader
    def opener(req,timeout):return io.BytesIO(json.dumps(release).encode() if req.full_url==API else payload)
    updater=Updater(False,opener);updater.worker();assert updater.state=='ready';verify(updater.payload,digest,len(payload))
    import shutil
    shutil.rmtree(updater.directory)
    updater=Updater(False,lambda req,timeout:io.BytesIO(json.dumps(release).encode() if req.full_url==API else payload[:-10]));updater.worker();assert updater.state=='error' and updater.directory is None
    def missing(req,timeout):raise HTTPError(API,404,'No releases',{},None)
    updater=Updater(False,missing);updater.worker();assert updater.state=='error' and '暂无' in updater.message
    with tempfile.TemporaryDirectory(prefix="update-check-' 空间-") as folder:
        target=os.path.join(folder,'SteelWilderness.exe');source=os.path.join(folder,'payload.bin')
        progress=os.path.join(folder,'玩家进度.json');bindings=os.path.join(folder,'按键设置.json')
        for path in (progress,bindings):
            with open(path,'wb') as f:f.write(b'preserve me')
        with open(source,'wb') as f:f.write(payload)
        from unittest.mock import patch
        for fail_launch in (False,True):
            with open(target,'wb') as f:f.write(b'old executable')
            calls=[]
            def launch(*args,**kwargs):
                calls.append(args)
                if fail_launch and len(calls)==1:raise OSError('Simulated launch failure')
            with patch('AutoUpdate.subprocess.Popen',side_effect=launch):
                result=apply_update(target,source,digest,len(payload),0)
            assert result==(1 if fail_launch else 0)
            with open(target,'rb') as f:assert f.read()==(b'old executable' if fail_launch else payload)
            status=json.load(open(target+'.update-state.json',encoding='utf-8'))
            assert status['phase']==('failed' if fail_launch else 'installed') and status['digest']==digest
            assert not os.path.exists(target+'.rollback.tmp') and not os.path.exists(source)
            with open(source,'wb') as f:f.write(payload)
        # Launch acceptance is enough; a slow child must not be killed by a four-second handshake.
        with patch('AutoUpdate.sys.executable',target),patch('AutoUpdate.subprocess.Popen') as spawn:
            install=Updater(False);install.enabled=True;install.state='ready';install.directory=folder;install.payload=source;install.asset=dict(digest=digest,size=len(payload))
            assert install.install() and install.state=='installing'
            args=spawn.call_args.args[0];assert args[1]=='--apply-update' and args[2]==target
            assert os.path.exists(args[0]) and json.load(open(target+'.update-state.json'))['phase']=='pending'
            assert not spawn.return_value.poll.called and not spawn.return_value.terminate.called
        for path in (progress,bindings):
            with open(path,'rb') as f:assert f.read()==b'preserve me'
    # A misleading newer tag attached to the already-installed bytes must not redownload.
    original_exe=AutoUpdate.sys.executable
    with tempfile.TemporaryDirectory() as folder:
        target=os.path.join(folder,'SteelWilderness.exe');open(target,'wb').write(payload)
        try:
            AutoUpdate.sys.executable=target
            calls=[]
            def identical(req,timeout):
                calls.append(req.full_url)
                return io.BytesIO(json.dumps(release).encode() if req.full_url==API else payload)
            same=Updater(False,identical);same.enabled=True;same.worker()
            assert same.state=='current' and calls==[API] and same.payload is None
            # A failed helper is visible next start and does not initiate another download.
            open(target+'.update-state.json','w',encoding='utf8').write(json.dumps({'phase':'failed','digest':digest}))
            blocked=Updater(True,identical);assert blocked.state=='error' and calls==[API]
        finally:AutoUpdate.sys.executable=original_exe
    print('PASS: release version/channel/source/digest checks, background download, truncated/404 recovery; literal Unicode/apostrophe paths, actual EXE replacement/rollback and save/binding preservation')
