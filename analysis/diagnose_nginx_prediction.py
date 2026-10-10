#!/usr/bin/env python3
"""Exploratory diagnosis from frozen NGINX evidence; never collect or refit."""
import csv
from pathlib import Path
import statistics as st
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'diagnostic'))
import nginx_prediction_common as c
import nginx_prediction_study as s


def stages(row):
    result = dict(dispatch_ns=row['DispatchNs'] - row['ScheduledNs'],
                  to_headers_ns=row['HeadersNs'] - row['DispatchNs'],
                  headers_to_body_ns=row['BodyDoneNs'] - row['HeadersNs'],
                  total_ns=row['BodyDoneNs'] - row['ScheduledNs'])
    c.require(all(x >= 0 for x in result.values()) and
              sum(result[k] for k in ('dispatch_ns', 'to_headers_ns', 'headers_to_body_ns')) == result['total_ns'],
              'Exact observed milestone decomposition failed')
    return result


def summary(rows, deadline):
    values = [stages(r) for r in rows]
    return dict(offers=len(rows), misses=sum(r['total_ns'] > deadline for r in values),
        miss_pct=100 * sum(r['total_ns'] > deadline for r in values) / len(rows),
        means_ms={k: st.mean(v[k] for v in values) / 1e6 for k in values[0]},
        medians_ms={k: st.median(v[k] for v in values) / 1e6 for k in values[0]},
        exploratory_below_18ms=sum(v['total_ns'] < 18000000 for v in values))


