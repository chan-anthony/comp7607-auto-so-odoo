"""Plot realized risk, external exposure and paired native elapsed time."""
import json,csv,sys,statistics
from math import ceil
from pathlib import Path
from plot_results import plt,save
def build(d,out):
    rows=[]
    for name,mode,rnd in [('Qwen','small','v2sequentialcpu01'),('Raw Kev · CPU','kev','v2sequentialcpu01'),('All cloud','strong','v2sequentialcpu01'),('Hybrid · CPU','authority_30','v2sequentialcpu01'),('Hybrid · GPU','authority_30','v2sequentialgpu01')]:
        stem=mode+'-'+rnd
        def load(s):return json.loads((d/(stem+'-'+s+'.json')).read_text(encoding='utf-8-sig'))
        m=load('manifest')['mail_to_committed_decision_ms'];s=load('scores');raw=load('native')
        assert len(m)==s['total']==len(raw)==20
        xs=sorted(m.values());calls=sum('GPT-6.2 Sol' in r['trace']['path'] for r in raw)
        rows.append(dict(name=name,mean_ms=statistics.mean(xs),p95_ms=xs[ceil(.95*len(xs))-1],calls=calls,cloud=5*calls,accuracy=5*s['correct_actions'],drafts=s['drafts'],wrong=s['wrong_drafts'],wdr=100*s['wrong_drafts']/s['drafts']))
    with (d/'paired-native-operating-points.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    fig,axes=plt.subplots(1,2,figsize=(9,3.9),sharey=True)
    colors=['#8b7655','#7764a8','#38444c','#49a5a1','#006c64']
    for ax,field,lab in zip(axes,['mean_ms','cloud'],['Mean mail-to-commit latency (ms)','Emails sent to cloud (%)']):
        for j,r in enumerate(rows):ax.scatter(r[field],r['wdr'],s=80,color=colors[j],label=r['name'],alpha=.85,marker=['o','s','^','v','D'][j])
        ax.axhline(5,color='#aa4751',linestyle='--',linewidth=1);ax.set_xlabel(lab);ax.set_ylim(bottom=-1)
    axes[0].set_ylabel('Wrong drafts / generated drafts (%)');axes[0].set_title('End-to-end latency');axes[1].set_title('Cloud exposure');fig.legend(*axes[0].get_legend_handles_labels(),loc='lower center',ncol=5,fontsize=9);fig.tight_layout(rect=[0,.09,1,1]);save(fig,out,'fig3-deployment')
if __name__=='__main__':build(*map(Path,sys.argv[1:3]))
