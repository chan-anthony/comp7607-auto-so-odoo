# Run in the Odoo shell on odoo_test. No sales documents are written.
# One dataset split and one model stage per run. Results are checkpointed by ID.
import json
import os
import time
from pathlib import Path
from odoo.addons.sale_email_order.models.sale_email_order import extract_strong

assert env.cr.dbname == "odoo_test"
split, tier = os.environ["EVAL_SPLIT"], os.environ["EVAL_TIER"]
assert split in ("calibration", "test", "stress") and tier in ("small", "strong", "kev")
base = Path(os.environ["EVAL_DIR"])
if split != "calibration" and not (base/"frozen-policies.json").is_file():
    raise ValueError("Freeze calibration policies before collecting held-out results")
manifest = "stress-manifest.json" if split == "stress" else "manifest.json"
cases = [c for c in json.loads((base/manifest).read_text()) if c["split"] == split]
if not cases:
    raise ValueError("Empty evaluation split")
def load_records(path):
    return {r["id"]: r for r in map(json.loads, path.read_text().splitlines())} if path.exists() else {}
outfile = base/f"{split}-{tier}.jsonl"
finished = load_records(outfile)
small = load_records(base/f"{split}-small.jsonl") if tier == "kev" else {}
if tier == "kev" and set(small) != {c["id"] for c in cases}:
    raise ValueError("Collect complete small-model predictions before Kev verification")

for case in cases:
    if case["id"] in finished:
        continue
    # No gold, case id, family, or synthetic variant name is visible to either model.
    rec = env["sale.email.order"].new({"name":case["subject"], "body":case["text"], "email_from":case["sender"]})
    start = time.monotonic()
    row = {"id": case["id"]}
    if tier == "kev":
        row["checks"] = rec._kev_check(small[case["id"]]["candidate"])
    else:
        if tier == "small":
            text, probs = rec._call_ollama()
        else:
            text, row["metadata"] = extract_strong(rec._extraction_messages())
            probs = None
        row["candidate"] = res = rec._parse_ai_response(text, probs)
        row["seconds"] = time.monotonic()-start
        # Apply the same catalogue lookup as the deployed path; do not guess a
        # product if the reference has no single match. Preserve repeated lines.
        mapped = []
        for item in res["lines"]:
            product = rec._find_product(item["product"])
            mapped.append([product.default_code if product else None, item["quantity"]])
        row["mapped_lines"] = mapped
        row["known_sender"] = bool(env["res.partner"].search_count([("email_normalized","=",case["sender"])]))
    if tier == "kev":
        row["seconds"] = time.monotonic()-start
    with outfile.open("a", encoding="utf8") as out:
        out.write(json.dumps(row, ensure_ascii=True)+"\n")
    print(split, tier, case["id"], flush=True)
