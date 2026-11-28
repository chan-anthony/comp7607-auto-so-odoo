"""Score frozen current-sender decisions including local abstention, by family."""
from authority_policy import *
import csv
def export(p,split):
    rows=prepare(p,split);cfg=json.loads((p/'authority-policy.json').read_text())
    allrows=[]
    for fam in ['ALL']+sorted({r[0]['family'] for r in rows}):
        rs=[r for r in rows if fam=='ALL' or r[0]['family']==fam]
        for op,point in cfg['cuts'].items():
            if point is None:continue
            count=stats(rs,cfg['model'],point['threshold']);allrows.append(dict(family=fam,op=op,**count))
    with (p/f'{split}-authority-online.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=allrows[0]);w.writeheader();w.writerows(allrows)
    print(allrows[:len([q for q in cfg['cuts'].values() if q])])
if __name__=='__main__':export(Path(sys.argv[1]),sys.argv[2])
