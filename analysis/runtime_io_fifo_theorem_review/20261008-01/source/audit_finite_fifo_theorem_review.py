"""Preserve and seal the desk-review packet; no experiments or messages."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil


REPO = Path(__file__).resolve().parent.parent
ROOT = REPO/'analysis/runtime_io_fifo_theorem_review/20261008-01'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def main():
    if (ROOT/'audit.json').exists() or (ROOT/'seal.json').exists():
        raise FileExistsError('review already audited or sealed')
    protected = json.loads((REPO/'analysis/runtime_io_paper_consolidation_review/20261008/protected_evidence_sha256.json').read_text())
    for name, expected in protected.items():
        assert digest(REPO/name) == expected, name
    paths = [
        'runtime_io_deadline_guard_exploration/20261008-review',
        'runtime_io_originality_review/20261008-01',
        'runtime_io_fifo_reference/20261008-01',
        'runtime_io_fifo_smt_baseline/20261008-01',
        'runtime_io_fifo_admission_step3/20261008-01',
        'runtime_io_fifo_hardcases_step4/20261008-01',
        'runtime_io_fifo_hardcases_step4/20261008-02-confirmation',
    ]
    old_seals = []
    for name in paths:
        folder = REPO/'analysis'/name
        seal = json.loads((folder/'seal.json').read_text())
        for rel, expected in seal['files_sha256'].items():
            assert digest(folder/rel) == expected, (name, rel)
        old_seals.append(dict(package=name, sealed_files_verified=len(seal['files_sha256']),
                              seal_sha256=digest(folder/'seal.json')))
    prior = json.loads((REPO/'analysis/runtime_io_fifo_admission_step3/20261008-01/review_report.json').read_text())
    for name, expected in prior['source_files_sha256'].items():
        assert digest(REPO/name) == expected, name
    historical = {
        'docs/runtime_io_short_working_draft_v4.md': 'd5418476bbf8bee996c1da0372f1ac9ba096c0569c288c6f051e406a8884058c',
        'docs/runtime_io_load_dependent_baseline_assessment_20261008.md': 'defd85ea1cefd04bda9b45d7fde9693e49e2bce6eeaabd9bc3f8be14c6092df5',
    }
    for name, expected in historical.items():
        assert digest(REPO/name) == expected, name
    structural = json.loads((ROOT/'structural_checks.json').read_text())
    assert structural['status'] == 'passed'
    for name, expected in structural['source_sha256'].items():
        assert digest(REPO/name) == expected, name
    sources = list(structural['source_sha256']) + [
        'analysis/audit_finite_fifo_theorem_review.py',
        'docs/runtime_io_fifo_theorem_review_packet_20261008.md',
        'docs/runtime_io_fifo_theorem_originality_assessment_20261008.md',
    ]
    frozen = ROOT/'source'
    frozen.mkdir()
    for name in sources:
        shutil.copyfile(REPO/name, frozen/Path(name).name)
    write_new(ROOT/'audit.json', dict(
        schema=1, created_utc=datetime.now(timezone.utc).isoformat(),
        source_files_sha256={name:digest(REPO/name) for name in sources},
        protected_files_verified=len(protected), historical_sha256=historical,
        step3_source_files_verified=len(prior['source_files_sha256']),
        old_seals=old_seals, structural_check_status=structural['status'],
        structural_problems_checked=structural['problems_checked'],
        independent_expert_review_received=False, external_message_sent=False,
        speedup_route='shelved', scientific_collection_launched=False,
        stronger_novelty_gate_passed=False,
        assistant_desk_verdict='likely routine specialization; no substantial originality established',
        pending_action='independent expert assessment of the precise theorem and proof'))
    hashes = {str(path.relative_to(ROOT)):digest(path)
              for path in sorted(ROOT.rglob('*')) if path.is_file()}
    write_new(ROOT/'seal.json', dict(files_sha256=hashes))
    for rel, expected in hashes.items():
        assert digest(ROOT/rel) == expected
    print(json.dumps(dict(protected_files_verified=len(protected),
                          old_seals_verified=len(old_seals),
                          new_sealed_files_verified=len(hashes))))


if __name__ == '__main__':
    main()
