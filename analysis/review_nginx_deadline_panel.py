#!/usr/bin/env python3
"""Read-only raw replay and separately sealed review of deadline-panel generation 01."""
import argparse
import contextlib
import io
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'diagnostic'))
import nginx_deadline_panel_common as c
import nginx_deadline_panel_study as study
import nginx_deadline_panel_guard as guard

OUT = ROOT / 'analysis/runtime_io_nginx_deadline_panel_review/20261010-generation01'
DOC = ROOT / 'docs/runtime_io_nginx_deadline_panel_assessment_20261010.md'


def calculate():
    with contextlib.redirect_stdout(io.StringIO()):
        result = study.replay()
    # Independently recompute the declared max-after-rate-average score and
    # interval arithmetic from the replayed cohort errors, rather than treating
    # the saved status or a favorable descriptive average as the decision.
    for policy, summary in result['policies'].items():
        scores = []
        for block in range(1, 7):
            cells = [r for r in result['errors'] if r['config']['policy'] == policy
                     and r['config']['block'] == block]
            c.require(len(cells) == 2 and sorted(r['config']['rate_rps'] for r in cells) == [4, 8],
                      'Independent scoring block incomplete')
            scores.append(max(sum(r['panel'][i]['absolute_error_pp']['matched'] for r in cells) / 2
                              for i in range(5)))
        saved = summary['methods']['matched']['worst_cutoff_block_score']
        mean = statistics.mean(scores)
        half = c.PROTOCOL['primary_t_multiplier'] * statistics.stdev(scores) / math.sqrt(6)
        c.require(scores == saved['blocks'] and math.isclose(mean, saved['mean']) and
                  all(math.isclose(x, y) for x, y in zip([mean - half, mean + half], saved['conditional_interval'])),
                  'Independent primary score differs')
        c.require(summary['matched_accuracy_supported'] == (mean + half <= 5), 'Accuracy verdict differs')
    counts = {}
    paths = dict(qualification='qualification/smoke', calibration='campaign/calibration',
                 validation='campaign/validation')
    for phase, relative in paths.items():
        rows = c.read(c.BASE / relative / 'summary.json')['rows']
        counts[phase] = dict(cohorts=len(rows), measurement_offers=sum(r['offers'] for r in rows),
            warmup_offers=sum(len(r['warmup_outcomes']) for r in rows),
            unsuccessful_measurement=sum(r['offers'] - r['successful'] for r in rows),
            unsuccessful_warmup=sum(not o['success'] for r in rows for o in r['warmup_outcomes']),
            observations=[{k:r[k] for k in ('config','observations','measurement_counter_delta','warmup_counter_delta')}
                          for r in rows if r['observations']])
        for r in rows:
            case = c.BASE / relative / f"cohort-{r['config']['index']}"
            c.require(not c.read(case / 'cleanup.json')['errors'], 'Service cleanup errors')
            c.require(c.read(case / 'policy-journal.json')['status'] == 'restored' and
                      c.read(case / 'policy-restoration-verified.json')['restored'], 'Policy restoration differs')
    total = sum(v['measurement_offers'] + v['warmup_offers'] for v in counts.values())
    c.require(total == 10530, 'Complete offered budget differs')
    forecast = c.read(c.BASE / 'campaign/forecast/forecast.json')
    examples = {}
    for policy in c.POLICIES:
        cells = [(r, d) for r in result['errors'] if r['config']['policy'] == policy for d in r['panel']]
        row, point = max(cells, key=lambda v:v[1]['absolute_error_pp']['matched'])
        examples[policy] = dict(config=row['config'], point=point, historical=row['historical'],
                               selected_after_validation=True, role='Descriptive largest-error illustration only')
    return dict(schema='nginx-deadline-panel-review-v1', status=result['status'], counts=counts,
        total_offers=total, panels=forecast['panels'], policies=result['policies'], examples=examples,
        campaign_summary=c.read(c.BASE / 'campaign/summary.json'),
        qualification_summary={k:v for k,v in c.read(c.BASE / 'qualification/summary.json').items() if k!='rows'},
        calibration_references={p:dict(offers=r['offers'], failed_offers=r['failed_offers'])
                                for p,r in forecast['references'].items()},
        raw_replay_verified=True, independent_primary_arithmetic_verified=True,
        forecast_barriers_verified=True, cleanup_and_restoration_verified=True,
        family_inference=result['family_inference'], calibration_uncertainty_propagated=False,
        novelty_established=False, causal_mechanism_identified=False, independent_host_replication=False,
        evidence_seal_sha256=c.sha(c.BASE / 'campaign/evidence-seal.json'),
        preparation_seal_sha256=c.sha(c.BASE / 'preparation-seal.json'),
        decision='Close the bounded collection. Preserve policy-matching advantage alongside unsupported multi-deadline accuracy; integrate the empirical scope result before choosing another hypothesis. No automatic retry, tuning, new selector or manuscript edit. Worker-wait held; friend-owned V31 pending.')


