"""Score one complete 20-email Odoo regression round. Input: UTF-8 JSON list
of {file, state, customer_email, lines: [{sku, quantity}], has_draft}.
The file field is the fixture filename; state is the native done/review state.
Never accept partial or repeated imports as a complete round.
"""
import csv
import json
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent


def score(rows):
    with (KIT / "expected_results.csv").open(encoding="utf-8-sig", newline="") as f:
        expected = {r["file"]: r for r in csv.DictReader(f)}
    lines = json.loads((KIT / "expected_lines.json").read_text())
    by_file = {r["file"]: r for r in rows}
    if len(rows) != len(by_file) or set(expected) != set(by_file):
        raise ValueError("Incomplete round, duplicate fixture, or unexpected filename")
    outcomes = []
    for name, e in expected.items():
        r = by_file[name]
        auto = r["has_draft"]
        wanted = e["expected_status"] == "Order Created"
        actual_lines = sorted((x["sku"], x["quantity"]) for x in r["lines"])
        exact = (auto and wanted and r["state"] == "done"
                 and r["customer_email"] == e["from"]
                 and actual_lines == sorted(lines[name[:2]].items()))
        correct_review = not auto and not wanted and r["state"] == "review"
        outcomes.append(dict(file=name, draft=auto, right_draft=exact,
                             right_action=bool(exact or correct_review),
                             missed_draft=wanted and not auto))
    n = len(rows)
    drafts = sum(x["draft"] for x in outcomes)
    right = sum(x["right_draft"] for x in outcomes)
    return dict(total=n, drafts=drafts, right_drafts=right, wrong_drafts=drafts-right,
                automation_coverage=drafts/n,
                wrong_rate_among_drafts=(drafts-right)/drafts if drafts else None,
                missed_drafts=sum(x["missed_draft"] for x in outcomes),
                correct_actions=sum(x["right_action"] for x in outcomes), rows=outcomes)


if __name__ == "__main__":
    print(json.dumps(score(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))), indent=2))
