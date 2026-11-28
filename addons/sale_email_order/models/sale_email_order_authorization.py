import json
import math
import re

from odoo import api, models, tools
from odoo.tools import file_open

# Start of the quoted, forwarded or replied-to history: only the text above it is the current sender's turn.
QUOTED = re.compile(r'(?im)^\s*(?:>+|from:\s|on .{3,120} wrote:|[- ]*(?:original|forwarded) message[- ]*)')
NOT_STANDARD = re.compile(r"\b(quot(?:e|ation)|rfq|how much|what.*cost|price for|pricing"
                          r"|discount|negotiat\w*|last year|ship.*rest|split delivery)\b", re.I)
INJECTION = re.compile(r'(?i)\b(?:ignore|override|disregard)\s+(?:all\s+)?(?:previous|system|prior)\s+instructions\b')
HISTORICAL = re.compile(r'(?i)\b(?:we ordered|our previous order|already shipped|existing shipment|order\s+#?\w*\d+)')
TRACKING = re.compile(r"(?i)\b(?:tracking|delivery status|when\b[^.?!\n]{0,80}\b(?:deliver\w*|arriv\w*)"
                      r"|where\b[^.?!\n]{0,60}\b(?:order|shipment))")
FRESH = re.compile(r'(?i)\b(?:please (?:send|ship|supply)|new order|add another|also send|release another)\b')
RISK = re.compile(r'\b(?:quot(?:e|ation)|pric(?:e|ing)|cancel\w*|withdraw\w*|track\w*|status|already shipped'
                  r'|when .*arriv\w*|where .*order)\b', re.I)
FIELD_VALUE = re.compile(r'"(category|product|quantity)"\s*:\s*("(?:\\.|[^"\\])*"|-?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)')

# Current-sender authority (strategies 'authority_*').
ASK = re.compile(r"\b(?:quot(?:e|ation)|pricing|how much|cost estimate|unit price|would .*cost|how (?:soon|long)"
                 r"|before (?:purchas|order)|not authori[sz]ed|subject to|only if|hypothetical|might need|not an order"
                 r"|please (?:hold|wait)|on hold|can you (?:confirm|check|see|find)|can you (?:tell|advise)|copy of"
                 r"|what(?:'s| is)|has .*arrived|when (?:is|will|did)|did .*sign|return label|already (?:paid|shipped)"
                 r"|for your records|no longer (?:need|require)|do not (?:ship|send)|don't (?:ship|send))\b", re.I)
BUY = re.compile(r"\b(?:please (?:send|ship|supply|release|dispatch|deliver|book|place)|(?:send|ship|supply|dispatch"
                 r"|release|order|deliver)\s+(?:us\s+)?\d+|we(?:'d like to| would like to| intend to| wish to) order"
                 r"|we(?:'re| are) (?:placing|ordering)|go ahead (?:with|and)|put .* on the van|we(?:'ll| will) take"
                 r"|draw down|call off|make it \d+|replenish us)\b", re.I)
CONDITION = re.compile(r'\b(?:only if|subject to|provided that|unless|if you can|if the|wait (?:for|until)'
                       r'|before (?:dispatch|releas)|do not release|not yet approved)\b', re.I)

# Scoped authorization: a directive in a root clause, not a verb anywhere in reported speech.
SCOPE_ROOT = re.compile(r"^(?:(?:hi|hello|thanks|team)[ ,:!-]+)?(?:please\s+|kindly\s+)?(?:ship|dispatch|supply"
                        r"|deliver|send|order|release|book|purchase)\b|^we (?:hereby (?:order|release)|are ordering"
                        r"|would like to order)\b", re.I)
ATTR = re.compile(r"\b(?:incorrectly|mistakenly|in error|was wrong|not accurate|misquot\w*|misprint|misread|typo"
                  r"|erroneous\w*|example|illustrat\w*|hypothetical|specimen|simulation|training|test data"
                  r"|draft wording|someone (?:said|wrote)|(?:minutes|memo|record|document|copy|transcript|form|note"
                  r"|label|screen|printout) (?:says?|said|reads?|lists?|shows?|suggests?)|acknowledge the correction"
                  r"|not (?:the lines|a request|an instruction)|do not (?:act|fulfil|process)|do not (?:send|ship)"
                  r"|cancel\w*|withdraw\w*|not authori[sz]ed)\b", re.I)
NEG = re.compile(r"\b(?:hold|wait|until|unless|provided|would you|could you|before|if|whether|instead of|rather than"
                 r"|except|omit|exclude|not|without|either| or |cancel|discount|negotiated|split"
                 r"|different addresses)\b", re.I)
