#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 ]]; then
    echo 'Run this as your normal user in an external interactive terminal.' >&2
    exit 1
fi
TASK_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TASK_HELPER="$TASK_DIR/diagnostic/kernel_tools.py"
TASK_REPORT="$TASK_DIR/analysis/runtime_io_v18_kernel_setup/$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p -- "$TASK_REPORT"
echo "Setup evidence: $TASK_REPORT"
/usr/bin/python3 "$TASK_HELPER" plan --output "$TASK_REPORT/install_plan.json"
/usr/bin/python3 - "$TASK_REPORT/install_plan.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]))
for r in p['transaction']: print(f"Install {r['name']} {r['version']}")
print(f"Download: {p['download_bytes']/1024**2:.1f} MiB")
print('Existing package upgrades: none. Sudo will ask for your local password.')
PY
sudo /usr/bin/python3 "$TASK_HELPER" install --plan "$TASK_REPORT/install_plan.json" | tee "$TASK_REPORT/install.log"
sudo /usr/bin/python3 "$TASK_HELPER" inventory > "$TASK_REPORT/inventory.json"
/usr/bin/python3 "$TASK_HELPER" assess --inventory "$TASK_REPORT/inventory.json" --output "$TASK_REPORT/assessment.json"
/usr/bin/python3 - "$TASK_REPORT" <<'PY'
import hashlib,json,pathlib,sys
p=pathlib.Path(sys.argv[1]);a=json.loads((p/'assessment.json').read_text())
files={q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in sorted(p.iterdir()) if q.is_file()}
(p/'setup_seal.json').write_text(json.dumps({'files_sha256':files,'performance_run':False},indent=2)+'\n')
print(json.dumps(a,indent=2))
print('Tool setup complete. No performance batch or persistent trace was started.')
print('Return to Codex to review this inventory and prepare bounded observation fixtures.')
PY
