#!/usr/bin/env python3
"""Download selected pinned public source text; never build or run a profiler."""
from pathlib import Path
import concurrent.futures
import hashlib
import json
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'analysis/runtime_io_profiler_semantics_gate/20261008'
PINS={'coz':('plasma-umass/coz','256e3c389424d6a1691ee5d18b5ecb5a6c1001ec',''),
      'bcoz':('s3yonsei/blocked_samples','2836bd096e1c5d07ab5fed83a69977e1e3a94a97','bcoz/')}

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'bounded-offline-research-check'})
    with urllib.request.urlopen(req,timeout=30) as r:return r.read()

def main():
    if (OUT/'sources/manifest.json').exists():raise ValueError('preserve existing source acquisition')
    entries=[]
    for name,(repo,commit,prefix) in PINS.items():
        url=f'https://api.github.com/repos/{repo}/git/trees/{commit}'
        data=json.loads(get(url))
        if prefix:
            tree=next(x['sha'] for x in data['tree'] if x['path']==prefix.rstrip('/'))
        else:tree=commit
        data=json.loads(get(f'https://api.github.com/repos/{repo}/git/trees/{tree}?recursive=1'))
        if data.get('truncated'):raise ValueError('truncated source tree')
        folder=OUT/'sources'/name;folder.mkdir(parents=True,exist_ok=True)
        (folder/'tree.json').write_text(json.dumps(data,indent=2)+'\n')
        for e in data['tree']:
            p=e['path']
            if e['type']!='blob' or e.get('size',0)>300000:continue
            if not (p.startswith(('libcoz/','include/','viewer/','go/')) or p in ('coz','README.md','LICENSE','LICENSE.md')):continue
            if p.endswith(('.png','.jpg','.svg','.woff','.map')):continue
            entries.append((name,repo,commit,prefix,p,e['sha']))
    def fetch(e):
        name,repo,commit,prefix,p,gitsha=e
        url=f'https://raw.githubusercontent.com/{repo}/{commit}/{prefix}{p}'
        raw=get(url)
        expected=hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()
        if expected!=gitsha:raise ValueError('Git blob hash mismatch: '+p)
        dest=OUT/'sources'/name/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
        return dict(profiler=name,repository=repo,commit=commit,path=prefix+p,url=url,
            saved_path=str(dest.relative_to(ROOT)),git_blob_sha1=gitsha,sha256=hashlib.sha256(raw).hexdigest())
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:records=list(pool.map(fetch,entries))
    (OUT/'sources/manifest.json').write_text(json.dumps(dict(pins=PINS,files=records,build=False,profiler_executed=False),indent=2)+'\n')
    print(json.dumps(dict(downloaded_files=len(records),pins=PINS,build=False,profiler_executed=False),indent=2))

if __name__=='__main__':main()
