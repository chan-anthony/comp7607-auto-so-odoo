"""Create a portable, network-free replay of actual native Odoo records."""
from pathlib import Path
import csv
import html
import json
import argparse
from email import policy
from email.parser import BytesParser

KIT=Path(__file__).resolve().parents[1]/'test_kit'
MODES={'small':('Qwen','small-base01'),'strong':('GPT-6.2 Sol','strong-replay01'),
       'confidence':('Qwen confidence ≥ 0.80','confidence-defaultdemo01'),
       'kev':('Kev error threshold 0.50','kev-defaultdemo01')}
CASES={'06':'Reply with a superseded quote','18':'Status inquiry','12':'Ambiguous product','01':'Standard order'}
def esc(x): return html.escape(str(x))
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))

def build(folder,out):
    records={m:{r['file']:r for r in load(folder/(stem+'-native.json'))}
             for m,(_,stem) in MODES.items()}
    scores={m:load(folder/(stem+'-scores.json')) for m,(_,stem) in MODES.items()}
    gold={r['file']:r for r in csv.DictReader((KIT/'expected_results.csv').open(encoding='utf-8-sig'))}
    blocks=[]
    for n,label in CASES.items():
        path=next((KIT/'emails').glob(n+'_*.eml')); f=path.name
        msg=BytesParser(policy=policy.default).parsebytes(path.read_bytes())
        body=msg.get_body(preferencelist=('plain',)).get_content().strip()
        panels=[]
        for m,(name,_) in MODES.items():
            r=records[m][f];trace=r.get('trace') or {}
            verdict=next(x for x in scores[m]['rows'] if x['file']==f)
            lines=''.join(f"<li>{esc(l['sku'])} × {esc(l['quantity'])}</li>" for l in r['lines'])
            checks=''.join(f"<li>{esc(k)}: {v:.3f}</li>" for k,v in trace.get('kev_checks',{}).items())
            head='Draft quotation' if r['has_draft'] else 'Sent to review'
            panels.append(f"""<article data-mode="{m}"><h3>{esc(name)}</h3>
<div class="route">{esc(' → '.join(trace.get('path',[])))}</div>
<h2>{head}</h2><ul>{lines}</ul><p>{esc(r['review_reason'] or '')}</p>
<p class="{'ok' if verdict['right_action'] else 'err'}">{'Matches' if verdict['right_action'] else 'Does not match'} expected action / lines</p>
<dl><dt>Expected workflow</dt><dd>{esc(gold[f]['expected_status'])}</dd>
<dt>Odoo email record</dt><dd>{r['request_id']}</dd><dt>Quotation record</dt><dd>{r['quotation_id'] or '—'}</dd>
<dt>Recorded model processing</dt><dd>{r['seconds']:.2f} s</dd></dl>
{('<h4>Kev error estimates</h4><ul>'+checks+'</ul>') if checks else ''}
<p class="muted">Whole regression round: {scores[m]['correct_actions']}/{scores[m]['total']} correct actions.</p></article>""")
        blocks.append(f"""<section data-case="{n}"><div><div class="muted">Synthetic fixture {n} · original email</div>
<h2>{esc(msg['Subject'])}</h2><pre>{esc(body)}</pre></div><div>{''.join(panels)}</div></section>""")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Group 55 · Email order replay</title><style>
*{box-sizing:border-box}body{font:16px/1.55 system-ui,sans-serif;margin:auto;padding:32px;max-width:1060px;background:#f5f7fa;color:#213343}h1,h2,h3{line-height:1.2}h2{font-size:22px}.route{color:#13585b;font-weight:650}.muted,dt{color:#536879}header,nav,section>div{background:white;padding:22px;border-radius:10px}nav{margin:14px 0;display:flex;gap:18px;flex-wrap:wrap}label{display:grid;gap:4px}section{display:grid;grid-template-columns:1fr 1fr;gap:14px}pre{white-space:pre-wrap;font:inherit}select,button{font:inherit;padding:6px}dl{display:grid;grid-template-columns:1.4fr 1fr}dd{margin:0}.ok,.err{font-weight:bold}.ok{color:#21624e}.err{color:#943620}[hidden]{display:none!important}@media(max-width:680px){body{padding:12px}section{grid-template-columns:1fr}}@media print{body{background:white;padding:0}button{display:none}}</style>
<header><span class="muted">Group 55 · Odoo decision replay · offline</span><h1>What happened to the order?</h1>
<p>Switch between recorded runs on the same email. No new model calls or database writes occur. The Kev demonstration uses 0.50, not the frozen evaluation threshold.</p></header>
<nav><label>Email<select id="email">'''+''.join(f'<option value="{k}">{k} · {v}</option>' for k,v in CASES.items())+
'''</select></label><label>Processing strategy<select id="mode">'''+''.join(f'<option value="{k}" {"selected" if k=="kev" else ""}>{esc(v[0])}</option>' for k,v in MODES.items())+
'''</select></label><button type="button" onclick="window.print()">Print current report</button></nav><main>'''+''.join(blocks)+'''</main>
<script>function choose(){document.querySelectorAll('[data-case]').forEach(e=>e.hidden=e.dataset.case!==document.querySelector('#email').value);document.querySelectorAll('[data-mode]').forEach(e=>e.hidden=e.dataset.mode!==document.querySelector('#mode').value)}document.querySelectorAll('select').forEach(e=>e.onchange=choose);choose()</script></html>''',encoding='utf8')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('output',type=Path);a=p.parse_args();build(a.folder,a.output)
