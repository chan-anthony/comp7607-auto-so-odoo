"""Local non-order disposition only. Input is the whole message, not an extracted keyword."""
import re
REF=re.compile(r'(?<![\w-])CASE-([1-9]\d*)(?![\w-])',re.I)
# A question, an instruction, a change, or an unrecognized extra sentence always
# remains in human work. Only full, no-action speech acts may leave that queue.
ATOM=[
 r'(?:for (?:your )?(?:records|information)(?: only)?|fyi|no (?:reply|response|action|follow[- ]?up)(?: is)? (?:needed|required|requested)|nothing (?:further )?(?:needed|required) from you|no need to (?:reply|respond)|for reference only)',
 r'(?:thanks|thank you)(?: for (?:the update|your help|the confirmation|letting us know))?',
 r'(?:we (?:have )?(?:received|filed|recorded)|our team (?:has )?(?:received|filed|recorded)) (?:your |the )?(?:update|notice|confirmation|copy|delivery note|paperwork|documents?)',
 r'(?:the |our )?(?:duplicate )?(?:copy|paperwork|notice|confirmation|record) (?:has been |is )(?:filed|received|recorded)',
 r'(?:this is )?(?:a )?(?:duplicate copy|courtesy copy|receipt acknowledgement|receipt acknowledgment)(?: for (?:your |our )?records)?',
 r'both [1-9]\d* [\w-]+(?: [\w-]+){0,5} and [1-9]\d* [\w-]+(?: [\w-]+){0,5} are illustrative quantities for the redline, not a call for stock',
]
FULL=re.compile('(?:'+'|'.join(ATOM)+')',re.I)
HARD=re.compile(r"\b(?:except|but|unless|before|please|confirm that|check|sign|need you|await|pending|hold|cancel|stop|change|incorrect|wrong|missing|damaged|dispute|overdue|if|refund|outstanding|not received|not filed|not recorded)\b",re.I)
def decide(body,known,lookup,subject=''):
    refs=set(int(x) for x in REF.findall(subject+' '+body));case=None
    if known and len(refs)==1:case=lookup(next(iter(refs)))
    content=REF.sub('',body).strip(' :#-')
    # A non-routine subject can impose a task even when the body only says thanks.
    subj=REF.sub('',subject).strip(' :#-')
    benign_subject=(not subj or re.fullmatch(r'(?:re:\s*)*(?:operations correspondence|procurement correspondence|correspondence with purchasing|purchasing desk|for your records|receipt|courtesy copy|case update|acknowledg[e]?ment|fyi|update)',subj,re.I))
    parts=[v.strip(' :,-') for v in re.split(r'[.!;\n]+|\s+[—–]\s+|,\s*(?=no (?:reply|response|action))',content) if v.strip(' :,-')]
    safe=bool(known and benign_subject and parts and '?' not in body and not HARD.search(content) and all(FULL.fullmatch(v) for v in parts))
    if refs and not case:safe=False
    if case:return ('linked_no_action' if safe else 'linked_human'),case
    return ('archived' if safe else 'human'),None

def draft_followup(body,subject=''):
    return bool(re.search(r'\?|\b(?:let (?:me|us) know|please (?:confirm|advise|explain|check|sign|return|forward|email|investigate)|tell (?:me|us)|awaiting your|reply|send (?:me|us) (?:the|a) (?:receipt|certificate|copy))\b',subject+' '+body,re.I))
