"""Extract uncertainty from emitted JSON values, never from the confidence field."""
import json
import math
import re


_VALUE = re.compile(r'"(category|product|quantity)"\s*:\s*("(?:\\.|[^"\\])*"|-?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)')


def field_logprobs(text, tokens):
    if not tokens:
        return None
    raw = text.encode("utf-8")
    spans = []
    for match in _VALUE.finditer(text):
        a, b = match.span(2)
        if text[a] == '"':
            a, b = a + 1, b - 1
        spans.append((match[1], len(text[:a].encode()), len(text[:b].encode())))
    buf = bytearray()
    vals = {}
    for token in tokens:
        start = len(buf)
        buf.extend(token["bytes"])
        for key, a, b in spans:
            if start < b and len(buf) > a:
                vals.setdefault(key, []).append(float(token["logprob"]))
    if bytes(buf) != raw or not vals or not all(math.isfinite(v) for vs in vals.values() for v in vs):
        return None
    return {k: {"mean": sum(v)/len(v), "min": min(v), "tokens": len(v)} for k,v in vals.items()}
