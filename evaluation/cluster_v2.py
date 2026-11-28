"""Paired scenario-cluster uncertainty at 30% budget; ties never use outcomes.
Intervals describe sensitivity to the sampled scenarios within these synthetic families.
"""
import json,sys
from pathlib import Path
import numpy as np
from authority_policy import prepare,rules

def rank(base,gain,score,k):
    if k==0:return base.sum()
    boundary=np.partition(score,-k)[-k];hi=score>boundary;tie=score==boundary
    return base.sum()+gain[hi].sum()+(k-hi.sum())*gain[tie].mean()
def main(p,split):
    cfg=json.loads((p/'authority-policy.json').read_text());r=prepare(p,split)
    # action correctness may rise on local review without an escalation.
    sm=np.array([int(x[4][1]) for x in r]);bg=np.array([int(x[5][1]) for x in r]);delta=bg-sm
    authbase=np.array([int(x[0]['gold_action']=='review') if x[3]=='local_review' else int(x[4][1]) for x in r])
    pending=np.array([x[3]=='assess' for x in r]); risk=np.array([rules._risk_probability(x[1],cfg['model']) for x in r]);verbal=np.array([x[2]['verbal'] for x in r]); lp=np.array([x[2]['logprob'] for x in r])
    # Stress templates reuse the same action wording across products. Resample
    # complete situations; challenge resamples its six scenarios within each family.
    strata={}
    for i,(c,*_) in enumerate(r):
        fam='stress' if split=='stress' else c['family'];cluster=c['family'] if split=='stress' else c['pair_id']
        strata.setdefault(fam,{}).setdefault(cluster,[]).append(i)
    def calc(idx):
        k=round(.3*len(idx)); where=idx[pending[idx]]
        if len(where)<k:return None
        A=authbase[idx].sum()+rank(np.zeros(len(where)),delta[where],risk[where],k)
        op={'random':sm[idx].sum()+k*delta[idx].mean(),'verbal':rank(sm[idx],delta[idx],verbal[idx],k),'logprob':rank(sm[idx],delta[idx],lp[idx],k)}
        return [(A-v)*100/len(idx) for v in op.values()]
    rng=np.random.default_rng(551126);sim=[];point=calc(np.arange(len(r)))
    for _ in range(1000):
        draw=[]
        for g in strata.values():
            clusters=list(g.values())
            for j in rng.integers(len(clusters),size=len(clusters)):draw.extend(clusters[j])
        v=calc(np.array(draw))
        if v is not None:sim.append(v)
    result={'point_pp':point,'order':['random','verbal','logprob'],'feasible_resamples':len(sim),'attempts':1000,'interval95_pp':np.quantile(sim,[.025,.975],axis=0).T.tolist() if sim else None}
    (p/f'{split}-budget30-cluster.json').write_text(json.dumps(result,indent=2));print(result)
if __name__=='__main__':main(Path(sys.argv[1]),sys.argv[2])
