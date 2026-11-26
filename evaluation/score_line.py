"""Evaluate frozen previous scoped risk policy against line evidence validation."""
from score_scope import run,json,Path,sys
from authority_policy import prepare,source_lists,linked
from v2_gate_pkg.line_authority import line_gate
def evaluate(p,out):
 run(p,out);rs=json.loads((out/'paired.json').read_text(encoding='utf8'));cs=[r[0] for r in prepare(p,'test')];sm,bg=[linked(p/f'test-{m}.jsonl',cs) for m in ('small','strong')]; from meta_router import verdict
 for r,c in zip(rs,cs):
  i=c['id'];assert i==r['id'];act,lines,proof=line_gate(c['text'],source_lists()['PRODUCTS'],sm[i]['known_sender'])
  use=act=='assess'
  if use:lines=bg[i]['mapped_lines'] if verdict(c,bg[i])[0] else []
  d=bool(lines);g=c['gold_action']=='draft';ok=(d==g and sorted(map(tuple,lines))==sorted(c['gold_draft_lines'].items()))
  r['previous']=r['new'];r['previous_route']=r['new_route'];r['previous_lines']=r['new_lines'];r['line_route']='strong' if use else act;r['line_lines']=lines;r['proof']=proof
  r['line']=dict(draft=int(d),wrong=int(d and not ok),ok=int(ok),local_ok=int(d and ok and not use),cloud=int(use),review=int(not d),missed=int(not d and g))
 sums={k:{m:sum(r[k][m] for r in rs) for m in rs[0][k]} for k in ['previous','line']}
 for v in sums.values():v['n']=len(rs);v['wdr']=v['wrong']/v['draft'] if v['draft'] else None
 (out/'line-pairs.json').write_text(json.dumps(rs,indent=2,ensure_ascii=False),encoding='utf8');(out/'line-summary.json').write_text(json.dumps(sums,indent=2));print(sums)
if __name__=='__main__':evaluate(*map(Path,sys.argv[1:3]))
