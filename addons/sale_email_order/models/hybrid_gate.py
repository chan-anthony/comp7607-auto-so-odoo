"""Deployment-side feature calculation. Never accepts gold, Strong or family."""
import math
import re
from .hybrid_rules import predict

NAMES = ('kev_category','kev_product','kev_quantity','intent_agree','sku_agree',
         'amount_agree','quoted','product_mentions','length','field_mean','field_min')
RISK=re.compile(r'\b(?:quot(?:e|ation)|pric(?:e|ing)|cancel\w*|withdraw\w*|track\w*|status|already shipped|when .*arriv\w*|where .*order)\b',re.I)

def signal(text,candidate,lines,catalogue,known_sender,field_scores,checks):
    action,rule_lines=predict(text,catalogue)
    draft=bool(candidate['category']=='standard' and candidate['confidence']>=.8 and
               known_sender and lines and all(x[0] for x in lines))
    a=sorted((str(k),float(v)) for k,v in lines)
    b=sorted((str(k),float(v)) for k,v in rule_lines)
    agree=(draft==(action=='draft'),sorted(k for k,v in a)==sorted(k for k,v in b),a==b)
    quoted=bool(re.search(r'(?im)^\s*(?:>|from:)',text))
    mentions=sum(any(re.search(r'(?<!\w)'+re.escape(str(s))+r'(?!\w)',text,re.I) for s in entry[:2]) for entry in catalogue)
    if not field_scores or 'category' not in field_scores:
        raise ValueError('Missing measured category token probabilities')
    n=sum(x['tokens'] for x in field_scores.values())
    mean=sum(x['tokens']*x['mean'] for x in field_scores.values())/n
    worst=min(x['min'] for x in field_scores.values())
    features=[checks[k] for k in ('category','product','quantity')]+list(map(float,agree))+[float(quoted),mentions,math.log1p(len(text)),mean,worst]
    return features, sum(not x for x in agree)+int(bool(RISK.search(text)))+int(text.count('>')>2)

def prob(features,model):
    z=model['intercept']+sum(w*(x-m)/s for w,x,m,s in zip(model['coef'],features,model['mean'],model['scale'],strict=True))
    return 1/(1+math.exp(-max(-60,min(60,z))))

def review_reason(text):
    """Local abstention on instructions impersonating system controls or pure tracking requests."""
    if re.search(r'(?i)\b(?:ignore|override|disregard)\s+(?:all\s+)?(?:previous|system|prior)\s+instructions\b', text):
        return 'Message attempts to supply system instructions'
    historical=re.search(r'(?i)\b(?:we ordered|our previous order|already shipped|existing shipment|order\s+#?\w*\d+)',text)
    tracking=re.search(r"(?i)\b(?:tracking|delivery status|when\b[^.?!\n]{0,80}\b(?:deliver\w*|arriv\w*)|where\b[^.?!\n]{0,60}\b(?:order|shipment))",text)
    fresh=re.search(r'(?i)\b(?:please (?:send|ship|supply)|new order|add another|also send|release another)\b',text)
    return 'Tracking an existing order; no new dispatch instruction' if historical and tracking and not fresh else None
