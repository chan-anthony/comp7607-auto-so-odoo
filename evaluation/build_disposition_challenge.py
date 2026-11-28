"""Prospective benchmark. Operational truth assigned from the business scenario before inference.
Ticket register is separate from model input. open=matching owner, closed/other=ineligible.
gold_order: a/b/ab; human: reply/action/none. Existing tickets do not imply work is finished.
"""
from pathlib import Path
from build_cases import source_lists
import random,json,sys
BANK={
'document_control':[
('a','none','none','Please supply {n} {A}.'),
('b','reply','none','Dispatch {m} {B}. Could you also tell us who signed the prior document?'),
('','none','none','We have filed the confirmation. For our records only.'),
('','reply','none','We received your documents. Where is the signed annex?'),
('','none','open','{ref}: We have recorded your update. No response required.'),
('','action','open','{ref}: No reply needed, but replace the old certificate in our file.'),
('','reply','closed','{ref}: Which revision did you send us?'),
('ab','none','none','Release {n} {A} and {m} {B} for the documentation team.')],
'customs_desk':[
('b','none','none','Yesterday customs listed {n} {A}. Please ship {m} {B}.'),
('','reply','open','{ref}: Please confirm the declaration value for {n} {A}.'),
('','none','none','Courtesy copy for your records. No action needed.'),
('','reply','none','For your records: do you still need our clearance stamp?'),
('','none','open','{ref}. Thanks for the confirmation.'),
('','action','other','{ref}: A clearance notice went to the wrong account. Redirect the notice.'),
('a','none','none','Please book {n} {A} against our usual account.'),
('','none','none','Our broker has retained the stamped copy. Nothing more is expected of your team.')],
'service_visit':[
('','none','open','{ref}: The paperwork is filed.'),
('a','reply','none','Send {n} {A}. Please advise when the technician can attend.'),
('','reply','none','The inspection is complete. Can your technician send the measurements?'),
('','action','open','{ref}: There is a second fault on site. Arrange another visit.'),
('b','none','none','Deliver {m} {B} to our service counter.'),
('','none','none','Thank you for letting us know. No follow-up required.'),
('','reply','missing','{ref}: Who handles the calibration request now?'),
('ab','none','none','Our service bench needs both lots. Please dispatch {n} {A} plus {m} {B}.')],
'dispatch_notification':[
('a','none','none','The carrier already collected {m} {B}. Dispatch {n} {A}.'),
('','none','open','{ref}. Our team has received the delivery note.'),
('','none','none','Receipt acknowledgement. No response requested.'),
('','action','none','The delivery note was filed under the wrong consignee. Amend the entry.'),
('','reply','open','{ref}: Thanks for the update. When will the missing pallet arrive?'),
('b','none','none','We hereby order {m} {B}.'),
('','action','closed','{ref}: The shipment is still short. Reopen the claim.'),
('','reply','none','No action on the shipment itself. We do need the driver to call us back.')],
'renewal_admin':[
('','none','none','We received your notice. No need to respond.'),
('','action','open','{ref}: We are changing the billing contact. Update the customer record.'),
('','none','open','{ref}. Duplicate copy for our records.'),
('','reply','other','{ref}: Is this our renewal or another branch’s?'),
('ab','none','none','Please supply {n} {A} and {m} {B}. Renewal paperwork is separate.'),
('','reply','none','We are waiting for your answer on the renewal date.'),
('a','none','none','Please release {n} {A} on our existing terms.'),
('','none','none','Just a courtesy note acknowledging receipt of your circular.')]}
def build():
 rng=random.Random(533920);s=source_lists();cases=[];register={}
 for fam,rows in BANK.items():
  for j,(order,human,status,text) in enumerate(rows):
   for k in range(4):
    a,b=rng.sample(s['PRODUCTS'],2);n,m=rng.sample(range(2,35),2);person,other=rng.sample(s['CUSTOMERS'],2);ref=51000+len(cases);lines=({a[0]:n} if 'a' in order else {})|({b[0]:m} if 'b' in order else {})
    if status in ('open','closed','other'):register[str(ref)]={'open':status!='closed','sender':other[2] if status=='other' else person[2],'company':1}
    subj=rng.choice(['Operations correspondence','Update','Procurement correspondence'])
    cases.append(dict(id=f'nd-{fam}-{j}-{k}',family=fam,pair_id=f'{fam}-{j}',split='test',subject=subj,text=text.format(A=a[rng.randrange(2)],B=b[rng.randrange(2)],m=m,n=n,ref=f'CASE-{ref}'),sender=person[2],company=1,gold_human=human,gold_case=ref if status=='open' else None,gold_archive=not lines and human=='none' and status=='none',gold_action='draft' if lines else 'review',gold_draft_lines=lines))
 return cases,register
if __name__=='__main__':
 p=Path(sys.argv[1]);cs,reg=build();assert len(cs)==160 and len({c['id'] for c in cs})==160
 for name,v in [('manifest',cs),('register',reg)]:
  with (p/(name+'.json')).open('x',encoding='utf8') as f:json.dump(v,f,indent=2,ensure_ascii=False)
