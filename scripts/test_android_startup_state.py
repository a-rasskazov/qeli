import tempfile,types,unittest
from pathlib import Path
from audit_android_leak_bursts import LeakBursts

class StartupStateTest(unittest.TestCase):
    def run_burst(self,label):
        calls=[];journal=[]
        def arun(*args,**kwargs):
            calls.append((args,kwargs))
            count=int(args[args.index("burst_count")+1]);observe="observe_network" in args
            journal.append("BURST_WATCH_READY run=1 uid=10148 device_ms=90")
            for family in ("ipv4","ipv6"):
                for protocol in ("tcp","udp"):
                    journal.append(f"BURST_BEGIN run=1 uid=10148 family={family} protocol={protocol} count={count}")
                    for i in range(count):
                        if observe:journal.append(f"BURST_STATE run=1 sample={i} uid=10148 family={family} protocol={protocol} before_ms=99 after_ms=100 network=103 vpn=true iface=tun0 v4=true v6=true")
                        journal.append(f"BURST run=1 sample={i} tag=Q29PROTECTED uid=10148 family={family} protocol={protocol} bytes=257 started_ms=100 done_ms=101 error=EACCES")
            journal.append("BURST_FINISHED run=1 uid=10148")
            return types.SimpleNamespace(returncode=0,stdout="fixture broadcast",stderr="")
        with tempfile.TemporaryDirectory() as temp:
            bursts=LeakBursts(arun,Path(temp),None,{'startup_state_enabled':True,'probe_uids':{'com.qeli.test':'10148'}})
            bursts.logs=lambda:"\n".join(journal)
            row=bursts.run(label)
        return row,calls[0]
    def test_cold_observation_uses_background_deadline_and_all_96_states(self):
        row,(argv,kwargs)=self.run_burst('cold-lockdown-start')
        self.assertEqual(len(row['samples']),96)
        self.assertEqual(len(row['network_states']),96)
        self.assertNotIn('--receiver-foreground',argv)
        self.assertEqual(kwargs['timeout'],35)
        self.assertFalse(any(v['success'] for v in row['samples']))
    def test_other_phases_keep_48_samples_and_foreground_deadline(self):
        row,(argv,kwargs)=self.run_burst('connected-steady')
        self.assertEqual(len(row['samples']),48)
        self.assertEqual(row['network_states'],[])
        self.assertIn('--receiver-foreground',argv)
        self.assertEqual(kwargs['timeout'],20)
if __name__=='__main__':unittest.main()
