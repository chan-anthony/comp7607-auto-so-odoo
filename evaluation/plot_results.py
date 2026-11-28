"""Render plots from the saved real records / complete precomputed curves."""
import argparse
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

plt.rcParams.update({"font.size":10,"axes.spines.right":False,"axes.spines.top":False,
                     "svg.fonttype":"none","axes.titlelocation":"left"})
def save(fig,out,name):
    out.mkdir(parents=True,exist_ok=True)
    for ext in ("png","svg"):
        fig.savefig(out/f"{name}.{ext}", dpi=180, bbox_inches="tight",facecolor="white")
    plt.close(fig)


def native_plot(folder,out):
    modes=[("Qwen","small-base01"),("Confidence (0.80)","confidence-defaultdemo01"),
           ("Kev (0.50)","kev-defaultdemo01"),("GPT-6.2 Sol","strong-replay01")]
    labels=[];groups=[];calls=[]
    for label,prefix in modes:
        native=json.loads((folder/(prefix+"-native.json")).read_text(encoding="utf-8-sig"))
        s=json.loads((folder/(prefix+"-scores.json")).read_text(encoding="utf-8-sig"))
        labels.append(label);calls.append(sum("GPT-6.2 Sol" in r["trace"]["path"] for r in native))
        groups.append([s["right_drafts"],s["correct_actions"]-s["right_drafts"],s["wrong_drafts"],s["missed_drafts"]])
        assert sum(groups[-1])==len(native)==20
    fig,(ax,bx)=plt.subplots(1,2,figsize=(9.4,3.3),gridspec_kw={"width_ratios":[2.25,1]},constrained_layout=True)
    left=[0]*4
    for j,(title,color) in enumerate(zip(["Correct draft","Correct review","Wrong draft","Missed draft"],
                                        ["#18776d","#a1d5c4","#c9513b","#efb467"])):
        v=[g[j] for g in groups];ax.barh(range(4),v,left=left,color=color,label=title,height=.64)
        for i,n in enumerate(v):
            if n:ax.text(left[i]+n/2,i,str(n),va="center",ha="center",color="white" if j in (0,2) else "#182e34",fontsize=9)
        left=[x+y for x,y in zip(left,v)]
    ax.set_yticks(range(4),labels);ax.invert_yaxis();ax.set_xlabel("Emails (20 per strategy)");ax.set_xlim(0,20)
    ax.set_title("A   Native Odoo outcomes",weight="bold");ax.legend(loc="upper left",bbox_to_anchor=(-.02,-.28),ncol=2,frameon=False)
    bx.barh(range(4),calls,color="#38577b",height=.52)
    for i,n in enumerate(calls):bx.text(n+.4,i,str(n),va="center")
    bx.set_yticks(range(4),[]);bx.invert_yaxis();bx.set_xlim(0,22.5);bx.set_xlabel("Strong-model calls")
    bx.set_title("B   Escalation cost proxy",weight="bold")
    save(fig,out,"native-regression")


def budget_plot(folder,out):
    splits=[s for s in ("calibration","test","stress") if (folder/f"{s}-budget-curve.csv").is_file()]
    fig,axes=plt.subplots(1,len(splits),figsize=(4.1*len(splits),3.4),squeeze=False,constrained_layout=True)
    for col,split in enumerate(splits):
        ax=axes[0][col]
        with (folder/f"{split}-budget-curve.csv").open() as f: rows=list(csv.DictReader(f))
        curves={}
        for m in ("random","confidence","kev"):
            rr=[r for r in rows if r["policy"]==m];n=int(rr[0]["n"])
            curves[m]=([100*int(r["strong_calls"])/n for r in rr],[100*float(r["expected_correct_actions"])/n for r in rr])
        if curves["random"]==curves["confidence"]==curves["kev"]:
            ax.plot(*curves["random"],color="#38577b",label="All three policies")
        else:
            for m,label,color,ls in [("random","Random","#666666",":"),("confidence","Qwen confidence","#ad501e","--"),("kev","Kev checks","#00776c","-")]:
                ax.plot(*curves[m],color=color,linestyle=ls,lw=2,label=label)
        ax.set_title(f"{split.title()}  ·  n = {n}",weight="bold")
        ax.set_xlim(0,100);ax.set_ylim(0,102);ax.set_xlabel("Emails escalated (%)")
        if not col:ax.set_ylabel("Correct actions (%)")
        ax.yaxis.set_major_locator(MaxNLocator(5));ax.grid(axis="y",alpha=.2);ax.legend(loc="lower right",frameon=False,fontsize=8)
    save(fig,out,"matched-budget-"+"-".join(splits))


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("panel",type=Path);p.add_argument("native",type=Path);p.add_argument("out",type=Path)
    a=p.parse_args();native_plot(a.native,a.out);budget_plot(a.panel,a.out)
