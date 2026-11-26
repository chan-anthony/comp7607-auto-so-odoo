# Paired sales-email evaluation

`build_cases.py OUTPUT` builds an initial controlled contrast panel, separate
from the teammate's 20 product-integration fixtures. It is not a sample of real
orders, nor the entire proposed 1,000-email corpus. Each template pair is
instantiated on the ten catalogue products; the two variants preserve the same
product context but change the requested business action. Six writing families
span purchase revisions, cancelled alternatives, shipping instructions, meeting
minutes, reported speech, and conditional prices. Customer and product
identities are intentionally shared (the ERP catalogue is fixed); the
calibration and test families are disjoint. Report results by family rather
than interpreting the ten catalogue substitutions as ten independent language
phenomena. Simulated customer replies are not included.

The model input is only the subject/body that the Odoo extraction path sees.
Gold category, expected action, expected product lines, fixture identifiers,
family, and split are for evaluation only. Use the development/calibration
families for threshold selection, then freeze settings before test inference
or scoring. Report the two panels separately. A correct review does not count
as a correct automatically generated quotation.

For the 20 existing integration fixtures, set ROUND_MANIFEST (e.g.
`/tmp/group55-round01-ids.json`) during import. After Odoo finishes processing,
use the same ROUND_MANIFEST and a ROUND_OUTPUT container path with
`test_kit/docker_run.sh export`. Copy the output JSON from the web container
and run `python test_kit/score_regression.py OUTPUT.json`. Every file must map
to one completed request from this import; a missing fixture invalidates the
round. Compare linked customer, product IDs (internal references) and quantities
on actual draft lines, not merely the model's JSON.
