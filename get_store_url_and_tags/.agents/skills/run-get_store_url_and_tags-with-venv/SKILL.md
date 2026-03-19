---
name: run-get_store_url_and_tags-with-venv
description: Run the `get_store_url_and_tags` program and create or reuse the project `.venv` virtual environment. Use when the user asks how to execute the pipeline or how to set up dependencies in this repository.
---

# Run `get_store_url_and_tags` with `.venv`

## When to use this skill

Use this skill when the user asks how to run the program in this repo, how to set up dependencies, or how to create/reuse the project virtual environment named `.venv`.

## Quick start (one-time setup)

From the repository root (this directory):

1. Create a virtualenv (reuses `.venv` if it already exists):

```bash
cd /home/rob/Development/mall-e/scripts

# Create .venv if missing
python3 -m venv .venv

# Activate it
source .venv/bin/activate
```
Product
```bash
pip install -U pip
pip install -r get_store_url_and_tags/requirements.txt
pip install -r get_store_url_and_tags/requirements-test.txt
```

## Reuse `.venv` (typical workflow)

When `.venv` already exists, just activate it and reinstall deps only if requirements changed:

```bash
cd /home/rob/Development/mall-e/scripts
source .venv/bin/activate

# Optional, when requirements.txt changed
pip install -r get_store_url_and_tags/requirements.txt
```

## Run the pipeline

The program entrypoint is a module:

```bash
PYTHONPATH=scripts python -m get_store_url_and_tags
```

Common examples:

1. Run discovery + scraping for a single store:

```bash
PYTHONPATH=scripts python -m get_store_url_and_tags --stores Abercrombie
```

2. Discovery-only:

```bash
PYTHONPATH=scripts python -m get_store_url_and_tags --disable-fetch-clothing-items
```

3. Scrape a specific category path:

```bash
PYTHONPATH=scripts python -m get_store_url_and_tags --category "Womens/Bottoms"
```

4. Dump discovered URLs to `get_store_url_and_tags/debug/`:

```bash
PYTHONPATH=scripts python -m get_store_url_and_tags --dump-store-urls --disable-fetch-clothing-items
```

## Optional: install Playwright browser dependencies

If you run the scraper and Playwright fails due to missing Chromium/system dependencies, run:

```bash
playwright install --with-deps chromium
```

## Run unit tests

```bash
cd /home/rob/Development/mall-e/scripts
source .venv/bin/activate
PYTHONPATH=scripts pytest get_store_url_and_tags/tests/ -q
```

## Troubleshooting notes

1. If `python -m pytest` says `pytest` is missing, run `pip install -r get_store_url_and_tags/requirements-test.txt`.
2. If the module can’t be imported, ensure you are running from the repo root and set `PYTHONPATH=scripts`.
3. Keep the `.venv` directory checked into `.gitignore` (it should already be ignored in this repo).

