"""Standard short-context GPT-6.2 Sol list-price estimate, USD (not an invoice).
Source: https://developers.openai.com/api/docs/models/gpt-6.2-sol
Checked 2026-11-26. Local Qwen/Kev are not metered by OpenAI; report their
processing time separately, not as a zero-cost infrastructure claim.
"""
def usd(usage):
    i=usage["input_tokens"]
    o=usage["output_tokens"]
    d=usage.get("input_tokens_details") or {}
    cached=d.get("cached_tokens",0)
    writes=d.get("cache_write_tokens",0)
    split=d.get("cache_write_tokens_details") or {}
    short=split.get("ttl_30m_tokens",0)
    long=split.get("ttl_12h_tokens",0)
    if writes!=short+long or cached+writes>i or i>272000:
        raise ValueError("Unsupported token accounting; check current pricing before estimating")
    return (2*(i-cached-writes)+0.10*cached+2.50*short+5*long+10*o)/1_000_000
