"""Score native workflow decisions against independent operational labels."""
import json,csv,sys
from pathlib import Path
from collections import Counter
def score(d):
 def read(n):return json.loads((d/n).read_text(encoding='utf8'))
 cases={c['id']:c for c in read('manifest.json')};pairs=read('native-pairs.json')
 assert len(pairs)==len({r['id'] for r in pairs})==len(cases)
 result={};ledger=[]
 for mode in ('authority_line','authority_disposition'):
  a=Counter()
  for r in pairs:
   c=cases[r['id']];v=r[mode];lines=dict(v['lines']);g=c['gold_draft_lines']; h=c['gold_human'];human=v['human'];matched=v['case'] is not None
   assert lines==dict(r['authority_line']['lines']) and v['cloud']==r['authority_line']['cloud']
   a.update(dict(n=1,draftable=bool(g),drafts=bool(lines),wrong_drafts=bool(lines) and lines!=g,missed_drafts=bool(g) and not lines,correct_workflow=lines==g,local_correct_drafts=bool(g) and lines==g and not v['cloud'],cloud=v['cloud'],human=human,need_reply=h=='reply',missed_reply=h=='reply' and not human,need_action=h=='action',missed_action=h=='action' and not human,unneeded_human=h=='none' and human,linked=matched,correct_link=matched and v['case']==c['gold_case'],gold_link=c['gold_case'] is not None,wrong_link=matched and v['case']!=c['gold_case'],archive=v['state']=='archived',bad_archive=v['state']=='archived' and not c['gold_archive'],linked_human=v['route']=='linked_human',linked_no_action=v['route']=='linked_no_action',draft_plus_human=bool(lines) and human))
   if mode=='authority_disposition':ledger.append(dict(id=c['id'],family=c['family'],scenario=c['pair_id'],email=c['text'],gold_lines=g,required=h,expected_case=c['gold_case'],base=r['authority_line'],revised=v))
  result[mode]=dict(a)
 (d/'results.json').write_text(json.dumps(result,indent=2))
 with (d/'blind-decisions.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=ledger[0]);w.writeheader();w.writerows([{k:json.dumps(v,ensure_ascii=False) if isinstance(v,dict) else v for k,v in r.items()} for r in ledger])
 print(json.dumps(result))
if __name__=='__main__':score(Path(sys.argv[1]))
