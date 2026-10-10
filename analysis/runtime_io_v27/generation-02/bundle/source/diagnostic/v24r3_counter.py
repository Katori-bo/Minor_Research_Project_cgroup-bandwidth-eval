"""Decode retained native raw records after collection, never during acquisition."""
import hashlib
import json
import re


def decode(document):
    if document.get('schema')!=3 or document.get('sampler_revision')!='v24r3-native':
        raise ValueError('native record identity differs')
    result={k:v for k,v in document.items() if k!='samples'}
    result['samples']=[]
    for source in document['samples']:
        if source['read_errno']!=0:raise ValueError('native acquisition failed')
        values={}
        for line in source['raw'].splitlines():
            fields=line.split()
            if len(fields)!=2 or fields[0] in values or not re.fullmatch('[0-9]+',fields[1]):
                raise ValueError('invalid/duplicate native counter text')
            values[fields[0]]=int(fields[1])
        if not {'usage_usec','user_usec','system_usec'}<=values.keys():
            raise ValueError('native counter text lacks required keys')
        result['samples'].append(dict((k,v) for k,v in source.items() if k!='raw')|dict(cpu_stat=values))
    return result


def decode_file(path, output, save):
    value=decode(json.loads(path.read_text()))
    value['raw_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    save(output,value)
    return value
