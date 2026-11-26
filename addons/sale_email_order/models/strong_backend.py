"""OpenAI extraction backend. Never persist credentials or provider error bodies."""
import os
import time

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def extract(messages, *, model="gpt-6.2-sol", timeout=120):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY is not configured")
    start = time.monotonic()
    request = Request(
        "https://api.openai.com/v1/responses",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        data=json.dumps({"model": model, "input": messages, "store": False,
              "text": {"format": {"type": "json_object"}}, "max_output_tokens": 2048}).encode(),
    )
    try:
        with urlopen(request, timeout=timeout) as reply:
            data = json.load(reply)
    except HTTPError as exc:
        raise ValueError(f"OpenAI extraction returned HTTP {exc.code}") from None
    except (URLError, TimeoutError) as exc:
        raise ValueError("OpenAI extraction connection failed") from exc
    if data.get("status") != "completed":
        raise ValueError("OpenAI extraction did not complete")
    text = "".join(part.get("text", "") for item in data.get("output", [])
                   if item.get("type") == "message" for part in item.get("content", [])
                   if part.get("type") == "output_text")
    if not text:
        raise ValueError("OpenAI extraction returned no output text")
    return text, {"model": data.get("model"), "usage": data.get("usage"),
                  "latency_seconds": time.monotonic() - start}
