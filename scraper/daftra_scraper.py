"""
Daftra ERP Scraper - Fast Version
==================================
Grabs your session cookies from Edge (already logged in),
then crawls all pages using direct HTTP requests - no browser needed.
10-20x faster than Selenium.

HOW TO RUN:
  1. Log in to https://moustafazen90.daftra.com/ in Edge normally
  2. Run: python daftra_scraper.py
"""

import time
import re
import sqlite3
import shutil
import os
import json
import threading
from urllib.parse import urlparse, urljoin
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from http.cookiejar import CookieJar

import requests
from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL        = "https://moustafazen90.daftra.com"
OUTPUT_FILE     = "daftra_analysis.md"
MAX_PAGES       = 300
MAX_WORKERS     = 8        # parallel requests
REQUEST_TIMEOUT = 10
EXCLUDED_EXTS   = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".svg",
                   ".css", ".js", ".ico", ".woff", ".woff2", ".ttf", ".zip"}
# ─────────────────────────────────────────────────────────────────────────────


# ── Cookie extraction from Edge ───────────────────────────────────────────────

def get_edge_cookies(domain: str) -> dict:
    """
    Read cookies directly from Edge's SQLite cookie store.
    Returns a dict of {name: value} for the given domain.
    """
    # Possible Edge cookie DB locations
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Edge/User Data/Default/Network/Cookies",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Edge/User Data/Default/Cookies",
        Path(os.environ.get("USERPROFILE", "")) / "AppData/Local/Microsoft/Edge/User Data/Default/Network/Cookies",
        Path(os.environ.get("USERPROFILE", "")) / "AppData/Local/Microsoft/Edge/User Data/Default/Cookies",
        # Debug profile used by our launch command
        Path("C:/edge-debug/Default/Network/Cookies"),
        Path("C:/edge-debug/Default/Cookies"),
    ]

    cookie_db = None
    for c in candidates:
        if c.exists():
            cookie_db = c
            break

    if not cookie_db:
        print("  Could not find Edge cookie database. Trying without cookies...")
        return {}

    # Copy DB to temp location (Edge may have it locked)
    tmp = Path(os.environ.get("TEMP", ".")) / "edge_cookies_tmp.db"
    shutil.copy2(cookie_db, tmp)

    cookies = {}
    host = urlparse("https://" + domain).netloc or domain

    try:
        conn = sqlite3.connect(str(tmp))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT name, value, encrypted_value, host_key FROM cookies "
            "WHERE host_key LIKE ?",
            (f"%{domain.split('/')[0]}%",)
        )
        rows = cur.fetchall()
        conn.close()

        for row in rows:
            name  = row["name"]
            value = row["value"]
            # If value is empty it's encrypted (Windows DPAPI) — skip decryption,
            # just use what we have; session cookies usually have plaintext value
            if value:
                cookies[name] = value

        print(f"  Found {len(cookies)} cookies for {domain}")
    except Exception as e:
        print(f"  Cookie read error: {e}")
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass

    return cookies


