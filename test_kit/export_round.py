# Read-only Odoo-shell script. Use the same ROUND_MANIFEST as the import.
import os
import json
from pathlib import Path

manifest = json.loads(Path(os.environ["ROUND_MANIFEST"]).read_text(encoding="utf-8"))
if manifest["database"] != env.cr.dbname:
    raise ValueError("Manifest belongs to another database")
out = []
for name, ident in manifest["records"].items():
    rec = env["sale.email.order"].browse(ident).exists()
    if not rec or rec.state not in ("done", "review"):
        raise ValueError(f"{name}: missing record or processing not finished")
    so = rec.sale_order_id
    if so and so.state != "draft":
        raise ValueError(f"{name}: linked document is not a draft")
    out.append(dict(file=name, state=rec.state, has_draft=bool(so),
                    customer_email=so.partner_id.email_normalized if so else None,
                    lines=[dict(sku=l.product_id.default_code, quantity=l.product_uom_qty)
                           for l in so.order_line] if so else [],
                    category=rec.category, confidence=rec.confidence, seconds=rec.processing_time,
                    trace=rec.inference_trace,
                    review_reason=rec.review_reason, request_id=rec.id, quotation_id=so.id or None))
Path(os.environ["ROUND_OUTPUT"]).write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"Exported {len(out)} completed requests")
