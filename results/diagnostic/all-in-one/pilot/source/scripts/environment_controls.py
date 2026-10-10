"""Read-only environment controls; thresholds are protocol choices, not hardware limits."""
from pathlib import Path
import shutil
import statistics
import subprocess

POLICY = dict(initial_idle_sec=600, sample_sec=5, window_sec=60,
              max_range_c=2.0, max_abs_slope_c_per_min=1.0,
              baseline_tolerance_c=3.0, timeout_sec=1200)


def power_settings(include_profile=False):
    result = {'policies': {}, 'platform_profile': None, 'external_power': {}}
    for policy in sorted(Path('/sys/devices/system/cpu/cpufreq').glob('policy*')):
        row = {}
        for field in ['scaling_driver', 'scaling_governor', 'energy_performance_preference',
                      'scaling_min_freq', 'scaling_max_freq']:
            p = policy / field
            if p.exists():
                row[field] = p.read_text().strip()
        result['policies'][policy.name] = row
    p = Path('/sys/firmware/acpi/platform_profile')
    if p.exists():
        result['platform_profile'] = p.read_text().strip()
    for supply in sorted(Path('/sys/class/power_supply').glob('*')):
        if (supply / 'online').exists():
            result['external_power'][supply.name] = (supply / 'online').read_text().strip()
    if include_profile:
        result['desktop_profile'] = None
        if shutil.which('powerprofilesctl'):
            r = subprocess.run(['powerprofilesctl', 'get'], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                result['desktop_profile'] = r.stdout.strip()
    return result


def comparable_power(settings):
    return {k: v for k, v in settings.items() if k != 'desktop_profile'}


def window_summary(samples, baseline=None, policy=POLICY):
    if len(samples) < 2 or samples[-1]['elapsed_sec'] - samples[0]['elapsed_sec'] < policy['window_sec']:
        return None
    keys = set(samples[0]['temperatures'])
    if not keys or any(set(s['temperatures']) != keys for s in samples):
        raise RuntimeError('Temperature sensors disappeared or changed during settling.')
    if baseline is not None and set(baseline) != keys:
        raise RuntimeError('Temperature sensors differ from the session baseline.')
    x = [s['elapsed_sec'] / 60 for s in samples]
    xmean = statistics.mean(x)
    denominator = sum((t - xmean) ** 2 for t in x)
    sensors = {}
    for key in sorted(keys):
        vals = [s['temperatures'][key] for s in samples]
        mean = statistics.mean(vals)
        slope = sum((t - xmean) * (v - mean) for t, v in zip(x, vals)) / denominator
        span = max(vals) - min(vals)
        near = baseline is None or abs(mean - baseline[key]) <= policy['baseline_tolerance_c']
        sensors[key] = dict(mean_c=mean, range_c=span, slope_c_per_min=slope, near_baseline=near)
    stable = all(v['range_c'] <= policy['max_range_c'] and
                 abs(v['slope_c_per_min']) <= policy['max_abs_slope_c_per_min'] and
                 v['near_baseline'] for v in sensors.values())
    return {'stable': stable, 'sensors': sensors}
