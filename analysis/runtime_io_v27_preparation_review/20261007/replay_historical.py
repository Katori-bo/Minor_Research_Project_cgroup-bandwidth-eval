import importlib, json, sys, time
from pathlib import Path
sys.dont_write_bytecode=True
root=Path('/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency')
number=int(sys.argv[1]);session=root/f'analysis/runtime_io_v{number}/generation-01'
frozen=session/'preparation/source'
# Load historical implementation from its saved source tree. Remap artifact
# locations to the original checkout; no source, hash or verification is changed.
sys.path.insert(0,str(frozen/'diagnostic'))
sys.path.insert(1,str(frozen/'scripts'))
verify=importlib.import_module(f'v{number}_verify')
common=importlib.import_module(f'v{number}_common')
for module in list(sys.modules.values()):
    filename=getattr(module,'__file__',None)
    if filename is None or not Path(filename).is_relative_to(frozen):continue
    for name,value in list(vars(module).items()):
        if isinstance(value,Path) and value.is_relative_to(frozen):
            setattr(module,name,root/value.relative_to(frozen))
start=time.monotonic();result=verify.verify_completion(session)
receipt=dict(independent_completion_replay_passed=True,decision=result['decision'],duration_sec=time.monotonic()-start,
             implementation='historical_preparation_source_snapshot',source_seal_sha256=common.digest(session/'preparation/seal.json'),
             artifact_root_remapped_only=True,verification_checks_modified=False)
common.save(root/f'analysis/runtime_io_v27_preparation_review/20261007/V{number}_replay.json',receipt)
print(f'V{number} frozen-source replay passed: '+result['decision'],flush=True)
