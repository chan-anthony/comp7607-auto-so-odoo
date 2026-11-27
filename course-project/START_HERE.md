# Group 55: Odoo procurement email workflow

Download [Workflow_Replay.html](Workflow_Replay.html) (or open it from a local checkout) and open it in a browser. The replay compares two recorded Odoo decisions for each of 160 synthetic emails. It runs offline and makes no API calls.

- [Historical audit: 65 non-orders](historical65.csv) — each message, its staff obligation, and the disposition decision.
- [Blind comparison: 160 paired decisions](blind-decisions.csv) — inspect the expected action, quotation lines, cloud exposure, human queue, and case link.
- [Native evaluation protocol](../evaluation/FINAL_REPRODUCE.md) and [runtime setup](../evaluation/ENVIRONMENT.md). The CSVs are review exports; raw evaluation archives are not included on this branch.
