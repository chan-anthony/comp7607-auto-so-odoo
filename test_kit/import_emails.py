# Feeds .eml files into the Odoo mail gateway, exactly like an incoming mail server would.
# Run inside the Odoo shell:
#   EML_DIR=/path/to/emails odoo-bin shell -d <db> --no-http < import_emails.py
# Options (environment variables):
#   EML_DIR    folder with the .eml files (default: ./emails)
#   EML_ONLY   comma-separated file prefixes to import, e.g. "01,13,20" (default: all)
#   EML_FRESH  "1" = give each email a new Message-ID so it can be imported again (default: off;
#              Odoo silently skips a Message-ID it has already processed)
import os
import json
import uuid
from email import message_from_bytes, policy
from pathlib import Path

folder = Path(os.environ.get("EML_DIR", "emails")).resolve()
only = [p.strip() for p in os.environ.get("EML_ONLY", "").split(",") if p.strip()]
fresh = os.environ.get("EML_FRESH") == "1"

files = sorted(folder.glob("*.eml"))
if only:
    files = [f for f in files if any(f.name.startswith(p) for p in only)]
if not files:
    raise SystemExit(f"No .eml files found in {folder}")

EmailOrder = env["sale.email.order"]
before = set(EmailOrder.search([]).ids)
round_ids = {}
for path in files:
    raw = path.read_bytes()
    if fresh:
        msg = message_from_bytes(raw, policy=policy.SMTP)
        del msg["Message-ID"]
        msg["Message-ID"] = f"<{path.stem}-{uuid.uuid4().hex[:12]}@sample.test>"
        raw = msg.as_bytes()
    try:
        record_id = env["mail.thread"].message_process("sale.email.order", raw)
        env.cr.commit()
        status = "new record" if record_id and record_id not in before else "NO RECORD (duplicate Message-ID or loop protection, see server log)"
        print(f"{path.name:42} -> sale.email.order {record_id}  {status}")
        if record_id and record_id not in before:
            round_ids[path.name] = record_id
            before.add(record_id)
    except Exception as error:  # keep going with the next email
        env.cr.rollback()
        print(f"{path.name:42} -> FAILED: {error}")

if os.environ.get("ROUND_MANIFEST"):
    Path(os.environ["ROUND_MANIFEST"]).write_text(
        json.dumps({"database": env.cr.dbname, "records": round_ids}, indent=2), encoding="utf-8")
print("Done. The cron 'Email Orders: Process with AI' was triggered and will process the new emails.")
