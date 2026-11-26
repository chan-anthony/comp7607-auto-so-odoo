"""Final visuals and offline replay. All numeric labels use native paired outputs."""
import json,csv,sys,html
from pathlib import Path
from plot_results import plt,save
from score_disposition import score
def build(d,old,out):
 def load(p):return json.loads(p.read_text(encoding='utf8'))
 score(d);S=load(d/'results.json');A,B=S.values();R=load(old/'fresh/line-summary.json');C,E=R.values()
 out.mkdir(exist_ok=True,parents=True)
 def bars(title,labels,series,names,stem):
  fig,ax=plt.subplots(figsize=(7.0,max(2.5,len(labels)*.65+.9)));cs=['#8497a2','#00786b']
  for j,(s,n) in enumerate(zip(series,names)):
   ys=[i+(j-.5)*.34 for i in range(len(labels))];ax.barh(ys,s,.32,label=n,color=cs[j])
   for y,v in zip(ys,s):ax.text(v+.6,y,str(v),ha='left',va='center',fontsize=9)
  ax.set_yticks(range(len(labels)),labels);ax.invert_yaxis();ax.set_xlabel('Emails');ax.set_title(title);ax.set_xlim(0,max(max(v) for v in series)*1.17);fig.legend(loc='lower center',ncol=2);fig.tight_layout(rect=[0,.10,1,1]);save(fig,out/'figures',stem)
 bars('Line-level authorization · earlier 150-email blind panel',['Wrong drafts','Correct local drafts','Sent to cloud','Sent to human review'],[[g[k] for k in ['wrong','local_ok','cloud','review']] for g in [C,E]],['Former scope rule','Per-line authorization'],'authorization')
 bars('Same 160 emails, same quotation decisions',['Emails requiring a person','Unnecessary human referrals','Required replies without a human path','Drafts with human follow-up','Sent to cloud'],[[g[k] for k in ['human','unneeded_human','missed_reply','draft_plus_human','cloud']] for g in [A,B]],['Line authorization only','With non-order disposition'],'workload')
 labels=['Draft only','Draft plus follow-up','Unlinked human queue','Existing case + human','Existing case, no new work','Archive']
 counts=[B['drafts']-B['draft_plus_human'],B['draft_plus_human'],B['human']-B['draft_plus_human']-B['linked_human'],B['linked_human'],B['linked_no_action'],B['archive']]
 assert sum(counts)==B['n'];fig,ax=plt.subplots(figsize=(7,3.4));ax.barh(labels,counts,color=['#00786b','#b96a39','#b96a39','#b96a39','#00786b','#00786b']);ax.invert_yaxis();ax.set_xlim(0,max(counts)*1.22)
 for i,v in enumerate(counts):ax.text(v+.5,i,str(v),va='center')
 ax.set_title('Where each email actually ended');ax.set_xlabel('Emails');fig.tight_layout();save(fig,out/'figures','outcomes')
 cs={c['id']:c for c in load(d/'manifest.json')};pairs=load(d/'native-pairs.json');cards=[]
 for r in pairs:
  c=cs[r['id']];o=r['authority_line'];v=r['authority_disposition'];cards.append(dict(id=c['id'],family=c['family'],text=c['text'],subject=c['subject'],required=c['gold_human'],ref=c['gold_case'],base=o,new=v))
 (d/'examples.json').write_text(json.dumps([next(a for a in cards if a['id'].startswith(p)) for p in ['nd-document_control-4-','nd-document_control-5-','nd-document_control-1-','nd-dispatch_notification-2-','nd-service_visit-6-','nd-customs_desk-5-']],indent=2,ensure_ascii=False),encoding='utf8')
 import string
 page=string.Template("""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width, initial-scale=1"><title>Group 55 | Who still needs to act?</title><style>*{box-sizing:border-box}body{font:16px/1.5 system-ui;background:#edf4f3;color:#18343c;max-width:1100px;margin:auto;padding:25px}header,article{background:white;border-radius:12px;padding:20px;margin:10px 0}h1{margin:0;color:#09675c}select{font:inherit;max-width:100%;padding:7px}section{display:grid;grid-template-columns:1fr 1fr;gap:10px}pre{white-space:pre-wrap;font:inherit}b{color:#135e60}@media(max-width:700px){section{display:block}}</style><header><small>COMP7607A · Group 55 · recorded Odoo transactions · offline</small><h1>Who still needs to act?</h1><p>Pick an incoming message. A reference links only to a matching open case. A linked request for action still counts as human work.</p><select id=q></select></header><article><b id=sub></b><pre id=mail></pre></article><section><article><h2>Line authorization only</h2><div id=l></div></article><article><h2>With non-order disposition</h2><div id=r></div></article></section><article id=gold></article><script type=application/json id=ds>$payload</script><script>const data=JSON.parse(ds.textContent);for(const row of data)q.add(new Option(row.id,row.id));function render(){const row=data.find(x=>x.id===q.value);sub.textContent=row.subject;mail.textContent=row.text;for(const [key,to] of [['base',l],['new',r]]){const d=row[key];to.innerText=['Native state: '+d.state,'Needs a person: '+(d.human?'YES':'No'),'Cloud exposure: '+(d.cloud?'YES':'No'),'Matched case: '+(d.case?'CASE-'+d.case:'—'),'Quotation lines: '+(d.lines.map(x=>x.join(' × ')).join(', ')||'—')].join('\\n')}gold.textContent='Expected staff obligation: '+row.required+' · Expected matching case: '+(row.ref?'CASE-'+row.ref:'none')}q.value='nd-document_control-5-0';q.onchange=render;render()</script>""").substitute(payload=json.dumps(cards,ensure_ascii=False).replace('<','\\u003c'))
 (out/'Workflow_Replay.html').write_text(page,encoding='utf8')
if __name__=='__main__':build(*map(Path,sys.argv[1:4]))
