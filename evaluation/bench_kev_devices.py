"""Paired three-check localhost microbenchmark; never sends email to a cloud endpoint."""
import argparse,json,time,statistics,sys
from urllib.request import Request,build_opener,ProxyHandler
from pathlib import Path
from math import ceil
RULES={'category':'Is the proposed category inconsistent with the current customer request?',
       'product':'Is any currently requested product missing, substituted, or included only from a quotation, cancellation or signature?',
       'quantity':'Does any proposed quantity disagree with the final amount requested for that product?'}
client=build_opener(ProxyHandler({}))
def call(port,c,r):
    state={'email':c['text'],'category':r['category'],'lines':r['lines'],'category_guide':'standard: clear order; complex: ambiguous or special conditions; quote: price inquiry'}
    b=json.dumps({'model':'kev-latest','state':json.dumps(state,ensure_ascii=False),'questions':{k:{'type':'noul','instructions':v} for k,v in RULES.items()}}).encode()
    t=time.perf_counter()
    with client.open(Request(f'http://127.0.0.1:{port}/v1/systemone',data=b,headers={'Content-Type':'application/json'}),timeout=120) as f:
        checks=json.load(f)['answers']
    return dict(ms=(time.perf_counter()-t)*1000,checks={k:float(checks[k]['noul']) for k in RULES})
def main(p,out):
    cs=[c for c in json.loads((p/'manifest.json').read_text()) if c['split']=='test'];sm={r['id']:r['candidate'] for r in map(json.loads,(p/'test-small.jsonl').read_text().splitlines())}
    # One product realization per scenario; warmup uses a different realization.
    selected=[c for c in cs if c['id'].endswith('-0')];assert len(selected)==30
    warm=next(c for c in cs if c['id'].endswith('-1'))
    ports={'cpu':8008,'gpu':8009};res={'warmup':{},'rows':[]}
    for d,port in ports.items():res['warmup'][d]=call(port,warm,sm[warm['id']])
    for j,c in enumerate(selected):
        row={'id':c['id']}
        for d in (list(ports) if j%2==0 else reversed(ports)):
            row[d]=call(ports[d],c,sm[c['id']])
        res['rows'].append(row)
    res['summary']={}
    for d in ports:
        a=sorted(r[d]['ms'] for r in res['rows']);res['summary'][d]=dict(mean=statistics.mean(a),median=statistics.median(a),p95=a[ceil(.95*len(a))-1])
    res['max_probability_difference']=max(abs(r['cpu']['checks'][k]-r['gpu']['checks'][k]) for r in res['rows'] for k in RULES)
    out.write_text(json.dumps(res,indent=2));print(res['summary'])
if __name__=='__main__':main(*map(Path,sys.argv[1:3]))
