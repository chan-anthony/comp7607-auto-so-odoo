"""Cloud confirmation comparator: local rules may abstain but never create a draft."""
from authority_policy import *
import csv
def bench(p,split):
    rows=prepare(p,split);out=[]
    for family in ['ALL']+sorted({r[0]['family'] for r in rows}):
        rs=[r for r in rows if family=='ALL' or r[0]['family']==family]
        v=[(br!='local_review',b if br!='local_review' else (False,c['gold_action']=='review'),c) for c,x,sc,br,s,b in rs]
        out.append(dict(family=family,n=len(v),calls=sum(u for u,r,c in v),drafts=sum(r[0] for u,r,c in v),wrong=sum(r[0] and not r[1] for u,r,c in v),correct=sum(r[1] for u,r,c in v),missed=sum(not r[0] and c['gold_action']=='draft' for u,r,c in v),local_correct_drafts=0))
    with (p/f'{split}-confirm.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=out[0]);w.writeheader();w.writerows(out)
    print(out[0])
if __name__=='__main__':bench(Path(sys.argv[1]),sys.argv[2])
