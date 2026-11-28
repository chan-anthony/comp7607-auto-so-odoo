# Run in Odoo shell. Both variants see the same native case state and identical model output.
import json,os,re
from pathlib import Path
from unittest.mock import patch
from http.client import IncompleteRead
from odoo.addons.sale_email_order.models.sale_email_order import LEGACY_STRATEGIES,STRATEGY_DEFAULTS
assert env.cr.dbname=='odoo_test'
p=Path('/tmp/group55-disposition'); cases=json.loads((p/'manifest.json').read_text()); register=json.loads((p/'register.json').read_text())
Model=env['sale.email.order']; ids={};rev={}; rows=[]
for ref,t in register.items():
 ticket=Model.create(dict(name='Existing procurement review case',body='Earlier correspondence',email_from=t['sender'],state='review' if t['open'] else 'archived'))
 ids[int(ref)]=ticket.id;rev[ticket.id]=int(ref)
replay_only=os.getenv('DISPOSITION_REPLAY_ONLY')=='1'
old_bodies={r['id']:r['body'] for r in json.loads((p/'native-pairs.json').read_text())} if replay_only else {}
OrderModel=type(env['sale.email.order']);real=OrderModel._call_openai
cachepath=p/'strong-candidates.jsonl'
cache={v['input']:v['result'] for v in map(json.loads,cachepath.read_text().splitlines())} if cachepath.exists() else {}
def once(record,messages):
 if replay_only:
  msgs=[dict(m) for m in messages];assert msgs[-1]['role']=='user' and msgs[-1]['content']==msg
  assert re.sub(r'CASE-\d+', 'CASE-ID',msg)==re.sub(r'CASE-\d+','CASE-ID',old_bodies[c['id']])
  msgs[-1]['content']=old_bodies[c['id']]
 else:msgs=messages
 key=json.dumps(msgs,ensure_ascii=False,sort_keys=True)
 if replay_only and key not in cache:raise AssertionError('Missing previously measured candidate')
 if key not in cache:
  for trial in range(3):
   try:out=real(record,messages);break
   except IncompleteRead:
    if trial==2:raise
  cache[key]=out
  with cachepath.open('a',encoding='utf8') as f:f.write(json.dumps(dict(input=key,result=out))+'\n')
 return tuple(cache[key])
with patch.object(OrderModel,'_call_openai',once):
 for c in cases:
  msg=re.sub(r'CASE-(\d+)',lambda m:'CASE-'+str(ids.get(int(m[1]),1900000000+int(m[1]))),c['text'])
  row={'id':c['id'],'body':msg}
  for mode in ['authority_line','authority_disposition']:
   for key,value in dict(STRATEGY_DEFAULTS,**LEGACY_STRATEGIES[mode]).items():env['ir.config_parameter'].sudo().set_param(f'sale_email_order.{key}',value)
   r=Model.create(dict(name=c['subject'],body=msg,email_from=c['sender']))
   r._process();tr=r.inference_trace or {};assert not (r.review_reason or '').startswith('AI call failed'),(c['id'],r.review_reason)
   lines=sorted((l.product_id.default_code,l.product_uom_qty) for l in r.sale_order_id.order_line);link=rev.get(r.related_case_id.id)
   if r.related_case_id:
    assert r in r.related_case_id.related_inbound_ids
    notes=[v for v in r.related_case_id.message_ids if ('Associated inbound email '+str(r.id)+';') in str(v.body)]
    assert bool(notes)==(tr.get('disposition')=='linked_human')
   # This predicate mirrors the current native All human work queue, including draft+reply.
   queued=bool(Model.search_count([('id','=',r.id),'|',('state','=','review'),('followup_needed','=',True)]))
   row[mode]=dict(state=r.state,lines=lines,human=queued,cloud='GPT-6.2 Sol' in tr.get('path',[]),route=tr.get('disposition') or tr.get('line_route'),case=link,trace=tr.get('line_evidence'),record=r.id)
   if mode=='authority_disposition' and queued:
    had_draft=bool(r.sale_order_id)
    r.action_finish_followup()
    assert not r.followup_needed and r.state==('done' if had_draft else 'handled')
  rows.append(row);print(c['id'],flush=True)
env.cr.rollback()
(p/'native-pairs.json').write_text(json.dumps(rows,indent=2))
print('Complete; test records rolled back.',len(rows))
