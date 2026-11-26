"""Prospective post-repair challenge. Text and semantic truth fixed before scoring."""
from build_cases import source_lists
from pathlib import Path
import random,sys,json
BANK={
"delegated_purchaser":[
("a","Covering for Mina today. Her note said {o}, but the quantity I am releasing against her requisition is {n} {A}. Use the normal destination."),
("r","Mina copied me on a request for {n} {A} addressed to the other vendor. Do you know whether that vendor acknowledged it?"),
("b","I can sign for the {m} {B} myself; get that lot on its way. Only Mina can sign for the {n} {A}, and she is away."),
("r","I can sign for {m} {B} after Mina countersigns. Can your desk send me the form?"),
("ab","Sam has handed the purchase desk to me. Book both lots under my name: {n} {A}; {m} {B}."),
("r","The approver changed from Sam to me. Leave the current {n} {A} transaction untouched; just update your contact list.")],
"partial_backorder":[
("a","The backorder is separate. For the third floor's new requirement put {n} {A} on a fresh ticket."),
("r","Our ledger still shows {n} {A} on backorder. Which date is showing at your end?"),
("b","Carry the outstanding {A} forward, no change there. The extra line for dispatch now is {m} {B}."),
("r","Would moving {m} {B} ahead of the {n} {A} backorder attract another freight charge?"),
("ab","Top up the branch independently of the backorder: ship {m} {B} together with {n} {A}."),
("r","Only if the original backorder is void should its {n} {A} be re-entered. We're still checking its status.")],
"meeting_action_owner":[
("a","Action log, item {o}: supplier to dispatch {n} {A}. That's your action from today's meeting; process it on our account."),
("r","Action log, item {o}: buyer to investigate {n} {A}. Your action was just to circulate the specification."),
("b","Facilities is pricing {A} elsewhere. The only action for your desk is delivery of {m} {B}; book it today."),
("r","The meeting pencilled in {m} {B}. Can you attach catalogue pricing to the minutes for Friday's vote?"),
("ab","Closing the minutes: release the two approved lines for our site, {n} {A} and {m} {B}."),
("r","Our minutes incorrectly say your desk should send {n} {A} and {m} {B}. Please acknowledge the correction, not the lines.")],
"asset_service":[
("a","The maintenance call is closed. Separately we need new stock: deliver {n} {A} to our usual depot."),
("r","Asset team logged {n} {A} for inspection. Can your service engineer take the job?"),
("b","No repair is needed on {A}. Instead send our office {m} new {B}, against the normal account."),
("r","We may replace {m} {B} if the inspection fails. Is the warranty still valid?"),
("ab","For the installation crew, send fresh units: {n} of {A}, {m} of {B}. Labour is handled in-house."),
("r","I'm attaching serial numbers for the {n} {A} and {m} {B} already installed. Please register their warranty.")],
"release_window":[
("a","The loading slot has opened. Put {n} {A} on our regular consignment; the old slot number {o} is obsolete."),
("r","If the loading slot opens we can accept {n} {A}. Keep the goods where they are until our call."),
("b","Use today's slot for {m} {B}. Leave the suggested {n} {A} off the consignment."),
("r","What time would the truck need to leave for {m} {B} to reach slot {o}? We are building the schedule."),
("ab","Today's manifest for you to fulfil: {n} {A} plus {m} {B}. Dock and payment details as before."),
("r","Could you find the gate pass used for the last {n} {A}? The carrier lists window {o} on the receipt.")]}
def build():
 src=source_lists();rng=random.Random(225671);out=[]
 for fam,rows in BANK.items():
  for j,(act,tmpl) in enumerate(rows):
   for k,n in enumerate(rng.sample(range(2,33),5)):
    a,b=rng.sample(src['PRODUCTS'],2);m=rng.randrange(2,24);o=rng.randrange(44,109)
    text=tmpl.format(A=a[rng.randrange(2)],B=b[rng.randrange(2)],n=n,m=m,o=o)
    lines=({a[0]:n} if 'a' in act else {})|({b[0]:m} if 'b' in act else {})
    out.append(dict(id=f'new-{fam}-{j}-{k}',split='test',family=fam,pair_id=f'{fam}-{j}',subject='Procurement correspondence',text=text,sender=rng.choice(src['CUSTOMERS'])[2],gold_action='draft' if lines else 'review',gold_draft_lines=lines))
 assert len(out)==len({r['text'] for r in out})==150
 return out
if __name__=='__main__':
 with Path(sys.argv[1]).open('x',encoding='utf8') as f:json.dump(build(),f,indent=2)
