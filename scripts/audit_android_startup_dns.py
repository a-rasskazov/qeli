#!/usr/bin/env python3
"""Cold system-policy start and uncached ordinary-UID DNS in an isolated Release AVD."""
import ipaddress,json,re,time


class StartupDns:
    def __init__(self, arun, evidence, result):
        self.arun,self.evidence,self.result=arun,evidence,result
        self.rows=result['dns_probes']=[]
        self.next_name=int(time.time_ns())

    def probe(self, stage, expect_reply, modes=('system','raw')):
        for mode in modes:
            self.next_name+=1;name='q29-'+str(self.next_name)+'.test'
            before=time.time()
            command=['shell','am','broadcast','--include-stopped-packages','--receiver-foreground','-n','com.qeli.test/com.qeli.SystemNetworkProbeReceiver','--es','tag','Q29PROTECTED','--es','dns_name',name,'--es','dns_mode',mode]
            broadcast=self.arun(*command,timeout=15)
            log=self.arun('shell','su','0','cat','/data/user/0/com.qeli.test/files/q29-probes.log').stdout
            lines=[v for v in log.splitlines() if 'DNS uid=' in v and 'name='+name+' ' in v]
            assert len(lines)==1,lines
            line=lines[0]
            assert 'uid='+self.result['probe_uids']['com.qeli.test']+' ' in line,line
            success=('answers=' in line or 'reply_sha256=' in line)
            if stage=='physical-baseline':
                assert success or 'SocketTimeoutException:' in line,line
            else:assert success==expect_reply,(stage,mode,line)
            if expect_reply and mode=='system':
                addresses=line.split(' answers=',1)[1].strip().split(',')
                assert {str(ipaddress.ip_address(v)) for v in addresses}=={'198.19.0.1','2001:db8:29::1'},line
            if not expect_reply:assert 'error=' in line,line
            (self.evidence/('dns-'+stage+'-'+mode+'.log')).write_text(log)
            (self.evidence/('dns-'+stage+'-'+mode+'-broadcast.txt')).write_text(broadcast.stdout+broadcast.stderr)
            row=dict(stage=stage,mode=mode,name=name,expected_reply=expect_reply,success=success,host_before=before,host_after=time.time(),line=line)
            self.rows.append(row)
            (self.evidence/'dns-probes.json').write_text(json.dumps(self.rows,indent=2)+'\n')
            print('DNS_COMPLETE '+stage+' '+mode+' success='+str(success),flush=True)

    def enable_lockdown(self, settings, bursts):
        # Observe the real confirmation first so UI dump latency is outside the
        # short burst. The only action crossing the burst is tapping TURN ON.
        tree=settings.ui('cold-before-lockdown');node,widget=settings.widget(tree,'Block connections without VPN')
        assert widget.get('checked')=='false'
        settings.tap(node);tree=settings.ui('cold-lockdown-confirmation')
        positive=settings.text_node(tree,'TURN ON');assert positive is not None,'cold start confirmation absent'
        row=bursts.run('cold-lockdown-start',lambda:settings.tap(positive),tag='Q29RECOVERED')
        logs=self.arun('shell','logcat','-d','-v','epoch','-s','VpnSvc:D','Q29Probe:I','Q29Trigger:I').stdout
        (self.evidence/'cold-start-epoch.log').write_text(logs)
        matches=[v for v in logs.splitlines() if 'Native NetworkPlan 1 APPLIED:' in v]
        assert len(matches)==1,matches
        epoch=float(matches[0].split()[0]);row['network_plan_applied_device_epoch']=epoch
        first={}
        for family in ('ipv4','ipv6'):
            for protocol in ('tcp','udp'):
                samples=[v for v in row['samples'] if v['family']==family and v['protocol']==protocol and v['started_ms']>=epoch*1000]
                assert samples,('burst ended before NetworkPlan',family,protocol)
                sample=min(samples,key=lambda v:v['started_ms'])
                first[family+'-'+protocol]=dict(sample=sample['sample'],delay_ms=round(sample['started_ms']-epoch*1000,3),success=sample['success'],detail=sample['detail'])
        self.result['cold_start']=dict(immediate_first_socket_status='PASS' if all(v['success'] for v in first.values()) else 'FAIL_POST_PLAN_BLOCKING',network_plan_applied_device_epoch=epoch,first_post_plan=first,coverage='First fresh sampled sockets after APPLIED; bounded sampling, not synchronous CONNECTED observation')
        (self.evidence/'leak-bursts.json').write_text(json.dumps(self.result['leak_bursts'],indent=2)+'\n')
        tail=bursts.run('startup-followup')
        assert all(v['success'] for v in tail['samples']),('bounded startup follow-up failed',tail)
        tree=settings.ui('cold-lockdown-enabled');_,widget=settings.widget(tree,'Block connections without VPN');assert widget.get('checked')=='true'
