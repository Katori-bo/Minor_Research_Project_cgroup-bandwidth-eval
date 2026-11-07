"""Test the external shell wrapper with fake launchers and fake sudo only."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class CombinedAuth(unittest.TestCase):
    def run_fixture(self,auth_failure=0,go_failure=False):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);diagnostic=root/'diagnostic';diagnostic.mkdir()
            shutil.copy2(ROOT/'diagnostic/start_slo_local_supplement_all.sh',diagnostic/'start.sh')
            package=root/'handoff/slo-host01-20261011-local-supplement-03'
            runtime=package/'runtime';runtime.mkdir(parents=True)
            (runtime/'prelaunch_local_supplement.py').write_text("""import os,sys
from pathlib import Path
app=sys.argv[sys.argv.index('--application')+1]
with Path(os.environ['FIXTURE_LOG']).open('a') as f:f.write('preflight '+app+'\\n')
""")
            (package/'start_local_supplement.sh').write_text("""#!/bin/bash
if [[ "$1" == Go ]]; then echo setup >> "$FIXTURE_LOG"; fi
echo "launch $1" >> "$FIXTURE_LOG"
if [[ "$1" == Go && "$FIXTURE_GO_FAILURE" == 1 ]]; then exit 9; fi
""")
            binaries=root/'fakebin';binaries.mkdir()
            sudo=binaries/'sudo';sudo.write_text("""#!/bin/bash
count=0
if [[ -e "$FIXTURE_COUNT" ]]; then read -r count < "$FIXTURE_COUNT"; fi
count=$((count+1))
echo "$count" > "$FIXTURE_COUNT"
echo "auth $count" >> "$FIXTURE_LOG"
if [[ "$count" == "$FIXTURE_AUTH_FAILURE" ]]; then exit 1; fi
""");sudo.chmod(0o755)
            log=root/'events';environment=dict(os.environ,
                PATH=str(binaries)+os.pathsep+os.environ['PATH'],FIXTURE_LOG=str(log),
                FIXTURE_COUNT=str(root/'count'),FIXTURE_AUTH_FAILURE=str(auth_failure),
                FIXTURE_GO_FAILURE='1' if go_failure else '0')
            result=subprocess.run(['bash',str(diagnostic/'start.sh'),'--amendment-accepted','--allocation-confirmed'],
                capture_output=True,text=True,env=environment,timeout=10)
            return result.returncode,log.read_text().splitlines()

    def test_authentication_precedes_each_launch_and_setup_is_once(self):
        code,events=self.run_fixture()
        self.assertEqual(code,0)
        self.assertEqual(events,['preflight Go','auth 1','setup','launch Go',
                                 'preflight NGINX','auth 2','launch NGINX'])

    def test_expired_second_authentication_stops_before_nginx_launch(self):
        code,events=self.run_fixture(auth_failure=2)
        self.assertNotEqual(code,0)
        self.assertNotIn('launch NGINX',events)
        self.assertEqual(events[-2:],['preflight NGINX','auth 2'])

    def test_first_campaign_failure_stops_second_authentication_and_launch(self):
        code,events=self.run_fixture(go_failure=True)
        self.assertNotEqual(code,0)
        self.assertNotIn('auth 2',events)
        self.assertNotIn('launch NGINX',events)


if __name__=='__main__':unittest.main()
