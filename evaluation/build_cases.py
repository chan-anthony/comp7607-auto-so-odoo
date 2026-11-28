"""Synthetic, catalogue-grounded contrast sets (not customer traffic).

Each family has a distinct writing pattern and contrasting customer actions;
no family crosses the calibration/test boundary. Change quantities and SKUs
within a family without claiming the variants are independent templates.
"""
import ast
from email.message import EmailMessage
from pathlib import Path
import argparse
import json
import random

ROOT = Path(__file__).resolve().parents[1]
FAMILIES = {
    "calibration": {
        "amendment": (
            "Yesterday the plan was {old} {name}. Our approved quantity is now {n}. Please ship the revised quantity.",
            "Yesterday the plan was {old} {name}. Our approved quantity is now {n}. What would the revised lot cost? This is not an order."),
        "substitution": (
            "Please remove {other} from the list. The only line authorised for purchase is {sku}, quantity {n}.",
            "Please remove {other} from the list. We still need a price for {sku}, quantity {n}, before authorising purchase."),
        "split_destination": (
            "Dispatch {n} units of {sku} to our usual receiving desk; all units go together.",
            "Dispatch {n} units of {sku}; deliver one to our new office and the rest to our usual receiving desk."),
    },
    "test": {
        "minutes": (
            "Purchasing minutes: the suggestion of {old} was rejected. Decision: buy {n} of {sku}. Please act on that decision.",
            "Purchasing minutes: the suggestion of {old} was rejected. Decision: obtain pricing on {n} of {sku}. Approval will come later."),
        "reported_speech": (
            "My colleague mentioned {other} in passing. My actual order is {n} {name}. Nothing else, thanks.",
            "My colleague mentioned {other} in passing. Could you quote for {n} {name}? We haven't chosen a supplier."),
        "price_condition": (
            "For the workshop, reserve {n} x {sku}. Invoice at catalogue price. This is our firm order.",
            "For the workshop, reserve {n} x {sku} only if you match last year's discounted price; otherwise hold it."),
    },
}
REVIEW_CLASS = {"split_destination": "complex", "price_condition": "complex"}


def source_lists():
    tree = ast.parse((ROOT/"test_kit/setup_test_data.py").read_text(encoding="utf8"))
    return {node.targets[0].id: ast.literal_eval(node.value) for node in tree.body
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in {"PRODUCTS", "CUSTOMERS"}}


def build():
    lists = source_lists()
    products, customers = lists["PRODUCTS"], lists["CUSTOMERS"]
    rng = random.Random(7607)
    for split, families in FAMILIES.items():
        for family, pair in families.items():
            for i, (sku, name, _) in enumerate(products):
                sender = customers[i % len(customers)][2]
                ctx = dict(n=rng.randint(2, 17), old=rng.randint(19, 35), sku=sku, name=name,
                           other=products[(i+1) % len(products)][0])
                for variant, template in enumerate(pair):
                    category = REVIEW_CLASS.get(family, "quote") if variant else "standard"
                    yield dict(id=f"{family}-{i:02d}-{variant}", split=split, family=family,
                               pair_id=f"{family}-{i:02d}", sender=sender, subject="Purchasing correspondence",
                               text=template.format(**ctx), gold_category=category,
                               gold_action="review" if variant else "draft",
                               gold_draft_lines={} if variant else {sku: ctx["n"]})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    output = parser.parse_args().output
    output.mkdir(parents=True, exist_ok=True)
    cases = list(build())
    for case in cases:
        folder = output/case["split"]/"emails"
        folder.mkdir(parents=True, exist_ok=True)
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = case["sender"], "orders@example.com", case["subject"]
        msg["Message-ID"] = f"<{case['id']}@group55.example>"
        msg.set_content(case["text"])
        (folder/(case["id"]+".eml")).write_bytes(msg.as_bytes())
    (output/"manifest.json").write_text(json.dumps(cases, indent=2), encoding="utf8")
