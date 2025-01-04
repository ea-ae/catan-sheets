# Quickstart

1. Create a new file called `.env` in the project root
1. Setup the environment with `DISCORD_TOKEN` and `TWOSHEEP_API_KEY`
1. Add the generated `service_account_key.json` file for the google APIs
1. Install poetry, e.g. `pipx install poetry`
1. Install dependencies via `poetry install`
1. Set the correct constants (e.g. channel IDs)
1. Run bot via `poetry run python catan-sheets/main.py`

# Contributing

Try to (somewhat) respect mypy types (unless you're lazy). Use black formatter.
