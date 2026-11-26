"""Each local quotation line must cite a current clause and bound quantity.
No inherited verified_draft or candidate-agreement path.
"""
import re
from .authority import scope
from .hybrid_gate import review_reason
VERB=r'(?:send|ship|dispatch|deliver|release|supply|order|purchase|book|allocate|issue|provide|pack|despatch|replenish)'
ROOT=re.compile(r'^(?:(?:for (?:this|our|today.s|the new) [^,;]{1,35}|today|now|separately|instead|this time|in the meantime|for today)[,: ]+)?(?:(?:please|kindly|also)\s+)*(?:'+VERB+r'\b|we (?:are ordering|order|hereby order|would like to order|require|need)\b|(?:our |the )?(?:new |current |additional )?(?:order|request|release) (?:is (?:for )?|for )|(?:can|could|would) you (?:please )?(?:ship|supply|send|dispatch)\b)',re.I)
PAST=re.compile(r'\b(?:last (?:week|month|shift)|previous|already|earlier|historical|yesterday|receipt|duplicate|invoice copy|status|tracking|what|when|whether|how much|pricing|quote|quotation|unit price|estimate|example|sample text|proof|printout|found|artwork|transcript|incorrectly|reported|reads?|mentioned|showed|said|says?|wrote|suggested|proposed|photograph|display|personal purchase|tentative)\b',re.I)
STOP=re.compile(r"\b(?:if|unless|subject to|pending|hold|wait|not yet|only after|discount|split delivery|provided that)\b",re.I)
CANCEL=re.compile(r"\b(?:cancel|withdraw|void|disregard|omit|exclude|leave out|do not (?:ship|send)|don't (?:ship|send))\b",re.I)
def line_gate(text,cat,known):
    if not known:return 'review',[],[]
    cur,_=scope(text);cat=list(cat);evidence={};excluded=[];uncertain=False
    if review_reason(cur) and 'system' in review_reason(cur).lower():return 'review',[],[]
    # Quoted snippets are never affirmative evidence in a containing sentence.
    segments=re.split(r'[.!?;\n]+|\s+[—–]\s+|,\s*(?:but|instead)\s+|\s+but\s+|,\s*(?=(?:please|kindly|ship|send|dispatch|supply|release)\b)',cur,flags=re.I)
    for raw in segments:
        t=raw.strip(' ,:'); 
        if not t:continue
        scrub=re.sub(r'“[^”]*”|"[^"]*"',' ',t)
        hits=[]
        for sku,name,*_ in cat:
            tok=r'(?<![\w-])(?:'+re.escape(sku)+'|'+re.escape(name)+r')(?![\w-])'
            for h in re.finditer(tok,scrub,re.I):
                before=scrub[:h.start()];after=scrub[h.end():]
                qty=re.search(r'(?<![\w./-])([1-9]\d*)\s*(?:[x×]\s*|(?:units?|pieces?)\s+of\s+|of\s+)?$',before,re.I) or re.match(r'\s*(?:[×x:|]|[-,]?\s*qty\.?\s*[:=]?)\s*([1-9]\d*)(?![\w./-])',after,re.I)
                hits.append((sku,int(qty[1]) if qty else None))
        if CANCEL.search(scrub) and not PAST.search(scrub):
            if hits:
                for k,_ in hits:evidence.pop(k,None)
            else:evidence.clear()
            excluded.append(t);continue
        root=ROOT.search(scrub)
        if root and not STOP.search(scrub) and not PAST.search(scrub):
            if not hits or any(q is None for _,q in hits):uncertain=True;continue
            if re.search(r'\b(?:or|except|rather than|not|remaining|rest)\b',scrub,re.I):uncertain=True;continue
            for k,q in hits:
                if k in evidence and evidence[k][0]!=q:uncertain=True
                evidence[k]=(q,t)
        elif hits:
            if PAST.search(scrub) or STOP.search(scrub) or CANCEL.search(scrub):excluded.append(t)
            else:uncertain=True
        elif STOP.search(scrub) and evidence:uncertain=True
    proofs=[dict(sku=k,quantity=q,clause=t) for k,(q,t) in evidence.items()]
    if uncertain:return 'assess',[],proofs
    if proofs:return 'draft',sorted((v['sku'],v['quantity']) for v in proofs),proofs
    if excluded or '?' in cur or review_reason(cur):return 'review',[],[]
    return 'assess',[],[]