def main():
    replay = s.replay()
    c.require(replay['status'] == 'full_response_prediction_accuracy_not_supported', 'Campaign result differs')
    base = c.BASE / 'campaign'
    deadline = c.read(base / 'forecast/forecast.json')['primary_deadline_ns']
    comparison = c.read(base / 'comparison.json')
    cases, traces, encoded = [], [], set()
    cache = {}
    for role in ('pilot', 'calibration', 'validation'):
        for cfg in c.configs(role):
            case = base / role / f"cohort-{cfg['index']}"
            raw = c.read(case / 'measurement.json')['Rows']
            warm = c.read(case / 'warmup.json')['Rows']
            cache[(role, cfg['index'])] = raw
            value = summary(raw, deadline)
            result = c.read(case / 'result.json')
            c.require(result['successful'] == len(raw) and not result['domain_exits'], 'Eligibility differs')
            gaps = [raw[i]['DispatchNs'] - raw[i - 1]['BodyDoneNs'] for i in range(1, len(raw))]
            c.require(all(g > 0 for g in gaps), 'Client response overlap observed')
            for row in raw:
                encoded.add((row['BodyBytes'], row['BodySHA256']))
                traces.append(dict(role=role, cohort=cfg['index'], profile=cfg['profile'] or 'reference',
                    request_id=row['ID'], scheduled_ns=row['ScheduledNs'], **stages(row)))
            cpu = result['measurement_counter_delta']
            c.require(cpu['nr_throttled'] == cpu['throttled_usec'] == 0, 'Throttle observed')
            initial = c.read(case / 'initial.json')
            cases.append(dict(role=role, config=cfg, **value, warmup=summary(warm, deadline),
                minimum_previous_body_to_next_dispatch_ms=min(gaps) / 1e6,
                cpu_ms_per_offer=cpu['usage_usec'] / len(raw) / 1000,
                cpu_user_ms_per_offer=cpu['user_usec'] / len(raw) / 1000,
                cpu_system_ms_per_offer=cpu['system_usec'] / len(raw) / 1000,
                parent_cpu_limits=initial['ancestors'],
                client_response_windows_overlap=False))
    c.require(len(encoded) == 1 and len(traces) == 7300, 'Output or offer identity differs')
    anomaly_rows = cache[('validation', 4)]
    reference_rows = [r for i in (2, 9, 12, 14, 16) for r in cache[('validation', i)]]
    anomaly = summary(anomaly_rows, deadline)
    reference = summary(reference_rows, deadline)
    contrasts = {k: anomaly['means_ms'][k] - reference['means_ms'][k] for k in anomaly['means_ms']}
    c.require(abs(sum(contrasts[k] for k in ('dispatch_ns', 'to_headers_ns', 'headers_to_body_ns')) -
                  contrasts['total_ns']) < 1e-12, 'Mean contrast does not conserve observed duration')
    segments = []
    for start in range(0, 300, 30):
        segments.append(dict(first_offer_index=start, last_offer_index=start + 29,
                             **summary(anomaly_rows[start:start + 30], deadline)))
    cal = [r for i in range(1, 5) for r in cache[('calibration', i)]]
    offsets = [-100000, -50000, 0, 50000, 100000]
    sensitivity = [dict(offset_ns=offset, deadline_ns=deadline + offset,
                        calibration_miss_pct=summary(cal, deadline + offset)['miss_pct']) for offset in offsets]
    contrasts_ac = []
    for block in range(1, 7):
        by_profile = {e['profile']: e for e in comparison['errors'] if e['block'] == block}
        contrasts_ac.append(100 * (by_profile['C']['observed_miss_fraction'] - by_profile['A']['observed_miss_fraction']))
    cfg_b = c.PROTOCOL['validation_intervals_ns']['B']
    alias = dict(calibration_schedule_residue_cycle=[0],
        A_schedule_residues_modulo_100ms_ns=[(i * 250000000) % 100000000 for i in range(2)],
        B_first_three_residues_modulo_100ms_ns=[(i * cfg_b) % 100000000 for i in range(3)],
        B_residue_after_three_offers_ns=(3 * cfg_b) % 100000000,
        C_schedule_residues_modulo_100ms_ns=[(i * 125000000) % 100000000 for i in range(4)],
        absolute_quota_phase_observed=False,
        interpretation='Relative offer grids sample different residues; no exact client-clock origin or quota-replenishment trace identifies actual budget phase.')
    out = ROOT / 'analysis/runtime_io_nginx_prediction_diagnosis/20261010-generation01'
    if out.exists():
        for name, digest in c.read(out / 'evidence-seal.json')['files_sha256'].items():
            c.require(c.sha(ROOT / name) == digest, 'Diagnosis changed: ' + name)
        print('Saved-evidence diagnosis verifies:', out / 'report.md'); return
    out.mkdir(parents=True)
    report = dict(status='saved_evidence_diagnosis_complete', analysis_role='post-hoc exploratory; primary result unchanged',
        prospective_replay=replay, primary_deadline_ns=deadline, cases=cases,
        encoded_response_identity=dict(bytes=next(iter(encoded))[0], sha256=next(iter(encoded))[1]),
        anomaly_vs_other_same_rate=dict(anomaly=anomaly, other_five_pooled=reference, mean_difference_ms=contrasts,
            after_headers_fraction_of_mean_difference=contrasts['headers_to_body_ns'] / contrasts['total_ns']),
        anomaly_30_offer_segments=segments,
        anomaly_first_30=summary(anomaly_rows[:30], deadline),
        anomaly_remaining_270=summary(anomaly_rows[30:], deadline),
        exploratory_deadline_sensitivity=sensitivity,
        post_hoc_same_block_C_minus_A_miss_pp=contrasts_ac,
        schedule_residue_description=alias,
        absent_measurements=['per-request server CPU and queue stages', 'scheduler/runnable-time trace',
            'time-resolved competing CPU users', 'CPU frequency/temperature timeline',
            'client GC and decode timeline', 'network/disk event trace', 'quota-phase clock origin'],
        mechanism_identified=False, experiment_started=False,
        conclusion='Persistent within-cohort response variation, mainly after headers, and a steep deadline region limit this rate-invariant forecast. Recorded cgroup throttling and output/runtime changes do not explain it; finer causal attribution is unavailable.')
    c.save(out / 'report.json', report)
    with (out / 'request-stage-traces.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(traces[0])); writer.writeheader(); writer.writerows(traces)
    lines = ['# NGINX saved-evidence diagnosis', '',
        'Date: 2026-10-10. Exploratory analysis of the preserved generation-01 campaign.',
        'No workload was run; the prospective deadline, forecast, trial inclusion,',
        'accuracy criterion and unsupported result remain unchanged. All sealed',
        'campaign records and the comparison replay verify.', '',
        '## 1. The large excursion persisted within the measurement window', '',
        'Validation cohort 4 (block 2, approximately 6 requests/s) had 88.333% misses.',
        'Its 25 warmup offers had median 20.476486 ms and 36% misses at the fixed',
        '20.565395 ms deadline. The first 30 measurement offers had 56.667% misses;',
        'the remaining 270 had 91.852% misses and median 21.485907 ms. Thus a single',
        'slow request or the first request cannot explain the cohort result. These',
        'post-hoc segments describe persistence, not a statistically estimated change point.', '',
        '| Offer indices (zero-based) | Median full response ms | Miss % |',
        '|---|---:|---:|']
    for seg in segments:
        lines.append(f"| {seg['first_offer_index']}–{seg['last_offer_index']} | {seg['medians_ms']['total_ns']:.3f} | {seg['miss_pct']:.3f} |")
    lines += ['', '## 2. Observed timing locates the longer interval', '',
        'Compare the excursion with all 1,500 offers in the other five same-rate',
        'cohorts, retaining every offer. Differences of means add exactly across',
        'these client milestones; component medians would not generally add.', '',
        '| Observed interval | Other five mean ms | Excursion mean ms | Difference ms |',
        '|---|---:|---:|---:|']
    names = dict(dispatch_ns='Scheduled offer to dispatch', to_headers_ns='Dispatch to headers',
                 headers_to_body_ns='Headers to complete body', total_ns='Entire full response')
    for key, label in names.items():
        lines.append(f"| {label} | {reference['means_ms'][key]:.6f} | {anomaly['means_ms'][key]:.6f} | {contrasts[key]:+.6f} |")
    lines += ['',
        'About 87.9% of the extra mean duration occurs after headers arrive. Client',
        'dispatch delay is slightly smaller in the excursion. This excludes a larger',
        'offer-to-dispatch delay as the explanation for its longer mean response.',
        'Headers-to-body time includes streaming compression, server scheduling,',
        'client scheduling and delivery. It is not an observed server processing',
        'time and does not identify which component slowed.', '',
        'The identical encoded output in all 7,300 measured responses is 251,268',
        'bytes with SHA256 09c01067d654a0d044672211cc80919f1a71116554ccd5b5da35dab9da0318af.',
        'Application/input hashes, runtime resources, PID/start identities and thread',
        'sets also verify. No response/output-size change explains the excursion.', '',
        'No measured client response windows overlap in any of the 25 cohorts.',
        'The next dispatch occurs more than 100 ms after the preceding complete',
        'body across validation. This rules out overlapping client HTTP response',
        'windows in the saved record; it does not establish an internal FIFO queue',
        'measurement or exclusive CPU execution.', '',
        '## 3. CPU and timing distributions show variation without a traced cause', '',
        'The excursion uses 19.013133 ms cgroup CPU per measured offer. Other',
        'same-rate cohorts span 18.408100–19.039043 ms. Cohorts 9 and 12 have',
        'comparable or larger average CPU use but only 47.667% and 44% misses.',
        'Aggregate CPU per offer therefore does not uniquely explain the miss',
        'excursion. CPU accounting includes the declared common drain controls',
        'and cannot assign CPU time to individual requests.', '',
        'An exploratory <18 ms response threshold exposes differing lower tails:',
        'same-rate cohorts 2/4/9/12/14/16 contain 57/1/2/1/58/57 such offers.',
        'The threshold was selected after inspecting the saved distributions and',
        'is not a new scientific gate. The entire excursion distribution shifted;',
        'cohorts 9 and 12 also lost most fast responses without its large central',
        'shift. A single common stationary response distribution is not demonstrated.', '',
        'Both measurement throttle counters remain zero in all cohorts. The saved',
        'ancestor CPU limit is unlimited; stable affinity confines the service to',
        'CPU 2 but records no competing-task timeline or CPU reservation. No saved',
        'scheduler trace, per-request CPU stages, client GC timeline, thermal/frequency',
        'timeline or network event trace resolves the longer interval.', '',
        '## 4. Tight-deadline sensitivity and balanced-rate patterns', '',
        'The pooled calibration has 50% misses at the frozen deadline. At diagnostic',
        'offsets of -100/-50/+50/+100 us, its miss fractions are 57.750/53.938/',
        '45.625/41.625%. Moving by only 0.1 ms crosses roughly eight percentage',
        'points of this steep CDF region. This explains how small timing shifts can',
        'produce substantial probability errors; these alternative deadlines are',
        'post-hoc arithmetic, not substitute endpoints or new validated forecasts.', '',
        'At the unchanged deadline, 8 requests/s has fewer misses than 4 requests/s',
        'in every balanced block. The six C-minus-A differences are',
        ', '.join(f'{x:.3f}' for x in contrasts_ac) + ' percentage points.',
        'Their mean is -5.222 points. This is an observed within-block association,',
        'not proof that increasing load causally improves latency.', '',
        'Relative scheduled offsets modulo 100 ms differ: the 5/s reference repeats',
        'one residue, 4/s alternates two, approximately 6/s nearly cycles three',
        '(with 1 ns drift per three offers), and 8/s cycles four. There is no saved',
        'exact client-clock origin or quota-replenishment trace to map those grids',
        'onto actual quota phase. All six same-rate cohorts share the same grid but',
        'show different distributions. Cadence alone is therefore not a demonstrated',
        'explanation for the block-2 excursion.', '',
        '## 5. What this diagnosis resolves', '',
        'The unsupported accuracy outcome survives a correct evidence replay.',
        'Its largest excursion is persistent and mainly visible after response',
        'headers, with unchanged output/runtime and no recorded measurement',
        'throttling or client response overlap. Together with calibration variation',
        'and steep-deadline sensitivity, this identifies a stationarity limitation',
        'of the tested complete-response forecast. It does not identify a scheduler,',
        'compression, client, frequency, networking or quota-phase mechanism.', '',
        'Record this diagnosis with the negative transfer result. Do not rerun this',
        'generation, discard the excursion or retune its deadline. Any future',
        'mechanism study would need measurements that can separate the observed',
        'headers-to-body interval and client/server state; defining one remains',
        'a separate prospective task. No further experiment is proposed here.', '']
    (out / 'report.md').write_text('\n'.join(lines))
    paths = [Path(__file__).resolve(), out / 'report.json', out / 'report.md', out / 'request-stage-traces.csv',
             c.BASE / 'bundle-seal.json', base / 'evidence-seal.json']
    c.save(out / 'evidence-seal.json', dict(files_sha256={str(p.relative_to(ROOT)): c.sha(p) for p in paths}))
    print(out / 'report.md')


if __name__ == '__main__': main()
