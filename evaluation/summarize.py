"""Generate checkable tables from a completed, frozen policy replay."""
import csv
import json
import sys
from pathlib import Path


def summarize(path):
    data=json.loads(path.read_text(encoding="utf8"))
    maps={m:{row["id"]:row for row in result["rows"]} for m,result in data.items()}
    ids=set(maps["small"])
    if not ids or any(set(v)!=ids for v in maps.values()):
        raise ValueError("Paired evaluation requires identical cases for all policies")
    table=[]
    for mode,rows in maps.items():
        families=sorted({r["family"] for r in rows.values()})
        for family in [None,*families]:
            subset=[r for r in rows.values() if family is None or r["family"]==family]
            big=sum(r["strong"] for r in subset)
            rescued=sum(r["strong"] and not maps["small"][r["id"]]["right"] and
                        maps["strong"][r["id"]]["right"] for r in subset)
            harmed=sum(r["strong"] and maps["small"][r["id"]]["right"] and
                       not maps["strong"][r["id"]]["right"] for r in subset)
            table.append(dict(mode=mode,family=family or "ALL",n=len(subset),
                              correct_actions=sum(r["right"] for r in subset),
                              drafts=sum(r["draft"] for r in subset),
                              wrong_drafts=sum(r["draft"] and not r["right"] for r in subset),
                              strong_calls=big,rescued_by_upgrade=rescued,harmed_by_upgrade=harmed,
                              unchanged_on_upgrade=big-rescued-harmed,
                              strong_tokens=sum(r["strong_tokens"] for r in subset)))
    out=path.with_suffix(".csv")
    with out.open("w",newline="",encoding="utf8") as f:
        writer=csv.DictWriter(f,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
    return out


if __name__=="__main__":
    print(summarize(Path(sys.argv[1])))
