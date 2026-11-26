import json
from pathlib import Path
assert env.cr.dbname=='odoo_test'
cases=json.loads(Path('/tmp/group55-line16.json').read_text())
params=env['ir.config_parameter'].sudo()
params.set_param('sale_email_order.strategy','authority_line')
verified=[]
for c in cases:
    r=env['sale.email.order'].create(dict(name='Scoped-line regression',body=c['text'],email_from=c['sender']))
    r._process()
    assert 'strong_call' not in r.inference_trace
    ls=sorted((x.product_id.default_code,x.product_uom_qty) for x in r.sale_order_id.order_line)
    assert ls==sorted(c['gold_draft_lines'].items()) and (r.state=='done')==(c['gold_action']=='draft'),c['id']
    verified.append(dict(id=c['id'],state=r.state,lines=ls,evidence=r.inference_trace.get('line_evidence')))
env.cr.rollback()
Path('/tmp/group55-line16-result.json').write_text(json.dumps(verified))
print('Verified native draft lines, 16 fixtures, transaction rolled back')
