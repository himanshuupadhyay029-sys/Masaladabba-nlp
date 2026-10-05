"""
Collect raw ingredient lines from recipe pages.

Reads URLs from data/raw/urls.txt, fetches each page politely (2s delay,
browser-like user-agent), extracts the ingredient lines, dedupes them and
writes one line per row to data/raw/lines.txt.

If a site blocks us (403/429/timeouts) we print a clear message. If nothing
could be scraped at all, we fall back to data/raw/manual_lines.txt.

Usage:  python src/scrape.py
"""

import html
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
URLS_FILE = ROOT / "data" / "raw" / "urls.txt"
OUT_FILE = ROOT / "data" / "raw" / "lines.txt"
MANUAL_FILE = ROOT / "data" / "raw" / "manual_lines.txt"

DELAY_SECONDS = 2
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 "
        "(college NLP project; indian-recipe-ner)"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}


def read_list_file(path):
    """Read non-empty, non-comment lines from a text file."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]


def clean_line(text):
    """Normalise whitespace and a few HTML artefacts.

    We keep the text as close to the original as possible: the messiness
    (fractions like ½, "tbsp.", Hinglish spellings) is exactly what the NER
    model has to learn, so we do NOT lowercase or correct spelling here.
    """
    text = html.unescape(text)                # "&amp;" -> "&" (JSON-LD keeps HTML entities)
    text = text.replace("\xa0", " ")          # non-breaking spaces from HTML
    text = re.sub(r"\s+", " ", text)          # collapse newlines/tabs/multiple spaces
    text = re.sub(r"^None\s+", "", text)      # some sites print a missing quantity as "None"
    return text.strip(" -•*\t")


# ---------- extraction strategies ----------

def from_json_ld(soup):
    """Most recipe sites embed schema.org Recipe data as JSON-LD for Google.
    Its 'recipeIngredient' field is a clean list of ingredient lines."""
    found = []

    def walk(node):
        if isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            if "recipeIngredient" in node:
                found.extend(str(x) for x in node["recipeIngredient"])
            for key in ("@graph", "mainEntity"):
                if key in node:
                    walk(node[key])

    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            walk(json.loads(tag.string or ""))
        except json.JSONDecodeError:
            continue
    return found


def from_html(soup):
    """Fallback: look for common ingredient markup in the page HTML."""
    selectors = [
        "li.wprm-recipe-ingredient",           # WP Recipe Maker (Hebbar's, Veg Recipes of India)
        "[itemprop='recipeIngredient']",       # schema.org microdata (Archana's, older sites)
        "li.ingredient",
        ".recipe-ingredients li",
        ".ingredients li",
    ]
    for sel in selectors:
        items = soup.select(sel)
        if items:
            return [li.get_text(" ", strip=True) for li in items]
    return []


def scrape_url(url):
    """Fetch one page and return its ingredient lines.
    Returns None if the site blocked us / failed, [] if nothing was found."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
    except requests.RequestException as e:
        print(f"  [BLOCKED/FAILED] could not fetch: {e.__class__.__name__}")
        return None

    if resp.status_code in (401, 403, 429, 503):
        print(f"  [BLOCKED] HTTP {resp.status_code} - the site is refusing scrapers.")
        return None
    if resp.status_code != 200:
        print(f"  [FAILED] HTTP {resp.status_code}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    lines = from_json_ld(soup) or from_html(soup)
    return [clean_line(l) for l in lines if clean_line(l)]


def dedupe(lines):
    """Remove duplicates case-insensitively, keeping first occurrence order."""
    seen, result = set(), []
    for line in lines:
        key = line.lower()
        if key not in seen:
            seen.add(key)
            result.append(line)
    return result


def main():
    urls = read_list_file(URLS_FILE)
    print(f"Found {len(urls)} URLs in {URLS_FILE.relative_to(ROOT)}")

    all_lines, blocked = [], []
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}")
        lines = scrape_url(url)
        if lines is None:
            blocked.append(url)
        elif not lines:
            print("  [EMPTY] page loaded but no ingredient list was found.")
        else:
            print(f"  got {len(lines)} lines")
            all_lines.extend(lines)
        if i < len(urls):
            time.sleep(DELAY_SECONDS)  # be polite to the server

    if blocked:
        print(f"\n{len(blocked)} URL(s) were blocked or failed:")
        for u in blocked:
            print(f"  - {u}")

    if not all_lines:
        print(
            "\nNothing could be scraped. Falling back to "
            f"{MANUAL_FILE.relative_to(ROOT)} - add lines there by hand "
            "(copy-paste from the recipe pages)."
        )
        all_lines = read_list_file(MANUAL_FILE)

    lines = dedupe(all_lines)
    OUT_FILE.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print(f"\nWrote {len(lines)} unique lines to {OUT_FILE.relative_to(ROOT)} "
          f"({len(all_lines) - len(lines)} duplicates removed)")


if __name__ == "__main__":
    main()
