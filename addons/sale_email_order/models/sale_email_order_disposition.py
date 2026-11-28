import re

from odoo import api, models

# Case #42, case–42, CASE:42 and CASE-42 are the same reference; a mutated word such as C4SE-42 is not.
CASE_REF = re.compile(r'(?<![\w-])CASE\s*[-–—:#]+\s*([1-9]\d*)(?![\w-])', re.I)
# A question, an instruction, a change, or an unrecognized extra sentence always
# remains in human work. Only full, no-action speech acts may leave that queue.
NO_ACTION = re.compile('(?:' + '|'.join([
    r'(?:for (?:your )?(?:records|information)(?: only)?|fyi|no (?:reply|response|action|follow[- ]?up)(?: is)? '
    r'(?:needed|required|requested)|nothing (?:further )?(?:needed|required) from you|no need to (?:reply|respond)'
    r'|for reference only)',
    r'(?:thanks|thank you)(?: for (?:the update|your help|the confirmation|letting us know))?',
    r'(?:we (?:have )?(?:received|filed|recorded)|our team (?:has )?(?:received|filed|recorded)) (?:your |the )?'
    r'(?:update|notice|confirmation|copy|delivery note|paperwork|documents?)',
    r'(?:the |our )?(?:duplicate )?(?:copy|paperwork|notice|confirmation|record) (?:has been |is )(?:filed|received|recorded)',
    r'(?:this is )?(?:a )?(?:duplicate copy|courtesy copy|receipt acknowledgement|receipt acknowledgment)'
    r'(?: for (?:your |our )?records)?',
    r'both [1-9]\d* [\w-]+(?: [\w-]+){0,5} and [1-9]\d* [\w-]+(?: [\w-]+){0,5} are illustrative quantities for the '
    r'redline, not a call for stock',
]) + ')', re.I)
HARD = re.compile(r"\b(?:except|but|unless|before|please|confirm that|check|sign|need you|await|pending|hold|cancel"
                  r"|stop|change|incorrect|wrong|missing|damaged|dispute|overdue|if|refund|outstanding|not received"
                  r"|not filed|not recorded)\b", re.I)
BENIGN_SUBJECT = re.compile(r'(?:re:\s*)*(?:operations correspondence|procurement correspondence|correspondence with '
                            r'purchasing|purchasing desk|for your records|receipt|courtesy copy|case update'
                            r'|acknowledg[e]?ment|fyi|update)', re.I)
FOLLOWUP = re.compile(r'\?|\b(?:let (?:me|us) know|please (?:confirm|advise|explain|check|sign|return|forward|email'
                      r'|investigate)|tell (?:me|us)|awaiting your|reply|send (?:me|us) (?:the|a) (?:receipt'
                      r'|certificate|copy))\b', re.I)


class SaleEmailOrderDisposition(models.AbstractModel):
    """Stage 2 text rules: whether a person still needs to act on the email (strategy 'authority_disposition')."""
    _name = 'sale.email.order.disposition'
    _description = "Email Order Non-Order Disposition Rules"

    @api.model
    def _disposition_route(self, body, known, lookup, subject=''):
        """Return (route, case_id) of a non-order: archived, linked_no_action, linked_human or human."""
        body = self.env['sale.email.order.authorization']._clip_thread(body)[0]
        refs = {int(x) for x in CASE_REF.findall(subject + ' ' + body)}
        case = lookup(next(iter(refs))) if known and len(refs) == 1 else None
        content = CASE_REF.sub('', body).strip(' :#-')
        # A non-routine subject can impose a task even when the body only says thanks.
        subj = CASE_REF.sub('', subject).strip(' :#-')
        parts = [v.strip(' :,-') for v in re.split(r'[.!;\n]+|\s+[—–]\s+|,\s*(?=no (?:reply|response|action))', content)
                 if v.strip(' :,-')]
        safe = bool(known and (not subj or BENIGN_SUBJECT.fullmatch(subj)) and parts and '?' not in body
                    and not HARD.search(content) and all(NO_ACTION.fullmatch(v) for v in parts) and (case or not refs))
        if case:
            return ('linked_no_action' if safe else 'linked_human'), case
        return ('archived' if safe else 'human'), None

    @api.model
    def _draft_followup(self, body, subject=''):
        """Whether the current turn of a drafted order still asks staff for something."""
        return bool(FOLLOWUP.search(subject + ' ' + self.env['sale.email.order.authorization']._clip_thread(body)[0]))
