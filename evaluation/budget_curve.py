"""Finite-batch escalation ranking at equal strong-call budgets.

Complement, not replacement, for the deployed frozen-threshold results.
Scores only order examples. Quality labels never break score ties: at the
boundary report expected results under uniform sampling within a tied group.
No individual fractional call is presented as an observed deployment.
"""
import csv
import json
import sys
from itertools import groupby
from pathlib import Path
from replay_policies import evaluate, linked


def curve(cases, pools):
    small={r['id']:r for r in evaluate(cases,pools,'small',0)['rows']}
    big={r['id']:r for r in evaluate(cases,pools,'strong',0)['rows']}
    for mode in ('random','confidence','kev'):
        def priority(i):
            if mode=='random':
                return 0
            if mode=='confidence':
                return 1-pools[0][i]['candidate']['confidence']
            return max(pools[2][i]['checks'].values())
        order=sorted(small,key=priority,reverse=True)
        def bad(row):
            return int(row['draft'] and not row['right'])
        total=[sum(r['right'] for r in small.values()),sum(map(bad,small.values())),0.0]
        n=len(order); used=0
        def record(k, v):
            return dict(policy=mode,n=n,strong_calls=k,expected_correct_actions=v[0],
                        expected_wrong_drafts=v[1],estimated_api_usd=v[2])
        yield record(0,total)
        for _, group in groupby(order,key=priority):
            ids=list(group)
            diff=[sum(big[i]['right']-small[i]['right'] for i in ids),
                  sum(bad(big[i])-bad(small[i]) for i in ids),
                  sum(big[i]['api_usd'] for i in ids)]
            for k in range(1,len(ids)+1):
                yield record(used+k,[v+d*k/len(ids) for v,d in zip(total,diff)])
            total=[v+d for v,d in zip(total,diff)];used+=len(ids)


if __name__=='__main__':
    folder,split=Path(sys.argv[1]),sys.argv[2]
    if split not in ('calibration','test','stress'): raise ValueError(split)
    if split!='calibration' and not (folder/'frozen-policies.json').is_file():
        raise ValueError('Freeze before held-out evaluation')
    src='stress-manifest.json' if split=='stress' else 'manifest.json'
    cases=[c for c in json.loads((folder/src).read_text()) if c['split']==split]
    pools=[linked(folder/f'{split}-{m}.jsonl',cases) for m in ('small','strong','kev')]
    rows=list(curve(cases,pools))
    with (folder/f'{split}-budget-curve.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
