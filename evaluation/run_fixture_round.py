# Odoo shell, local test database only. Synthetic email inputs; no live mailbox.
# Commit each completed fixture and checkpoint the native record IDs for export.
import os
import json
from pathlib import Path
from email import policy
from email.parser import BytesParser
from odoo.tools import html2plaintext

assert env.cr.dbname == "odoo_test"
mode = os.environ["ROUND_MODE"]
assert mode in ("strong", "small", "confidence", "kev")
folder = Path(os.environ["EML_DIR"])
manifest = Path(os.environ["ROUND_MANIFEST"])
files = sorted(folder.glob("*.eml"))
assert len(files) == 20
saved = json.loads(manifest.read_text()) if manifest.exists() else {
    "database": env.cr.dbname, "strategy": mode, "records": {}}
assert saved["database"] == env.cr.dbname and saved["strategy"] == mode
params = env["ir.config_parameter"].sudo()
for path in files:
    if path.name in saved["records"]:
        continue
    msg = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    # Use Odoo's own MIME parser and incoming-message conversion.
    parsed = env["mail.thread"].message_parse(msg)
    sender = parsed.get("email_from") or parsed.get("from") or str(msg["From"])
    record = env["sale.email.order"].create({
        "name": parsed.get("subject") or str(msg["Subject"]),
        "email_from": sender, "body": html2plaintext(parsed.get("body") or "")})
    prior = params.get_param("sale_email_order.strategy", "small")
    params.set_param("sale_email_order.strategy", mode)
    record._process()
    params.set_param("sale_email_order.strategy", prior)
    if (record.review_reason or "").startswith("AI call failed:"):
        raise RuntimeError(f"{path.name}: {record.review_reason}")
    env.cr.commit()
    saved["records"][path.name] = record.id
    tmp = manifest.with_suffix(".tmp")
    tmp.write_text(json.dumps(saved, indent=2)); tmp.replace(manifest)
    print(path.name, record.state, flush=True)
