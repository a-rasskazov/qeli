#!/usr/bin/env python3
"""Q05/Q06 HTTP transactions, user policy and faults on an exact release in private NET/mount/PID namespaces.
The full-restart fault case binds a private rejecting systemctl shim; no host service calls.
"""
import argparse,ssl,base64,concurrent.futures,hashlib,hmac,http.client,json,os,re,signal,socket,subprocess,threading,time
from pathlib import Path

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for k in ('qeli','sha256','artifacts','routes','parent-net','parent-mnt','parent-pid'):ap.add_argument('--'+k,required=True)
 ap.add_argument('--scenario',choices=('basic','runtime','faults','crash','nonroot','users','users-live','users-storage','users-policy','users-durability','users-admission','users-bandwidth','archives'),required=True)
 a=ap.parse_args()
 for k in ('net','mnt','pid'):assert os.readlink('/proc/self/ns/'+k)!=getattr(a,'parent_'+k),'private namespace required: '+k
 binary=Path(a.qeli).resolve(strict=True);assert hashlib.sha256(binary.read_bytes()).hexdigest()==a.sha256
 root=Path(a.artifacts);root.mkdir(mode=0o700,parents=True,exist_ok=False);routes=json.loads(Path(a.routes).read_text());checks=[];events=[];observations=[];sup=None;stream=None;complete=False
 cfg=Path('/etc/qeli/server.conf');state=root/'state';state.mkdir(mode=0o700);port=24880;prefix='/audit';tls_mode=False;fixture_nonroot=False;password='fixture-only #; exact password';cookie='';env=dict(os.environ,STATE_DIRECTORY=str(state),QELI_CONTROL_SOCKET=str(root/'control.sock'))
 def save(finished=False):
  (root/'result.json').write_text(json.dumps(dict(status='PASS' if complete else 'FAIL' if finished else 'IN_PROGRESS',artifact_sha256=a.sha256,checks=checks,observations=observations,check_count=len(checks)),indent=2)+'\n')
 def check(name,ok,detail=None):
  checks.append(dict(name=name,status='PASS' if ok else 'FAIL',detail=detail));save();print(('PASS ' if ok else 'FAIL ')+name,flush=True);assert ok,(name,detail)
 def run(argv):
  p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=25);assert p.returncode==0,(argv[0:2],p.stdout);return p.stdout
 def req(path,method='GET',body=None,headers=None,token=None,source='127.0.0.1',use_prefix=True):
  hs={'X-Forwarded-For':'203.0.113.101'};hs.update(headers or {})
  if token is not None:hs['Cookie']='qeli_session='+token
  if isinstance(body,(dict,list)):body=json.dumps(body).encode();hs.setdefault('Content-Type','application/json')
  elif isinstance(body,str):body=body.encode();hs.setdefault('Content-Type','application/json')
  c=http.client.HTTPSConnection('127.0.0.1',port,timeout=30,source_address=(source,0),context=ssl._create_unverified_context()) if tls_mode else http.client.HTTPConnection('127.0.0.1',port,timeout=30,source_address=(source,0))
  try:
   c.request(method,(prefix if use_prefix else '')+path,body=body,headers=hs);r=c.getresponse();code=r.status;rh={k.lower():v for k,v in r.getheaders()};data=r.read()
  finally:c.close()
  try:value=json.loads(data)
  except (ValueError,UnicodeError):value={}
  events.append(dict(path=path,method=method,status=code,response_bytes=len(data),response_sha256=hashlib.sha256(data).hexdigest()));return code,value,rh,data
 def wait(f,label):
  end=time.monotonic()+25
  while time.monotonic()<end:
   if sup and sup.poll() is not None:raise RuntimeError('private supervisor exited: '+(root/'server.log').read_text()[-2000:])
   try:
    if f():return
   except (ConnectionError,OSError):pass
   time.sleep(.05)
  raise RuntimeError(label)
 def start():
  nonlocal sup,stream
  stream=(root/'server.log').open('a');command=[str(binary),'server','-c',str(cfg)]
  if a.scenario=='nonroot' or fixture_nonroot:command=['setpriv','--reuid=65534','--regid=65534','--clear-groups','--inh-caps=+net_admin,+net_raw','--ambient-caps=+net_admin,+net_raw']+command
  sup=subprocess.Popen(command,env=env,stdout=stream,stderr=subprocess.STDOUT)
  wait(lambda:req('/login')[0] in (200,303,403),'panel not ready');wait(lambda:':24843' in run(['ss','-lntu']) and Path('/etc/qeli/identity/fixture.key').exists(),'private worker not ready')
 def stop():
  if sup and sup.poll() is None:sup.send_signal(signal.SIGTERM);assert sup.wait(timeout=25)==0
  if stream:stream.close()
 def login(user='admin',pw=password,**kw):return req('/api/login','POST',{'username':user,'password':pw},**kw)
 def token_from(r):return r[2]['set-cookie'].split(';',1)[0].split('=',1)[1]
 def basic(user='admin',pw=password,scheme='Basic'):return {'Authorization':scheme+' '+base64.b64encode((user+':'+pw).encode()).decode()}
 def tree():return {str(p.relative_to('/etc/qeli')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/etc/qeli').rglob('*') if p.is_file() and not p.name.endswith('.lock')}
 def network():return {'links':run(['ip','-j','link']),'routes4':run(['ip','-4','route','show','table','all']),'routes6':run(['ip','-6','route','show','table','all']),'rules4':re.sub(r'\[\d+:\d+\]','[COUNTERS]','\n'.join(x for x in run(['iptables-save']).splitlines() if x.startswith('-A ') or (x.startswith(':') and ' - ' in x))),'rules6':re.sub(r'\[\d+:\d+\]','[COUNTERS]','\n'.join(x for x in run(['ip6tables-save']).splitlines() if x.startswith('-A ') or (x.startswith(':') and ' - ' in x)))}
 def snapshot_state():return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in state.glob('session*') if p.is_file() and not p.name.endswith('.lock')}
 for argv in (['ip','link','set','lo','up'],['ip','link','add','wan0','type','dummy'],['ip','link','set','wan0','up'],['ip','addr','add','192.0.2.1/24','dev','wan0'],['ip','route','add','default','dev','wan0']):run(argv)
 Path('/etc/qeli/users.conf').write_text('');cfg.write_text('''[auth]
users_file = /etc/qeli/users.conf
[web]
enabled = true
bind = 127.0.0.1
port = 24880
tls = false
secure_cookie = false
base_path = /audit
trusted_proxies = 127.0.0.1,198.51.100.0/24
public_host = panel.fixture.invalid
allowed_origins = https://extra.fixture.invalid:9443/panel,ssh.fixture.invalid:19000
session_ttl_secs = 600
brute_force.max_attempts = 3
brute_force.window_secs = 60
brute_force.lockout_secs = 2
[logging]
level = info
[profile:fixture]
bind.address = 127.0.0.1
bind.port = 24843
bind.transport = tcp
tun.name = qauth
tun.address = 10.77.0.1
pool.cidr = 10.77.0.0/24
routing.nat.enabled = false
routing.ipv6.mode = off
dns.enabled = false
obf.mode = fake-tls
''');cfg.chmod(0o600)
 run([str(binary),'set-web-password','--username','admin','--password',password,'--config',str(cfg)])
 before=network()


 if a.scenario=='archives':
  import io,tarfile
  old=cfg.read_text();cfg.unlink();cfg=Path('/etc/qeli/nested/server.ini');cfg.parent.mkdir();users=Path('/etc/qeli/auth/users.ini');users.parent.mkdir();users.write_text('')
  cfg.write_text(old.replace('/etc/qeli/users.conf',str(users)));cfg.chmod(0o600)
  def archive(items):
   out=io.BytesIO()
   with tarfile.open(fileobj=out,mode='w:gz',format=tarfile.PAX_FORMAT) as tar:
    for name,spec in items.items():
     spec=spec if isinstance(spec,dict) else {'data':spec};data=spec.get('data',b'');data=data.encode() if isinstance(data,str) else data
     t=tarfile.TarInfo(name);t.mode=spec.get('mode',0o600);t.uid=spec.get('uid',0);t.gid=spec.get('gid',0);t.type=spec.get('type',tarfile.REGTYPE);t.linkname=spec.get('linkname','');t.size=len(data) if t.type==tarfile.REGTYPE else 0
     tar.addfile(t,io.BytesIO(data) if t.type==tarfile.REGTYPE else None)
   return out.getvalue()
  def unpack(blob):
   with tarfile.open(fileobj=io.BytesIO(blob),mode='r:gz') as tar:return {m.name:tar.extractfile(m).read() for m in tar if m.isfile()}
  def live_tree():return {str(p.relative_to('/etc/qeli')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/etc/qeli').rglob('*') if p.is_file() and not p.name.endswith('.lock') and not any(x.startswith(('.pre-restore-','.restore-','.config-history')) for x in p.relative_to('/etc/qeli').parts)}
  def probe(name,blob,exact=False):
   previous=live_tree();r=req('/api/restore'+('?exact=1' if exact else ''),'POST',blob,headers={**basic(),'Content-Type':'application/gzip'})
   ok=r[0] in (400,409,422) and r[1].get('ok') is False and live_tree()==previous
   checks.append(dict(name=name+' refuses before publication',status='PASS' if ok else 'FAIL',detail={'http_status':r[0],'response':r[1],'live_unchanged':live_tree()==previous}));save();print(('PASS ' if ok else 'FAIL ')+name,flush=True)
   # Keep independent baseline probes valid even when the old release accepts one.
   for path,data in pristine.items():path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);path.chmod(0o600);os.chown(path,0,0)
   for path in [Path('/etc/qeli/web-tls-cert.pem'),Path('/etc/qeli/web-tls-key.pem')]:path.unlink(missing_ok=True)
  try:
   start();identity=Path('/etc/qeli/identity/fixture.key');pristine={cfg:cfg.read_bytes(),users:users.read_bytes(),identity:identity.read_bytes()}
   check('custom managed active config and identity startup',len(identity.read_bytes())==32 and login()[0]==200)
   # Both internal and portable archives must exclude earlier snapshots/uploads.
   Path('/etc/qeli/.pre-restore-old.tgz').write_bytes(b'old');Path('/etc/qeli/.restore-upload-old.tgz').write_bytes(b'old');Path('/etc/qeli/.restore-staging-old').mkdir();Path('/etc/qeli/.restore-staging-old/private').write_bytes(b'old')
   r=req('/api/backup',headers=basic());check('portable backup HTTP gzip download',r[0]==200 and r[2].get('content-type')=='application/gzip');members=unpack(r[3]);check('portable contains exact custom config users identity',all(members.get(str(p.relative_to('/etc')))==b for p,b in pristine.items()));check('portable excludes operation archives',not any('.pre-restore-' in n or '.restore-' in n for n in members))
   good=dict(members);good['qeli/roundtrip.txt']=b'archived';blob=archive(good);extra=Path('/etc/qeli/extra.txt');extra.write_text('live')
   r=req('/api/restore','POST',blob,headers=basic());check('overlay roundtrip succeeds with custom paths',r[0]==200 and r[1].get('ok') is True,r[1]);check('overlay retains live extras and exact identity',extra.exists() and identity.read_bytes()==pristine[identity] and cfg.read_bytes()==pristine[cfg])
   r=req('/api/restore?exact=1','POST',blob,headers=basic());ok=r[0]==200 and r[1].get('ok') is True and not extra.exists();checks.append(dict(name='exact roundtrip removes top-level extra with nested writer locks',status='PASS' if ok else 'FAIL',detail=r[1]));save();print(('PASS ' if ok else 'FAIL ')+'exact roundtrip',flush=True);extra.unlink(missing_ok=True);check('config users identity restored private modes',all((p.stat().st_mode&0o777)==0o600 for p in pristine));check('sidecar lock remains present',cfg.with_suffix(cfg.suffix+'.lock').exists())
   snaps=list(Path('/etc/qeli').glob('.pre-restore-*.tgz'));new=[p for p in snaps if p.name!='.pre-restore-old.tgz'];check('rollback snapshots exclude earlier snapshots/uploads',len(new)==2 and all(not any('.pre-restore-' in n or '.restore-' in n for n in unpack(p.read_bytes())) for p in new))
   # Clear deliberately synthetic operational entries; unrelated host paths remain private.
   Path('/etc/qeli/.pre-restore-old.tgz').unlink();Path('/etc/qeli/.restore-upload-old.tgz').unlink();run(['rm','-rf','/etc/qeli/.restore-staging-old'])
   for name,spec in [
    ('parent traversal',{'qeli/../outside':b'x'}),('absolute path',{'/tmp/q07-escape':b'x'}),
    ('symlink',{'qeli/link':{'type':tarfile.SYMTYPE,'linkname':'/tmp/outside'}}),('hardlink',{'qeli/link':{'type':tarfile.LNKTYPE,'linkname':'qeli/auth/users.ini'}}),
    ('fifo',{'qeli/pipe':{'type':tarfile.FIFOTYPE}}),('executable',{'qeli/program':{'data':b'x','mode':0o755}}),
    ('malformed active INI',{'qeli/nested/server.ini':b'invalid'}),('missing active INI',None),('missing users INI','users'),
    ('missing profile identity','identity'),('missing identity overlay','identity'),('malformed profile identity',{'qeli/identity/fixture.key':b'bad'}),
    ('invalid panel password hash',{'qeli/nested/server.ini':re.sub(rb'password_hash\s*=\s*[^\n]+',b'password_hash = bad',pristine[cfg])}),
    ('missing TLS pair',{'qeli/nested/server.ini':pristine[cfg].replace(b'tls = false',b'tls = true')}),
    ('invalid TLS pair',{'qeli/nested/server.ini':pristine[cfg].replace(b'tls = false',b'tls = true'),'qeli/web-tls-cert.pem':b'bad','qeli/web-tls-key.pem':b'bad'}),
    ('foreign config ownership',{'qeli/nested/server.ini':{'data':pristine[cfg],'uid':65534,'gid':65534}})]:
    candidate=dict(good)
    if spec is None:candidate.pop('qeli/nested/server.ini')
    elif spec=='users':candidate.pop('qeli/auth/users.ini')
    elif spec=='identity':candidate.pop('qeli/identity/fixture.key')
    else:candidate.update(spec)
    if name=='foreign config ownership':
     previous=live_tree();r=req('/api/restore','POST',archive(candidate),headers=basic());ok=r[0]==200 and r[1].get('ok') is True and cfg.stat().st_uid==0 and cfg.stat().st_gid==0
     checks.append(dict(name='restore normalizes trusted config owner',status='PASS' if ok else 'FAIL',detail={'http_status':r[0],'uid':cfg.stat().st_uid,'gid':cfg.stat().st_gid}));save();print(('PASS ' if ok else 'FAIL ')+'trusted owner',flush=True);os.chown(cfg,0,0)
    else:probe(name,archive(candidate),exact=name=='missing profile identity')
   probe('expanded tar size budget',archive({**good,'qeli/bomb':b'0'*(64*1024*1024+1)}))
   probe('entry count budget',archive({**good,**{'qeli/empty-'+str(i):b'' for i in range(5001)}}))
   import fcntl
   fd=os.open(str(cfg)+'.lock',os.O_RDWR);fcntl.flock(fd,fcntl.LOCK_EX)
   try:
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
     pending=pool.submit(req,'/api/restore','POST',blob,basic());time.sleep(.3)
     t=time.monotonic();second=req('/api/restore','POST',blob,headers=basic());check('concurrent restore immediately returns HTTP 409',second[0]==409 and time.monotonic()-t<2,second[1])
     t=time.monotonic();healthy=req('/api/status',headers=basic());check('status responds while restore waits on sidecar lock',healthy[0]==200 and time.monotonic()-t<2)
     fcntl.flock(fd,fcntl.LOCK_UN);first=pending.result();check('admitted restore completes after writer unlock',first[0]==200 and first[1].get('ok') is True,first[1])
   finally:fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)
   # Validate and actually restart an HTTPS panel using custom PEM paths.
   cert=root/'fixture-cert.pem';key=root/'fixture-key.pem'
   run(['openssl','req','-x509','-newkey','rsa:2048','-keyout',str(key),'-out',str(cert),'-days','1','-nodes','-subj','/CN=panel.fixture.invalid'])
   tls_cfg=pristine[cfg].replace(b'tls = false',b'tls = true\ntls_cert = /etc/qeli/tls/custom.pem\ntls_key = /etc/qeli/tls/custom.key')
   tls_archive={**good,'qeli/nested/server.ini':tls_cfg,'qeli/tls/custom.pem':cert.read_bytes(),'qeli/tls/custom.key':key.read_bytes()}
   r=req('/api/restore','POST',archive(tls_archive),headers=basic());check('custom matching TLS pair accepted',r[0]==200 and r[1].get('ok') is True,r[1])
   stop();tls_mode=True;start();check('fresh HTTPS panel starts and authenticates restored custom pair',login()[0]==200)
   r=req('/api/restore','POST',blob,headers=basic());check('HTTPS panel restores original archive',r[0]==200 and r[1].get('ok') is True,r[1]);stop();tls_mode=False
   check('malicious paths never escape managed root',not Path('/tmp/q07-escape').exists() and not Path('/etc/outside').exists())
   check('no operation temporary files leak',not list(Path('/etc/qeli').glob('.restore-*')))
   # A successful archive can be consumed by a fresh worker with unchanged pin.
   stop();start();check('fresh worker starts after roundtrip with unchanged identity',identity.read_bytes()==pristine[identity] and login()[0]==200)
   complete=all(c['status']=='PASS' for c in checks)
  finally:
   stop();save(True);(root/'http-events.json').write_text(json.dumps(events,indent=2)+'\n');check('private namespace network restored',network()==before);save(True)
  print(('PASS' if complete else 'FAIL')+' Q07 '+str(len(checks))+' checks',flush=True)
  if not complete:raise SystemExit(1)
 elif a.scenario=='basic':
  history=cfg.parent/'.config-history';mounted=[]
  def api(path,method='GET',body=None):
   r=req(path,method,body,headers=basic());check(method+' '+path+' HTTP response',r[0]==200,r[0]);return r[1]
  def current():
   r=api('/api/config/raw');check('current raw revision exact',r.get('ok') is True and r['revision']==hashlib.sha256(cfg.read_bytes()).hexdigest());return r
  def write_raw(text,rev):return api('/api/config/raw','PUT',{'raw':text,'expected_revision':rev})
  def untouched(label,text,pid):check(label+' preserves config and supervisor',cfg.read_bytes()==text and sup.pid==pid and sup.poll() is None)
  def denied(label,path,body):
   text=cfg.read_bytes();pid=sup.pid;value=api(path,'PUT' if path.startswith('/api/config') and '/history/' not in path else 'POST',body);check(label+' rejected',value.get('ok') is False,{'kind':value.get('kind'),'error':value.get('error')});untouched(label,text,pid);return value
  try:
   start();r=login();check('fixture admin login',r[0]==200);cookie=token_from(r)
   initial=cfg.read_bytes();initial_hash=re.search(r'password_hash\s*=\s*(.*)',initial.decode())[1];pid=sup.pid
   base=current();form=api('/api/config');check('Form and INI share exact revision',form.get('ok') is True and form['revision']==base['revision']);check('Form hides admin hash',not form['config']['web'].get('password_hash'))
   denied('missing revision Form','/api/config',{'config':form['config']})
   denied('missing revision INI','/api/config/raw',{'raw':base['raw']})
   denied('stale revision Form','/api/config',{'config':form['config'],'expected_revision':'0'*64})
   denied('stale revision INI','/api/config/raw',{'raw':base['raw'],'expected_revision':'0'*64})
   for label,text in [('invalid INI','not valid INI'),('bad boolean',base['raw'].replace('tls = false','tls = ture')),('file-only hook',base['raw']+'\nrouting.post_up = touch /tmp/q05-unwanted-hook\n'),('host LAN overlap',base['raw'].replace('10.77.0.1','192.0.2.2').replace('10.77.0.0/24','192.0.2.0/24'))]:
    denied(label,'/api/config/raw',{'raw':text,'expected_revision':base['revision']})
   check('file-only hook never executed',not Path('/tmp/q05-unwanted-hook').exists())
   # Form roundtrip keeps omitted secrets; no worker restart is implicit.
   value=api('/api/config','PUT',{'config':form['config'],'expected_revision':form['revision']});check('Form roundtrip saves and applies live',value.get('ok') is True and value.get('web_settings_applied') is True,value);check('Form preserves exact admin hash',re.search(r'password_hash\s*=\s*(.*)',cfg.read_text())[1]==initial_hash);check('private INI permissions',(cfg.stat().st_mode&0o777)==0o600);untouched_pid=sup.pid;check('save does not replace supervisor',untouched_pid==pid)
   base=current();old=cfg.read_bytes();value=write_raw(base['raw']+'\n# Q05 exact comment roundtrip\n',base['revision']);check('INI saves comments and returns exact new revision',value.get('ok') is True and cfg.read_text().endswith('# Q05 exact comment roundtrip\n') and value['revision']==hashlib.sha256(cfg.read_bytes()).hexdigest(),value)
   snapshot=value['snapshot'];check('snapshot exact previous bytes private',snapshot and (history/snapshot).read_bytes()==old and (history/snapshot).stat().st_mode&0o777==0o600 and history.stat().st_mode&0o777==0o700)
   check('INI masked admin hash restored',re.search(r'password_hash\s*=\s*(.*)',cfg.read_text())[1]==initial_hash)
   base=current();before_restore=cfg.read_bytes();value=api('/api/config/history/'+snapshot+'/restore','POST',{'expected_revision':base['revision']});check('history restores exact snapshot and preserves replaced config',value.get('ok') is True and cfg.read_bytes()==old and (history/value['rollback_snapshot']).read_bytes()==before_restore,value)
   base=current();requests=[{'raw':base['raw']+'\n# Q05 concurrent '+str(i)+'\n','expected_revision':base['revision']} for i in range(8)]
   with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:responses=list(pool.map(lambda b:req('/api/config/raw','PUT',b,headers=basic()),requests))
   values=[x[1] for x in responses];check('eight parallel writers: one success seven revision conflicts',all(x[0]==200 for x in responses) and sum(v.get('ok') is True for v in values)==1 and sum(v.get('kind')=='config_conflict' for v in values)==7,[{'ok':v.get('ok'),'kind':v.get('kind')} for v in values]);check('concurrent file is one complete candidate',sum(('# Q05 concurrent '+str(i)+'\n').encode() in cfg.read_bytes() for i in range(8))==1)
   # Snapshot publication faults must fail before touching the active INI.
   base=current();history.mkdir(exist_ok=True)
   run(['mount','-t','tmpfs','-o','size=4096,mode=0700','q05-history-full',str(history)]);mounted.append(history);(history/'fill').write_bytes(b'x'*4096)
   denied('snapshot ENOSPC','/api/config/raw',{'raw':base['raw']+'\n# ENOSPC candidate\n','expected_revision':base['revision']});run(['umount',str(history)]);mounted.pop()
   run(['mount','--bind',str(history),str(history)]);mounted.append(history);run(['mount','-o','remount,bind,ro',str(history)])
   denied('snapshot read-only','/api/config/raw',{'raw':base['raw']+'\n# readonly snapshot\n','expected_revision':base['revision']});run(['umount',str(history)]);mounted.pop()
   # A failed final rename must leave the old exact revision and running process.
   run(['mount','--bind',str(cfg),str(cfg)]);mounted.append(cfg)
   denied('target mount rename refusal','/api/config/raw',{'raw':base['raw']+'\n# failed publish\n','expected_revision':base['revision']});run(['umount',str(cfg)]);mounted.pop()
   check('no temporary INI inode leaks',not list(cfg.parent.glob('.server.conf.qeli-tmp-*')))
   base=current();text=cfg.read_bytes();lockpath=cfg.with_suffix(cfg.suffix+'.lock');fd=os.open(lockpath,os.O_RDWR|os.O_CREAT,0o600)
   import fcntl
   fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
   try:
    started=time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
     pending=pool.submit(write_raw,base['raw']+'\n# locked write\n',base['revision']);time.sleep(.15);t=time.monotonic();healthy=req('/api/status',headers=basic());check('status remains responsive during cross-process write lock',healthy[0]==200 and time.monotonic()-t<2);value=pending.result()
    check('cross-process lock request refuses within budget',value.get('ok') is False and time.monotonic()-started<8,value);untouched('lock refusal',text,pid)
   finally:fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)
   base=current();value=write_raw(base['raw']+'\n# recovery after faults\n',base['revision']);check('save recovers after filesystem and lock faults',value.get('ok') is True,value)
   check('cookie still valid after non-auth config saves',req('/api/status',token=cookie)[0]==200)
   check('admin login still works after Form INI and history roundtrips',login()[0]==200)
   complete=True
  finally:
   for p in reversed(mounted):run(['umount',str(p)])
   stop();save(True);(root/'http-events.json').write_text(json.dumps(events,indent=2)+'\n');check('private namespace network restored',network()==before);save(True)
  print('PASS Q05 '+str(len(checks))+' checks',flush=True)
 elif a.scenario=='users':
  users_path=Path('/etc/qeli/users.conf')
  def api(path,method='GET',body=None):
   response=req(path,method,body,headers=basic());check(method+' '+path+' HTTP response',response[0]==200,response[0]);return response[1]
  def user(name):return api('/api/users/'+name)['user']
  def denied(label,path,method,body):
   old=users_path.read_bytes();response=req(path,method,json.dumps(body),headers=basic());value=response[1]
   # Collect every regression on the old binary before failing the batch.
   ok=(response[0] in (400,415,422) or (response[0]==200 and value.get('ok') is False)) and users_path.read_bytes()==old
   checks.append(dict(name=label+' refuses and preserves exact users INI',status='PASS' if ok else 'FAIL',detail=dict(ok=value.get('ok'),error=value.get('error'))));save();print(('PASS ' if ok else 'FAIL ')+label,flush=True)
  try:
   start();hashed=api('/api/hash-password','POST',{'password':'fixture-client-password'})['hash']
   stop();cfg.write_text(cfg.read_text()+'\n[group:inline-limit]\nmax_sessions = 2\nbandwidth_limit_mbps = 5\n[user:inline-user]\npassword_hash = '+hashed+'\nenabled = true\ngroup = inline-limit\n');cfg.chmod(0o600);start()
   created=api('/api/users','POST',{'username':'limited','password_hash':hashed,'enabled':False,'max_sessions':2,'bandwidth':{'limit_mbps':5,'burst_mbps':7},'allowed_networks':['10.0.0.0/8'],'routes':[{'cidr':'172.16.0.0/16','gateway':'10.77.0.1'}]});check('create complete limited user',created.get('ok') is True,created)
   original=users_path.read_bytes();stored=user('limited');check('API hides both password representations','password_hash' not in stored and 'password_enc' not in stored);check('INI stores exact limits',stored['enabled'] is False and stored['max_sessions']==2 and stored['bandwidth']==dict(limit_mbps=5,burst_mbps=7));check('users INI private permissions',users_path.stat().st_mode&0o777==0o600)
   for key,values in [('enabled',['false',0,None,[]]),('bandwidth',[5,'5',[],None]),('password',[5,False,[],None]),('password_hash',[5,False,[],None])]:
    for i,value in enumerate(values):denied('update wrong '+key+' '+str(i),'/api/users/limited','PUT',{key:value})
   for i,value in enumerate([5,False,[],{},['10.77.0.1']]):denied('route gateway wrong type '+str(i),'/api/users/limited','PUT',{'routes':[{'cidr':'172.16.0.0/16','gateway':value}]})
   for i,value in enumerate([None,[],False,2,'invalid']):
    denied('update non-object '+str(i),'/api/users/limited','PUT',value)
    denied('bandwidth non-object '+str(i),'/api/users/limited/bandwidth','POST',value)
    denied('group non-object '+str(i),'/api/groups/inline-limit','PUT',value)
    denied('usage non-object '+str(i),'/api/usage/limited/limit','POST',value)
    denied('live bandwidth non-object '+str(i),'/api/clients/limited/bandwidth','POST',value)
   for i,value in enumerate([None,[],False,5]):denied('live bandwidth profile wrong type '+str(i),'/api/clients/limited/bandwidth','POST',{'mbps':5,'profile':value})
   for i,value in enumerate(['false',0,None,[]]):denied('create wrong enabled '+str(i),'/api/users','POST',{'username':'bad-enabled-'+str(i),'password_hash':hashed,'enabled':value})
   for i,value in enumerate([5,'5',[],None]):denied('create wrong bandwidth '+str(i),'/api/users','POST',{'username':'bad-bandwidth-'+str(i),'password_hash':hashed,'bandwidth':value})
   # Restore the limited entry after baseline probes that intentionally expose bad writes.
   users_path.write_bytes(original);users_path.chmod(0o600)
   for key in ('allowed_networks','profiles','client_subnets'):
    denied('mixed access array '+key,'/api/users/limited','PUT',{key:['10.0.0.0/8',False]})
   denied('missing group reference','/api/users/limited','PUT',{'group':'absent'})
   denied('overflow sessions','/api/users/limited','PUT',{'max_sessions':4294967296})
   denied('wrong route family','/api/users/limited','PUT',{'routes':[{'cidr':'172.16.0.0/16','gateway':'fd71::1'}]})
   check('inline user visible',user('inline-user')['enabled'] is True)
   check('disable inline creates authoritative file override',api('/api/users/inline-user/disable','POST',{}).get('ok') is True and user('inline-user')['enabled'] is False)
   denied('delete override must not resurrect inline access','/api/users/inline-user','DELETE',None)
   check('set group override',api('/api/groups/inline-limit','PUT',{'max_sessions':1,'bandwidth_limit_mbps':1}).get('ok') is True)
   denied('delete override must not weaken inline group','/api/groups/inline-limit','DELETE',None)
   # Identity failure must precede a legacy password reset, for both APIs.
   key=Path('/etc/qeli/identity/fixture.key');identity=key.read_bytes();old=users_path.read_bytes();key.unlink();key.mkdir(mode=0o700)
   try:
    result=api('/api/share','POST',{'profile':'fixture','host':'vpn.fixture.invalid','user':'limited','allow_reset':'true'});check('identity failure cannot reset legacy credentials',result.get('ok') is False and users_path.read_bytes()==old,result)
   finally:key.rmdir();key.write_bytes(identity);key.chmod(0o600)
   for badhost in ['https://vpn.fixture.invalid','[invalid]','vpn.fixture.invalid:0']:
    denied('share invalid endpoint '+badhost,'/api/share','POST',{'profile':'fixture','host':badhost,'user':'limited','allow_reset':'true'})
   r=api('/api/share','POST',{'profile':'fixture','host':'vpn.fixture.invalid','user':'limited'});check('hash-only user requires explicit reset',r.get('ok') is False and r.get('needs_reset') is True and users_path.read_bytes()==old)
   r=api('/api/share','POST',{'profile':'fixture','host':'vpn.fixture.invalid','user':'limited','allow_reset':'true'});check('explicit reset issues URI and QR',r.get('ok') is True and r.get('reset') is True and r.get('uri','').startswith('qeli://') and r.get('qr_svg','').startswith('<svg') and bool(r.get('new_password')))
   reset=users_path.read_bytes();r=api('/api/share','POST',{'profile':'fixture','host':'vpn.fixture.invalid','user':'limited'});check('reissue preserves credentials',r.get('ok') is True and r.get('reset') is False and r.get('new_password') is None and users_path.read_bytes()==reset)
   check('enable limited user',api('/api/users/limited/enable','POST',{}).get('ok') is True)
   check('save static address',api('/api/users/limited','PUT',{'static_ip':'10.77.0.50'}).get('ok') is True and user('limited')['static_ip']=='10.77.0.50')
   denied('static collision','/api/users','POST',{'username':'collision','password_hash':hashed,'static_ip':'10.77.0.50'})
   denied('static outside pool','/api/users/limited','PUT',{'static_ip':'10.78.0.50'})
   denied('static server address','/api/users/limited','PUT',{'static_ip':'10.77.0.1'})
   check('clear nullable static and group',api('/api/users/limited','PUT',{'static_ip':None,'group':None}).get('ok') is True and user('limited')['static_ip'] is None)
   expiry=2000000000;check('persist quota and expiry',api('/api/usage/limited/limit','POST',{'data_limit_gb':5,'expire_at':expiry}).get('ok') is True and user('limited')['data_limit_gb']==5 and user('limited')['expire_at']==expiry)
   check('password edit preserves quota and expiry',api('/api/users/limited','PUT',{'password':'changed-fixture-password'}).get('ok') is True and user('limited')['data_limit_gb']==5 and user('limited')['expire_at']==expiry)
   check('bandwidth endpoint saves',api('/api/users/limited/bandwidth','POST',{'limit_mbps':2,'burst_mbps':9}).get('ok') is True)
   bw=user('limited')['bandwidth'];checks.append(dict(name='bandwidth setter preserves explicit burst',status='PASS' if bw==dict(limit_mbps=2,burst_mbps=9) else 'FAIL',detail=bw));save()
   check('bandwidth edit saves',api('/api/users/limited','PUT',{'bandwidth':{'limit_mbps':5,'burst_mbps':7}}).get('ok') is True)
   bw=user('limited')['bandwidth'];checks.append(dict(name='bandwidth edit preserves explicit burst',status='PASS' if bw==dict(limit_mbps=5,burst_mbps=7) else 'FAIL',detail=bw));save()
   complete=all(c['status']=='PASS' for c in checks)
  finally:
   stop();save(True);(root/'http-events.json').write_text(json.dumps(events,indent=2)+'\n');check('private namespace network restored',network()==before);save(True)
  assert complete,'Q06 regression failures recorded in result.json'
  print('PASS Q06 users '+str(len(checks))+' checks',flush=True)
 elif a.scenario=='users-storage':
  users_path=Path('/etc/qeli/users.conf');mounted=[]
  def api(path,method='GET',body=None):
   r=req(path,method,body,headers=basic());check(method+' '+path+' HTTP response',r[0]==200,r[0]);return r[1]
  def control(cmd,name):
   with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as c:
    c.settimeout(8);c.connect(env['QELI_CONTROL_SOCKET']);c.sendall((json.dumps({'cmd':cmd,'username':name})+'\n').encode())
    with c.makefile('rb') as f:return json.loads(f.readline(65536))
  def reload_worker():
   old=(root/'server.log').read_text().count('SIGHUP: reloaded users database')
   m=re.search(r'127\.0\.0\.1:24843\s+.*pid=(\d+)',run(['ss','-lntp']));assert m
   os.kill(int(m[1]),signal.SIGHUP);wait(lambda:(root/'server.log').read_text().count('SIGHUP: reloaded users database')>old,'worker reload not observed')
  def probe(name,ok,detail):
   checks.append(dict(name=name,status='PASS' if ok else 'FAIL',detail=detail));save();print(('PASS ' if ok else 'FAIL ')+name,flush=True)
  try:
   start();hashed=api('/api/hash-password','POST',{'password':'fixture-client-password'})['hash']
   bodies=[{'username':'parallel-'+str(i),'password_hash':hashed,'max_sessions':i+1,'bandwidth':{'limit_mbps':i+1,'burst_mbps':i+3}} for i in range(8)]
   with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:responses=list(pool.map(lambda b:req('/api/users','POST',b,headers=basic()),bodies))
   check('eight concurrent creates all succeed',all(r[0]==200 and r[1].get('ok') is True for r in responses),[r[1].get('error') for r in responses])
   listed=api('/api/users')['users'];check('concurrent creates lose no accounts',all(any(u['username']==b['username'] and u['max_sessions']==b['max_sessions'] and u['bandwidth']==b['bandwidth'] for u in listed) for b in bodies))
   def mutate(i):return req('/api/users/parallel-0','PUT',{'max_sessions':17} if i==0 else {'bandwidth':{'limit_mbps':21,'burst_mbps':27}},headers=basic())
   with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(mutate,range(2)))
   check('parallel disjoint updates succeed',all(r[0]==200 and r[1].get('ok') is True for r in responses));u=api('/api/users/parallel-0')['user'];check('disjoint edits survive both writers',u['max_sessions']==17 and u['bandwidth']=={'limit_mbps':21,'burst_mbps':27})
   valid=users_path.read_bytes()
   for name,data in [('unknown-key',valid+b'\nmisspelled_limit = 7\n'),('bad-value',valid.replace(b'max_sessions = 17',b'max_sessions = garbage')),('bad-utf8',valid+b'\xff')]:
    assert data!=valid;users_path.write_bytes(data)
    r=req('/api/users/parallel-0','PUT',{'max_sessions':99},headers=basic());check(name+' refuses exact corrupted INI',r[0]==200 and r[1].get('ok') is False and users_path.read_bytes()==data,{'ok':r[1].get('ok'),'error':r[1].get('error')})
   users_path.write_bytes(valid);users_path.chmod(0o600)
   run(['mount','--bind',str(users_path),str(users_path)]);mounted.append(users_path)
   try:r=api('/api/users/parallel-0','PUT',{'max_sessions':99});check('rename EBUSY refuses without publication',r.get('ok') is False and users_path.read_bytes()==valid,r);check('rename EBUSY leaves no fragments',not list(users_path.parent.glob('.users.conf.qeli-tmp-*')))
   finally:run(['umount',str(users_path)]);mounted.pop()
   parent=Path('/etc/qeli');run(['mount','--bind',str(parent),str(parent)]);mounted.append(parent);run(['mount','-o','remount,bind,ro',str(parent)])
   try:r=api('/api/users/parallel-0','PUT',{'max_sessions':99});check('read-only users storage refuses and preserves bytes',r.get('ok') is False and users_path.read_bytes()==valid,r)
   finally:run(['umount',str(parent)]);mounted.pop()
   check('storage recovery succeeds',api('/api/users/parallel-0','PUT',{'max_sessions':18}).get('ok') is True)
   stop();initial_cfg=cfg.read_text();cfg.write_text(initial_cfg+'\n[user:removed-inline]\npassword_hash = '+hashed+'\nenabled = true\n');cfg.chmod(0o600);start();check('inline user loaded initially',control('show-routes','removed-inline').get('ok') is True)
   cfg.write_text(initial_cfg);cfg.chmod(0o600);reload_worker();check('inline removal visible in worker before mutation',control('show-routes','removed-inline').get('ok') is False)
   old=users_path.read_bytes();r=control('enable-user','removed-inline');after=control('show-routes','removed-inline');probe('removed inline account cannot be resurrected by control enable',r.get('ok') is False and users_path.read_bytes()==old and after.get('ok') is False,{'enable':r,'loaded_after':after,'persisted_account':b'[user:removed-inline]' in users_path.read_bytes()})
   cfg.write_text(initial_cfg+'\n[user:new-inline]\npassword_hash = '+hashed+'\nenabled = true\n');cfg.chmod(0o600);reload_worker();check('new inline user loaded after reload',control('show-routes','new-inline').get('ok') is True)
   r=control('disable-user','new-inline');probe('new inline account can be disabled by control after reload',r.get('ok') is True and b'[user:new-inline]' in users_path.read_bytes(),r)
   complete=all(c['status']=='PASS' for c in checks)
  finally:
   for target in reversed(mounted):run(['umount',str(target)])
   stop();save(True);(root/'http-events.json').write_text(json.dumps(events,indent=2)+'\n');check('private namespace network restored',network()==before);save(True)
  assert complete,'Q06 storage/control regressions recorded'
 elif a.scenario=='users-durability':
  users_path=Path('/etc/qeli/users.conf');mounted=[]
  shim_c=r"""
 #define _GNU_SOURCE
 #include <dlfcn.h>
 #include <errno.h>
 #include <fcntl.h>
 #include <stdio.h>
 #include <string.h>
 #include <sys/stat.h>
 #include <unistd.h>
 static int action(const char *want) { char b[64]={0}; int fd=open("/tmp/q06-storage-fault-action",O_RDONLY);if(fd<0)return 0;ssize_t n=read(fd,b,63);close(fd);return n>0 && !strcmp(b,want); }
 static void gate(const char *event) {int fd=open("/tmp/q06-storage-fault-event",O_CREAT|O_TRUNC|O_WRONLY,0600);if(fd>=0){write(fd,event,strlen(event));close(fd);}while(access("/tmp/q06-storage-fault-action",F_OK)==0)usleep(10000);}
 int rename(const char *old,const char *next) { static int(*real)(const char*,const char*);if(!real)real=dlsym(RTLD_NEXT,"rename");int target=!strcmp(next,"/etc/qeli/users.conf");if(target && action("before-rename"))gate("before-rename");int rc=real(old,next);if(rc==0 && target && action("after-rename"))gate("after-rename");return rc; }
 int fsync(int fd) { static int(*real)(int);if(!real)real=dlsym(RTLD_NEXT,"fsync");struct stat st;char path[64],name[512]={0};snprintf(path,sizeof(path),"/proc/self/fd/%d",fd);ssize_t n=readlink(path,name,511);if(n>=0 && fstat(fd,&st)==0 && S_ISDIR(st.st_mode) && !strcmp(name,"/etc/qeli") && action("dir-fsync")){unlink("/tmp/q06-storage-fault-action");errno=EIO;return -1;}return real(fd); }
 """
  shim=Path('/tmp/q06-storage-fault.so');c=Path('/tmp/q06-storage-fault.c');c.write_text(shim_c);run(['gcc','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror','-o',str(shim),str(c),'-ldl']);env['LD_PRELOAD']=str(shim);action=Path('/tmp/q06-storage-fault-action');event=Path('/tmp/q06-storage-fault-event')

  def api(path,method='GET',body=None):
   r=req(path,method,body,headers=basic());check(method+' '+path+' HTTP response',r[0]==200,r[0]);return r[1]
  def control(cmd,name,**extra):
   with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as c:
    c.settimeout(12);c.connect(env['QELI_CONTROL_SOCKET']);c.sendall((json.dumps(dict(cmd=cmd,username=name,**extra))+'\n').encode())
    with c.makefile('rb') as f:return json.loads(f.readline(65536))
  def reload_worker():
   old=(root/'server.log').read_text().count('SIGHUP: reloaded users database')
   m=re.search(r'127\.0\.0\.1:24843\s+.*pid=(\d+)',run(['ss','-lntp']));assert m
   os.kill(int(m[1]),signal.SIGHUP);wait(lambda:(root/'server.log').read_text().count('SIGHUP: reloaded users database')>old,'worker reload not observed')
  def probe(name,ok,detail):
   checks.append(dict(name=name,status='PASS' if ok else 'FAIL',detail=detail));save();print(('PASS ' if ok else 'FAIL ')+name,flush=True)
  try:
   start();hashed=api('/api/hash-password','POST',{'password':'fixture-client-password'})['hash']
   bodies=[{'username':'parallel-'+str(i),'password_hash':hashed,'max_sessions':i+1,'bandwidth':{'limit_mbps':i+1,'burst_mbps':i+3}} for i in range(8)]
   with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:responses=list(pool.map(lambda b:req('/api/users','POST',b,headers=basic()),bodies))
   check('eight concurrent creates all succeed',all(r[0]==200 and r[1].get('ok') is True for r in responses),[r[1].get('error') for r in responses])
   listed=api('/api/users')['users'];check('concurrent creates lose no accounts',all(any(u['username']==b['username'] and u['max_sessions']==b['max_sessions'] and u['bandwidth']==b['bandwidth'] for u in listed) for b in bodies))
   def mutate(i):return req('/api/users/parallel-0','PUT',{'max_sessions':17} if i==0 else {'bandwidth':{'limit_mbps':21,'burst_mbps':27}},headers=basic())
   with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(mutate,range(2)))
   check('parallel disjoint updates succeed',all(r[0]==200 and r[1].get('ok') is True for r in responses));u=api('/api/users/parallel-0')['user'];check('disjoint edits survive both writers',u['max_sessions']==17 and u['bandwidth']=={'limit_mbps':21,'burst_mbps':27})
   valid=users_path.read_bytes()
   for name,data in [('unknown-key',valid+b'\nmisspelled_limit = 7\n'),('bad-value',valid.replace(b'max_sessions = 17',b'max_sessions = garbage')),('bad-utf8',valid+b'\xff')]:
    assert data!=valid;users_path.write_bytes(data)
    r=req('/api/users/parallel-0','PUT',{'max_sessions':99},headers=basic());check(name+' refuses exact corrupted INI',r[0]==200 and r[1].get('ok') is False and users_path.read_bytes()==data,{'ok':r[1].get('ok'),'error':r[1].get('error')})
   users_path.write_bytes(valid);users_path.chmod(0o600)
   run(['mount','--bind',str(users_path),str(users_path)]);mounted.append(users_path)
   try:r=api('/api/users/parallel-0','PUT',{'max_sessions':99});check('rename EBUSY refuses without publication',r.get('ok') is False and users_path.read_bytes()==valid,r);check('rename EBUSY leaves no fragments',not list(users_path.parent.glob('.users.conf.qeli-tmp-*')))
   finally:run(['umount',str(users_path)]);mounted.pop()
   parent=Path('/etc/qeli');run(['mount','--bind',str(parent),str(parent)]);mounted.append(parent);run(['mount','-o','remount,bind,ro',str(parent)])
   try:r=api('/api/users/parallel-0','PUT',{'max_sessions':99});check('read-only users storage refuses and preserves bytes',r.get('ok') is False and users_path.read_bytes()==valid,r)
   finally:run(['umount',str(parent)]);mounted.pop()
   check('storage recovery succeeds',api('/api/users/parallel-0','PUT',{'max_sessions':18}).get('ok') is True)
   import fcntl
   with open(str(users_path)+'.lock','a') as held:
    fcntl.flock(held,fcntl.LOCK_EX);old=users_path.read_bytes();began=time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
     pending=pool.submit(req,'/api/users/parallel-0','PUT',{'max_sessions':22},basic());time.sleep(6);bounded=pending.done();unchanged=users_path.read_bytes()==old;fcntl.flock(held,fcntl.LOCK_UN);response=pending.result(timeout=20)
    probe('held lock fails within five seconds without writing',bounded and unchanged and response[1].get('ok') is False,dict(done_after_6s=bounded,unchanged_before_release=unchanged,response=response[1],elapsed=time.monotonic()-began))
   for label,path,method,body in [
    ('create','/api/users','POST',{'username':'uncertain','password_hash':hashed}),
    ('update','/api/users/uncertain','PUT',{'max_sessions':4}),
    ('disable','/api/users/uncertain/disable','POST',{}),
    ('enable','/api/users/uncertain/enable','POST',{}),
    ('bandwidth','/api/users/uncertain/bandwidth','POST',{'limit_mbps':7,'burst_mbps':9}),
    ('group-upsert','/api/groups/uncertain-template','PUT',{'max_sessions':2}),
    ('group-delete','/api/groups/uncertain-template','DELETE',None),
    ('share-reset','/api/share','POST',{'profile':'fixture','host':'vpn.fixture.invalid','user':'uncertain','allow_reset':'true'}),
    ('delete','/api/users/uncertain','DELETE',None),
   ]:
    old=users_path.read_bytes();action.write_text('dir-fsync');r=api(path,method,body)
    probe(label+' API reports published durability failure truthfully',r.get('ok') is False and users_path.read_bytes()!=old and 'persistence is uncertain' in r.get('error','') and 'NOT applied' not in r.get('error','') and r.get('published') is True and r.get('reload_requested') is True,r)
    if label=='create':wait(lambda:control('show-routes','uncertain').get('ok') is True,'published create did not reload worker');check('published failed create is accepted by worker readback',True)
    if label=='share-reset':
     again=api('/api/share','POST',{'profile':'fixture','host':'vpn.fixture.invalid','user':'uncertain'});check('published failed reset reissues persisted credentials without another reset',again.get('ok') is True and again.get('reset') is False and again.get('new_password') is None,again.get('ok'))
    if label=='delete':wait(lambda:control('show-routes','uncertain').get('ok') is False,'published delete did not reload worker');check('published failed delete revokes worker auth record',True)
   for cmd in ('disable-user','enable-user','set-limit','set-bandwidth'):
    old=users_path.read_bytes();action.write_text('dir-fsync');r=control(cmd,'parallel-0',mbps=8,data_limit_gb=11)
    probe(cmd+' control distinguishes published failure and refreshes live auth',r.get('ok') is False and users_path.read_bytes()!=old and 'persistence is uncertain' in r.get('error','') and 'NOT ' not in r.get('error','') and 'read back into live auth' in r.get('error',''),r)
   def worker():
    m=re.search(r'127\.0\.0\.1:24843\s+.*pid=(\d+)',run(['ss','-lntp']));return int(m[1]) if m else None
   for phase in ('before-rename','after-rename'):
    old=users_path.read_bytes();action.write_text(phase);event.unlink(missing_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
     pending=pool.submit(req,'/api/users/parallel-0','PUT',{'max_sessions':31 if phase=='before-rename' else 32},basic());wait(lambda:event.exists() and event.read_text()==phase,'users rename crash gate')
     expected=old if phase=='before-rename' else users_path.read_bytes();check(phase+' complete INI on expected side of rename',expected==old if phase=='before-rename' else b'max_sessions = 32' in expected)
     fragments=list(users_path.parent.glob('.users.conf.qeli-tmp-*'));check(phase+' temporary files are private',all(x.stat().st_mode&0o777==0o600 for x in fragments))
     wp=worker();assert wp is not None;os.kill(wp,signal.SIGKILL);sup.kill();sup.wait(timeout=10);stream.close();action.unlink(missing_ok=True)
     try:pending.result();disconnected=False
     except (ConnectionError,OSError,http.client.HTTPException):disconnected=True
     check(phase+' interrupted users request reports no success',disconnected)
    check(phase+' crash preserves exact complete users INI',users_path.read_bytes()==expected)
    for p in fragments:p.unlink(missing_ok=True)
    start();check(phase+' private worker recovers persisted account',control('show-routes','parallel-0').get('ok') is True)
   old=users_path.read_bytes();action.write_text('dir-fsync');r=api('/api/users/parallel-0','PUT',{'max_sessions':23});published=users_path.read_bytes()!=old
   probe('post-rename fsync error never claims change NOT applied',r.get('ok') is False and published and 'persistence is uncertain' in r.get('error','') and 'NOT applied' not in r.get('error',''),dict(response=r,published=published))
   check('post-rename publication is complete INI',b'max_sessions = 23' in users_path.read_bytes());check('post-rename fsync leaves no temporary INI',not list(users_path.parent.glob('.users.conf.qeli-tmp-*')))
   stop();initial_cfg=cfg.read_text();cfg.write_text(initial_cfg+'\n[user:removed-inline]\npassword_hash = '+hashed+'\nenabled = true\n');cfg.chmod(0o600);start();check('inline user loaded initially',control('show-routes','removed-inline').get('ok') is True)
   cfg.write_text(initial_cfg);cfg.chmod(0o600);reload_worker();check('inline removal visible in worker before mutation',control('show-routes','removed-inline').get('ok') is False)
   old=users_path.read_bytes();r=control('enable-user','removed-inline');after=control('show-routes','removed-inline');probe('removed inline account cannot be resurrected by control enable',r.get('ok') is False and users_path.read_bytes()==old and after.get('ok') is False,{'enable':r,'loaded_after':after,'persisted_account':b'[user:removed-inline]' in users_path.read_bytes()})
   cfg.write_text(initial_cfg+'\n[user:new-inline]\npassword_hash = '+hashed+'\nenabled = true\n');cfg.chmod(0o600);reload_worker();check('new inline user loaded after reload',control('show-routes','new-inline').get('ok') is True)
   r=control('disable-user','new-inline');probe('new inline account can be disabled by control after reload',r.get('ok') is True and b'[user:new-inline]' in users_path.read_bytes(),r)
   # Real ENOSPC on an owned private tmpfs, with auth.users_file selected at startup.
   stop();valid=users_path.read_bytes();store=Path('/etc/qeli/users-store');store.mkdir(mode=0o700);users_path=store/'users.conf';cfg.write_text(cfg.read_text().replace('users_file = /etc/qeli/users.conf','users_file = '+str(users_path)));cfg.chmod(0o600)
   run(['mount','-t','tmpfs','-o','size=65536,mode=700','tmpfs',str(store)]);mounted.append(store);users_path.write_bytes(valid);users_path.chmod(0o600);start()
   filler=store/'owned-filler';fd=os.open(filler,os.O_CREAT|os.O_WRONLY,0o600)
   try:
    while True:os.write(fd,b'x'*4096)
   except OSError as error:
    check('private tmpfs reaches actual ENOSPC',error.errno==28,str(error))
   finally:os.close(fd)
   old=users_path.read_bytes();r=api('/api/users/parallel-0','PUT',{'max_sessions':41});check('ENOSPC refuses before publication and preserves exact users INI',r.get('ok') is False and r.get('published') is False and users_path.read_bytes()==old,r);check('ENOSPC removes its temporary INI',not list(store.glob('.users.conf.qeli-tmp-*')))
   filler.unlink();check('write recovers after ENOSPC',api('/api/users/parallel-0','PUT',{'max_sessions':42}).get('ok') is True);valid=users_path.read_bytes();stop();run(['umount',str(store)]);mounted.pop();users_path.write_bytes(valid);users_path.chmod(0o600)
   # Root bypasses DAC, so EACCES must use an actual unprivileged private server.
   for name in ('q06-state','q06-control'):Path('/etc/qeli',name).mkdir(mode=0o700)
   env['STATE_DIRECTORY']='/etc/qeli/q06-state';env['QELI_CONTROL_SOCKET']='/etc/qeli/q06-control/control.sock'
   local_binary=Path('/etc/qeli/q06-fixture-qeli');local_binary.write_bytes(binary.read_bytes());local_binary.chmod(0o755);binary=local_binary
   for p in [root,state,Path('/etc/qeli'),*Path('/etc/qeli').rglob('*')]:os.chown(p,65534,65534)
   Path('/etc/qeli').chmod(0o700);fixture_nonroot=True;start();store.chmod(0o500);old=users_path.read_bytes()
   try:r=api('/api/users/parallel-0','PUT',{'max_sessions':43});check('nonroot EACCES refuses and preserves exact users INI',r.get('ok') is False and r.get('published') is False and users_path.read_bytes()==old and 'Permission denied' in r.get('error',''),r);check('EACCES leaves no temporary INI',not list(store.glob('.users.conf.qeli-tmp-*')))
   finally:store.chmod(0o700)
   check('nonroot write recovers after EACCES',api('/api/users/parallel-0','PUT',{'max_sessions':44}).get('ok') is True);check('nonroot atomic users file remains private and owned',users_path.stat().st_uid==65534 and users_path.stat().st_mode&0o777==0o600)
   complete=all(c['status']=='PASS' for c in checks)
  finally:
   for target in reversed(mounted):run(['umount',str(target)])
   stop();save(True);(root/'http-events.json').write_text(json.dumps(events,indent=2)+'\n');check('private namespace network restored',network()==before);save(True)
  assert complete,'Q06 storage/control regressions recorded'
 elif a.scenario=='users-live':
  clients=[];streams=[];ns='q06-client'
  def api(path,method='GET',body=None):
   r=req(path,method,body,headers=basic());assert r[0]==200,(method,path,r[0]);return r[1]
  def loaded(name):
   with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as c:
    c.settimeout(2);c.connect(env['QELI_CONTROL_SOCKET']);c.sendall((json.dumps({'cmd':'show-routes','username':name})+'\n').encode())
    with c.makefile('rb') as f:return json.loads(f.readline(65536)).get('ok') is True
  def present(name):return any(x.get('username')==name for x in api('/api/clients').get('clients',[]))
  def client_stop():
   for p in clients:
    if p.poll() is None:
     p.terminate()
     try:p.wait(timeout=25)
     except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
   clients.clear()
   for f in streams:f.close()
   streams.clear()
  try:
   for cmd in (['ip','netns','add',ns],['ip','link','add','q06-srv','type','veth','peer','name','q06-cli'],['ip','link','set','q06-cli','netns',ns],['ip','addr','add','198.18.0.1/30','dev','q06-srv'],['ip','link','set','q06-srv','up'],['ip','netns','exec',ns,'ip','link','set','lo','up'],['ip','netns','exec',ns,'ip','addr','add','198.18.0.2/30','dev','q06-cli'],['ip','netns','exec',ns,'ip','link','set','q06-cli','up'],['ip','netns','exec',ns,'ip','route','add','default','via','198.18.0.1']):run(cmd)
   run(['iptables','-A','INPUT','-i','q06-srv','-d','10.77.0.1','-j','DROP'])
   original=cfg.read_text().replace('[auth]','[auth]\nrequire_client_key_proof = false\nbind_static_to_session = false').replace('bind.address = 127.0.0.1','bind.address = 198.18.0.1')
   usage=Path('/etc/qeli/usage.json');usage.write_text(json.dumps({'live-'+t+'-quota':dict(used_down=1000000000,used_up=0,used_bytes=1000000000,last_seen=1,sessions=0) for t in ('tcp','udp')}));usage.chmod(0o600)
   for transport in ('tcp','udp'):
    cfg.write_text(original.replace('bind.transport = tcp','bind.transport = '+transport));cfg.chmod(0o600);start()
    for action in ('disable','update-disabled','delete','profile-denied','expiry','quota'):
     name='live-'+transport+'-'+action;body={'username':name,'password':'fixture-client-password','max_sessions':1}
     if action=='disable':
      group='live-limit-'+transport;check('create live group '+transport,api('/api/groups/'+group,'PUT',{'max_sessions':1,'bandwidth_limit_mbps':2}).get('ok') is True);body.update(group=group,max_sessions=0,static_ip='10.77.0.'+('50' if transport=='tcp' else '60'))
     value=api('/api/users','POST',body);check('create '+name,value.get('ok') is True,value)
     # The API confirms persistence/queued reload; wait for worker auth visibility.
     wait(lambda:loaded(name),'worker users reload did not complete: '+name)
     config=root/(name+'.conf');config.write_text('[qeli]\nserver = 198.18.0.1:24843\nproto = '+transport+'\nuser = '+name+'\npass = fixture-client-password\nmode = fake-tls\nbind_static = false\nquic = false\ndev = q06cli\ngateway = false\ndns = off\nkill_switch = false\ntimeout = 8\n[logging]\nlevel = info\n');config.chmod(0o600)
     client_env=dict(env,QELI_KNOWN_HOSTS=str(root/(name+'-known-hosts')),QELI_DEVICE_ID_FILE=str(root/(name+'-device-id')));log=(root/(name+'.log')).open('w');streams.append(log);proc=subprocess.Popen(['ip','netns','exec',ns,str(binary),'client','-c',str(config)],env=client_env,stdout=log,stderr=subprocess.STDOUT);clients.append(proc)
     wait(lambda:present(name),'client not authenticated: '+name);wait(lambda:'dev q06cli' in run(['ip','netns','exec',ns,'ip','route','get','10.77.0.1']),'client tunnel route missing: '+name);run(['ip','netns','exec',ns,'ping','-c','1','-W','2','10.77.0.1']);check(name+' has actual tunnel traffic',True)
     if action=='disable':
      row=next(x for x in api('/api/clients')['clients'] if x['username']==name);check(name+' gets fixed IP and group bandwidth',row['ip']==body['static_ip'] and row['bandwidth_limit_mbps']==2,row)
      check(name+' group bandwidth update saved',api('/api/groups/'+group,'PUT',{'max_sessions':1,'bandwidth_limit_mbps':3}).get('ok') is True)
      wait(lambda:any(x['username']==name and x['bandwidth_limit_mbps']==3 for x in api('/api/clients')['clients']),'group bandwidth not live');run(['ip','netns','exec',ns,'ping','-c','1','-W','2','10.77.0.1']);check(name+' remains usable after group bandwidth update',True)
      value=api('/api/users/'+name+'/disable','POST',{})
     elif action=='update-disabled':value=api('/api/users/'+name,'PUT',{'enabled':False})
     elif action=='delete':value=api('/api/users/'+name,'DELETE')
     elif action=='profile-denied':value=api('/api/users/'+name,'PUT',{'profiles':['other-profile']})
     elif action=='expiry':value=api('/api/usage/'+name+'/limit','POST',{'data_limit_gb':0,'expire_at':1})
     else:value=api('/api/usage/'+name+'/limit','POST',{'data_limit_gb':1,'expire_at':None})
     check(name+' mutation accepted',value.get('ok') is True,value)
     end=time.monotonic()+(15 if action in ('expiry','quota') else 3)
     while time.monotonic()<end and present(name):time.sleep(.1)
     still=present(name);probe=subprocess.run(['ip','netns','exec',ns,'ping','-c','1','-W','1','10.77.0.1'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
     ok=not still and probe.returncode!=0;checks.append(dict(name=name+' revokes open session and tunnel packets',status='PASS' if ok else 'FAIL',detail=dict(session_present=still,traffic_passes=probe.returncode==0)));save();print(('PASS ' if ok else 'FAIL ')+name+' live revoke',flush=True);client_stop()
    stop()
   complete=all(x['status']=='PASS' for x in checks)
  finally:
   client_stop();stop();run(['iptables','-D','INPUT','-i','q06-srv','-d','10.77.0.1','-j','DROP']);subprocess.run(['ip','link','del','q06-srv'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT);run(['ip','netns','del',ns]);save(True);(root/'http-events.json').write_text(json.dumps(events,indent=2)+'\n');after=network();(root/'network.json').write_text(json.dumps(dict(before=before,after=after),indent=2));check('private namespace network restored',after==before,[key for key in before if before[key]!=after[key]]);save(True)
  assert complete,'live revoke regression recorded'
 elif a.scenario=='users-policy':
  clients=[];streams=[];ns='q06-client'
  def api(path,method='GET',body=None):
   r=req(path,method,body,headers=basic());assert r[0]==200,(method,path,r[0]);return r[1]
  def loaded(name):
   with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as c:
    c.settimeout(2);c.connect(env['QELI_CONTROL_SOCKET']);c.sendall((json.dumps({'cmd':'show-routes','username':name})+'\n').encode())
    with c.makefile('rb') as f:return json.loads(f.readline(65536)).get('ok') is True
  def present(name):return any(x.get('username')==name for x in api('/api/clients').get('clients',[]))
  def client_stop():
   for p in clients:
    if p.poll() is None:
     p.terminate()
     try:p.wait(timeout=25)
     except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
   clients.clear()
   for f in streams:f.close()
   streams.clear()
  try:
   for cmd in (['ip','netns','add',ns],['ip','link','add','q06-srv','type','veth','peer','name','q06-cli'],['ip','link','set','q06-cli','netns',ns],['ip','addr','add','198.18.0.1/30','dev','q06-srv'],['ip','link','set','q06-srv','up'],['ip','netns','exec',ns,'ip','link','set','lo','up'],['ip','netns','exec',ns,'ip','addr','add','198.18.0.2/30','dev','q06-cli'],['ip','netns','exec',ns,'ip','link','set','q06-cli','up'],['ip','netns','exec',ns,'ip','route','add','default','via','198.18.0.1']):run(cmd)
   run(['iptables','-A','INPUT','-i','q06-srv','-d','10.77.0.1','-j','DROP'])
   for i in range(3):
    device_ns=ns+'-'+str(i);srv='q6srv'+str(i);cli='q6cli'+str(i);subnet='198.18.'+str(i+1)
    for cmd in (['ip','netns','add',device_ns],['ip','link','add',srv,'type','veth','peer','name',cli],['ip','link','set',cli,'netns',device_ns],['ip','addr','add',subnet+'.1/30','dev',srv],['ip','link','set',srv,'up'],['ip','netns','exec',device_ns,'ip','link','set','lo','up'],['ip','netns','exec',device_ns,'ip','addr','add',subnet+'.2/30','dev',cli],['ip','netns','exec',device_ns,'ip','link','set',cli,'up'],['ip','netns','exec',device_ns,'ip','route','add','default','via',subnet+'.1']):run(cmd)
    run(['iptables','-A','INPUT','-i',srv,'-d','10.77.0.1','-j','DROP'])
   original=cfg.read_text().replace('[auth]','[auth]\nrequire_client_key_proof = false\nbind_static_to_session = false').replace('bind.address = 127.0.0.1','bind.address = 198.18.0.1')
   usage=Path('/etc/qeli/usage.json');usage.write_text(json.dumps({'live-'+t+'-quota':dict(used_down=1000000000,used_up=0,used_bytes=1000000000,last_seen=1,sessions=0) for t in ('tcp','udp')}));usage.chmod(0o600)
   for transport in ('tcp','udp'):
    cfg.write_text(original.replace('bind.transport = tcp','bind.transport = '+transport));cfg.chmod(0o600);start()
    for action in ('acl','group-acl','own-override','subnets'):
     name='live-'+transport+'-'+action;body={'username':name,'password':'fixture-client-password','max_sessions':1}
     if action=='acl':body['allowed_networks']=['10.77.0.0/24','192.0.2.0/24']
     if action in ('group-acl','own-override'):
      group='policy-'+transport;check('create ACL group '+transport,api('/api/groups/'+group,'PUT',{'allowed_networks':[]}).get('ok') is True);body.update(group=group)
      if action=='own-override':body['allowed_networks']=['10.77.0.0/24']
     if action=='subnets':body['client_subnets']=['172.21.0.0/24']
     value=api('/api/users','POST',body);check('create '+name,value.get('ok') is True,value)
     # The API confirms persistence/queued reload; wait for worker auth visibility.
     wait(lambda:loaded(name),'worker users reload did not complete: '+name)
     config=root/(name+'.conf');config.write_text('[qeli]\nserver = 198.18.0.1:24843\nproto = '+transport+'\nuser = '+name+'\npass = fixture-client-password\nmode = fake-tls\nbind_static = false\nquic = false\ndev = q06cli\ngateway = false\ndns = off\nkill_switch = false\ntimeout = 8\n[logging]\nlevel = info\n');config.chmod(0o600)
     client_env=dict(env,QELI_KNOWN_HOSTS=str(root/(name+'-known-hosts')),QELI_DEVICE_ID_FILE=str(root/(name+'-device-id')));log=(root/(name+'.log')).open('w');streams.append(log);proc=subprocess.Popen(['ip','netns','exec',ns,str(binary),'client','-c',str(config)],env=client_env,stdout=log,stderr=subprocess.STDOUT);clients.append(proc)
     wait(lambda:present(name),'client not authenticated: '+name);wait(lambda:'dev q06cli' in run(['ip','netns','exec',ns,'ip','route','get','10.77.0.1']),'client tunnel route missing: '+name);run(['ip','netns','exec',ns,'ping','-c','1','-W','2','10.77.0.1']);check(name+' has actual tunnel traffic',True)
     if action=='acl':
      check(name+' equivalent ACL edit saved',api('/api/users/'+name,'PUT',{'allowed_networks':['192.0.2.0/24','10.77.0.0/24','192.0.2.0/24']}).get('ok') is True);time.sleep(.5)
      check(name+' equivalent ACL preserves session and packets',present(name) and subprocess.run(['ip','netns','exec',ns,'ping','-c','1','-W','1','10.77.0.1'],stdout=subprocess.DEVNULL).returncode==0)
      value=api('/api/users/'+name,'PUT',{'allowed_networks':['192.0.2.0/24']})
     elif action in ('group-acl','own-override'):value=api('/api/groups/'+group,'PUT',{'allowed_networks':['192.0.2.0/24']})
     else:
      run(['ip','netns','exec',ns,'ip','addr','add','172.21.0.2/32','dev','q06cli']);run(['ip','netns','exec',ns,'ping','-I','172.21.0.2','-c','1','-W','2','10.77.0.1']);check(name+' delegated source passes before removal',True)
      value=api('/api/users/'+name,'PUT',{'client_subnets':[]})
     check(name+' mutation accepted',value.get('ok') is True,value)
     if action=='own-override':
      time.sleep(.5);check(name+' own ACL overrides changed group without disconnect',present(name) and subprocess.run(['ip','netns','exec',ns,'ping','-c','1','-W','1','10.77.0.1'],stdout=subprocess.DEVNULL).returncode==0);client_stop();continue
     end=time.monotonic()+3
     while time.monotonic()<end and present(name):time.sleep(.1)
     still=present(name);probe=subprocess.run(['ip','netns','exec',ns,'ping','-c','1','-W','1','10.77.0.1'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
     ok=not still and probe.returncode!=0;checks.append(dict(name=name+' revokes open session and tunnel packets',status='PASS' if ok else 'FAIL',detail=dict(session_present=still,traffic_passes=probe.returncode==0)));save();print(('PASS ' if ok else 'FAIL ')+name+' live revoke',flush=True)
     if action=='subnets':
      gone='172.21.0.0/24' not in run(['ip','-4','route','show']);checks.append(dict(name=name+' removes delegated kernel route',status='PASS' if gone else 'FAIL'));save()
     client_stop()
    for inherited in (False,True):
     name='caps-'+transport+('-group' if inherited else '-user');body={'username':name,'password':'fixture-client-password','max_sessions':3}
     if inherited:
      group=name+'-template';check(name+' group seed',api('/api/groups/'+group,'PUT',{'max_sessions':3}).get('ok') is True);body.update(group=group,max_sessions=0)
     check(name+' user seed',api('/api/users','POST',body).get('ok') is True);wait(lambda:loaded(name),'cap seed reload');ips=[]
     for i in range(3):
      device_ns=ns+'-'+str(i);key=name+'-'+str(i);config=root/(key+'.conf');config.write_text('[qeli]\nserver = 198.18.0.1:24843\nproto = '+transport+'\nuser = '+name+'\npass = fixture-client-password\nmode = fake-tls\nbind_static = false\nquic = false\ndev = q06d'+str(i)+'\ngateway = false\ndns = off\nkill_switch = false\ntimeout = 8\n[logging]\nlevel = info\n');config.chmod(0o600)
      client_env=dict(env,QELI_KNOWN_HOSTS=str(root/(key+'-known-hosts')),QELI_DEVICE_ID_FILE=str(root/(key+'-device-id')));log=(root/(key+'.log')).open('w');streams.append(log);proc=subprocess.Popen(['ip','netns','exec',device_ns,str(binary),'client','-c',str(config)],env=client_env,stdout=log,stderr=subprocess.STDOUT);clients.append(proc)
      wait(lambda:len([x for x in api('/api/clients')['clients'] if x['username']==name])==i+1,'three device admission')
      wait(lambda:subprocess.run(['ip','netns','exec',device_ns,'ip','link','show','q06d'+str(i)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0,'client device setup');ips.append(next(x['ip'] for x in api('/api/clients')['clients'] if x['username']==name and x['ip'] not in ips));run(['ip','netns','exec',device_ns,'ping','-I','q06d'+str(i),'-c','1','-W','2','10.77.0.1']);time.sleep(.05)
     check(name+' has three actual devices',len(set(ips))==3)
     r=api('/api/groups/'+group,'PUT',{'max_sessions':1}) if inherited else api('/api/users/'+name,'PUT',{'max_sessions':1});check(name+' cap reduction saved',r.get('ok') is True)
     end=time.monotonic()+3
     while time.monotonic()<end and len([x for x in api('/api/clients')['clients'] if x['username']==name])!=1:time.sleep(.1)
     remaining=[x['ip'] for x in api('/api/clients')['clients'] if x['username']==name];ok=remaining==[ips[-1]];checks.append(dict(name=name+' cap immediately keeps newest device',status='PASS' if ok else 'FAIL',detail=dict(ips=ips,remaining=remaining)));save();print(('PASS ' if ok else 'FAIL ')+name+' live cap',flush=True)
     newest=subprocess.run(['ip','netns','exec',ns+'-2','ping','-I','q06d2','-c','1','-W','1','10.77.0.1'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5);check(name+' newest device retains tunnel packets',newest.returncode==0,newest.stdout)
     client_stop()
    stop()
   complete=all(x['status']=='PASS' for x in checks)
  finally:
   client_stop();stop()
   for i in range(3):
    srv='q6srv'+str(i);run(['iptables','-D','INPUT','-i',srv,'-d','10.77.0.1','-j','DROP']);run(['ip','link','del',srv]);run(['ip','netns','del',ns+'-'+str(i)])
   run(['iptables','-D','INPUT','-i','q06-srv','-d','10.77.0.1','-j','DROP']);subprocess.run(['ip','link','del','q06-srv'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT);run(['ip','netns','del',ns]);save(True);(root/'http-events.json').write_text(json.dumps(events,indent=2)+'\n');after=network();(root/'network.json').write_text(json.dumps(dict(before=before,after=after),indent=2));check('private namespace network restored',after==before,[key for key in before if before[key]!=after[key]]);save(True)
  assert complete,'live revoke regression recorded'
 elif a.scenario=='users-admission':
  clients=[];streams=[];ns='q06-client'
  def api(path,method='GET',body=None):
   r=req(path,method,body,headers=basic());assert r[0]==200,(method,path,r[0]);return r[1]
  def loaded(name):
   with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as c:
    c.settimeout(2);c.connect(env['QELI_CONTROL_SOCKET']);c.sendall((json.dumps({'cmd':'show-routes','username':name})+'\n').encode())
    with c.makefile('rb') as f:return json.loads(f.readline(65536)).get('ok') is True
  def present(name):return any(x.get('username')==name for x in api('/api/clients').get('clients',[]))
  def client_stop():
   for p in clients:
    if p.poll() is None:
     p.terminate()
     try:p.wait(timeout=25)
     except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
   clients.clear()
   for f in streams:f.close()
   streams.clear()
  try:
   for cmd in (['ip','netns','add',ns],['ip','link','add','q06-srv','type','veth','peer','name','q06-cli'],['ip','link','set','q06-cli','netns',ns],['ip','addr','add','198.18.0.1/30','dev','q06-srv'],['ip','link','set','q06-srv','up'],['ip','netns','exec',ns,'ip','link','set','lo','up'],['ip','netns','exec',ns,'ip','addr','add','198.18.0.2/30','dev','q06-cli'],['ip','netns','exec',ns,'ip','link','set','q06-cli','up'],['ip','netns','exec',ns,'ip','route','add','default','via','198.18.0.1']):run(cmd)
   run(['iptables','-A','INPUT','-i','q06-srv','-d','10.77.0.1','-j','DROP'])
   for i in range(3):
    device_ns=ns+'-'+str(i);srv='q6srv'+str(i);cli='q6cli'+str(i);subnet='198.18.'+str(i+1)
    for cmd in (['ip','netns','add',device_ns],['ip','link','add',srv,'type','veth','peer','name',cli],['ip','link','set',cli,'netns',device_ns],['ip','addr','add',subnet+'.1/30','dev',srv],['ip','link','set',srv,'up'],['ip','netns','exec',device_ns,'ip','link','set','lo','up'],['ip','netns','exec',device_ns,'ip','addr','add',subnet+'.2/30','dev',cli],['ip','netns','exec',device_ns,'ip','link','set',cli,'up'],['ip','netns','exec',device_ns,'ip','route','add','default','via',subnet+'.1']):run(cmd)
    run(['iptables','-A','INPUT','-i',srv,'-d','10.77.0.1','-j','DROP'])
   original=cfg.read_text().replace('[auth]','[auth]\nrequire_client_key_proof = false\nbind_static_to_session = false').replace('bind.address = 127.0.0.1','bind.address = 198.18.0.1')+'\nperf.connection.new_session_rate_max = 200\n'
   usage=Path('/etc/qeli/usage.json');usage.write_text(json.dumps({'live-'+t+'-quota':dict(used_down=1000000000,used_up=0,used_bytes=1000000000,last_seen=1,sessions=0) for t in ('tcp','udp')}));usage.chmod(0o600)
   for transport in ('tcp','udp'):
    cfg.write_text(original.replace('bind.transport = tcp','bind.transport = '+transport));cfg.chmod(0o600);start()
    for action in ('same-device','fixed-ip','session-cap'):
     name='admit-'+transport+'-'+action;body={'username':name,'password':'fixture-client-password','max_sessions':1 if action=='session-cap' else 0}
     if action=='fixed-ip':body['static_ip']='10.77.0.42'
     check(name+' seed',api('/api/users','POST',body).get('ok') is True);wait(lambda:loaded(name),'admission seed reload')
     for i in range(2):
      device_ns=ns+'-'+str(i);key=name+'-'+str(i);config=root/(key+'.conf');config.write_text('[qeli]\nserver = 198.18.0.1:24843\nproto = '+transport+'\nuser = '+name+'\npass = fixture-client-password\nmode = fake-tls\nbind_static = false\nquic = false\ndev = q06d'+str(i)+'\ngateway = false\ndns = off\nkill_switch = false\ntimeout = 8\n[logging]\nlevel = info\n');config.chmod(0o600)
      device_file=root/(name+'-shared-device-id' if action=='same-device' else key+'-device-id')
      client_env=dict(env,QELI_KNOWN_HOSTS=str(root/(key+'-known-hosts')),QELI_DEVICE_ID_FILE=str(device_file));log=(root/(key+'.log')).open('w');streams.append(log);proc=subprocess.Popen(['ip','netns','exec',device_ns,str(binary),'client','-c',str(config)],env=client_env,stdout=log,stderr=subprocess.STDOUT);clients.append(proc)
      wait(lambda:any(x['username']==name and x['peer'].startswith('198.18.'+str(i+1)+'.2:') for x in api('/api/clients')['clients']),'device admission')
      wait(lambda:subprocess.run(['ip','netns','exec',device_ns,'ip','link','show','q06d'+str(i)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0,'device tunnel setup')
      if action=='fixed-ip':check(key+' owns its fixed IPv4',any(x['username']==name and x['ip']=='10.77.0.42' for x in api('/api/clients')['clients']))
      run(['ip','netns','exec',device_ns,'ping','-I','q06d'+str(i),'-c','1','-W','2','10.77.0.1'])
     # Keep both processes alive: a plain EOF can trigger the old client's reconnect loop.
     samples=[];end=time.monotonic()+10
     while time.monotonic()<end:
      rows=[x for x in api('/api/clients')['clients'] if x['username']==name];samples.append([x['peer'] for x in rows]);time.sleep(.25)
     probe=subprocess.run(['ip','netns','exec',ns+'-1','ping','-I','q06d1','-c','1','-W','2','10.77.0.1'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
     old_log=(root/(name+'-0.log')).read_text();terminal='server terminated the session: Session replaced by a newer connection' in old_log
     # The CLI must stop retrying even though the OS process may remain alive for cleanup.
     ok=all(len(x)==1 and x[0].startswith('198.18.2.2:') for x in samples) and probe.returncode==0 and terminal
     checks.append(dict(name=name+' replacement remains newest without automatic reconnect',status='PASS' if ok else 'FAIL',detail=dict(samples=samples,old_client_exit=clients[0].poll(),new_client_exit=clients[1].poll(),terminal=terminal,probe=probe.stdout)));save();print(('PASS ' if ok else 'FAIL ')+name+' stable replacement',flush=True)
     client_stop();api('/api/clients/'+name+'/kick','POST',{})
     wait(lambda:not present(name),'admission teardown')
     # Reopen after both owners terminate to detect leaked or stolen device leases.
     check(name+' no orphan session after both clients stop',not present(name))
     check(name+' user teardown',api('/api/users/'+name,'DELETE').get('ok') is True)
    stop()
   # A device cap belongs to each profile, even when the account is shared.
   second='\n[profile:fixture2]\nbind.address = 198.18.0.1\nbind.port = 24844\nbind.transport = tcp\ntun.name = qauth2\ntun.address = 10.78.0.1\npool.cidr = 10.78.0.0/24\nrouting.nat.enabled = false\nrouting.ipv6.mode = off\ndns.enabled = false\nobf.mode = fake-tls\n'
   cfg.write_text(original+second);cfg.chmod(0o600);start();name='admit-profile-scope'
   check(name+' scoped user seed',api('/api/users','POST',{'username':name,'password':'fixture-client-password','max_sessions':1,'profiles':['fixture','fixture2']}).get('ok') is True);wait(lambda:loaded(name),'profile seed reload')
   for i in range(2):
    key=name+'-'+str(i);device_ns=ns+'-'+str(i);config=root/(key+'.conf');config.write_text('[qeli]\nserver = 198.18.0.1:'+str(24843+i)+'\nproto = tcp\nuser = '+name+'\npass = fixture-client-password\nmode = fake-tls\nbind_static = false\nquic = false\ndev = q06d'+str(i)+'\ngateway = false\ndns = off\nkill_switch = false\ntimeout = 8\n[logging]\nlevel = info\n');config.chmod(0o600)
    log=(root/(key+'.log')).open('w');streams.append(log);client_env=dict(env,QELI_KNOWN_HOSTS=str(root/(key+'-known-hosts')),QELI_DEVICE_ID_FILE=str(root/(key+'-device-id')));clients.append(subprocess.Popen(['ip','netns','exec',device_ns,str(binary),'client','-c',str(config)],env=client_env,stdout=log,stderr=subprocess.STDOUT))
    wait(lambda:len([x for x in api('/api/clients')['clients'] if x['username']==name])==i+1,'profile device admission');wait(lambda:subprocess.run(['ip','netns','exec',device_ns,'ip','link','show','q06d'+str(i)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0,'profile device setup');run(['ip','netns','exec',device_ns,'ping','-I','q06d'+str(i),'-c','1','-W','2','10.'+str(77+i)+'.0.1'])
   rows=[x for x in api('/api/clients')['clients'] if x['username']==name];check(name+' one device remains active on each profile',sorted(x['profile'] for x in rows)==['fixture','fixture2'])
   check(name+' narrow profile allowlist saved',api('/api/users/'+name,'PUT',{'profiles':['fixture2']}).get('ok') is True);wait(lambda:[x['profile'] for x in api('/api/clients')['clients'] if x['username']==name]==['fixture2'],'profile selective revoke')
   kept=subprocess.run(['ip','netns','exec',ns+'-1','ping','-I','q06d1','-c','1','-W','2','10.78.0.1'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5);check(name+' allowed profile retains tunnel traffic',kept.returncode==0,kept.stdout)
   check(name+' deleting account accepted',api('/api/users/'+name,'DELETE').get('ok') is True);wait(lambda:not present(name),'profile delete revoke');check(name+' deletion removes all profile sessions',not present(name));client_stop();stop()
   complete=all(x['status']=='PASS' for x in checks)
  finally:
   client_stop();stop()
   for i in range(3):
    srv='q6srv'+str(i);run(['iptables','-D','INPUT','-i',srv,'-d','10.77.0.1','-j','DROP']);run(['ip','link','del',srv]);run(['ip','netns','del',ns+'-'+str(i)])
   run(['iptables','-D','INPUT','-i','q06-srv','-d','10.77.0.1','-j','DROP']);subprocess.run(['ip','link','del','q06-srv'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT);run(['ip','netns','del',ns]);save(True);(root/'http-events.json').write_text(json.dumps(events,indent=2)+'\n');after=network();(root/'network.json').write_text(json.dumps(dict(before=before,after=after),indent=2));check('private namespace network restored',after==before,[key for key in before if before[key]!=after[key]]);save(True)
  assert complete,'live revoke regression recorded'
 elif a.scenario=='users-bandwidth':
  meter=None;meter_log=None;clients=[];streams=[];ns='q06-client'
  def api(path,method='GET',body=None):
   r=req(path,method,body,headers=basic());assert r[0]==200,(method,path,r[0]);return r[1]
  def loaded(name):
   with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as c:
    c.settimeout(2);c.connect(env['QELI_CONTROL_SOCKET']);c.sendall((json.dumps({'cmd':'show-routes','username':name})+'\n').encode())
    with c.makefile('rb') as f:return json.loads(f.readline(65536)).get('ok') is True
  def present(name):return any(x.get('username')==name for x in api('/api/clients').get('clients',[]))
  def client_stop():
   for p in clients:
    if p.poll() is None:
     p.terminate()
     try:p.wait(timeout=25)
     except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
   clients.clear()
   for f in streams:f.close()
   streams.clear()
  try:
   for cmd in (['ip','netns','add',ns],['ip','link','add','q06-srv','type','veth','peer','name','q06-cli'],['ip','link','set','q06-cli','netns',ns],['ip','addr','add','198.18.0.1/30','dev','q06-srv'],['ip','link','set','q06-srv','up'],['ip','netns','exec',ns,'ip','link','set','lo','up'],['ip','netns','exec',ns,'ip','addr','add','198.18.0.2/30','dev','q06-cli'],['ip','netns','exec',ns,'ip','link','set','q06-cli','up'],['ip','netns','exec',ns,'ip','route','add','default','via','198.18.0.1']):run(cmd)
   run(['iptables','-A','INPUT','-i','q06-srv','-d','10.77.0.1','-j','DROP'])
   for i in range(3):
    device_ns=ns+'-'+str(i);srv='q6srv'+str(i);cli='q6cli'+str(i);subnet='198.18.'+str(i+1)
    for cmd in (['ip','netns','add',device_ns],['ip','link','add',srv,'type','veth','peer','name',cli],['ip','link','set',cli,'netns',device_ns],['ip','addr','add',subnet+'.1/30','dev',srv],['ip','link','set',srv,'up'],['ip','netns','exec',device_ns,'ip','link','set','lo','up'],['ip','netns','exec',device_ns,'ip','addr','add',subnet+'.2/30','dev',cli],['ip','netns','exec',device_ns,'ip','link','set',cli,'up'],['ip','netns','exec',device_ns,'ip','route','add','default','via',subnet+'.1']):run(cmd)
    run(['iptables','-A','INPUT','-i',srv,'-d','10.77.0.1','-j','DROP'])
   original=cfg.read_text().replace('[auth]','[auth]\nrequire_client_key_proof = false\nbind_static_to_session = false').replace('bind.address = 127.0.0.1','bind.address = 198.18.0.1')
   usage=Path('/etc/qeli/usage.json');usage.write_text(json.dumps({'live-'+t+'-quota':dict(used_down=1000000000,used_up=0,used_bytes=1000000000,last_seen=1,sessions=0) for t in ('tcp','udp')}));usage.chmod(0o600)
   for transport in ('tcp','udp'):
    cfg.write_text(original.replace('bind.transport = tcp','bind.transport = '+transport));cfg.chmod(0o600);start()
    name='bw-'+transport;group=name+'-group'
    check(name+' unlimited group seed',api('/api/groups/'+group,'PUT',{'bandwidth_limit_mbps':0}).get('ok') is True)
    check(name+' inherited user seed',api('/api/users','POST',{'username':name,'password':'fixture-client-password','group':group,'bandwidth':{'limit_mbps':0,'burst_mbps':0}}).get('ok') is True);wait(lambda:loaded(name),'bandwidth seed reload')
    config=root/(name+'.conf');config.write_text('[qeli]\nserver = 198.18.0.1:24843\nproto = '+transport+'\nuser = '+name+'\npass = fixture-client-password\nmode = fake-tls\nbind_static = false\nquic = false\ndev = q06bw\ngateway = false\ndns = off\nkill_switch = false\ntimeout = 8\n[logging]\nlevel = info\n');config.chmod(0o600)
    client_env=dict(env,QELI_KNOWN_HOSTS=str(root/(name+'-known-hosts')),QELI_DEVICE_ID_FILE=str(root/(name+'-device-id')));log=(root/(name+'.log')).open('w');streams.append(log);proc=subprocess.Popen(['ip','netns','exec',ns,str(binary),'client','-c',str(config)],env=client_env,stdout=log,stderr=subprocess.STDOUT);clients.append(proc)
    wait(lambda:present(name),'bandwidth client admission');wait(lambda:subprocess.run(['ip','netns','exec',ns,'ip','link','show','q06bw'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0,'bandwidth device setup')
    run(['ip','netns','exec',ns,'ping','-I','q06bw','-c','1','-W','2','10.77.0.1'])
    meter_port=24900
    def measure(label,cap,reverse=False):
     nonlocal meter,meter_log,meter_port
     meter_port+=1;meter_log=(root/(name+'-'+label+'-iperf-server.log')).open('w')
     meter=subprocess.Popen(['iperf3','--server','--one-off','--bind','10.77.0.1','--port',str(meter_port)],stdout=meter_log,stderr=subprocess.STDOUT);wait(lambda:(':'+str(meter_port)) in run(['ss','-lnt']),'private meter readiness')
     cmd=['ip','netns','exec',ns,'iperf3','--client','10.77.0.1','--port',str(meter_port),'--time','3','--omit','1','--parallel','2','--json']
     if reverse:cmd+=['--reverse']
     result=json.loads(run(cmd));assert 'error' not in result,result.get('error');(root/(name+'-'+label+'.json')).write_text(json.dumps(result,indent=2)+'\n');mbps=result['end']['sum_received']['bits_per_second']/1000000
     ok=mbps>5 if cap==0 else .40*cap<=mbps<=1.35*cap
     check(name+' '+label+' actual aggregate throughput',ok,dict(receiver_mbps=round(mbps,3),limit_mbps=cap,direction='download' if reverse else 'upload',parallel_flows=2,measured_seconds=3,omitted_warmup_seconds=1))
     assert meter.wait(timeout=10)==0,'private meter exit';meter_log.close();meter=None;meter_log=None
    def applied(cap):wait(lambda:next(x['bandwidth_limit_mbps'] for x in api('/api/clients')['clients'] if x['username']==name)==cap,'live bandwidth policy')
    measure('unlimited-upload',0);measure('unlimited-download',0,True)
    check(name+' group cap 2 saved',api('/api/groups/'+group,'PUT',{'bandwidth_limit_mbps':2}).get('ok') is True);applied(2)
    measure('group-upload',2);measure('group-download',2,True)
    check(name+' own cap 1 and legacy burst 99 saved',api('/api/users/'+name,'PUT',{'bandwidth':{'limit_mbps':1,'burst_mbps':99}}).get('ok') is True);applied(1)
    measure('own-upload',1);measure('own-download',1,True)
    check(name+' group cap 3 saved',api('/api/groups/'+group,'PUT',{'bandwidth_limit_mbps':3}).get('ok') is True);applied(1);measure('own-override',1,True)
    check(name+' zero own cap restores inheritance',api('/api/users/'+name,'PUT',{'bandwidth':{'limit_mbps':0,'burst_mbps':99}}).get('ok') is True);applied(3);measure('inherit-after-clear',3,True)
    check(name+' zero group cap restores unlimited',api('/api/groups/'+group,'PUT',{'bandwidth_limit_mbps':0}).get('ok') is True);applied(0);measure('unlimited-after-clear',0,True)
    client_stop()
    stop()
   complete=all(x['status']=='PASS' for x in checks)
  finally:
   if meter and meter.poll() is None:meter.terminate();meter.wait(timeout=5)
   if meter_log:meter_log.close()
   client_stop();stop()
   for i in range(3):
    srv='q6srv'+str(i);run(['iptables','-D','INPUT','-i',srv,'-d','10.77.0.1','-j','DROP']);run(['ip','link','del',srv]);run(['ip','netns','del',ns+'-'+str(i)])
   run(['iptables','-D','INPUT','-i','q06-srv','-d','10.77.0.1','-j','DROP']);subprocess.run(['ip','link','del','q06-srv'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT);run(['ip','netns','del',ns]);save(True);(root/'http-events.json').write_text(json.dumps(events,indent=2)+'\n');after=network();(root/'network.json').write_text(json.dumps(dict(before=before,after=after),indent=2));check('private namespace network restored',after==before,[key for key in before if before[key]!=after[key]]);save(True)
  assert complete,'live revoke regression recorded'
 elif a.scenario=='runtime':
  def api(path,method='GET',body=None):
   r=req(path,method,body,headers=basic(pw=password));check(method+' '+path+' HTTP response',r[0]==200,r[0]);return r[1]
  def current():
   r=api('/api/config/raw');check('current raw exact revision',r.get('ok') is True and r['revision']==hashlib.sha256(cfg.read_bytes()).hexdigest());return r
  def putraw(raw):
   c=current();return api('/api/config/raw','PUT',{'raw':raw,'expected_revision':c['revision']})
  def worker():
   text=run(['ss','-lntp']);m=re.search(r'127\.0\.0\.1:24843\s+.*pid=(\d+)',text);return int(m[1]) if m else None
  def unchanged(label,old,wpid):check(label+' leaves config and worker unchanged',cfg.read_bytes()==old and worker()==wpid and sup.poll() is None)
  try:
   start();original=cfg.read_text();sup_pid=sup.pid;wpid=worker();check('private worker pid known',wpid is not None);old_cookie=token_from(login())
   modes=['reality-tls','reality','fake-tls','obfs-ws','obfs-none','plain','udp-fake-tls','udp-quic','udp-obfs','obfs-awg']
   for mode in modes:
    old=cfg.read_bytes();c=current();preview=api('/api/config/quickstart/'+mode);check(mode+' preview does not persist',preview.get('ok') is True and cfg.read_bytes()==old and worker()==wpid)
    result=api('/api/config/quickstart/'+mode,'POST',{'expected_revision':c['revision'],'ip_mode':'ipv4'});check(mode+' apply saves one complete profile',result.get('ok') is True and result['revision']==hashlib.sha256(cfg.read_bytes()).hexdigest(),{'ok':result.get('ok'),'error':result.get('error')});check(mode+' save preserves supervisor and worker',sup.pid==sup_pid and worker()==wpid)
    stored=api('/api/config')['config'];check(mode+' returned profile matches actual stored profile',next(p for p in stored['profiles'] if p['name']==mode)==result['profile'])
    c=current();repeated=api('/api/config/quickstart/'+mode,'POST',{'expected_revision':c['revision'],'ip_mode':'ipv4'});check(mode+' reapply preserves profile credentials',repeated.get('ok') is True and repeated['reused'] is True and repeated['sid']==result['sid'] and repeated['obfs_key']==result['obfs_key']);check(mode+' no implicit restart after reapply',worker()==wpid)
   for mode,body in [('fake-tls',{}),('fake-tls',{'expected_revision':'0'*64}),('bad-mode',{'expected_revision':current()['revision']}),('fake-tls',{'expected_revision':current()['revision'],'ip_mode':'bogus'})]:
    old=cfg.read_bytes();r=api('/api/config/quickstart/'+mode,'POST',body);check('invalid Quick Start request rejected',r.get('ok') is False,{'kind':r.get('kind'),'error':r.get('error')});unchanged('invalid Quick Start',old,wpid)
   # Restore through the INI API, then exercise actual credential hot reload.
   r=putraw(original);check('Quick Start cleanup through INI save',r.get('ok') is True)
   old_password=password;new_password='fixture replacement #; password'
   hashed=api('/api/hash-password','POST',{'password':new_password});check('password hash endpoint valid',hashed.get('ok') is True and hashed.get('hash','').startswith('$argon2'))
   form=api('/api/config');form['config']['web']['password_hash']=hashed['hash'];r=api('/api/config','PUT',{'config':form['config'],'expected_revision':form['revision']});check('password change saved and applied live',r.get('ok') is True and r.get('web_settings_applied') is True)
   check('password reload replaces no process',sup.pid==sup_pid and worker()==wpid)
   check('old cookie revoked immediately',req('/api/status',token=old_cookie)[0]==401)
   check('old password rejected immediately',login(pw=old_password)[0]==401)
   password=new_password;new_cookie=token_from(login(pw=password));check('new password and new cookie accepted live',req('/api/status',token=new_cookie)[0]==200)
   form=api('/api/config');form['config']['web']['allowed_ips']=['127.0.0.1'];form['config']['web']['trusted_proxies']=[]
   r=api('/api/config','PUT',{'config':form['config'],'expected_revision':form['revision']});check('allowlist applies live',r.get('ok') is True and r.get('web_settings_applied') is True)
   check('allowed peer remains admitted',req('/api/status',token=new_cookie)[0]==200);check('disallowed peer denied live despite forged forwarding',req('/api/status',token=new_cookie,source='127.0.0.2',headers={'X-Forwarded-For':'127.0.0.1'})[0]==403)
   form=api('/api/config');form['config']['web']['allowed_ips']=[];r=api('/api/config','PUT',{'config':form['config'],'expected_revision':form['revision']});check('allowlist removal recovers peer live',r.get('ok') is True and req('/api/status',token=new_cookie,source='127.0.0.2')[0]==200)
   # Startup-only values remain fixed until a full restart, and worker restart refuses.
   form=api('/api/config');form['config']['web']['port']=24881;form['config']['web']['base_path']='/newmount';r=api('/api/config','PUT',{'config':form['config'],'expected_revision':form['revision']});check('startup-only changes explicitly require full restart',r.get('ok') is True and r.get('needs_full_restart') is True)
   check('old listener and router remain active until full restart',req('/api/status',token=new_cookie)[0]==200 and req('/newmount/login',use_prefix=False)[0]==404)
   r=api('/api/server/restart','POST',{});check('worker restart refuses startup-only changes',r.get('ok') is False and r.get('kind')=='full_restart_required');check('refused restart leaves healthy worker',worker()==wpid)
   r=putraw(original);check('restore startup settings through API',r.get('ok') is True);password=old_password
   # A hand-edited invalid file must not kill a known-good worker.
   for label,bad in [('invalid INI','not valid INI'),('invalid runtime profile',original.replace('bind.port = 24843','bind.port = 0')),('host overlap',original.replace('10.77.0.1','192.0.2.2').replace('10.77.0.0/24','192.0.2.0/24'))]:
    cfg.write_text(bad);cfg.chmod(0o600);r=api('/api/server/restart','POST',{});check(label+' restart refused',r.get('ok') is False,{'error':r.get('error')});check(label+' preserves worker and supervisor',worker()==wpid and sup.pid==sup_pid);cfg.write_text(original);cfg.chmod(0o600)
   # Real worker replacement, with the HTTP supervisor and session retained.
   old_cookie=token_from(login(pw=password));r=api('/api/server/restart','POST',{});check('valid worker restart accepted',r.get('ok') is True)
   wait(lambda:worker() is not None and worker()!=wpid,'worker replacement did not complete');new_worker=worker();check('worker pid changed and supervisor stayed',new_worker!=wpid and sup.pid==sup_pid and sup.poll() is None);check('old worker gone',not Path('/proc/'+str(wpid)).exists());check('admin cookie survives worker restart',req('/api/status',token=old_cookie)[0]==200)
   r=api('/api/server/full-restart','POST',{});check('manual namespace instance refuses absent systemd',r.get('ok') is False and 'systemd' in r.get('error','').lower());check('full restart refusal leaves worker alive',worker()==new_worker and sup.poll() is None)
   complete=True
  finally:
   stop();save(True);(root/'http-events.json').write_text(json.dumps(events,indent=2)+'\n');check('private namespace network restored',network()==before);save(True)
  print('PASS Q05 runtime '+str(len(checks))+' checks',flush=True)
 elif a.scenario=='faults':
  def api(path,method='GET',body=None):
   r=req(path,method,body,headers=basic());check(method+' '+path+' HTTP response',r[0]==200,r[0]);return r[1]
  def worker():
   m=re.search(r'127\.0\.0\.1:24843\s+.*pid=(\d+)',run(['ss','-lntp']));return int(m[1]) if m else None
  def warnings():return api('/api/status').get('warnings',[])
  def wait_warning(needle):wait(lambda:any(needle in w for w in req('/api/status',headers=basic())[1].get('warnings',[])),'missing full restart outcome: '+needle)
  marker=Path('/tmp/q05-systemctl.calls');mode=Path('/tmp/q05-systemctl.mode');mounts=[]
  # This shim is bind-mounted only inside the already-verified private mount namespace.
  mock=Path('/tmp/q05-systemctl');mock.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> /tmp/q05-systemctl.calls\ncase "$(cat /tmp/q05-systemctl.mode)" in timeout) sleep 30;; esac\nexit 1\n');mock.chmod(0o755)
  try:
   start();original=cfg.read_bytes();wpid=worker();pid=sup.pid
   Path('/run/systemd/system').mkdir(parents=True);run(['mount','--bind',str(mock),'/usr/bin/systemctl']);mounts.append('/usr/bin/systemctl');mode.write_text('reject')
   r=api('/api/server/full-restart','POST',{});check('detached full restart reports request acceptance',r.get('ok') is True);wait_warning('exited with');check('systemctl rejection surfaced in status',any('Restart did NOT take effect:' in w and 'exited with' in w for w in warnings()));check('rejected dispatch preserves live worker and config',worker()==wpid and cfg.read_bytes()==original and sup.pid==pid);calls=marker.read_text().splitlines();check('exact selected unit is the only shim dispatch',calls==['restart '+r['unit']])
   r=api('/api/server/full-restart','POST',{});check('second request accepted before delayed check',r.get('ok') is True);cfg.write_text('not valid INI');cfg.chmod(0o600);wait_warning('restart refused');check('delayed revalidation prevented command dispatch',marker.read_text().splitlines()==calls and worker()==wpid);cfg.write_bytes(original);cfg.chmod(0o600)
   mode.write_text('timeout');started=time.monotonic();r=api('/api/server/full-restart','POST',{});check('timeout dispatch initially accepted',r.get('ok') is True);wait_warning('could not confirm');elapsed=time.monotonic()-started;check('timeout outcome explicitly uncertain within bound',15<=elapsed<23 and any('may already be queued' in w for w in warnings()),{'seconds':round(elapsed,3)});check('timeout killed owned shim child and preserved worker',worker()==wpid and 'sleep 30' not in run(['ps','-eo','args']))
   complete=True
  finally:
   stop()
   for target in reversed(mounts):run(['umount',target])
   save(True);(root/'http-events.json').write_text(json.dumps(events,indent=2)+'\n');check('private namespace network restored',network()==before);save(True)
  print('PASS Q05 detached faults '+str(len(checks))+' checks',flush=True)
 elif a.scenario=='crash':
  shim_c=r"""
 #define _GNU_SOURCE
 #include <dlfcn.h>
 #include <errno.h>
 #include <fcntl.h>
 #include <stdio.h>
 #include <string.h>
 #include <sys/stat.h>
 #include <unistd.h>
 static int action(const char *want) { char b[64]={0}; int fd=open("/tmp/q05-fault-action",O_RDONLY);if(fd<0)return 0;ssize_t n=read(fd,b,63);close(fd);return n>0 && !strcmp(b,want); }
 static void gate(const char *event) {int fd=open("/tmp/q05-fault-event",O_CREAT|O_TRUNC|O_WRONLY,0600);if(fd>=0){write(fd,event,strlen(event));close(fd);}while(access("/tmp/q05-fault-action",F_OK)==0)usleep(10000);}
 int rename(const char *old,const char *next) { static int(*real)(const char*,const char*);if(!real)real=dlsym(RTLD_NEXT,"rename");int target=!strcmp(next,"/etc/qeli/server.conf");if(target && action("before-rename"))gate("before-rename");int rc=real(old,next);if(rc==0 && target && action("after-rename"))gate("after-rename");return rc; }
 int fsync(int fd) { static int(*real)(int);if(!real)real=dlsym(RTLD_NEXT,"fsync");struct stat st;char path[64],name[512]={0};snprintf(path,sizeof(path),"/proc/self/fd/%d",fd);ssize_t n=readlink(path,name,511);if(n>=0 && fstat(fd,&st)==0 && S_ISDIR(st.st_mode) && !strcmp(name,"/etc/qeli") && action("dir-fsync")){unlink("/tmp/q05-fault-action");errno=EIO;return -1;}return real(fd); }
 """
  shim=Path('/tmp/q05-fault.so');c=Path('/tmp/q05-fault.c');c.write_text(shim_c);run(['gcc','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror','-o',str(shim),str(c),'-ldl']);env['LD_PRELOAD']=str(shim);action=Path('/tmp/q05-fault-action');event=Path('/tmp/q05-fault-event')
  def api(path,method='GET',body=None):
   r=req(path,method,body,headers=basic());check(method+' '+path+' HTTP response',r[0]==200,r[0]);return r[1]
  def worker():
   m=re.search(r'127\.0\.0\.1:24843\s+.*pid=(\d+)',run(['ss','-lntp']));return int(m[1]) if m else None
  def putraw(raw,revision):return api('/api/config/raw','PUT',{'raw':raw,'expected_revision':revision})
  def crash():
   wp=worker();check('owned worker available before crash',wp is not None)
   os.kill(wp,signal.SIGKILL);sup.kill();sup.wait(timeout=10);stream.close()
  try:
   start();original=cfg.read_bytes();check('fault shim loaded in private supervisor',str(shim) in Path('/proc/'+str(sup.pid)+'/maps').read_text())
   for phase in ('before-rename','after-rename'):
    current=api('/api/config/raw');old=cfg.read_bytes();next_raw=current['raw']+'\n# crash '+phase+'\n';action.write_text(phase);event.unlink(missing_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
     pending=pool.submit(req,'/api/config/raw','PUT',{'raw':next_raw,'expected_revision':current['revision']},basic())
     wait(lambda:event.exists() and event.read_text()==phase,'write publication gate not hit')
     check(phase+' rollback snapshot already exists',any(p.read_bytes()==old for p in cfg.parent.joinpath('.config-history').glob('*.conf')))
     check(phase+' disk is exact expected side of rename',cfg.read_bytes()==old if phase=='before-rename' else cfg.read_bytes().endswith(('# crash '+phase+'\n').encode()))
     leftovers=list(cfg.parent.glob('.server.conf.qeli-tmp-*'));check(phase+' temporary inodes remain private',all(p.stat().st_mode&0o777==0o600 for p in leftovers));crash();action.unlink(missing_ok=True)
     try:pending.result();disconnected=False
     except (ConnectionError,OSError,http.client.HTTPException):disconnected=True
     check(phase+' interrupted HTTP gives no false success',disconnected)
    check(phase+' crash leaves a complete readable INI',cfg.read_bytes()==old if phase=='before-rename' else cfg.read_bytes().endswith(('# crash '+phase+'\n').encode()))
    # Only remove exact private temporary paths witnessed before this deliberate SIGKILL.
    for p in leftovers:p.unlink(missing_ok=True)
    start();check(phase+' exact release restarts and admin works',login()[0]==200 and worker() is not None)
   current=api('/api/config/raw');old=cfg.read_bytes();action.write_text('dir-fsync');r=putraw(current['raw']+'\n# fsync uncertain publication\n',current['revision']);check('directory fsync failure explicitly reports uncertain publication',r.get('ok') is False and 'persistence is uncertain' in r.get('error',''),{'ok':r.get('ok'),'error':r.get('error')});check('fsync error does not invent rollback',cfg.read_bytes()!=old and cfg.read_bytes().endswith(b'# fsync uncertain publication\n'));check('fsync failure preserves rollback snapshot and live admin',any(p.read_bytes()==old for p in cfg.parent.joinpath('.config-history').glob('*.conf')) and login()[0]==200);check('fsync failure leaves no temporary INI',not list(cfg.parent.glob('.server.conf.qeli-tmp-*')))
   current=api('/api/config/raw');r=putraw(current['raw']+'\n# save after uncertain outcome\n',current['revision']);check('fresh revision recovers after uncertain publication',r.get('ok') is True)
   complete=True
  finally:
   action.unlink(missing_ok=True);stop();save(True);(root/'http-events.json').write_text(json.dumps(events,indent=2)+'\n');check('private namespace network restored',network()==before);save(True)
  print('PASS Q05 crash '+str(len(checks))+' checks',flush=True)
 elif a.scenario=='nonroot':
  for private_name in ('q05-state','q05-control'):Path('/etc/qeli',private_name).mkdir(mode=0o700)
  env['STATE_DIRECTORY']='/etc/qeli/q05-state';env['QELI_CONTROL_SOCKET']='/etc/qeli/q05-control/control.sock'
  local_binary=Path('/etc/qeli/q05-fixture-qeli');local_binary.write_bytes(binary.read_bytes());local_binary.chmod(0o755);binary=local_binary
  for p in [root,state,Path('/etc/qeli'),*Path('/etc/qeli').rglob('*')]:os.chown(p,65534,65534)
  Path('/etc/qeli').chmod(0o700)
  def api(path,method='GET',body=None):
   r=req(path,method,body,headers=basic());check(method+' '+path+' HTTP response',r[0]==200,r[0]);return r[1]
  def putraw(text,rev):return api('/api/config/raw','PUT',{'raw':text,'expected_revision':rev})
  try:
   start();pid=sup.pid;status=Path('/proc/'+str(pid)+'/status').read_text();check('real non-root panel UID',re.search(r'^Uid:\s+65534\s+65534\s+65534\s+65534$',status,re.M) is not None);check('non-root fixture login works',login()[0]==200)
   base=api('/api/config/raw');r=putraw(base['raw']+'\n# non-root write\n',base['revision']);check('non-root normal save succeeds',r.get('ok') is True,r);check('non-root publication preserves owner and private mode',cfg.stat().st_uid==65534 and cfg.stat().st_mode&0o777==0o600)
   base=api('/api/config/raw');old=cfg.read_bytes();parent=cfg.parent;parent.chmod(0o500)
   try:r=putraw(base['raw']+'\n# denied non-root rename\n',base['revision'])
   finally:parent.chmod(0o700)
   check('actual EACCES final write refused',r.get('ok') is False and ('Permission denied' in r.get('error','') or 'permission denied' in r.get('error','')),{'ok':r.get('ok'),'error':r.get('error')});check('EACCES preserves exact INI and supervisor',cfg.read_bytes()==old and sup.pid==pid and sup.poll() is None);check('EACCES leaves no temporary fragments',not list(parent.glob('.server.conf.qeli-tmp-*')))
   history=parent/'.config-history';os.chown(history,0,0);history.chmod(0o000)
   try:r=putraw(base['raw']+'\n# denied history access\n',base['revision'])
   finally:os.chown(history,65534,65534);history.chmod(0o700)
   check('actual EACCES rollback snapshot refused',r.get('ok') is False and 'rollback snapshot' in r.get('error',''),{'ok':r.get('ok'),'error':r.get('error')});check('snapshot EACCES preserves exact INI',cfg.read_bytes()==old)
   r=putraw(base['raw']+'\n# non-root recovery\n',base['revision']);check('non-root recovery after both EACCES faults',r.get('ok') is True and login()[0]==200)
   complete=True
  finally:
   Path('/etc/qeli').chmod(0o700);stop();save(True);(root/'http-events.json').write_text(json.dumps(events,indent=2)+'\n');check('private namespace network restored',network()==before);save(True)
  print('PASS Q05 non-root '+str(len(checks))+' checks',flush=True)
if __name__=='__main__':main()