OPEN_ITEM = re.compile(r'\b(?:add|also|another|plus|balance|rest|remaining|instead|change|make it|only|pending)\b|\d',
                       re.I)
FILLER = re.compile(r'(?:[\s,:&/+-]|\band\b|\bplus\b|\btogether\b|\bplease\b)*', re.I)

# Per-line authorization (Stage 1): each line must cite a current clause and a bound quantity.
VERB = r'(?:send|ship|dispatch|deliver|release|supply|order|purchase|book|allocate|issue|provide|pack|despatch|replenish)'
LINE_ROOT = re.compile(r'^(?:(?:for (?:this|our|today.s|the new) [^,;]{1,35}|today|now|separately|instead|this time'
                       r'|in the meantime|for today)[,: ]+)?(?:(?:please|kindly|also)\s+)*(?:' + VERB + r'\b|we (?:are '
                       r'ordering|order|hereby order|would like to order|require|need)\b|(?:our |the )?(?:new |current '
                       r'|additional )?(?:order|request|release) (?:is (?:for )?|for )|(?:can|could|would) you '
                       r'(?:please )?(?:ship|supply|send|dispatch)\b)', re.I)
PAST = re.compile(r'\b(?:last (?:week|month|shift)|previous|already|earlier|historical|yesterday|receipt|duplicate'
                  r'|invoice copy|status|tracking|what|when|whether|how much|pricing|quote|quotation|unit price'
                  r'|estimate|example|sample text|proof|printout|found|artwork|transcript|incorrectly|reported|reads?'
                  r'|mentioned|showed|said|says?|wrote|suggested|proposed|photograph|display|personal purchase'
                  r'|tentative)\b', re.I)
STOP = re.compile(r"\b(?:if|unless|subject to|pending|hold|wait|not yet|only after|discount|split delivery"
                  r"|provided that)\b", re.I)
CANCEL = re.compile(r"\b(?:cancel|withdraw|void|disregard|omit|exclude|leave out|do not (?:ship|send)"
                    r"|don't (?:ship|send))\b", re.I)
SEGMENT = re.compile(r'[.!?;\n]+|\s+[—–]\s+|,\s*(?:but|instead)\s+|\s+but\s+'
                     r'|,\s*(?=(?:please|kindly|ship|send|dispatch|supply|release)\b)', re.I)
QTY_BEFORE = re.compile(r'(?<![\w./-])([1-9]\d*)\s*(?:[x×]\s*|(?:units?|pieces?)\s+of\s+|of\s+)?$', re.I)
QTY_AFTER = re.compile(r'\s*(?:[×x:|]|[-,]?\s*qty\.?\s*[:=]?)\s*([1-9]\d*)(?![\w./-])', re.I)
UNSURE = re.compile(r'\b(?:or|except|rather than|not|remaining|rest)\b', re.I)


