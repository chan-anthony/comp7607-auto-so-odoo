#!/usr/bin/env bash
# Run the test kit against Odoo in Docker Compose.
# Expected layout: this kit folder sits next to docker-compose.yml and .env:
#   <repo>/docker-compose.yml, <repo>/.env, <repo>/sale_email_order_test_kit/docker_run.sh
# Works from any current folder: the script always runs from <repo>.
#   ./sale_email_order_test_kit/docker_run.sh setup     # create test customers and products
#   ./sale_email_order_test_kit/docker_run.sh import    # import all sample emails
# The Odoo database name comes from ODOO_DB in <repo>/.env, or from DB=<name> on the command line:
#   DB=<odoo database> ./sale_email_order_test_kit/docker_run.sh setup
#   DB=<odoo database> ./sale_email_order_test_kit/docker_run.sh import   # import all sample emails
#   DB=<odoo database> EML_ONLY=01,13,20 ./sale_email_order_test_kit/docker_run.sh import
#   DB=<odoo database> EML_FRESH=1 ./sale_email_order_test_kit/docker_run.sh import   # re-import with new Message-IDs
#
# DB is the Odoo database name (see http://localhost:8069/web/database/manager),
# NOT the Postgres service name (mydb).
# The Postgres connection is read from the container's own HOST / USER / PASSWORD
# environment (set in docker-compose.yml). Override with DB_HOST / DB_USER / DB_PASSWORD if needed.
# Other settings: SERVICE (default: web), COMPOSE (default: "docker compose").
set -euo pipefail

ACTION=${1:-}
KIT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_DIR=$(dirname "$KIT_DIR")
cd "$PROJECT_DIR"
found_compose=
for f in compose.yaml compose.yml docker-compose.yaml docker-compose.yml; do
  [ -f "$f" ] && found_compose=$f
done
if [ -z "$found_compose" ] && [ -z "${COMPOSE:-}" ]; then
  echo "No docker-compose.yml found in $PROJECT_DIR. Put sale_email_order_test_kit next to docker-compose.yml." >&2
  exit 1
fi
if [ -z "${DB:-}" ] && [ -f .env ]; then
  DB=$(grep -E '^ODOO_DB=' .env | tail -n1 | cut -d= -f2- | tr -d '"'"'"'\r' || true)
fi
DB=${DB:?Set ODOO_DB=<Odoo database name> in .env, or pass DB=<name>}
SERVICE=${SERVICE:-web}
COMPOSE=${COMPOSE:-docker compose}
REMOTE_EMAILS=/tmp/sale_email_order_emails

odoo_shell() {  # $1 = script on the host, piped into the Odoo shell inside the container
  $COMPOSE exec -T \
    -e ODOO_DB="$DB" \
    -e DB_HOST="${DB_HOST:-}" -e DB_USER="${DB_USER:-}" -e DB_PASSWORD="${DB_PASSWORD:-}" \
    -e EML_DIR="$REMOTE_EMAILS" -e EML_ONLY="${EML_ONLY:-}" -e EML_FRESH="${EML_FRESH:-}" \
    -e ROUND_MANIFEST="${ROUND_MANIFEST:-}" -e ROUND_OUTPUT="${ROUND_OUTPUT:-}" \
    "$SERVICE" sh -c 'exec odoo shell -d "$ODOO_DB" --no-http \
      --db_host="${DB_HOST:-$HOST}" --db_user="${DB_USER:-$USER}" --db_password="${DB_PASSWORD:-$PASSWORD}"' \
    < "$1"
}

case "$ACTION" in
  export)
    : "${ROUND_MANIFEST:?Set ROUND_MANIFEST to the import manifest path inside the container}"
    : "${ROUND_OUTPUT:?Set ROUND_OUTPUT to the output path inside the container}"
    odoo_shell "$KIT_DIR/export_round.py"
    ;;
  setup)
    odoo_shell "$KIT_DIR/setup_test_data.py"
    ;;
  import)
    # Copy the emails into the container, replacing any earlier copy.
    $COMPOSE exec -T -u root "$SERVICE" rm -rf "$REMOTE_EMAILS"
    $COMPOSE cp "$KIT_DIR/emails" "$SERVICE:$REMOTE_EMAILS"
    $COMPOSE exec -T -u root "$SERVICE" chmod -R a+rX "$REMOTE_EMAILS"
    odoo_shell "$KIT_DIR/import_emails.py"
    ;;
  *)
    echo "Usage: DB=<Odoo database name> $0 setup|import" >&2
    exit 1
    ;;
esac
