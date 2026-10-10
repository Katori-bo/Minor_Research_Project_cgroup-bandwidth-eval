#!/usr/bin/env python3
"""Classify saved BPF ownership without modifying the root audit or host."""
import argparse
import hashlib
import json
from pathlib import Path

import leftover_observer_audit as audit

ROOT = Path(__file__).resolve().parents[1]
SYSTEMD = {'restrict_filesystems':'lsm','sd_devices':'cgroup_device',
           'sd_fw_ingress':'cgroup_skb','sd_fw_egress':'cgroup_skb'}
SELF_MAPS = {'libbpf_global':(32,0), 'libbpf_det_bind':(32,0), 'pid_iter.rodata':(4,1152)}


def classify(value):
    original=audit.assess(value)
    allowed={'BPF '+k+' objects need ownership review' for k in ('prog','link','map')}
    if original['missing'] or set(original['findings'])-allowed:
        raise ValueError('incomplete audit or non-BPF observers require separate review')
    process={p['pid']:p for p in value['processes']['rows']}
    def holder(obj,comm,pid=None):
        return any(p['comm']==comm and (pid is None or p['pid']==pid)
            and process.get(p['pid'],{}).get('comm')==comm
            and process[p['pid']]['uid']==0 for p in obj.get('pids',[]))
    programs=value['bpf']['prog']['items']; maps=value['bpf']['map']['items']; links=value['bpf']['link']['items']
    by_prog={p['id']:p for p in programs}; by_map={p['id']:p for p in maps}
    if len(by_prog)!=len(programs) or len(by_map)!=len(maps): raise ValueError('duplicate BPF identities')
    decisions=[]; systemd_ids=set(); network_maps=set()
    for p in programs:
        if p.get('orphaned'): raise ValueError('orphaned program requires review')
        if SYSTEMD.get(p.get('name'))==p['type'] and holder(p,'systemd',1):
            systemd_ids.add(p['id'])
            decisions.append(dict(kind='prog',id=p['id'],classification='systemd_service_policy',
                evidence='known policy program type/name and PID1 systemd descriptor holder'))
            continue
        # One observed code fingerprint and referenced map; no blanket
        # socket-filter exemption is granted.
        refs=p.get('map_ids',[])
        if (p['type']=='socket_filter' and p.get('tag')=='3dca42c7d2a04d67'
                and p.get('gpl_compatible') is False and len(refs)==1 and refs[0] in by_map):
            m=by_map[refs[0]]
            if (m['type']=='hash' and m['bytes_key']==4 and m['bytes_value']==1
                    and m['max_entries']==8 and holder(m,'NetworkManager')):
                network_maps.add(m['id'])
                decisions.append(dict(kind='prog',id=p['id'],classification='network_filter_associated_with_NetworkManager',
                    evidence=f"observed code tag, socket-filter type and sole map {m['id']} held by verified root NetworkManager",
                    limit='Socket owner is inferred from the shared map; its socket descriptor was not independently attributed.'))
                continue
        raise ValueError('unclassified BPF program: '+str(p['id']))
    referenced={i for p in programs for i in p.get('map_ids',[])}
    for m in maps:
        if m['id'] in network_maps:
            category='NetworkManager_held_filter_map'
        elif (m.get('name')=='cgroup_hash' and m['type']=='hash_of_maps' and holder(m,'systemd',1)
              and any(m['id'] in by_prog[i].get('map_ids',[]) for i in systemd_ids)):
            category='systemd_filesystem_policy_map'
        elif (m.get('name') in SELF_MAPS and m['type']=='array' and m['bytes_key']==4
              and (m['bytes_value'],m['flags'])==SELF_MAPS[m['name']] and m['max_entries']==1
              and m['id'] not in referenced
              and all(p['comm']=='bpftool' for p in m.get('pids',[]))):
            category='bpftool_libbpf_inventory_infrastructure'
        else: raise ValueError('unclassified BPF map: '+str(m['id']))
        decisions.append(dict(kind='map',id=m['id'],classification=category))
    seen=set()
    for link in links:
        if link['id'] in seen: raise ValueError('duplicate link identity')
        seen.add(link['id']); p=by_prog.get(link['prog_id'],{})
        if (link['type']!='tracing' or link.get('prog_type')!='lsm' or link.get('attach_type')!='lsm_mac'
                or p.get('name')!='restrict_filesystems' or p.get('id') not in systemd_ids
                or not holder(link,'systemd',1)):
            raise ValueError('unclassified BPF link: '+str(link['id']))
        decisions.append(dict(kind='link',id=link['id'],classification='systemd_LSM_filesystem_policy'))
    return dict(status='no_unexplained_experimental_observer_in_reviewed_snapshot',
        performance_eligible=True,decisions=decisions,counts=dict(prog=len(programs),map=len(maps),link=len(links)),
        historical_cause_established=False,host_modified=False,
        limitation='Ownership classification applies to this saved snapshot only. System-service filters remain active. '
            'This does not establish zero overhead, historical absence or unchanged network state. '
            'The socket-filter association uses its NetworkManager-held map, not direct socket ownership. '
            'bpftool uses transient BPF infrastructure to enumerate descriptor owners.')


def review(path):
    path=Path(path).absolute()
    if path.parent!=ROOT/'analysis/runtime_io_leftover_observer_audit' or path.is_symlink():
        raise ValueError('use saved dedicated audit evidence')
    data=json.loads(path.read_text())
    if data['uid']!=0 or audit.assess(data)!=data['assessment']:
        raise ValueError('root audit/assessment inconsistent')
    if data['audit_script_sha256']!=hashlib.sha256((ROOT/'diagnostic/leftover_observer_audit.py').read_bytes()).hexdigest():
        raise ValueError('audit implementation changed')
    result=classify(data)
    result.update(audit_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        reviewer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        audit_path=str(path),boot_id=data['boot_id']['text'])
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('write','verify')); p.add_argument('--audit',type=Path,required=True)
    a=p.parse_args(); result=review(a.audit); sidecar=a.audit.with_suffix('.review.json')
    if a.command=='write':
        with sidecar.open('x') as f: json.dump(result,f,indent=2); f.write('\n')
    elif json.loads(sidecar.read_text())!=result: raise ValueError('ownership review changed')
    print(result['status']); print('Review: '+str(sidecar))


if __name__=='__main__': main()
