"""No-model baseline: classify intent, match a known product and adjacent quantity.
Vocabulary is based on the original regression kit. Missing or ambiguous lines
go to review. No gold fields, test IDs or template names are inputs.
"""
import re


def predict(text, catalogue):
    if re.search(r"\b(quot(?:e|ation)|rfq|how much|what.*cost|price for|pricing)\b", text, re.I):
        return "review", []
    if re.search(r"\b(discount|negotiat\w*|last year|ship.*rest|split delivery)\b", text, re.I):
        return "review", []
    found=[]
    for sku,name,*_ in catalogue:
        token=rf"(?<![\w-])(?:{re.escape(sku)}|{re.escape(name)})(?![\w-])"
        if not re.search(token,text,re.I):
            continue
        match=(re.search(rf"\b(\d+)\s*(?:x\s*|units? of\s+)?{token}",text,re.I)
               or re.search(rf"{token}\s*(?:x|[-:]|quantity[: ]*)\s*(\d+)\b",text,re.I))
        if not match or int(match[1])<=0:
            return "review", []
        found.append((sku,int(match[1])))
    return ("draft", sorted(found)) if found else ("review", [])


def score(cases,catalogue):
    rows=[]
    for c in cases:
        action,lines=predict(c["text"],catalogue)
        ok=action==c["gold_action"] and (action=="review" or lines==sorted(c["gold_draft_lines"].items()))
        rows.append(dict(id=c["id"],family=c["family"],draft=action=="draft",right=ok,
                         strong=False,strong_tokens=0))
    drafts=sum(x["draft"] for x in rows);bad=sum(x["draft"] and not x["right"] for x in rows)
    return dict(n=len(rows),drafts=drafts,wrong_drafts=bad,coverage=drafts/len(rows),
                wrong_given_draft=bad/drafts if drafts else None,strong_calls=0,strong_tokens=0,
                right=sum(x["right"] for x in rows),rows=rows)
