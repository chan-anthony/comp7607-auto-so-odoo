"""Observe paired outcomes from the same model candidates; save a per-email ledger."""
import csv,json,sys
from pathlib import Path
from authority_policy import prepare,decision,prob,source_lists,linked
from v2_gate_pkg.authority_scope import resolve

def run(p,out,split='test'):
    cfg=json.loads((p/'authority-policy.json').read_text());cut=cfg['cuts']['risk']['threshold'];cat=source_lists()['PRODUCTS'];R=prepare(p,split);C=[r[0] for r in R]
    sm,bg=[linked(p/f'{split}-{m}.jsonl',C) for m in ['small','strong']]
    ledger=[]
    for c,x,sc,br,s,b in R:
        i=c['id'];score=prob(x,cfg['model']);dest=decision(br,score,cut);oldr=sm[i] if dest=='small' else bg[i]; oldlines=oldr['mapped_lines'] if (s[0] if dest=='small' else b[0] if dest=='strong' else False) else []
        ov=resolve(c['text'],cat,sm[i]['known_sender']);reason=ov[2] if ov else 'unchanged';newdest=ov[0] if ov else dest;newlines=ov[1] if ov else oldlines
        gold=sorted(c['gold_draft_lines'].items())
        def metrics(lines,cloud):
            d=bool(lines);ok=(d==(c['gold_action']=='draft') and sorted(map(tuple,lines))==gold)
            return dict(draft=int(d),wrong=int(d and not ok),ok=int(ok),local_ok=int(d and ok and not cloud),cloud=int(cloud),review=int(not d),missed=int(not d and c['gold_action']=='draft'))
        a=metrics(oldlines,dest=='strong');n=metrics(newlines,newdest=='strong')
        ledger.append(dict(id=i,family=c['family'],scenario=c['pair_id'],text=c['text'],gold=gold,old_branch=br,old_route=dest,new_route=newdest,reason=reason,old_lines=oldlines,new_lines=newlines,qwen=sm[i]['candidate'],old=a,new=n))
    out.mkdir(parents=True,exist_ok=True)
    (out/'paired.json').write_text(json.dumps(ledger,indent=2,ensure_ascii=False),encoding='utf8')
    sums={k:{m:sum(r[k][m] for r in ledger) for m in ledger[0][k]} for k in ['old','new']}
    for k,v in sums.items():v['n']=len(ledger);v['wdr']=v['wrong']/v['draft'] if v['draft'] else None
    (out/'scores.json').write_text(json.dumps(sums,indent=2));print(sums)
if __name__=='__main__':run(*map(Path,sys.argv[1:3]))
