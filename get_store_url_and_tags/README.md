# Store Category URL Discovery and Tagging

Discovers category URLs from clothing store websites and scrapes product listings. Tags are auto-generated from navigation/breadcrumbs for use downstream.

## Setup (clean install)

You need **Python 3.8+**, a **virtualenv**, the packages in `requirements.txt`, and **Chromium** via Playwright. Steps differ slightly by OS; pick your platform below.

### 1. Create a virtualenv and install Python dependencies

**Linux (Ubuntu / Debian)**

```bash
cd /path/to/mall-e/scripts/get_store_url_and_tags
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**macOS**

```bash
cd /path/to/mall-e/scripts/get_store_url_and_tags
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

(If your Mac only has `python`, use `python` instead of `python3`; ensure it’s 3.8+ with `python3 --version` or `python --version`.)

**Windows (PowerShell)**

```powershell
cd C:\path\to\mall-e\scripts\get_store_url_and_tags
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Windows (Command Prompt)**

```cmd
cd C:\path\to\mall-e\scripts\get_store_url_and_tags
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

On Windows, if `python` is not in PATH, try `py -3 -m venv venv` and then `py -3 -m pip install -r requirements.txt`.

### 2. Install Chromium for Playwright

With the virtualenv activated, install Playwright’s Chromium (required once per environment):

**Linux (Ubuntu)**  
Chromium needs system libraries (fonts, GPU, etc.). Install browser and deps in one step (may prompt for `sudo`):

```bash
playwright install --with-deps chromium
```

If you already ran `playwright install chromium` and then see missing-library errors when launching, run:

```bash
sudo playwright install-deps chromium
```

**macOS**  
No system deps needed. Just:

```bash
playwright install chromium
```

**Windows**  
No system deps needed. Just:

```bash
playwright install chromium
```

(In PowerShell or Command Prompt, same command.)

### 3. Run the script

Use the **repo root** so `scripts` is on `PYTHONPATH`:

**Linux / macOS**

```bash
cd /path/to/mall-e
source scripts/get_store_url_and_tags/venv/bin/activate
PYTHONPATH=scripts python -m get_store_url_and_tags --stores Abercrombie
```

**Windows (PowerShell)**

```powershell
cd C:\path\to\mall-e
.\scripts\get_store_url_and_tags\venv\Scripts\Activate.ps1
$env:PYTHONPATH = "scripts"; python -m get_store_url_and_tags --stores Abercrombie
```

**Windows (Command Prompt)**

```cmd
cd C:\path\to\mall-e
scripts\get_store_url_and_tags\venv\Scripts\activate.bat
set PYTHONPATH=scripts
python -m get_store_url_and_tags --stores Abercrombie
```

Alternatively, run from inside the script directory (Linux/macOS: `PYTHONPATH=. python -m get_store_url_and_tags ...`; Windows: `set PYTHONPATH=.` then `python -m get_store_url_and_tags ...`).

---

## 1. How to Use

### Run from repo root (recommended)

From the repo root with virtualenv activated. **Linux/macOS:** set `PYTHONPATH=scripts` in the same line as the command. **Windows (PowerShell):** `$env:PYTHONPATH="scripts"`; **Windows (CMD):** `set PYTHONPATH=scripts` (then run the `python -m ...` command).

```bash
# Process all stores in config (discovery + scraping)
PYTHONPATH=scripts python -m get_store_url_and_tags

# Process only specific stores (comma-separated)
PYTHONPATH=scripts python -m get_store_url_and_tags --stores Abercrombie
PYTHONPATH=scripts python -m get_store_url_and_tags --stores "AmericanEagle,Abercrombie"

# Discovery only (no product scraping)
PYTHONPATH=scripts python -m get_store_url_and_tags --disable-fetch-clothing-items

# Output products as JSON
PYTHONPATH=scripts python -m get_store_url_and_tags --json

# Run browser with window visible (useful when sites use bot checks)
PYTHONPATH=scripts python -m get_store_url_and_tags --headless=false

# Use a custom config file
PYTHONPATH=scripts python -m get_store_url_and_tags --config ./my-stores.json
```

### Verify stores with debug options

```bash
# Dump discovered category URLs to debug/ (see section 5)
PYTHONPATH=scripts python -m get_store_url_and_tags --dump-store-urls --disable-fetch-clothing-items

# Limit how many category URLs are scraped per store (quick smoke test)
PYTHONPATH=scripts python -m get_store_url_and_tags --max-urls-per-shop 2

# Dump product page HTML to debug/ for building new parsers
PYTHONPATH=scripts python -m get_store_url_and_tags --dump-item-html --max-urls-per-shop 1 --stores AmericanEagle
```

---

## 2. Config Options

### CLI options (main.py)

| Option | Default | Description |
|--------|---------|-------------|
| `--stores` | (all) | Comma-separated store names to process |
| `--config` | `config/stores.json` | Path to JSON config file |
| `--dump-store-urls` | false | Write discovered URLs to `debug/<store>_urls_<timestamp>.json` |
| `--headless` | `true` | Run browser headless (`true` / `false`) |
| `--disable-fetch-clothing-items` | false | Only run discovery; do not scrape products |
| `--category` | (none) | Skip discovery; only fetch items for this category path (e.g. `Womens/Bottoms/Jeans`) |
| `--json` | false | Emit products as JSON to stdout |
| `--dump-item-html` | false | Save product listing page HTML to `debug/<safe_url>-dump.html` for parser development |
| `--max-urls-per-shop` | (none) | Cap number of category URLs scraped per store (for debugging) |
| `--verbose` / `-v` | false | DEBUG logging |
| `--store-in-database` | false | Persist scraped products to Firestore (or configured backend) |

