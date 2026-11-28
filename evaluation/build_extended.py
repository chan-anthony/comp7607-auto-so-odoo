"""Additional controlled workload for the 1,000-email proposal.

880 cases = 11 business situations x 4 customer actions x 2 register variants
x 10 primary SKUs. This is a separate stress panel, not 880 independent natural
email templates. Freeze all thresholds on the separate calibration panel first.
"""
import json
from pathlib import Path
import argparse
from build_cases import source_lists

SITUATIONS = [
    ('replacement','We are replacing the equipment in room 12.','Room 12 is getting new equipment.'),
    ('correction','The amount on the last spreadsheet is obsolete.','Ignore the figures in our previous spreadsheet.'),
    ('old_po','Our prior PO {old} has already shipped.','PO {old} was completed last month.'),
    ('signature','This request is from the office team.','Office purchasing here.'),
    ('delivery','The receiving desk closes at 5 pm.','Please note our warehouse shuts at 17:00.'),
    ('alternate','Someone suggested {other}, but we ruled it out.','We decided against the alternative {other}.'),
    ('budget','Our equipment allocation is for cost centre {old}.','Charge approved purchases to cost centre {old}.'),
    ('catalogue','We checked your current catalogue this morning.','The item references below are from your current list.'),
    ('stocktake','Our stock count shows {old} units on hand, not on order.','Inventory on the shelf is {old}; this is not a requested quantity.'),
    ('thread','I am following up on the conversation with our buyer.','Following our call with procurement:'),
    ('project','The installation has moved to building {old}.','Please note the new project site is building {old}.'),
]
ACTION = {
    'single': ('Please supply {n} units of {sku}.','We are placing a firm order for {n} of the {name}.'),
    'multi': ('Please supply {n} x {sku} and {m} x {other}.','Order confirmed: {other} ({m} units) plus {name} ({n} units).'),
    'quote': ('Could you quote for {n} x {sku}? We have not authorised purchase.','We need the unit price for {n} of {name} before purchasing.'),
    'conditional': ('Supply {n} x {sku} only if you can apply our special negotiated price.','We would take {n} units of {name} subject to the discount agreed last year.'),
}


def build():
    catalog=source_lists()
    products, customers=catalog['PRODUCTS'],catalog['CUSTOMERS']
    for j,(family,*intro) in enumerate(SITUATIONS):
        for i,(sku,name,_) in enumerate(products):
            other=products[(i+j%9+1)%len(products)][0]
            n,m=2+(i*7+j)%29,1+(i+j*3)%8
            ctx=dict(old=100+5*j+i,n=n,m=m,sku=sku,name=name,other=other)
            for k in range(2):
                for act,clauses in ACTION.items():
                    text=(intro[k]+' '+clauses[k]).format(**ctx)
                    if family=='signature':
                        text += '\n--\nAsset referenced in company signature (not for purchase): '+other
                    if family=='thread':
                        text += '\n\n> Earlier suggestion, superseded: 8 x '+other
                    lines={sku:n,other:m} if act=='multi' else {sku:n} if act=='single' else {}
                    yield dict(id=f'ext-{family}-{i:02d}-{k}-{act}',family=family,
                               split='stress',pair_id=f'ext-{family}-{i:02d}-{k}',
                               subject='Office procurement',text=text,sender=customers[i%len(customers)][2],
                               gold_category={'single':'standard','multi':'standard','quote':'quote','conditional':'complex'}[act],
                               gold_action='draft' if lines else 'review',gold_draft_lines=lines)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path); args=p.parse_args()
    cases=list(build()); assert len(cases)==880 and len({c['text'] for c in cases})==880
    args.output.write_text(json.dumps(cases,indent=2),encoding='utf8')
