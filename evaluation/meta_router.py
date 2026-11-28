"""Fit once on 75, select thresholds on disjoint 75, serialize for pure-Python Odoo."""
import argparse, json, sys
from pathlib import Path
import numpy as np
from build_cases import source_lists
from replay_policies import linked
from module_rules import rules
# Feature order of rules._risk_signal, stored with the fitted policy.
NAMES=('kev_category','kev_product','kev_quantity','intent_agree','sku_agree','amount_agree','quoted','product_mentions','length','field_mean','field_min')

def verdict(c,r):
    lines=r['mapped_lines']; draft=bool(r['candidate']['category']=='standard' and r['candidate']['confidence']>=.8 and r['known_sender'] and lines and all(x[0] for x in lines))
    right=(sorted(map(tuple,lines))==sorted(c['gold_draft_lines'].items()) and c['gold_action']=='draft') if draft else c['gold_action']=='review'
    return draft,bool(right)
def fit(X,y):
    X=np.asarray(X,float);y=np.asarray(y,float);mu=X.mean(0);sd=X.std(0);sd[sd==0]=1
    A=np.column_stack([np.ones(len(X)),(X-mu)/sd]); w=np.zeros(A.shape[1]);pen=np.eye(len(w));pen[0,0]=0
    for _ in range(60):
        p=1/(1+np.exp(-np.clip(A@w,-60,60))); dw=np.linalg.solve(A.T@((p*(1-p))[:,None]*A)+pen,A.T@(p-y)+pen@w)
        w-=dw
        if max(abs(dw))<1e-9:break
    return dict(names=NAMES,mean=mu.tolist(),scale=sd.tolist(),intercept=w[0],coef=w[1:].tolist())
def base(c,s,k,cat):
    x,g=rules._risk_signal(c['text'],s['candidate'],s['mapped_lines'],cat,s['known_sender'],s['field_scores'],k['checks'])
    return x,dict(verbal=1-s['candidate']['confidence'],logprob=-x[-1],raw=max(x[:3]),disagreement=g)
def main(folder):
    cases=[c for c in json.loads((folder/'manifest.json').read_text()) if c['split']=='calibration']
    parts=json.loads((folder/'calibration-partition.json').read_text()); cat=source_lists()['PRODUCTS']
    s,b,k=[linked(folder/f'calibration-{m}.jsonl',cases) for m in ['small','strong','kev']]
    rec=[]
    for c in cases:
        i=c['id'];x,scores=base(c,s[i],k[i],cat); rec.append((parts[c['pair_id']],x,scores,verdict(c,s[i]),verdict(c,b[i])))
    train=[r for r in rec if r[0]=='fit'];val=[r for r in rec if r[0]=='threshold'];assert len(train)==len(val)==75
    active=[r for r in train if r[2]['disagreement']>0]
    model=fit([r[1] for r in active],[not r[3][1] for r in active]); cuts={}
    for _,x,sc,*_ in val: sc['hybrid']=rules._risk_probability(x,model) if sc['disagreement'] else -1.0
    for key in val[0][2]:
        opts=[]
        for t in sorted({r[2][key] for r in val}|{max(r[2][key] for r in val)+1}):
            calls=[r[2][key]>=t for r in val]; actions=[r[4] if call else r[3] for call,r in zip(calls,val)]
            nd=sum(d for d,_ in actions); nw=sum(d and not ok for d,ok in actions)
            opts.append(dict(threshold=t,calls=sum(calls),drafts=nd,wrong=nw,correct=sum(ok for d,ok in actions)))
        good=[v for v in opts if v['drafts'] and v['wrong']/v['drafts']<.05]
        cuts[key]={'risk':min(good,key=lambda v:v['calls']) if good else None}
        for q in (.2,.3):
            cuts[key][str(q)]=min(opts,key=lambda v:(abs(v['calls']/len(val)-q),v['calls']))
    with (folder/'frozen-policies.json').open('x') as f:json.dump(dict(model=model,cuts=cuts,calibration='empirical, no population guarantee',ties='escalate entire boundary group; nearest calibration budget'),f,indent=2)
if __name__=='__main__':main(Path(sys.argv[1]))

