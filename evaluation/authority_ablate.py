"""Routing-only ablation under identical authority actions and a fixed call budget."""
import csv,sys
from pathlib import Path
import numpy as np
from authority_policy import prepare,prob,json
from cluster_v2 import rank
def main(p,sp):
 cfg=json.loads((p/'authority-policy.json').read_text());rs=prepare(p,sp)
 unresolved=[r for r in rs if r[3]=='assess'];n=len(rs);m=len(unresolved)
 def vec(v):return np.array([int(v[1]),int(v[0]),int(v[0] and not v[1])])
 base=sum(vec((False,r[0]['gold_action']=='review') if r[3]=='local_review' else r[4]) for r in rs)
 delta=np.array([vec(r[5])-vec(r[4]) for r in unresolved]);out=[]
 for method in ('random','verbal','logprob','raw','disagreement','trained'):
  scores=np.array([prob(r[1],cfg['model']) if method=='trained' else 0. if method=='random' else r[2][method] for r in unresolved])
  for k in range(m+1):
   right,drafts,wrong=[base[j]+rank(np.zeros(m),delta[:,j],scores,k) for j in range(3)]
   out.append(dict(policy=method,n=n,calls=k,correct=right,drafts=drafts,wrong=wrong,wdr=wrong/drafts if drafts else None))
 with (p/f'{sp}-authority-ablations.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=out[0]);w.writeheader();w.writerows(out)
if __name__=='__main__':main(Path(sys.argv[1]),sys.argv[2])
