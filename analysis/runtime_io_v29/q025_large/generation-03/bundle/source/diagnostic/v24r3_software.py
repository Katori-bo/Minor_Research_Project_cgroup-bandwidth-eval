"""Native build/software provenance and full-duration regular-file check."""
import sys
import v24r3_model as model
import v24r3_counter as counter

SOURCES=('diagnostic/v24r3_counter.c','diagnostic/v24r3_counter.py',
         'diagnostic/v24r3_model.py','diagnostic/v24r3_software.py',
         'analysis/check_v24r3_sampler.py')

def summarize(probe,path):
    samples=model.validate_samples(probe,path)
    duration=(probe['finished_ns']-probe['started_ns'])/1e9
    if not 110<=duration<=110.1 or not 5000<=len(samples)<=6000:
        raise ValueError('native synthetic recording lacks full110-second coverage')
    spans=[b['after_ns']-a['before_ns'] for a,b in zip(samples,samples[1:])]
    if max(spans)>60_000_000:raise ValueError('native synthetic adjacent coverage exceeds60ms')
    return dict(duration_sec=duration,own_cpu_ms=probe['own_cpu_ns']/1e6,
                max_adjacent_span_ms=max(spans)/1e6,**model.acquisition_diagnostics(probe))

def verify_build(c):
    c.verify_seal(c.BUILD);m=c.read(c.BUILD/'manifest.json')
    if (m['source_sha256']!=c.digest(c.ROOT/'diagnostic/v24r3_counter.c')
            or m['binary_sha256']!=c.digest(c.BUILD/'counter') or not m['compile_passed']):
        raise ValueError('native build identity differs')
    return m

def verify_receipt(directory,c):
    build=verify_build(c);c.verify_seal(directory);m=c.read(directory/'report.json')
    if (m['decision']!='native_synthetic_sampler_pass' or m['performance_run'] is not False
            or m['runtime_qualified'] is not False or m['binary_sha256']!=build['binary_sha256']
            or m['source_hashes']!={n:c.digest(c.ROOT/n) for n in SOURCES}):
        raise ValueError('native software receipt identity differs')
    raw=c.read(directory/'counter.raw.json');probe=counter.decode(raw)
    if probe!=c.read(directory/'counter.json'):raise ValueError('native decoding differs from raw')
    if summarize(probe,str(directory/'synthetic.cpu.stat'))!=m['summary']:
        raise ValueError('native synthetic summary differs')
    if c.read(directory/'argv.json')!=[str(c.BUILD/'counter'),'--path',str(directory/'synthetic.cpu.stat'),'--output',str(directory/'counter.raw.json')]:
        raise ValueError('native software command differs')
    if (directory/'stdout').read_text()!='READY\n':raise ValueError('native software readiness differs')
    return m
