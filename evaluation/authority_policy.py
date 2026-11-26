"""Freeze authority-aware operating points before opening the new challenge."""
from meta_router import *
from v2_gate_pkg.authority import triage

def decision(branch,score,cut):
    if branch=='local_review': return 'review'
    if branch=='verified_draft': return 'small'
    return 'strong' if score>=cut else 'small'

def prepare(p,split):
    cs=[c for c in json.loads((p/('stress-manifest.json' if split=='stress' else 'manifest.json')).read_text()) if c['split']==split]
    sm,bg,kv=[linked(p/f'{split}-{m}.jsonl',cs) for m in ['small','strong','kev']];cat=source_lists()['PRODUCTS'];rs=[]
    for c in cs:
        i=c['id'];s=sm[i];v=verdict(c,s);x,sc=base(c,s,kv[i],cat)
        branch,reason=triage(c['text'],cat,s['mapped_lines'],v[0])
        rs.append((c,x,sc,branch,v,verdict(c,bg[i])))
    return rs
def stats(rows,model,cut):
    counts=dict(n=len(rows),calls=0,kev_calls=0,drafts=0,wrong=0,correct=0,missed=0,local_correct_drafts=0,local_reviews=0)
    for c,x,sc,branch,s,b in rows:
        dest=decision(branch,prob(x,model),cut)
        d,ok={'small':s,'strong':b,'review':(False,c['gold_action']=='review')}[dest]
        counts['calls']+=dest=='strong';counts['kev_calls']+=branch=='assess';counts['drafts']+=d;counts['correct']+=ok;counts['wrong']+=d and not ok;counts['missed']+=not d and c['gold_action']=='draft';counts['local_correct_drafts']+=d and ok and dest!='strong';counts['local_reviews']+=not d and dest!='strong'
    return counts
def freeze(p):
    rs=prepare(p,'calibration');part=json.loads((p/'calibration-partition.json').read_text())
    train=[r for r in rs if part[r[0]['pair_id']]=='fit' and r[3]=='assess']
    val=[r for r in rs if part[r[0]['pair_id']]=='threshold']
    model=fit([r[1] for r in train],[not r[4][1] for r in train]); grid=sorted({-1.,2.}|{prob(r[1],model) for r in val if r[3]=='assess'})
    opts=[dict(threshold=t,**stats(val,model,t)) for t in grid]
    safe=[v for v in opts if v['drafts'] and v['wrong']/v['drafts']<.05];cuts={'risk':min(safe,key=lambda v:(v['calls'],-v['correct'])) if safe else None}
    for b in [.2,.3]:cuts[str(b)]=min(opts,key=lambda v:(abs(v['calls']/len(val)-b),v['calls']))
    with (p/'authority-policy.json').open('x') as f:json.dump(dict(model=model,cuts=cuts,nfit=len(train),fit_scope='assess only'),f,indent=2)
if __name__=='__main__':freeze(Path(sys.argv[1]))

