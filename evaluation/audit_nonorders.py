"""Per-message operating labels for the old panel; no real ticket register was supplied."""
import csv,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parents[2]
from module_rules import rules
OPS={
'audit_trail-0':('reply','Explain logged dispatch and supply timestamp'),
'audit_trail-3':('reply','Classify the audit event as receipt or dispatch'),
'audit_trail-5':('action','Audit hold: verify no release is pending'),
'branch_transfer-1':('reply','Confirm whether the other branch filed a requisition'),
'branch_transfer-3':('reply','Identify receiving branch'),
'branch_transfer-5':('action','Track an outstanding allocation decision'),
'carrier_claim-1':('reply','Sign and return damage declaration; claim number alone is not a verified case'),
'carrier_claim-3':('reply','Investigate missing cartons and answer sender'),
'contract_redlines-0':('reply','Clarify the drafter’s intent'),
'contract_redlines-3':('archive','Illustrative quantities only; no action or response requested'),
'contract_redlines-5':('action','Decision needed on waiver before any purchase'),
'event_setup-1':('reply','Identify whether the quoted instruction is obsolete'),
'event_setup-4':('reply','Answer loading-door fit question')}
def audit(src,out):
 rows=json.loads(src.read_text(encoding='utf8'));tab=[]
 for r in rows:
  if r['gold']:continue
  label,why=OPS[r['scenario']];route,_=rules._disposition_route(r['text'],True,lambda _:None,'Operations correspondence')
  tab.append(dict(id=r['id'],scenario=r['scenario'],email=r['text'],operational_gold=label,reason=why,verified_ticket='',route=route,human=int(route=='human')))
 assert len(tab)==65 and all((r['operational_gold']=='archive')==(r['route']=='archived') for r in tab)
 out.parent.mkdir(exist_ok=True,parents=True)
 with out.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=tab[0]);w.writeheader();w.writerows(tab)
 from collections import Counter
 print(Counter(r['operational_gold'] for r in tab))
if __name__=='__main__':audit(*map(Path,sys.argv[1:3]))