class SaleEmailOrderAuthorization(models.AbstractModel):
    """Stage 1 text rules: which lines the current sender authorized, and how risky the small-model answer is."""
    _name = 'sale.email.order.authorization'
    _description = "Email Order Line Authorization Rules"

    # ------------------------------------------------------------
    # Current-sender authorization (no gold fields, test IDs or template names are inputs)
    # ------------------------------------------------------------

    @api.model
    def _clip_thread(self, text):
        """Return the current sender's turn and whether quoted or forwarded history follows it."""
        mark = QUOTED.search(text)
        return (text[:mark.start()] if mark else text).strip(), bool(mark)

    @api.model
    def _catalogue_term(self, sku, name):
        """Pattern matching the reference or the name of a catalogue product as a whole term."""
        return rf"(?<![\w-])(?:{re.escape(sku)}|{re.escape(name)})(?![\w-])"

    @api.model
    def _review_reason(self, text):
        """Local abstention on instructions impersonating system controls or pure tracking requests."""
        if INJECTION.search(text):
            return 'Message attempts to supply system instructions'
        if HISTORICAL.search(text) and TRACKING.search(text) and not FRESH.search(text):
            return 'Tracking an existing order; no new dispatch instruction'
        return None

    @api.model
    def _predict_lines(self, text, catalogue):
        """No-model baseline: a known product with an adjacent quantity, else review."""
        if NOT_STANDARD.search(text):
            return 'review', []
        found = []
        for sku, name, *_ in catalogue:
            term = self._catalogue_term(sku, name)
            if not re.search(term, text, re.I):
                continue
            match = (re.search(rf"\b(\d+)\s*(?:x\s*|units? of\s+)?{term}", text, re.I)
                     or re.search(rf"{term}\s*(?:x|[-:]|quantity[: ]*)\s*(\d+)\b", text, re.I))
            if not match or int(match[1]) <= 0:
                return 'review', []
            found.append((sku, int(match[1])))
        return ('draft', sorted(found)) if found else ('review', [])

    @api.model
    def _triage_authority(self, text, catalogue, local_lines, small_draft):
        """Only the current sender can authorize a dispatch: local_review, verified_draft or assess."""
        if reason := self._review_reason(text):
            return 'local_review', reason
        current, quoted = self._clip_thread(text)
        ask, buy = bool(ASK.search(current)), bool(BUY.search(current))
        if CONDITION.search(current) or re.search(r'(?:^|[.!?]\s+)if\s', current, re.I):
            return 'local_review', 'Conditional authority; no unconditional dispatch'
        if not buy and (ask or (quoted and '?' in current)):
            return 'local_review', 'Current sender requests information, not dispatch'
        if buy and not ask:
            action, lines = self._predict_lines(current, catalogue)
            if small_draft and action == 'draft' and sorted(map(tuple, local_lines)) == lines:
                return 'verified_draft', 'Current dispatch instruction and catalogue lines agree'
        return 'assess', 'Unresolved authorization or unmatched lines'

    @api.model
    def _resolve_scope(self, text, catalogue, known):
        """Return ('draft', lines, why) or ('review', [], why) when the root clauses settle it, else None."""
        current = self._clip_thread(text)[0]
        if not known:
            return None
        clauses = [s.strip() for s in re.split(r'[.!?;\n]+', current) if s.strip()]
        excluded = [s for s in clauses if ATTR.search(s)]
        directs = [s for s in clauses if SCOPE_ROOT.search(s) and not ATTR.search(s)]
        # A later withdrawal/condition can revoke an earlier directive; no fast draft.
        if excluded and not directs:
            return 'review', [], 'Reported or withdrawn wording is not a current dispatch'
        if not directs or '?' in current or CONDITION.search(current):
            return None
        if any(NEG.search(s) for s in clauses if s not in excluded):
            return None
        if excluded and any(clauses.index(s) > clauses.index(directs[-1]) for s in excluded):
            return None
        # Never apply the positive override if another clause contributes an unresolved item.
        other = ' '.join(s for s in clauses if s not in directs and s not in excluded)
        if OPEN_ITEM.search(other):
            return None
        all_lines = {}
        for clause in directs:
            covered = set()
            for sku, name, *_ in catalogue:
                term = self._catalogue_term(sku, name)
                if re.search(term, other, re.I):
                    return None
                occurrences = re.findall(term, clause, re.I)
                if not occurrences:
                    continue
                if len(occurrences) != 1 or sku in all_lines:
                    return None
                # The ordered number must attach directly to this catalogue term.
                matches = list(re.finditer(r'(?<![\w.-])([1-9]\d*)\s*(?:[x×]\s*|units?\s+of\s+|of\s+)?' + term, clause, re.I))
                if len(matches) != 1:
                    return None
                all_lines[sku] = int(matches[0][1])
                covered.update(range(*matches[0].span()))
            if not covered:
                return None
            residue = SCOPE_ROOT.sub('', ''.join(' ' if i in covered else ch for i, ch in enumerate(clause))).strip()
            # Closed grammar, reject unparsed free text, unknown products, units, or prices.
            if not FILLER.fullmatch(residue):
                return None
        return 'draft', sorted(all_lines.items()), 'Root dispatch with fully consumed catalogue lines'

    @api.model
    def _line_gate(self, text, catalogue, known, subject=''):
        """Return (action, lines, evidence): 'draft' with cited lines, 'review', or 'assess' (escalate)."""
        if not known:
            return 'review', [], []
        cur = self._clip_thread(text)[0]
        local_reason = self._review_reason(cur)
        if local_reason and 'system' in local_reason.lower():
            return 'review', [], []
        catalogue, evidence, excluded, uncertain = list(catalogue), {}, [], False
        for raw in SEGMENT.split(cur):
            clause = raw.strip(' ,:')
            if not clause:
                continue
            # Quoted snippets are never affirmative evidence in a containing sentence.
            scrub = re.sub(r'“[^”]*”|"[^"]*"', ' ', clause)
            hits = []
            for sku, name, *_ in catalogue:
                for hit in re.finditer(self._catalogue_term(sku, name), scrub, re.I):
                    qty = QTY_BEFORE.search(scrub[:hit.start()]) or QTY_AFTER.match(scrub[hit.end():])
                    hits.append((sku, int(qty[1]) if qty else None))
            if CANCEL.search(scrub) and not PAST.search(scrub):
                if not hits:
                    evidence.clear()
                for sku, _qty in hits:
                    evidence.pop(sku, None)
                excluded.append(clause)
            elif LINE_ROOT.search(scrub) and not STOP.search(scrub) and not PAST.search(scrub):
                if not hits or any(q is None for _sku, q in hits) or UNSURE.search(scrub):
                    uncertain = True
                    continue
                for sku, qty in hits:
                    uncertain |= sku in evidence and evidence[sku][0] != qty
                    evidence[sku] = (qty, clause)
            elif hits:
                if PAST.search(scrub) or STOP.search(scrub) or CANCEL.search(scrub):
                    excluded.append(clause)
                else:
                    uncertain = True
            elif STOP.search(scrub) and evidence:
                uncertain = True
        proofs = [{'sku': k, 'quantity': q, 'clause': t} for k, (q, t) in evidence.items()]
        # A condition in the subject (e.g. 'split delivery') leaves the body's lines unresolved.
        if uncertain or (proofs and STOP.search(subject)):
            return 'assess', [], proofs
        if proofs:
            return 'draft', sorted((v['sku'], v['quantity']) for v in proofs), proofs
        if excluded or '?' in cur or local_reason:
            return 'review', [], []
        return 'assess', [], []

    # ------------------------------------------------------------
    # Risk score of the small-model answer
    # ------------------------------------------------------------

    @api.model
    @tools.ormcache('name')
    def _risk_policy(self, name):
        """Calibrated risk policy shipped in data/, read once per registry."""
        with file_open(f'sale_email_order/data/{name}') as policy:
            return json.load(policy)

    @api.model
    def _field_logprobs(self, text, tokens):
        """Uncertainty of the emitted category/product/quantity values, never of the confidence field."""
        if not tokens:
            return None
        spans = []
        for match in FIELD_VALUE.finditer(text):
            start, end = match.span(2)
            if text[start] == '"':
                start, end = start + 1, end - 1
            spans.append((match[1], len(text[:start].encode()), len(text[:end].encode())))
        buffer, values = bytearray(), {}
        for token in tokens:
            start = len(buffer)
            buffer.extend(token['bytes'])
            for key, first, last in spans:
                if start < last and len(buffer) > first:
                    values.setdefault(key, []).append(float(token['logprob']))
        if bytes(buffer) != text.encode() or not values or not all(math.isfinite(v) for vs in values.values() for v in vs):
            return None
        return {k: {'mean': sum(v) / len(v), 'min': min(v), 'tokens': len(v)} for k, v in values.items()}

    @api.model
    def _risk_signal(self, text, candidate, lines, catalogue, known_sender, field_scores, checks):
        """Return the risk features of the small-model candidate and its count of disagreement signals."""
        action, rule_lines = self._predict_lines(text, catalogue)
        draft = bool(candidate['category'] == 'standard' and candidate['confidence'] >= .8
                     and known_sender and lines and all(x[0] for x in lines))
        mine = sorted((str(k), float(v)) for k, v in lines)
        rules = sorted((str(k), float(v)) for k, v in rule_lines)
        agree = (draft == (action == 'draft'), [k for k, _ in mine] == [k for k, _ in rules], mine == rules)
        quoted = bool(re.search(r'(?im)^\s*(?:>|from:)', text))
        mentions = sum(any(re.search(r'(?<!\w)' + re.escape(str(s)) + r'(?!\w)', text, re.I) for s in entry[:2])
                       for entry in catalogue)
        if not field_scores or 'category' not in field_scores:
            raise ValueError('Missing measured category token probabilities')
        tokens = sum(x['tokens'] for x in field_scores.values())
        mean = sum(x['tokens'] * x['mean'] for x in field_scores.values()) / tokens
        worst = min(x['min'] for x in field_scores.values())
        features = [checks[k] for k in ('category', 'product', 'quantity')] + list(map(float, agree)) \
            + [float(quoted), mentions, math.log1p(len(text)), mean, worst]
        return features, sum(not x for x in agree) + int(bool(RISK.search(text))) + int(text.count('>') > 2)

    @api.model
    def _risk_probability(self, features, model):
        z = model['intercept'] + sum(w * (x - m) / s for w, x, m, s in
                                     zip(model['coef'], features, model['mean'], model['scale'], strict=True))
        return 1 / (1 + math.exp(-max(-60, min(60, z))))
