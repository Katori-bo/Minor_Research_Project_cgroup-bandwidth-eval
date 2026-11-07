"""All acquired raw offers and existing control-call accounting; no new probes."""
from pathlib import Path
import common as r


def acquired(directory):
    rows=[]
    for path in Path(directory).rglob('*.json'):
        if 'bundle' in path.relative_to(directory).parts:continue
        if path.name not in ('warmup.json','loadgen.json','measurement.json'):continue
        try:
            raw=r.read(path)
            if 'Rows' in raw:observed=len(raw['Rows']);declared=raw['Count']
            elif 'requests' in raw:observed=len(raw['requests']);declared=raw['total_scheduled']
            else:continue
            rows.append(dict(path=str(path.relative_to(directory)),sha256=r.sha(path),declared_offers=declared,
                recorded_rows=observed,client_dropped=raw.get('client_dropped'),parseable=True))
        except (ValueError,KeyError):rows.append(dict(path=str(path.relative_to(directory)),parseable=False,sha256=r.sha(path)))
    return rows


def control_calls():
    import kernel_service_bridge as bridge
    values=dict(getattr(bridge,'HTTP_CALLS',{}))
    try:
        import nginx_helpers as nginx
        for key,count in getattr(nginx,'HTTP_CALLS',{}).items():values[key]=values.get(key,0)+count
    except ImportError:pass
    return dict(attempted_existing_control_calls=values,
        additional_probes_sent=False,server_acceptance_not_inferred_from_attempts=True)
