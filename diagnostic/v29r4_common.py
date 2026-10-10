"""Final-context repeat; retained scientific inputs, separate frozen runner."""
from v29_common import *
import v29_common as retained_v29

if ACTIVE!='q025_large':
    raise ValueError('Final-context runner requires RESEARCH_V29_CONTEXT=q025_large')


def owned_directory(value):
    p=retained_v29.owned_directory(value)
    if p.name!='generation-04':
        raise ValueError('Use the new generation-04 final-context directory')
    return p


def source_hashes():
    names=set(retained_v29.source_hashes())
    names.update(str(p.relative_to(ROOT)) for p in (ROOT/'diagnostic').glob('v29r4_*.py'))
    names.update(('diagnostic/test_v29r4.py','diagnostic/start_v29_final.sh',
                  'docs/runtime_io_v29_final_execution.md'))
    return {name:digest(ROOT/name) for name in sorted(names)}
