"""Resolve asserted dispatch clauses before validating their SKU/quantity pairs."""
import re
from .authority import scope, ASK, CONDITION
# Require a directive in a root clause, not a verb anywhere in reported speech.
ROOT=re.compile(r"^(?:(?:hi|hello|thanks|team)[ ,:!-]+)?(?:please\s+|kindly\s+)?(?:ship|dispatch|supply|deliver|send|order|release|book|purchase)\b|^we (?:hereby (?:order|release)|are ordering|would like to order)\b",re.I)
ATTR=re.compile(r"\b(?:incorrectly|mistakenly|in error|was wrong|not accurate|misquot\w*|misprint|misread|typo|erroneous\w*|example|illustrat\w*|hypothetical|specimen|simulation|training|test data|draft wording|someone (?:said|wrote)|(?:minutes|memo|record|document|copy|transcript|form|note|label|screen|printout) (?:says?|said|reads?|lists?|shows?|suggests?)|acknowledge the correction|not (?:the lines|a request|an instruction)|do not (?:act|fulfil|process)|do not (?:send|ship)|cancel\w*|withdraw\w*|not authori[sz]ed)\b",re.I)
NEG=re.compile(r"\b(?:hold|wait|until|unless|provided|would you|could you|before|if|whether|instead of|rather than|except|omit|exclude|not|without|either| or |cancel|discount|negotiated|split|different addresses)\b",re.I)
def resolve(text,catalogue,known):
 current,_=scope(text)
 if not known:return None
 clauses=[s.strip() for s in re.split(r'[.!?;\n]+',current) if s.strip()]
 excluded=[s for s in clauses if ATTR.search(s)]
 directs=[s for s in clauses if ROOT.search(s) and not ATTR.search(s)]
 # A later withdrawal/condition can revoke an earlier directive; no fast draft.
 if excluded and not directs:return ('review',[],'Reported or withdrawn wording is not a current dispatch')
 if not directs or '?' in current or CONDITION.search(current):return None
 if any(NEG.search(s) for s in clauses if s not in excluded):return None
 if excluded and any(clauses.index(s)>clauses.index(directs[-1]) for s in excluded):return None
 # Never apply the positive override if another clause contributes an unresolved item.
 other=' '.join(s for s in clauses if s not in directs and s not in excluded)
 if re.search(r'\b(?:add|also|another|plus|balance|rest|remaining|instead|change|make it|only|pending)\b|\d',other,re.I):return None
 all_lines={}
 for clause in directs:
  found=0; covered=set()
  for sku,name,*_ in catalogue:
   tok=r'(?<![\w-])(?:'+re.escape(sku)+'|'+re.escape(name)+r')(?![\w-])'
   if re.search(tok,other,re.I):return None
   occurrences=list(re.finditer(tok,clause,re.I))
   if not occurrences:continue
   if len(occurrences)!=1 or sku in all_lines:return None
   # The ordered number must attach directly to this catalogue term.
   matches=list(re.finditer(r'(?<![\w.-])([1-9]\d*)\s*(?:[x×]\s*|units?\s+of\s+|of\s+)?'+tok,clause,re.I))
   if len(matches)!=1:return None
   item=matches[0];all_lines[sku]=int(item[1]);found+=1;covered.update(range(item.start(),item.end()))
  if not found:return None
  residue=''.join(' ' if i in covered else ch for i,ch in enumerate(clause))
  residue=ROOT.sub('',residue).strip()
  # Closed grammar, reject unparsed free text, unknown products, units, or prices.
  if not re.fullmatch(r'(?:[\s,:&/+-]|\band\b|\bplus\b|\btogether\b|\bplease\b)*',residue,re.I):return None
 return ('draft',sorted(all_lines.items()),'Root dispatch with fully consumed catalogue lines')
