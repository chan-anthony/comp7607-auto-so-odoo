"""Independent prospective scenarios for the scoped-authority revision; never filter on outputs."""
from build_cases import source_lists
from pathlib import Path
import json,random,sys
BANK={
"printer_proofs":[
('r','The artwork on page {o} tells readers to ship {n} {A}. Is that the version you printed?'),
('a','Page {o} is the obsolete artwork. Separately, please supply {n} {A}.'),
('r','Our proof contains a misprint: please send {n} {A} should have been removed. Just correct the artwork.'),
('ab','Please ship {n} {A} and {m} {B}. The proof has already been signed off.'),
('b','Discard the old print layout. Against our account put {m} {B} on the van; the {A} belong to the photograph.'),
('r','Before printing, tell us what {n} {A} plus {m} {B} would come to.')],
"handover_notes":[
('a','This is my shift now. Send {n} {A}.'),
('r','I found the instruction to release {n} {A} in the handover book. Has the night shift already done it?'),
('b','The {n} {A} belong to the previous shift. For this shift send {m} {B} on the morning run.'),
('r','Shift lead says she might want {m} {B}. Hold the requisition for her signature.'),
('ab','Dispatch {m} {B} plus {n} {A}.'),
('r','Night shift booked {n} {A} and {m} {B} yesterday. We need their delivery reference.')],
"bid_clarification":[
('r','The bid specimen reads: supply {n} {A}. Please mark up the sample text, not our order book.'),
('a','The tender discussion is over. Please deliver {n} {A}.'),
('r','For bid comparison only, what lead time would you allow for {n} {A} and {m} {B}?'),
('b','We have placed the {A} portion elsewhere. Your awarded portion is {m} {B}; proceed with delivery.'),
('ab','Please supply {n} {A} and {m} {B}. Thank you.'),
('r','If we win the tender the first batch would be {m} {B}. Is your rate valid through Friday?')],
"reimbursement":[
('a','Finance has settled the claim. Order {n} {A}.'),
('r','The expense report says order {n} {A}, but that was a personal purchase. We just need a duplicate receipt.'),
('r','We paid for {m} {B} at the counter. Which exchange rate belongs on our reimbursement?'),
('ab','For central stores rather than the expense claim, ship {n} {A} together with {m} {B} this week.'),
('b','Please dispatch {m} {B}. Charge our usual account.'),
('r','Can we reclaim the deposit on {n} {A} if the proposed purchase never proceeds?')],
"migration_records":[
('r','Our import screen shows dispatch {n} {A}. The line is test data; check that no consignment was raised.'),
('a','Migration finished. Release {n} {A}.'),
('b','The migrated {A} quantity is the historical balance. The new request is for {m} {B}; please send them.'),
('r','The import will duplicate {m} {B} if you run it now. Leave the queue alone.'),
('ab','We are ordering {m} {B} and {n} {A}. Please use the new billing profile.'),
('r','What SKU should replace the retired entry for {n} {A} in the import file?')]}
def build():
 rng=random.Random(729115); src=source_lists();rows=[]
 for fam,grp in BANK.items():
  for j,(act,t) in enumerate(grp):
   for k,n in enumerate(rng.sample(range(2,34),5)):
    a,b=rng.sample(src['PRODUCTS'],2);m=rng.randint(2,24)
    lines=({a[0]:n} if 'a' in act else {})|({b[0]:m} if 'b' in act else {})
    rows.append(dict(id=f'scope-{fam}-{j}-{k}',split='test',family=fam,pair_id=f'{fam}-{j}',subject='Correspondence with purchasing',text=t.format(n=n,m=m,A=a[rng.randrange(2)],B=b[rng.randrange(2)],o=rng.randint(51,133)),sender=rng.choice(src['CUSTOMERS'])[2],gold_action='draft' if lines else 'review',gold_draft_lines=lines))
 assert len(rows)==len({r['text'] for r in rows})==150
 return rows
if __name__=='__main__':
 with Path(sys.argv[1]).open('x',encoding='utf8') as f:json.dump(build(),f,indent=2)
