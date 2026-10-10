"""Seal reviewer-style decision while preserving every preceding package."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil


REPO = Path(__file__).resolve().parent.parent
ROOT = REPO/'analysis/runtime_io_fifo_reviewer_assessment/20261008-01'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def main():
    if ROOT.exists():
        raise FileExistsError(ROOT)
    protected = json.loads((REPO/'analysis/runtime_io_paper_consolidation_review/20261008/protected_evidence_sha256.json').read_text())
    for name, expected in protected.items():
        assert digest(REPO/name) == expected, name
    previous = [
        'runtime_io_deadline_guard_exploration/20261008-review',
        'runtime_io_originality_review/20261008-01',
        'runtime_io_fifo_reference/20261008-01',
        'runtime_io_fifo_smt_baseline/20261008-01',
        'runtime_io_fifo_admission_step3/20261008-01',
        'runtime_io_fifo_hardcases_step4/20261008-01',
        'runtime_io_fifo_hardcases_step4/20261008-02-confirmation',
        'runtime_io_fifo_theorem_review/20261008-01',
    ]
    seals = []
    for name in previous:
        folder = REPO/'analysis'/name
        seal = json.loads((folder/'seal.json').read_text())
        for rel, expected in seal['files_sha256'].items():
            assert digest(folder/rel) == expected, (name, rel)
        seals.append(dict(package=name, files_verified=len(seal['files_sha256']),
                          seal_sha256=digest(folder/'seal.json')))
    prior = json.loads((REPO/'analysis/runtime_io_fifo_theorem_review/20261008-01/audit.json').read_text())
    for name, expected in {**prior['source_files_sha256'], **prior['historical_sha256']}.items():
        assert digest(REPO/name) == expected, name
    ROOT.mkdir(parents=True)
    source = ROOT/'source'
    source.mkdir()
    names = ['docs/runtime_io_fifo_reviewer_verdict_20261008.md',
             'analysis/audit_finite_fifo_reviewer_verdict.py']
    for name in names:
        shutil.copyfile(REPO/name, source/Path(name).name)
    write_new(ROOT/'sources.json', dict(
        schema=1, date='2026-10-08', review_kind='assistant reviewer-style assessment',
        sources=[
            dict(url='https://www.mit.edu/~dbertsim/papers/Robust%20Optimization/Robust%20Queueing%20Theory.pdf',
                 inspected='Section 2 Equation (2), PDF page index 6', access='author full text',
                 use='standard FCFS formula; extension to the stated tail-drop model is our own derivation'),
            dict(url='https://www.researchgate.net/publication/221298325_Symbolic_Computation_of_Schedulability_Regions_Using_Parametric_Timed_Automata',
                 inspected='Section 4.2 and Figure 3', access='author-uploaded full text',
                 use='parameter regions extracted from symbolic paths; different schedulability objective'),
            dict(url='https://www.fit.vut.cz/research/result/c57593/.cs',
                 inspected='institutional metadata, abstract and author/CESNET links',
                 access='metadata accessible; linked author PDF and CESNET HTML retrieval failed',
                 use='locates 17-page report; does not close full-text gap'),
        ],
        additional_search_queries=[
            '"FIFO" "service time" "parameter" "loss" exact analysis',
            '"finite buffer" "deterministic" "parametric" analysis',
            '"queue" "admission" "piecewise affine" parameter',
            '"FIFO" "deadline" "symbolic" service time',
            '"parametric simulation" queue discrete event',
            '"parametric" "finite-buffer" "deadline"',
            '"FIFO" "admission" "monotonicity" deterministic',
            '"discrete event" "parameter space" "partition" simulation',
        ],
        query_results_are_absence_proof=False,
        full_firstness_resolved=False, independent_peer_review=False,
        prior_ledger='analysis/runtime_io_fifo_theorem_review/20261008-01/sources.json'))
    write_new(ROOT/'audit.json', dict(
        schema=1, created_utc=datetime.now(timezone.utc).isoformat(),
        protected_files_verified=len(protected), old_seals=seals,
        earlier_source_files_verified=len(prior['source_files_sha256']),
        historical_sha256=prior['historical_sha256'],
        source_files_sha256={name:digest(REPO/name) for name in names},
        review_verdict='insufficient demonstrated novelty; likely routine specialization',
        apparent_correctness_error_found=False,
        formal_machine_checked_proof=False, exact_published_twin_established=False,
        contribution_candidate='closed as current stronger-paper lead on present evidence',
        external_review_required_for_investment_decision=False,
        external_review_request_sent=False, scientific_collection_launched=False,
        new_performance_runs=0, prior_tests_rerun=False))
    hashes = {str(p.relative_to(ROOT)):digest(p)
              for p in sorted(ROOT.rglob('*')) if p.is_file()}
    write_new(ROOT/'seal.json', dict(files_sha256=hashes))
    for name, expected in hashes.items():
        assert digest(ROOT/name) == expected
    print(json.dumps(dict(protected_files_verified=len(protected),
                          old_seals_verified=len(seals),
                          new_sealed_files_verified=len(hashes))))


if __name__ == '__main__':
    main()
