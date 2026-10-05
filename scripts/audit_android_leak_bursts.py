#!/usr/bin/env python3
"""Bounded ordinary-UID probe bursts crossing real carrier/stop actions."""
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,re,struct,time
from android_lab_ui import wait_until


class LeakBursts:
    def __init__(self, arun, evidence, echo, result):
        self.arun,self.evidence,self.echo,self.result=arun,evidence,echo,result
        self.rows=result['leak_bursts']=[]
        self.next_run=1

    def logs(self):return self.arun('shell','logcat','-d','-s','Q29Probe:I','Q29Trigger:I').stdout

    def run(self, label, action=None, tag='Q29PROTECTED'):
        run=self.next_run;self.next_run+=1
        before=time.time()
        command=['shell','am','broadcast','--include-stopped-packages','--receiver-foreground','-n','com.qeli.test/com.qeli.SystemNetworkProbeReceiver','--es','tag',tag,'--ei','burst_run',str(run),'--ei','burst_count','12']
        with ThreadPoolExecutor(max_workers=1) as executor:
            future=executor.submit(self.arun,*command,timeout=20)
            wait_until(lambda:sum('BURST_BEGIN run='+str(run)+' ' in line for line in self.logs().splitlines())==4,'four probe streams did not start',8)
            trigger=None
            if action is not None:
                # Android logcat provides device-clock boundaries; host time is
                # recorded separately, on the same clock as the private pcap.
                start=time.time()
                self.arun('shell','log','-t','Q29Trigger','BEGIN run='+str(run)+' '+label)
                action()
                self.arun('shell','log','-t','Q29Trigger','END run='+str(run)+' '+label)
                trigger=dict(host_before=start,host_after=time.time())
            output=future.result(timeout=15)
        assert output.returncode==0,output.stderr
        logs=self.logs();assert 'BURST_FINISHED run='+str(run)+' ' in logs,logs
        selected=[]
        expression=r'BURST run='+str(run)+r' sample=(\d+) tag=(\w+) uid=(\d+) family=(ipv[46]) protocol=(tcp|udp) bytes=257 started_ms=(\d+) done_ms=(\d+) (.*)'
        for line in logs.splitlines():
            m=re.search(expression,line)
            if not m:continue
            sample,seen_tag,uid,family,proto,started,done,tail=m.groups();sample=int(sample)
            assert seen_tag==tag and uid==self.result['probe_uids']['com.qeli.test'] and 0<=sample<12
            data=bytearray((i*31+17)%251 for i in range(257));marker=tag.encode();data[:len(marker)]=marker;data[len(marker):len(marker)+8]=struct.pack('!II',run,sample)
            expected=bytes(data)[::-1] if proto=='tcp' else b'Q29:'+bytes(data)
            digest=hashlib.sha256(data).hexdigest();reply=hashlib.sha256(expected).hexdigest()
            success='reply=Q29:'+tag in tail
            if success:assert 'sha256='+digest in tail and 'reply_sha256='+reply in tail,tail
            else:assert 'error=' in tail,tail
            selected.append(dict(sample=sample,uid=int(uid),family=family,protocol=proto,started_ms=int(started),done_ms=int(done),success=success,payload_sha256=digest,reply_sha256=reply,detail=tail))
        assert len(selected)==48 and len({(v['family'],v['protocol'],v['sample']) for v in selected})==48,selected
        row=dict(label=label,run=run,tag=tag,host_before=before,host_after=time.time(),trigger=trigger,samples=selected)
        (self.evidence/('burst-'+label+'-logcat.log')).write_text(logs)
        (self.evidence/('burst-'+label+'-broadcast.txt')).write_text(output.stdout+output.stderr)
        self.rows.append(row);(self.evidence/'leak-bursts.json').write_text(json.dumps(self.rows,indent=2)+'\n')
        print('BURST_COMPLETE '+label+' samples=48 replies='+str(sum(v['success'] for v in selected)),flush=True)
        return row

    def force_stop(self, open_settings, switch, logs, probe):
        row=self.run('force-stop',lambda:self.arun('shell','am','force-stop','com.qeli'))
        wait_until(lambda:not re.search(r'^\d+: tun\d',self.arun('shell','su','0','ip','-o','link','show').stdout,re.M),'force-stop retained TUN',15)
        assert not self.arun('shell','pidof','com.qeli',check=False).stdout.strip()
        policy={k:self.arun('shell','settings','get','secure',k).stdout.strip() for k in ('always_on_vpn_app','always_on_vpn_lockdown')}
        assert policy=={'always_on_vpn_app':'com.qeli','always_on_vpn_lockdown':'1'},policy
        blocked=self.run('stopped-lockdown',tag='Q29BLOCKED')
        assert not any(v['success'] for v in blocked['samples']),blocked
        # A user force-stop intentionally marks the package stopped. Explicitly
        # reopen and re-enable the OS policy; do not infer automatic redelivery.
        old=logs().count('Auth OK:')
        self.arun('shell','am','start','-n','com.qeli/.MainActivity')
        open_settings();switch('Block connections without VPN',False);switch('Always-on VPN',False)
        switch('Always-on VPN',True);switch('Block connections without VPN',True)
        wait_until(lambda:logs().count('Auth OK:')>old and 'Native NetworkPlan' in logs(),'manual recovery after force-stop failed',35)
        self.result['leak_manual_recovery']=[probe('Q29MANUAL',True,label='burst-recovery-'+f+'-'+p,family=f,protocol=p,payload_bytes=16384 if p=='tcp' else 257) for f in ('ipv4','ipv6') for p in ('tcp','udp')]
        self.result['leak_force_stop_policy']=policy
        open_settings()
