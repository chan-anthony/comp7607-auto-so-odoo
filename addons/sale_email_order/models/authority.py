"""Current-sender authority checks. Actions: local_review, verified_draft, assess.
Only the current sender can authorize a new dispatch; a forwarded SKU alone cannot.
"""
import re
from .hybrid_rules import predict
from .hybrid_gate import review_reason

MARK=re.compile(r'(?im)^\s*(?:>+|from:\s|on .{3,120} wrote:|[- ]*(?:original|forwarded) message[- ]*)')
ASK=re.compile(r"\b(?:quot(?:e|ation)|pricing|how much|cost estimate|unit price|would .*cost|how (?:soon|long)|before (?:purchas|order)|not authori[sz]ed|subject to|only if|hypothetical|might need|not an order|please (?:hold|wait)|on hold|can you (?:confirm|check|see|find)|can you (?:tell|advise)|copy of|what(?:'s| is)|has .*arrived|when (?:is|will|did)|did .*sign|return label|already (?:paid|shipped)|for your records|no longer (?:need|require)|do not (?:ship|send)|don't (?:ship|send))\b",re.I)
BUY=re.compile(r"\b(?:please (?:send|ship|supply|release|dispatch|deliver|book|place)|(?:send|ship|supply|dispatch|release|order|deliver)\s+(?:us\s+)?\d+|we(?:'d like to| would like to| intend to| wish to) order|we(?:'re| are) (?:placing|ordering)|go ahead (?:with|and)|put .* on the van|we(?:'ll| will) take|draw down|call off|make it \d+|replenish us)\b",re.I)
CONDITION=re.compile(r'\b(?:only if|subject to|provided that|unless|if you can|if the|wait (?:for|until)|before (?:dispatch|releas)|do not release|not yet approved)\b',re.I)
def scope(text):
    m=MARK.search(text);return (text[:m.start()] if m else text).strip(),bool(m)
def triage(text,catalogue,local_lines,small_draft):
    if reason:=review_reason(text):return 'local_review',reason
    current,quoted=scope(text);ask=bool(ASK.search(current));buy=bool(BUY.search(current))
    if CONDITION.search(current) or re.search(r'(?:^|[.!?]\s+)if\s',current,re.I):return 'local_review','Conditional authority; no unconditional dispatch'
    if not buy and (ask or (quoted and '?' in current)):return 'local_review','Current sender requests information, not dispatch'
    if buy and not ask:
        action,lines=predict(current,catalogue)
        if small_draft and action=='draft' and sorted(map(tuple,local_lines))==lines:
            return 'verified_draft','Current dispatch instruction and catalogue lines agree'
    return 'assess','Unresolved authorization or unmatched lines'

