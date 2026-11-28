"""New line-level challenge; authored scenarios and gold precede all predictions."""
from build_cases import source_lists
from pathlib import Path
import json,random,sys
SC={
'carrier_claim':[
('b','The carrier lost {n} {A} last Wednesday. Please dispatch {m} {B} to us.'),
('r','Claim form {o} reproduces the words "ship {n} {A}". Could you sign the damage declaration?'),
('a','Please send {n} {A}. The compensation claim for {m} {B} is separate.'),
('r','Before we request another {m} {B}, has the driver located the missing cartons?'),
('ab','Replace our stock with {n} {A} and {m} {B}; bill the replenishment as normal.'),
('a','Yesterday our branch received {m} {B}. For our branch today, supply {n} {A}.')],
'branch_transfer':[
('a','Dispatch {n} {A} to our usual receiving desk. The sister branch already has {m} {B}.'),
('r','The other branch asked us to order {n} {A} for them. Did they send you their own requisition?'),
('b','Please supply {m} {B}. Last month we transferred {n} {A} internally.'),
('r','The branch ledger lists {n} {A} and {m} {B}. Which branch took delivery?'),
('ab','Our replenishment ticket is ready for fulfilment: {m} {B} and {n} {A}, usual address.'),
('r','If east branch releases its allocation we can take {n} {A}. Wait for their reply.')],
'contract_redlines':[
('r','Counsel highlighted the phrase “dispatch {n} {A}” in section {o}. What did your drafter intend?'),
('b','The contract illustration mentions {n} {A}. Order {m} {B} for our account now.'),
('ab','Please deliver {n} {A} plus {m} {B}; the signed terms remain unchanged.'),
('r','Both {n} {A} and {m} {B} are illustrative quantities for the redline, not a call for stock.'),
('a','We hereby order {n} {A}. Do not send {m} {B}.'),
('r','We would sign for {m} {B} provided that you waive the handling fee.')],
'event_setup':[
('b','The rehearsal used {n} {A}. For this event please deliver {m} {B}.'),
('r','A volunteer read aloud: send {n} {A}. Was that from last year’s running sheet?'),
('a','We need {n} {A} for setup. What is the rental price for {m} {B} for a later event?'),
('ab','Release {n} {A} and {m} {B} for Friday’s installation.'),
('r','Would {n} {A} and {m} {B} fit through the loading entrance? We are still planning.'),
('b','Omit {n} {A} from the rehearsal list; please dispatch {m} {B} for the actual event.')],
'audit_trail':[
('r','Please explain why the log says release {n} {A}. We are reconciling records and need the timestamp.'),
('a','During the audit we counted {m} {B} already on hand. Please ship {n} {A}.'),
('b','The recorded entry for {n} {A} belongs to an earlier quarter. Authorisation for today covers {m} {B}; go ahead with that line.'),
('r','Are the {m} {B} on audit line {o} a receipt or a dispatch?'),
('ab','Please supply {n} {A} and {m} {B}. Reference audit clearance {o}.'),
('r','Our draft request for {n} {A} has not cleared audit. Do not release stock.')]}
def build():
 s=source_lists();rng=random.Random(55491);r=[]
 for family,bank in SC.items():
  for j,(tag,template) in enumerate(bank):
   for k,n in enumerate(rng.sample(range(2,32),5)):
    a,b=rng.sample(s['PRODUCTS'],2);m=rng.randrange(2,30);lines=({a[0]:n} if 'a' in tag else {})|({b[0]:m} if 'b' in tag else {})
    r.append(dict(id=f'line-{family}-{j}-{k}',family=family,pair_id=f'{family}-{j}',split='test',subject='Operations correspondence',sender=rng.choice(s['CUSTOMERS'])[2],text=template.format(n=n,m=m,A=a[rng.randrange(2)],B=b[rng.randrange(2)],o=rng.randrange(41,101)),gold_action='draft' if lines else 'review',gold_draft_lines=lines))
 assert len(r)==len({x['text'] for x in r})==150;return r
if __name__=='__main__':
 with Path(sys.argv[1]).open('x',encoding='utf8') as f:json.dump(build(),f,indent=2)