### Config file: `config/stores.json`

**Per-store fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Display name; must match scraper `STORE_NAME` if you have a scraper |
| `homepage` | yes | Start URL for discovery |
| `domain` | yes | Domain for robots.txt and filtering (e.g. `ae.com`) |
| `discovery_strategy` | no | `"auto"` (default), `"sitemap"`, `"navigation"`, or `"links"` — see below |
| `extra_category_patterns` | no | Regex list; URLs matching are kept as category pages |
| `extra_exclude_patterns` | no | Regex list; URLs matching are excluded |
| `max_path_depth` | no | Max path segments (e.g. 3 = `/a/b/c`); deeper URLs dropped |

**Discovery strategies:**

- **auto**: Try sitemap → navigation → link crawler; stop when a strategy returns URLs.
- **sitemap**: Only sitemap discovery.
- **navigation**: Only nav-menu discovery.
- **links**: Only link-crawler discovery.

**Global `settings` (optional in JSON):**

| Key | Default | Description |
|-----|---------|-------------|
| `rate_limit_seconds` | 2.0 | Delay between requests (link crawler) |
| `max_retries` | 3 | Retries for HTTP/robots |
| `request_timeout_seconds` | 30.0 | Timeout for HTTP and browser |
| `max_crawl_depth` | 2 | Max depth for link crawler |

---

## 3. Scrapers (product parsers)

Product listing pages are parsed by **per-store scrapers** in `scraping/scrapers/`. Each store that supports product scraping has a module that subclasses `BaseScraper` and implements `parse_html(soup, tags)`.

### How to add a new parser

1. **Dump sample HTML** for the store’s category page:
   ```bash
   PYTHONPATH=scripts python -m get_store_url_and_tags --dump-item-html --max-urls-per-shop 1 --stores YourStore
   ```
   Inspect `debug/<safe_url>-dump.html` to find selectors for product cards, name, price, link, image.

2. **Create** `scraping/scrapers/<store_slug>.py` (e.g. `loft.py`):
   - Define `STORE_NAME = "Loft"` (must match the `name` in `config/stores.json`).
   - Subclass `BaseScraper`, call `super().__init__(STORE_NAME)` and set `self.base_url`.
   - Implement `parse_html(self, soup: BeautifulSoup, tags: list[str]) -> List[Product]`:
     - Find product cards (e.g. by class or `data-*`).
     - For each card, extract name, price, link, image URL.
     - Return `List[Product]` with `store`, `item_name`, `item_image_link`, `item_link`, `price`, `tags`.

3. **Register** the scraper in `scraping/scrapers/__init__.py`:
   - `from . import <store_slug>`
   - Add `<store_slug>.STORE_NAME: <store_slug>.<ClassName>` to `_REGISTRY`.

Stores in config but not in `_REGISTRY` will be discovered (URLs + tags) but their category pages will be skipped during scraping with a warning.

---

## 4. Adding More Stores to the List

1. **Add a store entry** in `config/stores.json` under `"stores"`:
   ```json
   {
     "name": "NewStore",
     "homepage": "https://www.newstore.com/",
     "domain": "newstore.com",
     "discovery_strategy": "auto"
   }
   ```
   Use `extra_category_patterns` / `extra_exclude_patterns` / `max_path_depth` if needed.

2. **Run discovery** (and optionally dump URLs to verify):
   ```bash
   PYTHONPATH=scripts python -m get_store_url_and_tags --stores NewStore --dump-store-urls --disable-fetch-clothing-items
   ```
   Check `debug/newstore_urls_<timestamp>.json` for discovered category URLs and tags.

3. **Optional: add a product scraper** so the pipeline can scrape products from that store (see section 3). If you don’t add a scraper, discovery still runs; scraping will log “No scraper available” for that store.

---

## 5. Verifying Stores (debug options)

- **Discovery only + dump URLs**  
  Confirms that category URLs and tags are found:
  ```bash
  PYTHONPATH=scripts python -m get_store_url_and_tags --dump-store-urls --disable-fetch-clothing-items
  ```
  Output: `debug/<store>_urls_<timestamp>.json` per store.

- **Limit category URLs per store**  
  Quick check that scraping runs without processing every category:
  ```bash
  PYTHONPATH=scripts python -m get_store_url_and_tags --max-urls-per-shop 2
  ```
  Only the first 2 discovered URLs per store are scraped.

- **Single store, verbose**  
  Debug one store with detailed logs:
  ```bash
  PYTHONPATH=scripts python -m get_store_url_and_tags --stores Abercrombie -v
  ```

- **Dump product page HTML**  
  Use when writing or fixing a parser:
  ```bash
  PYTHONPATH=scripts python -m get_store_url_and_tags --dump-item-html --max-urls-per-shop 1 --stores YourStore
  ```
  Saves HTML to `debug/<safe_url>-dump.html` for inspection.

Combine as needed, e.g. `--dump-store-urls --disable-fetch-clothing-items --max-urls-per-shop 1 --stores NewStore -v`.
