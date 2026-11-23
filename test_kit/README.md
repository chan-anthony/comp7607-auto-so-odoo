# sale_email_order test kit (Odoo 19.0, Docker Compose)

Place this folder next to docker-compose.yml and .env:

    <repo>/
    ├── docker-compose.yml
    ├── .env                      (ODOO_DB = Odoo database to test)
    ├── addons/sale_email_order/
    ├── config/odoo.conf
    └── test_kit/
        ├── docker_run.sh
        ├── emails/*.eml
        ├── expected_results.csv
        ├── import_emails.py
        └── setup_test_data.py

1. Install sale_email_order in Odoo (Apps > Update Apps List > install).
2. Load test data: ./test_kit/docker_run.sh setup
3. Import the emails: ./test_kit/docker_run.sh import
4. Open Sales > Orders > Email Orders, group by Status / Category, compare with expected_results.csv.

Re-import the same emails: EML_FRESH=1 ./test_kit/docker_run.sh import
Import only some: EML_ONLY=01,13,20 ./test_kit/docker_run.sh import
Other database for one run: DB=other_db ./test_kit/docker_run.sh import
