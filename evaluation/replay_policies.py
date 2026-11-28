"""Compare cached model results without changing any order or calling a model.

python replay_policies.py freeze DATA_DIR  # calibration split only
python replay_policies.py score DATA_DIR   # test with saved calibration cutoffs
"""
import argparse
import json
from pathlib import Path
from lexical_baseline import score as score_lexical
from build_cases import source_lists
from api_cost import usd


def linked(path, cases):
    rows = [json.loads(s) for s in path.read_text().splitlines()]
    indexed = {r["id"]: r for r in rows}
    if len(rows) != len(indexed) or set(indexed) != {c["id"] for c in cases}:
        raise ValueError(f"Incomplete or duplicate results in {path}")
    return indexed


def evaluate(cases, pools, mode, cut, accept=0.8):
    out = []
    for c in cases:
        i = c["id"]
        s, b, k = (pool[i] for pool in pools)
        use_big = mode == "strong" or (mode == "confidence" and s["candidate"]["confidence"] < cut) or (
            mode == "kev" and max(k["checks"].values()) >= cut)
        r = b if use_big else s
        pred, lines = r["candidate"], r["mapped_lines"]
        draft = bool(pred["category"] == "standard" and pred["confidence"] >= accept
                     and r["known_sender"] and lines and all(x[0] for x in lines))
        if draft:
            right = c["gold_action"] == "draft" and sorted(map(tuple, lines)) == sorted(c["gold_draft_lines"].items())
        else:
            right = c["gold_action"] == "review"
        out.append(dict(id=i, family=c["family"], draft=draft, right=right, strong=use_big,
                        seconds=(s["seconds"] if mode != "strong" else 0)
                        + (b["seconds"] if use_big else 0) + (k["seconds"] if mode == "kev" else 0),
                        api_usd=usd(b["metadata"]["usage"]) if use_big else 0,
                        strong_tokens=b["metadata"]["usage"]["total_tokens"] if use_big else 0))
    drafts = sum(x["draft"] for x in out)
    bad = sum(x["draft"] and not x["right"] for x in out)
    return dict(n=len(out), right=sum(x["right"] for x in out), drafts=drafts, wrong_drafts=bad,
                wrong_given_draft=bad/drafts if drafts else None, coverage=drafts/len(out),
                strong_calls=sum(x["strong"] for x in out), strong_tokens=sum(x["strong_tokens"] for x in out),
                replay_model_seconds=sum(x["seconds"] for x in out),
                estimated_openai_usd=sum(x["api_usd"] for x in out), rows=out)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("action",choices=["freeze","score","stress"]);p.add_argument("folder",type=Path)
    args=p.parse_args(); folder=args.folder
    split={"freeze":"calibration","score":"test","stress":"stress"}[args.action]
    manifest="stress-manifest.json" if split=="stress" else "manifest.json"
    cases=[c for c in json.loads((folder/manifest).read_text()) if c["split"]==split]
    pools=[linked(folder/f"{split}-{m}.jsonl",cases) for m in ("small","strong","kev")]
    policy_file=folder/"frozen-policies.json"
    if args.action=="freeze":
        # Match the calibration strong-call count of the original 0.8 router.
        # On ties prefer fewer wrong drafts, then more correct outcomes, then
        # fewer calls. No test outcomes are read to choose this point.
        target=evaluate(cases,pools,"confidence",0.8)["strong_calls"]
        cuts=[0, 1.0000001]+[max(r["checks"].values()) for r in pools[2].values()]
        def objective(t):
            r=evaluate(cases,pools,"kev",t)
            return abs(r["strong_calls"]-target),r["wrong_drafts"],-r["right"],r["strong_calls"],t
        selected=min(cuts,key=objective)
        with policy_file.open("x") as f: json.dump({"kev":selected,"confidence":0.8,"accept":0.8},f,indent=2)
    cfg=json.loads(policy_file.read_text())
    result={m:evaluate(cases,pools,m,cfg.get(m,0),cfg["accept"]) for m in ("small","strong","confidence","kev")}
    result["lexical"]=score_lexical(cases,source_lists()["PRODUCTS"])
    (folder/f"{split}-policy-scores.json").write_text(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
