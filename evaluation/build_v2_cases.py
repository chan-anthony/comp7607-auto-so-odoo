"""V2 scenario register. Each row fixes its gold independently of inference.
A/B denote catalogue items, n/m their current counts; o is superseded or incidental.
Repeated realizations are clustered by scenario; they are not independent templates.
"""
import json,random,sys
from pathlib import Path
from build_cases import source_lists
CA={
"stockroom":[
("a","Down to {o} on the shelf. Could you replenish us with {n} {A} on our usual account?"),
("r","Counted {n} {A} here versus {o} in your dispatch note. Can you reconcile those?"),
("b","We have enough {A} after all. The shortfall is {m} {B}; send those along."),
("r","The stockroom might need {m} {B} next month. Could you pencil in what that would run us?"),
("ab","For the shelf refill, put {n} {A} and {m} {B} on the van."),
("r","Stock check only: can your depot cover {n} {A} and {m} {B} by Friday?")],
"cost_centres":[
("a","CC-{o} is open again. Book {n} {A} to it and deliver to our usual dock."),
("r","If CC-{o} reopens we'll take {n} {A}. Finance hasn't released it yet."),
("b","For CC-{o}, the {A} allocation is closed; release {m} {B} against the remaining balance."),
("r","Please split {m} {B} across both cost centres. We'll send the allocations tomorrow."),
("ab","Approved against one account: {n} x {A}; {m} x {B}. Process together."),
("r","What's the extended amount against CC-{o} for {n} {A}? Need that for approval.")],
"receiving":[
("a","Dock {o} will be staffed. Send {n} {A} with your next run."),
("r","Did dock {o} sign for the {n} {A}? We're missing the delivery slip."),
("b","We can receive the {m} {B} now. Send those; the {A} were received yesterday."),
("r","Before dispatching {m} {B}, check whether dock {o} has room. Wait for our reply."),
("ab","Dock {o}, one delivery please: {n} {A} plus {m} {B}. Usual terms."),
("r","The driver left {n} {A} and {m} {B} at dock {o}. Can you forward proof of receipt?")],
"sample_return":[
("a","Your demo unit worked. Please send {n} new {A} on our account, excluding the demo."),
("r","Can we return the {n} {A} from the demo? Send a return label."),
("b","Keep the {A} sample on loan. Supply {m} new {B} for installation."),
("r","We tested {m} {B} and need repair paperwork rather than replacements."),
("ab","Demo finished. Ship fresh stock for rollout: {n} {A}, {m} {B}."),
("r","Before we commit, is the return window for {n} {A} the same as for {m} {B}?")],
"invoice_match":[
("a","That invoice covers the old batch. For the next run please ship {n} {A} separately."),
("r","Invoice {o} lists {n} {A}. Could you check the tax line?"),
("b","The paid invoice for {A} is settled. Please supply {m} {B} on a new invoice."),
("r","Accounts needs a copy of invoice {o} for {m} {B}; nothing arrived by email."),
("ab","Invoice the next delivery separately: please ship {n} x {A} and {m} x {B}."),
("r","Do the {n} {A} and {m} {B} on invoice {o} include freight?")]}
TE={
"clipped_forward":[
("a","Top part of the chain got clipped. The dispatch instruction that stands is {n} {A}.\n> Buyer floated {o} last week."),
("r","Forward ends mid-sentence. Can you find the rest before anyone releases the {n} {A}?\n> please send"),
("b","The forwarded extract is stale. Send {m} {B} to our regular address.\nFrom: Stores\n{n} {A}"),
("ab","Please release both lines in the surviving attachment extract:\n{A} | {n}\n{B} | {m}\n> older version removed"),
("r","Can you see who wrote the clipped line below?\n> Ship {n} {A} and {m} {B}"),
("r","This is for your records, forwarding what the buyer sent another supplier.\n> release {n} {A}")],
"spoken_amendment":[
("a","Scratch my arithmetic. Make it {n} of the {A} for us, not {o}. Same drop-off."),
("r","Hang on, was it {n} {A} or {o}? Leave the ticket alone till I check."),
("b","My bad, mixed the names up. Send {m} {B}; skip the {A}."),
("r","Before you change that ticket from {n} {A} to {m} {B}, tell me the difference in price."),
("ab","Quick correction before the truck leaves: {n} {A}, plus {m} {B}. That's the lot to send."),
("r","Ignore my voice note about another {n} {A}. Keep the existing shipment as it is.")],
"mixed_enquiry":[
("a","What would {m} {B} cost down the road? For today just send {n} {A}; don't wait on the pricing."),
("r","Our request sheet says ship {n} {A}, but for now all purchasing needs is your figure."),
("b","Price {n} {A} for next week. In the meantime release {m} {B} against our account."),
("ab","Send {n} {A} and {m} {B} at the listed rates. Separately, who handles volume pricing for next year?"),
("r","How much would the shipment of {n} {A} plus {m} {B} come to, delivered?"),
("r","Our buyer asked me to compare {n} {A} with {m} {B}. Which lot costs less to ship?")],
"revocation":[
("a","The hold on {n} {A} has been lifted. Go ahead with those; the other lines are withdrawn."),
("r","We signed the sheet for {n} {A} yesterday but have withdrawn it this morning. Please acknowledge."),
("b","Strike the {A} from today's sheet. The {m} {B} line still goes out; please release it."),
("r","Release {m} {B} only if our withdrawal misses your cutoff. Has it missed it?"),
("ab","Cancel the hold, not the goods. The lines to dispatch are {n} {A} and {m} {B}."),
("r","Our authorisation for {n} {A} expired yesterday. Send the paperwork for renewing it.")],
"standing_release":[
("a","Against blanket reference {o}, draw down {n} {A} for delivery to our normal site."),
("r","Blanket reference {o} has {n} {A} outstanding. When is the existing release arriving?"),
("b","Leave the {A} balance untouched. Call off {m} {B} under blanket {o} and deliver as usual."),
("ab","Drawdown for this week under {o}: {A} / {n}; {B} / {m}. Same consignee."),
("r","Show the remaining entitlement under blanket {o} after a hypothetical draw of {n} {A}."),
("r","Put the proposed draw of {m} {B} on hold until someone signs for the previous batch.")]}
def build():
    src=source_lists(); cat=src['PRODUCTS']; cust=src['CUSTOMERS']; rng=random.Random(551126)
    for split,bank,reps in [('calibration',CA,5),('test',TE,6)]:
        for family,rows in bank.items():
            for j,(action,body) in enumerate(rows):
                used=set()
                for k in range(reps):
                    a,b=rng.sample(cat,2); n,m=rng.sample(range(2,31),2); o=rng.randrange(51,119)
                    while n in used: n=rng.randrange(2,31)
                    used.add(n)
                    ctx=dict(A=a[rng.randrange(2)],B=b[rng.randrange(2)],n=n,m=m,o=o)
                    lines=({a[0]:n} if 'a' in action else {})|({b[0]:m} if 'b' in action else {})
                    yield dict(id=f'v2-{family}-{j}-{k}',split=split,family=family,pair_id=f'{family}-{j}',subject='Purchasing desk',text=body.format(**ctx),sender=rng.choice(cust)[2],gold_action='draft' if lines else 'review',gold_draft_lines=lines)
if __name__=='__main__':
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True); rows=list(build())
    assert len(rows)==330 and len({r['text'] for r in rows})==330
    with (out/'manifest.json').open('x',encoding='utf8') as f:json.dump(rows,f,indent=2,ensure_ascii=False)