def get_cookies_from_selenium() -> dict:
    """
    Fallback: connect to Edge via remote debugging just to steal cookies,
    then disconnect immediately.
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
        opts = Options()
        opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        driver = webdriver.Edge(options=opts)

        # Switch to Daftra tab
        for handle in driver.window_handles:
            driver.switch_to.window(handle)
            if BASE_URL in driver.current_url:
                break

        raw = driver.get_cookies()
        cookies = {c["name"]: c["value"] for c in raw}
        print(f"  Got {len(cookies)} cookies from Edge remote debugging")
        # Don't quit — just disconnect by letting driver go out of scope
        return cookies
    except Exception as e:
        print(f"  Selenium fallback failed: {e}")
        return {}


# ── URL helpers ───────────────────────────────────────────────────────────────

def is_same_domain(url: str) -> bool:
    return urlparse(url).netloc == urlparse(BASE_URL).netloc


def clean_url(url: str) -> str:
    p = urlparse(url)
    # Keep path + minimal query, drop fragment
    return p._replace(fragment="").geturl().rstrip("/")


def should_skip(url: str) -> bool:
    path = urlparse(url).path.lower()
    ext  = path.rsplit(".", 1)[-1]
    if f".{ext}" in EXCLUDED_EXTS:
        return True
    skip = ["logout", "signout", "sign-out", "log-out",
            "delete", "remove", "javascript:", "#"]
    return any(s in url.lower() for s in skip)


# ── Page scraping ─────────────────────────────────────────────────────────────

def fetch_page(session: requests.Session, url: str) -> tuple[str, BeautifulSoup | None]:
    """Fetch a single URL and return (url, soup). Returns (url, None) on error."""
    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if resp.status_code != 200:
            return url, None
        ct = resp.headers.get("content-type", "")
        if "html" not in ct:
            return url, None
        soup = BeautifulSoup(resp.text, "html.parser")
        return url, soup
    except Exception:
        return url, None


def extract_links(soup: BeautifulSoup, base: str) -> list[str]:
    links = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if not href or href.startswith("javascript"):
            continue
        full = urljoin(base, href)
        links.append(clean_url(full))
    return links


def extract_info(url: str, soup: BeautifulSoup) -> dict:
    title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled"

    info = {
        "url":            url,
        "title":          title,
        "headings":       [],
        "nav_items":      [],
        "buttons":        [],
        "inputs":         [],
        "table_headers":  [],
        "select_options": [],
        "tabs":           [],
        "badges":         [],
        "cards":          [],
    }

    # Headings
    for tag in ["h1", "h2", "h3", "h4"]:
        for el in soup.find_all(tag):
            t = el.get_text(strip=True)
            if t:
                info["headings"].append(f"{tag.upper()}: {t}")

    # Nav items
    seen_nav = set()
    nav_selectors = ["nav", "[class*=sidebar]", "[class*=menu]", "[class*=navbar]", "[id*=nav]"]
    for sel in nav_selectors:
        container = soup.select_one(sel)
        if not container:
            continue
        for a in container.find_all("a", href=True):
            text = a.get_text(strip=True)
            href = urljoin(url, a["href"])
            if text and text not in seen_nav:
                seen_nav.add(text)
                info["nav_items"].append({"label": text, "href": href})

    # Buttons
    seen_btns = set()
    for el in soup.find_all(["button", "input"]):
        if el.name == "input" and el.get("type") not in ("submit", "button", "reset"):
            continue
        t = (el.get_text(strip=True) or el.get("value") or
             el.get("title") or el.get("aria-label") or "").strip()
        if t and t not in seen_btns:
            seen_btns.add(t)
            info["buttons"].append(t)
    # Also <a class="btn...">
    for el in soup.select("a[class*=btn]"):
        t = el.get_text(strip=True)
        if t and t not in seen_btns:
            seen_btns.add(t)
            info["buttons"].append(t)

    # Inputs
    for el in soup.find_all(["input", "textarea", "select"]):
        itype = el.get("type", el.name)
        if itype in ("hidden", "submit", "button", "reset"):
            continue
        label = ""
        el_id = el.get("id")
        if el_id:
            lbl = soup.find("label", {"for": el_id})
            if lbl:
                label = lbl.get_text(strip=True)
        placeholder = el.get("placeholder", "")
        name        = el.get("name", "")
        display     = label or placeholder or name or itype
        if display:
            info["inputs"].append({"type": itype, "label": display, "name": name})

    # Table headers
    for th in soup.find_all("th"):
        t = th.get_text(strip=True)
        if t:
            info["table_headers"].append(t)

    # Select options
    for sel_el in soup.find_all("select"):
        name = sel_el.get("name") or sel_el.get("id") or "select"
        opts = [o.get_text(strip=True) for o in sel_el.find_all("option") if o.get_text(strip=True)]
        if opts:
            info["select_options"].append({"name": name, "options": opts})

    # Tabs
    for el in soup.select("[role=tab], .nav-tabs a, [class*=tab]"):
        t = el.get_text(strip=True)
        if t and t not in info["tabs"]:
            info["tabs"].append(t)

    # Badges / status
    for el in soup.select(".badge, [class*=badge], [class*=status], [class*=tag]"):
        t = el.get_text(strip=True)
        if t and t not in info["badges"]:
            info["badges"].append(t)

    # Cards / widgets
    for el in soup.select(".card-title, .card-header, [class*=card] h3, [class*=card] h4"):
        t = el.get_text(strip=True)
        if t and t not in info["cards"]:
            info["cards"].append(t)

    return info


# ── Markdown output ───────────────────────────────────────────────────────────

def info_to_markdown(info: dict, page_num: int) -> str:
    lines = ["\n---\n", f"## Page {page_num}: {info['title']}",
             f"**URL:** {info['url']}\n"]

    def section(title, items, fmt=lambda x: f"- {x}"):
        if items:
            lines.append(f"### {title}")
            for i in items:
                lines.append(fmt(i))
            lines.append("")

    section("Headings", info["headings"])
    section("Navigation / Menu Items", info["nav_items"],
            fmt=lambda i: f"- **{i['label']}** → `{i['href']}`")
    section("Tabs", info["tabs"])
    section("Buttons / Actions", info["buttons"])

    if info["table_headers"]:
        lines.append("### Table Columns")
        lines.append("| " + " | ".join(info["table_headers"]) + " |")
        lines.append("| " + " | ".join(["---"] * len(info["table_headers"])) + " |")
        lines.append("")

    if info["inputs"]:
        lines.append("### Form Fields / Inputs")
        lines += ["| Type | Label / Name |", "| --- | --- |"]
        lines += [f"| {i['type']} | {i['label']} |" for i in info["inputs"]]
        lines.append("")

    if info["select_options"]:
        lines.append("### Dropdowns")
        for s in info["select_options"]:
            lines.append(f"**{s['name']}:** " + ", ".join(s["options"]))
        lines.append("")

    section("Status Labels / Badges", info["badges"])
    section("Cards / Widgets", info["cards"])

    return "\n".join(lines)


# ── Main crawl ────────────────────────────────────────────────────────────────

def scrape():
    print("=" * 55)
    print("  Daftra Fast Scraper")
    print("=" * 55)

    # ── Get cookies ──────────────────────────────────────────────────────────
    print("\nStep 1: Getting session cookies from Edge...")
    domain = urlparse(BASE_URL).netloc
    cookies = get_cookies_from_selenium()

    if not cookies:
        print("  Trying to read from Edge cookie file...")
        cookies = get_edge_cookies(domain)

    if not cookies:
        print("\n  ⚠ No cookies found!")
        print("  Make sure Edge is open and you are logged in to Daftra.")
        print("  Also try launching Edge with:")
        print('  Start-Process msedge.exe "--remote-debugging-port=9222"')
        return

    # ── Build session ─────────────────────────────────────────────────────────
    session = requests.Session()
    session.cookies.update(cookies)
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0"
        ),
        "Accept-Language": "ar,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })

    # Test login
    print("\nStep 2: Testing connection...")
    resp = session.get(BASE_URL, timeout=10)
    if "login" in resp.url or "signin" in resp.url:
        print("  ⚠ Session expired or not logged in. Please log in to Daftra in Edge first.")
        return
    print(f"  ✓ Connected! Status: {resp.status_code}")

    # ── Crawl ─────────────────────────────────────────────────────────────────
    print(f"\nStep 3: Crawling (up to {MAX_PAGES} pages, {MAX_WORKERS} parallel workers)...\n")

    visited    = set()
    queue_lock = threading.Lock()
    pages_lock = threading.Lock()
    queue      = deque([clean_url(BASE_URL)])
    all_pages  = []        # [(url, info), ...]  ordered by discovery
    url_order  = []        # track insertion order

    def process_url(url):
        url_soap = fetch_page(session, url)
        return url_soap

    total_done = 0

    while queue and len(visited) < MAX_PAGES:
        # Grab a batch of URLs to process in parallel
        batch = []
        while queue and len(batch) < MAX_WORKERS:
            url = queue.popleft()
            if url in visited or should_skip(url) or not is_same_domain(url):
                continue
            visited.add(url)
            batch.append(url)

        if not batch:
            break

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futures = {ex.submit(fetch_page, session, url): url for url in batch}
            for future in as_completed(futures):
                url, soup = future.result()
                total_done += 1
                if soup is None:
                    print(f"  [{total_done:>3}] ✗ {url}")
                    continue

                info = extract_info(url, soup)
                all_pages.append((url, info))
                print(f"  [{total_done:>3}] ✓ {info['title'][:60]}")

                # Enqueue new links
                for link in extract_links(soup, url):
                    if link not in visited and is_same_domain(link) and not should_skip(link):
                        queue.append(link)

    # Sort pages by URL for clean output
    all_pages.sort(key=lambda x: x[0])

    # ── Write markdown ────────────────────────────────────────────────────────
    print(f"\nStep 4: Writing {len(all_pages)} pages to {OUTPUT_FILE} ...")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# Daftra ERP — Full Analysis\n")
        f.write(f"**Base URL:** {BASE_URL}  \n")
        f.write(f"**Pages crawled:** {len(all_pages)}  \n\n")
        f.write("## Table of Contents\n")
        for i, (url, page) in enumerate(all_pages, 1):
            title  = page["title"] or "Untitled"
            anchor = re.sub(r"[^a-z0-9\-]", "", title.lower().replace(" ", "-"))
            f.write(f"{i}. [{title}](#{anchor})  \n")
        f.write("\n")
        for i, (url, page) in enumerate(all_pages, 1):
            f.write(info_to_markdown(page, i))

    print(f"\n{'=' * 55}")
    print(f"  ✅ Done! Saved to: {OUTPUT_FILE}")
    print(f"  Total pages analysed: {len(all_pages)}")
    print(f"{'=' * 55}")


if __name__ == "__main__":
    scrape()
