"""Expected counts at exact budgets on unresolved emails; keep resolved paths local."""
import itertools,csv,sys
from authority_policy import *
def export_curve(p,sp):
    rows=prepare(p,sp);m=json.loads((p/'authority-policy.json').read_text())['model'];n=len(rows)
    def v(pair):
        draft,ok=pair;return np.array([ok,draft,draft and not ok],float)
    total=np.zeros(3);pending=[]
    for c,x,sc,br,s,b in rows:
        if br=='local_review':total+=v((False,c['gold_action']=='review'))
        else:
            total+=v(s)
            if br=='assess':pending.append((prob(x,m),v(b)-v(s)))
    rec=[]
    def add(k,r):
        ok,d,b=r;rec.append(dict(panel=sp,policy='authority',operating=k,n=n,calls=k,correct=ok,drafts=d,wrong=b,wdr=b/d if d else None))
    add(0,total);used=0
    for _,g in itertools.groupby(sorted(pending,key=lambda r:-r[0]),lambda r:r[0]):
        a=list(g);diff=sum(r[1] for r in a)
        for j in range(1,len(a)+1):add(used+j,total+diff*j/len(a))
        total+=diff;used+=len(a)
    with (p/f'{sp}-authority-curves.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rec[0]);w.writeheader();w.writerows(rec)
if __name__=='__main__':export_curve(Path(sys.argv[1]),sys.argv[2])
