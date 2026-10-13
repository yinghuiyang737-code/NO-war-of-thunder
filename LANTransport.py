"""Bounded nonblocking TCP transport for the four-player LAN room."""
import socket,json,time
MAX_PACKET=2_000_000
PROTOCOL=1
PORT=27840
class Transport:
    def __init__(self,host=False,address='',port=PORT):
        self.host=host;self.listener=None;self.peers={};self.next_peer=1;self.events=[]
        if host:
            self.listener=socket.socket();self.listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);self.listener.bind((address or '0.0.0.0',port));self.listener.listen(4);self.listener.setblocking(False);self.port=self.listener.getsockname()[1]
        else:
            s=socket.socket();s.settimeout(2.);s.connect((address,port));s.setblocking(False);self.peers[0]=dict(socket=s,buffer=b'',out=bytearray(),seen=time.monotonic(),closing=False);self.port=port
    def send(self,peer,message):
        p=self.peers.get(peer)
        if not p:return
        raw=(json.dumps(message,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8')
        if len(raw)>MAX_PACKET:raise ValueError('Network packet too large')
        if len(p['out'])>MAX_PACKET*3:self.drop(peer,'接收速度过慢');return
        p['out'].extend(raw)
    def broadcast(self,message):
        for peer in list(self.peers):self.send(peer,message)
    def drop(self,peer,reason='连接已断开'):
        p=self.peers.pop(peer,None)
        if p:
            p['socket'].close();self.events.append((peer,{'type':'disconnected','reason':reason}))
    def pump(self):
        if self.listener:
            for _ in range(8):
                try:s,address=self.listener.accept()
                except BlockingIOError:break
                s.setblocking(False);peer=self.next_peer;self.next_peer+=1
                self.peers[peer]=dict(socket=s,buffer=b'',out=bytearray(),seen=time.monotonic(),closing=False)
                self.events.append((peer,{'type':'connected'}))
        for peer,p in list(self.peers.items()):
            try:
                for _ in range(8):
                    try:raw=p['socket'].recv(131072)
                    except BlockingIOError:break
                    if not raw:self.drop(peer);break
                    p['seen']=time.monotonic();p['buffer']+=raw
                    if len(p['buffer'])>MAX_PACKET:self.drop(peer,'数据格式错误');break
                    while b'\n' in p['buffer']:
                        line,p['buffer']=p['buffer'].split(b'\n',1)
                        try:message=json.loads(line.decode('utf-8'))
                        except (ValueError,UnicodeDecodeError):self.drop(peer,'数据格式错误');break
                        if not isinstance(message,dict):self.drop(peer,'数据格式错误');break
                        self.events.append((peer,message))
                if peer not in self.peers:continue
                if p['out']:
                    try:sent=p['socket'].send(p['out']);del p['out'][:sent]
                    except BlockingIOError:pass
                if p['closing'] and not p['out']:self.drop(peer)
                elif time.monotonic()-p['seen']>15:self.drop(peer,'连接超时')
            except (OSError,ConnectionError):self.drop(peer)
        events=self.events;self.events=[];return events
    def close(self):
        for p in self.peers.values():p['socket'].close()
        self.peers.clear()
        if self.listener:self.listener.close();self.listener=None

def local_addresses():
    try:addresses=socket.gethostbyname_ex(socket.gethostname())[2]
    except OSError:addresses=[]
    return list(dict.fromkeys(a for a in addresses if not a.startswith('127.'))) or ['127.0.0.1']
