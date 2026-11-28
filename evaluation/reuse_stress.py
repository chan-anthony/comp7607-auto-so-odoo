"""Reuse measured stress outputs only for identical inference inputs, never labels."""
import json,sys,shutil
from pathlib import Path
old,new=map(Path,sys.argv[1:3])
def records(folder,tier):
    a=[json.loads(line) for line in (folder/f'stress-{tier}.jsonl').read_text().splitlines()]
    assert len(a)==len(set(r['id'] for r in a))==880
    return {r['id']:r for r in a}
a,b,k=records(old,'small'),records(new,'small'),records(old,'kev')
assert (old/'stress-manifest.json').read_bytes()==(new/'stress-manifest.json').read_bytes()
assert set(a)==set(b)==set(k)==set(records(old,'strong'))
# The Kev prompt contains category and lines (not confidence/logprob metadata).
match=[i for i in b if all(a[i]['candidate'][key]==b[i]['candidate'][key] for key in ('lines','category'))]
with (new/'stress-kev.jsonl').open('x') as f:
    for i in match:f.write(json.dumps(k[i])+'\n')
shutil.copyfile(old/'stress-strong.jsonl',new/'stress-strong.jsonl')
(new/'stress-cache-reuse.json').write_text(json.dumps(dict(strong=880,kev=len(match),kev_recompute=880-len(match),source=old.name),indent=2))
print(len(match),'exact verifier input matches;',880-len(match),'require inference')
