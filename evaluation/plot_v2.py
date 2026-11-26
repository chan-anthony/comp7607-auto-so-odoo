"""Render v2 real native outcomes, fixed-budget comparisons and operating points."""
import argparse,csv,json
from pathlib import Path
from plot_results import plt,save
C={'random':'#828282','verbal':'#c68b33','logprob':'#a8495e','raw':'#7764a8','disagreement':'#47809a','hybrid':'#097d6d'}
def native(v1,v2,out):
    cases=[('Qwen',v1,'small-base01'),('Raw Kev',v1,'kev-defaultdemo01'),('Hybrid',v2,'hybrid_30-v2hybrid30cpu01'),('Hybrid + local review',v2,'hybrid_guard30-guardcpu01'),('Current-sender hybrid',v2,'authority_30-v2sequentialcpu01'),('All cloud',v1,'strong-replay01')]
    fig,axes=plt.subplots(1,2,figsize=(8.6,3.4),gridspec_kw={'width_ratios':[1.6,1]})
    for i,(name,d,prefix) in enumerate(cases):
        s=json.loads((d/f'{prefix}-scores.json').read_text(encoding='utf-8-sig'));rows=json.loads((d/f'{prefix}-native.json').read_text(encoding='utf-8-sig'))
        wrong=s['wrong_drafts'];miss=s['missed_drafts'];good=s['correct_actions'];x=0
        for v,color in [(good,'#117d71'),(wrong,'#bb494e'),(miss,'#d89d45')]:
            axes[0].barh(i,v,left=x,color=color); 
            if v:axes[0].text(x+v/2,i,str(v),ha='center',va='center',color='white',fontsize=9)
            x+=v
        calls=sum('GPT-6.2 Sol' in r['trace']['path'] for r in rows);axes[1].barh(i,calls,color='#42658b');axes[1].text(calls+.25,i,str(calls),va='center')
    axes[0].set_yticks(range(len(cases)),[x[0] for x in cases]);axes[1].set_yticks([]);axes[0].set_title('Correct / wrong draft / missed draft');axes[1].set_title('Emails sent to cloud');axes[1].set_xlim(0,22);axes[0].set_xlim(0,20)
    for ax in axes:ax.invert_yaxis();ax.set_xlabel('Emails (n = 20)')
    fig.tight_layout();save(fig,out,'fig1-native')
def curves(data,out,authority=False):
    fig,ax=plt.subplots(2,2,figsize=(9,6.3),sharex=True,sharey='row')
    for j,(split,title) in enumerate([('test','New challenge · 150' if authority else 'Prospective evaluation · 180'),('stress','Interference panel · 880')]):
        rows=list(csv.DictReader((data/f'{split}-curves.csv').open())); n=int(rows[0]['n'])
        palette=dict(C)
        if authority:
            rows+=list(csv.DictReader((data/f'{split}-authority-curves.csv').open()))
            palette['authority']='#151e35'
        for p,col in palette.items():
            a=[r for r in rows if r['policy']==p];x=[100*float(r['calls'])/n for r in a];w=2.8 if p==('authority' if authority else 'hybrid') else 1.25
            for y,z in enumerate([[100*float(r['correct'])/n for r in a],[100*float(r['wdr']) if r['wdr'] else float('nan') for r in a]]):
                ax[y,j].plot(x,z,label=p,color=col,lw=w);ax[y,j].axvspan(20,40,alpha=.018,color='black')
        ax[0,j].set_title(title);ax[1,j].set_xlabel('Emails sent to cloud (%)');ax[1,j].axhline(5,color='#8b2734',ls='--',lw=1)
    ax[0,0].set_ylabel('Correct actions (%)');ax[1,0].set_ylabel('Wrong drafts / drafts (%)');fig.legend(*ax[0,0].get_legend_handles_labels(),ncol=6,loc='lower center');fig.tight_layout(rect=[0,.055,1,1]);save(fig,out,'fig2-current-sender' if authority else 'fig2-risk-coverage')
if __name__=='__main__':
    import sys
    root=Path(sys.argv[1]);out=root/'deliverables/Group55_V2/figures'
    native(root/'internal/native-replay',root/'internal/localfirst_v2/native',out)
    if (root/'internal/localfirst_v2/stress-curves.csv').exists():curves(root/'internal/localfirst_v2',out)

    if (root/'internal/localfirst_authority/stress-authority-curves.csv').exists():curves(root/'internal/localfirst_authority',out,True)