def markdown(r):
    lines = ['# Completed NGINX deadline-panel assessment', '',
        '10 October 2026. Fresh prospective generation 01; previous sealed studies remain unchanged.', '',
        '**The complete campaign verifies. Neither policy meets the frozen multi-deadline accuracy gate,',
        'although matching policy substantially improves on pooled calibration.**', '',
        f"Status: `{r['status']}`. Qualification took {r['qualification_summary']['elapsed_sec']/60:.2f} minutes;",
        f"science took {r['campaign_summary']['elapsed_sec']/60:.2f} minutes. All 10,530 offered responses succeeded:",
        '1,030 qualification offers, 1,600 calibration measurements plus 100 warmup offers, and',
        '7,200 validation measurements plus 600 warmup offers. All six qualification services,',
        'four fresh calibration services and 24 validation services completed. Normal and independent',
        'dead-owner policy restoration fixtures, source seals, request accounting, owned cleanup and',
        'advance global/per-service forecast barriers pass canonical raw replay. Independent arithmetic',
        'also verifies the primary block scores and decisions. No cohort or cutoff was replaced.', '',
        '## Frozen primary decision', '',
        'For each policy/block, average absolute miss-probability errors across 4/s and 8/s at each',
        'of the five cutoffs, then take the maximum cutoff error. The mean of six such block scores',
        'is the primary score, in percentage points (pp). Each matched-policy 97.5% conditional',
        'interval must have upper endpoint <=5 pp. Matching has the same full acquisition as the controls.', '',
        '| Policy | Matched score (pp) | Conditional 97.5% interval (pp) | Accuracy supported | Pooled score (pp) |',
        '|---|---:|---:|---|---:|']
    for p,v in r['policies'].items():
        x=v['methods']['matched']['worst_cutoff_block_score'];lo,hi=x['conditional_interval']
        lines.append(f"| {p} | {x['mean']:.3f} | [{lo:.3f}, {hi:.3f}] | {'Yes' if v['matched_accuracy_supported'] else 'No'} | {v['methods']['pooled']['worst_cutoff_block_score']['mean']:.3f} |")
    lines += ['', 'P1 has a point score below 5 pp but its upper interval bound exceeds 5 pp. Failure to',
        'support accuracy does not prove population error above 5 pp. The P0 interval also includes',
        'values below the margin. Two policy intervals use Bonferroni family coverage >=95% only',
        'conditional on independent approximately normal block scores. There are six chronological',
        'blocks; independence and normality are unverified. Shared calibration is conditioned upon',
        'and its uncertainty is not propagated. This tests average block adequacy at this panel,',
        'not every individual cohort/rate or every finite deadline.', '',
        '## Policy-matching advantage and ordinary controls', '',
        'The pooled-minus-matched primary scores give a secondary descriptive advantage:', '']
    for p,v in r['policies'].items():
        g=v['matched_vs_pooled_gain'];lo,hi=g['conditional_interval']
        lines.append(f"- {p}: {g['mean']:.3f} pp, conditional descriptive 95% interval [{lo:.3f}, {hi:.3f}] pp.")
    lines += ['', 'Both meet the predeclared secondary >=2 pp mean and positive lower-bound flag. This',
        'does not replace the failed absolute-accuracy gates or establish a new estimator.', '',
        '| Policy | Reference | Worst-cutoff block mean (pp) | Upper conditional interval (pp) | Panel-average MAE (pp) |',
        '|---|---|---:|---:|---:|']
    for p,v in r['policies'].items():
        for name,x in v['methods'].items():
            score=x['worst_cutoff_block_score']
            lines.append(f"| {p} | {name} | {score['mean']:.3f} | {score['conditional_interval'][1]:.3f} | {x['panel_average']['mean']:.3f} |")
    lines += ['', 'Only matched is the primary accuracy method. The controls remain descriptive; no winner',
        'is selected after validation. P0 baseline equals matched by construction. Warmup-only',
        'scores are worse; the weighted matched update gives similar point scores and no upper',
        'bound <=5 pp in either policy. The 25-offer warmup does not establish an advance reliability',
        'signal. All controls are charged the acquired 1,600 calibration offers and same warmup.', '',
        '## Deadline scope', '',
        'Cutoffs were frozen from 800 fresh calibration measurements per policy using lower-order',
        'ranks 79, 199, 399, 599, 719, without validation outcomes. Every cutoff was finite.', '',
        '| Policy | Quantile | Deadline (ms) | Matched mean error (pp) |',
        '|---|---|---:|---:|']
    for p,panel in r['panels'].items():
        for point in panel:
            score=r['policies'][p]['methods']['matched']['per_cutoff'][point['quantile']]
            lines.append(f"| {p} | {point['quantile']} | {point['deadline_ns']/1e6:.6f} | {score['mean']:.3f} |")
    lines += ['', 'Panel-average MAE is 3.483 pp for P0 and 3.067 pp for P1. Averaging cutoffs would',
        'hide the hardest cutoff; those values are descriptive and do not change the primary gates.',
        'There are 11 cohort/cutoff errors above 5 pp out of 60 in each policy. Maximum individual',
        'errors are 19.667 pp (P0) and 11.000 pp (P1). These are 120 correlated errors, not 120',
        'independent statistical replicates; inference uses six block units per policy.', '',
        'At the additional historical 20.565395 ms deadline, matched MAE is 3.181 pp for P0 and',
        '0 pp for P1. P1 calibration and validation each have zero misses there: that endpoint is',
        'saturated and does not demonstrate accuracy near the calibration CDF transition.', '']
    for p,e in r['examples'].items():
        d=e['point'];cfg=e['config']
        lines.append(f"- Descriptive {p} example: cohort {cfg['index']} at {cfg['rate_rps']}/s, cutoff {d['quantile']} ({d['deadline_ns']/1e6:.6f} ms), predicts {100*d['predictions']['matched']:.3f}% misses versus {100*d['observed']:.3f}% observed; error {d['absolute_error_pp']['matched']:.3f} pp. Historical-cutoff error: {e['historical']['absolute_error_pp']['matched']:.3f} pp.")
    lines += ['', 'These examples are selected after validation to illustrate the complete frozen result;',
        'they are not new chosen endpoints, acceptance tests or pre-validation rules.', '',
        '## Retained observations and interpretation', '',
        'Validation cohort 1 (P0, 8/s, block 1) records one throttled period and 4,703 us aggregate',
        'measurement throttling. It is retained. No other qualification/calibration/validation',
        'observation flags or failed offers occur. The aggregate counter cannot assign throttling',
        'to a particular request or explain the forecast error. Matching EPP readback does not fix',
        'physical frequency. The current-host policy snapshot matched the prepared baseline when',
        'this review was saved, through a read-only check; historical boundary/restoration records',
        'are separately verified. No settings were changed during assessment.', '',
        'The prospectively declared panel confirms an empirical scope limitation: accurate forecasts',
        'at one historical cutoff, including a saturated cutoff, do not establish the frozen',
        'multi-deadline accuracy criterion. Matching policy helps substantially here but does not',
        'qualify that criterion. No causal explanation, latent-distribution shift test, uniform',
        'CDF bound, novel estimator or useful advance reliability selector is established.',
        'This is fresh evidence after known development results, on the same host, not independent',
        'host replication. Numeric differences from earlier panels are not causal treatment effects.', '',
        'Close this bounded experiment and preserve its complete result for manuscript integration.',
        'Do not automatically repeat, relax the margin, drop the throttled cohort or tune a selector',
        'on these outcomes and call it confirmed. Before more collection, any new reliability signal',
        'needs a concrete mechanism, measurement feasibility and equal-cost ordinary comparator.',
        'Worker-wait remains held; the friend-owned independent V31 replication remains pending.',
        'The open manuscript is unchanged by this review.', '',
        'Replay this assessment with `python3 -B analysis/review_nginx_deadline_panel.py --verify`.', '']
    return '\n'.join(lines)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify',action='store_true')
    args=parser.parse_args();r=calculate()
    if args.verify:
        for name,digest in c.read(OUT/'inputs_sha256.json').items():
            c.require(c.sha(ROOT/name)==digest,'Review input changed: '+name)
        for name,digest in c.read(OUT/'review-seal.json')['files_sha256'].items():
            c.require(c.sha(ROOT/name)==digest,'Review artifact changed: '+name)
        c.require(r==c.read(OUT/'review.json') and markdown(r)==(OUT/'report.md').read_text(),
                  'Deadline-panel review replay differs')
        print('Complete deadline-panel evidence, independent scores, forecast barriers and sealed review verify.')
        return
    c.require(not OUT.exists() and not DOC.exists(),'Preserve existing review; no overwrite')
    snapshot=guard.snapshot();baseline=c.read(c.BASE/'policy-baseline.json')
    c.require(snapshot==baseline,'Current policy differs from prepared baseline')
    prep=c.read(c.BASE/'preparation-review-seal.json')['files_sha256']
    for name,digest in prep.items():c.require(c.sha(c.BASE/name)==digest,'Preparation review changed: '+name)
    OUT.mkdir(parents=True)
    c.save(OUT/'review.json',r)
    report=markdown(r)
    (OUT/'report.md').write_text(report);DOC.write_text(report)
    (OUT/'protocol_snapshot.md').write_bytes((ROOT/c.FILES[-1]).read_bytes())
    c.save(OUT/'host-policy-check.json',dict(snapshot=snapshot,prepared_baseline=baseline,
        matched_now=True,host_policy_writes=False,performance_measurement=False))
    paths={p for p in c.BASE.rglob('*') if p.is_file()}
    paths.update(ROOT/name for name in c.sources())
    paths.update(ROOT/name for name in c.read(c.BASE/'preparation-seal.json')['files_sha256'])
    for phase in ('qualification','campaign'):
        paths.add(Path(c.read(c.BASE/phase/'observer-inventory.json')['path']))
    c.save(OUT/'inputs_sha256.json',{str(p.relative_to(ROOT)):c.sha(p) for p in sorted(paths)})
    artifacts=[p for p in OUT.rglob('*') if p.is_file()]+[Path(__file__),DOC]
    c.save(OUT/'review-seal.json',dict(files_sha256={str(p.relative_to(ROOT)):c.sha(p) for p in sorted(artifacts)}))
    print('Completed deadline-panel review preserved: '+str(OUT/'report.md'))


if __name__=='__main__':main()
