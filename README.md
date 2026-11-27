## Course project: email triage in Odoo

[Start here: offline demo and paired evaluation data](course-project/START_HERE.md).

# Setup: Odoo 19 + Postgres + Ollama with Docker Compose

1. Clone the repo and go into it: `git clone <repo-url> && cd <repo-folder>`
2. Create the env file: `cp .env-sample .env`
3. Edit `.env`:
   - `POSTGRES_PASSWORD` – your Postgres password (if `db_data/` already exists, use the password it was created with)
   - `OLLAMA_PORT` – port for Ollama, e.g. `11435`
   - `ODOO_DB` – your Odoo database name
4. Give Odoo write access: `sudo chown -R 1000:100 web_data`
5. Make sure `config/odoo.conf` contains `addons_path = /mnt/extra-addons`
6. Check the settings are filled in: `docker compose config`
7. Start: `docker compose up -d`
8. Pull the model: `docker compose exec ollama ollama pull qwen2.5:1.5b`
9. Check Ollama: `curl http://127.0.0.1:<OLLAMA_PORT>/api/tags`
10. Open Odoo at `http://localhost:8069`
11. Install the module: Apps > Update Apps List > install `sale_email_order`
12. In Odoo, Sales > Configuration > Settings > Email Orders (AI): set Ollama URL to `http://ollama:<OLLAMA_PORT>`

## Test with test_kit

`test_kit/` holds 20 sample order emails, scripts to load test customers and products and import the emails into Odoo, and the expected result for each email. See `test_kit/README.md` for how to run it.
