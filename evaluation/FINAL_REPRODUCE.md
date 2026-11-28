# Final course release: non-order disposition

The final optional strategy in Sales settings is **Line authorization + non-order disposition**. It does not change the quotation decision from the per-line strategy. Unknown or actionable mail stays in a human queue. Set the strategy on an isolated test database only after updating the addon. The option is not enabled automatically.

## Reproduce without cloud, credentials or Docker
Unzip the source and evidence archives. From the source root run:

    python evaluation/score_disposition.py PATH_TO_EXTRACTED_EVIDENCE/final
    python evaluation/audit_nonorders.py PATH_TO_EXTRACTED_EVIDENCE/previous/line-pairs.json historical65-recomputed.csv
    python -m unittest discover -s evaluation -p "test_nonorder.py"

The first command recomputes results and the 160-row decision CSV from transaction-derived native outputs, not from predictions inferred by the scorer. The fields in the operational gold describe a staff obligation, not an observed reply. The audit CSV gives the actual text, prior case ID, business interpretation, expected work and routing decision for each of the 65 historical non-orders.

## Native replay protocol
Use synthetic data and the dedicated odoo_test database. The existing module setup and seed catalogue are described in evaluation/ENVIRONMENT.md. Upgrade sale_email_order before selecting the final strategy. evaluation/build_disposition_challenge.py writes the frozen manifest and separate synthetic case register into a new folder. evaluation/run_disposition_native.py is an Odoo shell script, not a standalone Python program. It instantiates registered open/closed review case fixtures, checks sender ownership and company, and runs authority_line / authority_disposition against the same inputs. The evaluator exports the database states, quotation SKU/quantity lines, queue membership and case attachments, then rolls back the test transaction. Sensitive config is not included.

For cache-only native replay, copy final/{manifest.json,register.json,native-pairs.json,strong-candidates.jsonl} into the container folder /tmp/group55-disposition (make it writable by the container's web user). Run the native script with DISPOSITION_REPLAY_ONLY=1 in the project Odoo shell; missing cached inputs raise instead of contacting any provider. During replay only the transaction-created case IDs are normalized back to the original request; any different non-ID message or prompt is rejected. Re-score using the newly exported native-pairs.json. 84 cloud-exposed emails per policy was the observed routing count; 54 distinct cloud prompts were collected and replayed across equivalent inputs. This is not a comparison of charges.

## What operators see
“All human work” includes state=review OR followup_needed. An actionable email linked to another case counts once (not zero and not twice). A mixed order can retain its quotation and still require a reply. Mark staff work complete after actual handling; this closes the follow-up without deleting or confirming any quotation. A no-action link appears in “Associated inbound emails” on the verified case; it posts no case note and assigns no new action. Unrecognized references, closed cases and different senders do not link. Matching the sender address is not proof of identity for a production system.

No user study or employee time study was conducted. Reduction measures emails requiring handling, not labor minutes or total real-world ticket volume.
