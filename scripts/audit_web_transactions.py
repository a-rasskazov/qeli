#!/usr/bin/env python3
"""Q05 HTTP transactions and faults on an exact release in private NET/mount/PID namespaces.
The full-restart fault case binds a private rejecting systemctl shim; no host service calls.
"""
import argparse,ssl,base64,concurrent.futures,hashlib,hmac,http.client,json,os,re,signal,subprocess,threading,time
from pathlib import Path

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for k in ('qeli','sha256','artifacts','routes','parent-net','parent-mnt','parent-pid'):ap.add_argument('--'+k,required=True)
 ap.add_argument('--scenario',choices=('basic','runtime','faults','crash','nonroot'),required=True)
 a=ap.parse_args()
 for k in ('net','mnt','pid'):assert os.readlink('/proc/self/ns/'+k)!=getattr(a,'parent_'+k),'private namespace required: '+k
 binary=Path(a.qeli).resolve(strict=True);assert hashlib.sha256(binary.read_bytes()).hexdigest()==a.sha256
 root=Path(a.artifacts);root.mkdir(mode=0o700,parents=True,exist_ok=False);routes=json.loads(Path(a.routes).read_text());checks=[];events=[];observations=[];sup=None;stream=None;complete=False
 cfg=Path('/etc/qeli/server.conf');state=root/'state';state.mkdir(mode=0o700);port=24880;prefix='/audit';tls_mode=False;password='fixture-only #; exact password';cookie='';env=dict(os.environ,STATE_DIRECTORY=str(state),QELI_CONTROL_SOCKET=str(root/'control.sock'))
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
  if a.scenario=='nonroot':command=['setpriv','--reuid=65534','--regid=65534','--clear-groups','--inh-caps=+net_admin,+net_raw','--ambient-caps=+net_admin,+net_raw']+command
  sup=subprocess.Popen(command,env=env,stdout=stream,stderr=subprocess.STDOUT)
  wait(lambda:req('/login')[0] in (200,303,403),'panel not ready');wait(lambda:':24843' in run(['ss','-lnt']) and Path('/etc/qeli/identity/fixture.key').exists(),'private worker not ready')
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


 if a.scenario=='basic':
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
