"""Compute online deployment and equal-budget expected counts; no tuning."""
import csv,itertools,collections
from meta_router import *
from lexical_baseline import predict
from v2_gate_pkg.hybrid_gate import review_reason
def main(p,split):
    cases=[c for c in json.loads((p/('stress-manifest.json' if split=='stress' else 'manifest.json')).read_text()) if c['split']==split]
    cfg=json.loads((p/'frozen-policies.json').read_text())
    s,b,k=[linked(p/f'{split}-{m}.jsonl',cases) for m in ['small','strong','kev']]
    cat=source_lists()['PRODUCTS'];rows=[]
    for c in cases:
        i=c['id'];x,sc=base(c,s[i],k[i],cat);sc['hybrid']=prob(x,cfg['model']) if sc['disagreement'] else -1;sc['random']=0
        a,l=predict(c['text'],cat);v=(a=='draft',a==c['gold_action'] and (a=='review' or l==sorted(c['gold_draft_lines'].items())))
        rows.append((i,sc,verdict(c,s[i]),verdict(c,b[i]),v,c['gold_action']=='draft'))
    def vec(r,v,cloud): 
        d,ok=v
        return np.array([float(cloud),d,ok,d and not ok,r[5] and not d,(not cloud) and d and ok],float)
    def record(mode,op,v):
        cloud,d,ok,bad,miss,local=v
        return dict(panel=split,policy=mode,operating=op,n=len(rows),calls=cloud,local_share=1-cloud/len(rows),drafts=d,correct=ok,wrong=bad,wdr=bad/d if d else None,missed=miss,correct_local_drafts=local)
    online=[]; curves=[]
    for key,col in [('small',2),('strong',3),('lexical',4)]:
        online.append(record(key,'fixed',sum(vec(r,r[col],key=='strong') for r in rows)))
    guard=cfg['cuts']['hybrid']['0.3']['threshold']
    guarded=[]
    for c,r in zip(cases,rows):
        if review_reason(c['text']):
            guarded.append(vec(r,(False,not r[5]),False))
        else:
            cloud=r[1]['hybrid']>=guard
            guarded.append(vec(r,r[3] if cloud else r[2],cloud))
    online.append(record('guarded-hybrid','0.3',sum(guarded)))
    for key in rows[0][1]:
        for op,config in cfg['cuts'].get(key,{}).items():
            if config is None:continue
            t=config['threshold'];online.append(record(key,op,sum(vec(r,r[3] if r[1][key]>=t else r[2],r[1][key]>=t) for r in rows)))
        val=sum(vec(r,r[2],False) for r in rows);used=0;curves.append(record(key,used,val))
        for _,group in itertools.groupby(sorted(rows,key=lambda r:-r[1][key]),lambda r:r[1][key]):
            grp=list(group); delta=sum(vec(r,r[3],True)-vec(r,r[2],False) for r in grp)
            for j in range(1,len(grp)+1):
                curves.append(record(key,used+j,val+delta*j/len(grp)))
            val+=delta;used+=len(grp)
    for tag,data in [('online',online),('curves',curves)]:
        with (p/f'{split}-{tag}.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=data[0]);w.writeheader();w.writerows(data)
if __name__=='__main__':main(Path(sys.argv[1]),sys.argv[2])
