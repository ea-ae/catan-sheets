# Quickstart

1. Create a new file called `.env` in the project root
2. Setup the environment with `DISCORD_TOKEN` and `TWOSHEEP_API_KEY`
3. Add the generated `service_account_key.json` file for the google APIs
4. Install poetry, e.g. `pipx install poetry`
5. Install dependencies via `poetry install`
6. Set the correct constants (e.g. channel IDs)
7. Run bot via `poetry run python catan-sheets/main.py`

# Contributing

Try to (somewhat) respect mypy types (unless you're lazy). Use black formatter.
