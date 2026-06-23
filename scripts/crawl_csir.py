"""
One-time crawler: downloads all CSIR India technologies and saves to
backend/sources/data/csir_india.json

Run from the apctt-gateway directory:
    python scripts/crawl_csir.py

Requirements: httpx, beautifulsoup4  (pip install httpx beautifulsoup4)
"""

import asyncio
import json
import re
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

BASE = "https://techindiacsir.anusandhan.net/online"
LIST_URL = f"{BASE}/Control.do?_tech="
OUT_PATH = Path(__file__).parent.parent / "backend" / "sources" / "data" / "csir_india.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; APCTT-Gateway-Crawler/1.0)"}
CONCURRENCY = 5      # parallel fetches
DELAY = 0.4          # seconds between batches


async def get_all_tech_urls(client: httpx.AsyncClient) -> list[str]:
    """Scrape the listing page for all *-T-*-tech.htm hrefs."""
    print("Fetching technology list…")
    r = await client.get(LIST_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    urls = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r"-T-\d+-tech\.htm$", href):
            # Make absolute
            if not href.startswith("http"):
                href = f"{BASE}/{href.lstrip('/')}"
            urls.append(href)
    print(f"Found {len(urls)} technology URLs")
    return list(dict.fromkeys(urls))  # deduplicate preserving order


def parse_tech_page(html: str, url: str) -> dict:
    """Extract structured fields from an individual technology page."""
    soup = BeautifulSoup(html, "html.parser")
    text = lambda sel, default="": (soup.select_one(sel) or object).__dict__.get("string") or \
        (soup.select_one(sel).get_text(strip=True) if soup.select_one(sel) else default)

    # Tech ID from URL
    m = re.search(r"-T-(\d+)-tech\.htm", url)
    tech_id = m.group(1) if m else ""

    # Title — usually in h1, h2, or a prominent heading
    title = ""
    for tag in ["h1", "h2", "h3", ".tech-title", ".title"]:
        el = soup.select_one(tag)
        if el and el.get_text(strip=True):
            title = el.get_text(strip=True)
            break
    if not title:
        title = soup.title.get_text(strip=True) if soup.title else "Untitled"

    # Grab all paragraph text for summary
    paras = [p.get_text(" ", strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 30]
    summary = " ".join(paras[:3])

    # Institute — look for CSIR-* pattern
    institute = ""
    body_text = soup.get_text(" ")
    m_inst = re.search(r"(CSIR[-–]\w[\w\s\-]+(?:Institute|Laboratory|Centre|Research|CFTRI|CSIO|IHBT|CCMB|CDRI|CIMAP|CLRI|CSMCRI|IICB|SERC|NML|NCL|NIIST|NEERI|IMMT|CIMFR|IGIB|IIIM|IICT|CECRI|CRRI|CBRI|AMPRI|NIO|NGRI|NISCAIR|NISTADS)[\w\s]*)", body_text)
    if m_inst:
        institute = m_inst.group(1).strip()

    # TRL
    trl = ""
    m_trl = re.search(r"TRL[-\s]*(\d)", body_text, re.IGNORECASE)
    if m_trl:
        trl = f"TRL-{m_trl.group(1)}"

    # Sector — look for table rows or labelled sections
    sector = "Technology"
    for kw in ["Agriculture", "Food", "Health", "Energy", "Environment", "ICT",
                "Manufacturing", "Materials", "Biotech", "Chemical", "Defence"]:
        if kw.lower() in body_text.lower():
            sector = kw
            break

    # Keywords from slug
    slug_part = url.split("/")[-1].replace(f"-T-{tech_id}-tech.htm", "")
    keywords = [w for w in slug_part.replace("-", " ").split() if len(w) > 3]

    return {
        "id": f"csir_{tech_id}",
        "tech_id": tech_id,
        "title": title,
        "summary": summary[:800],
        "institute": institute,
        "trl": trl,
        "sector": sector,
        "keywords": keywords[:10],
        "url": url,
    }


async def crawl_one(client: httpx.AsyncClient, url: str, idx: int, total: int) -> dict | None:
    try:
        r = await client.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        record = parse_tech_page(r.text, url)
        print(f"  [{idx}/{total}] {record['title'][:60]}")
        return record
    except Exception as e:
        print(f"  [{idx}/{total}] FAILED {url} — {e}")
        return None


async def main():
    results = []
    async with httpx.AsyncClient(follow_redirects=True) as client:
        urls = await get_all_tech_urls(client)
        total = len(urls)

        # Process in batches of CONCURRENCY
        for i in range(0, total, CONCURRENCY):
            batch = urls[i:i + CONCURRENCY]
            tasks = [crawl_one(client, url, i + j + 1, total) for j, url in enumerate(batch)]
            records = await asyncio.gather(*tasks)
            results.extend([r for r in records if r])
            await asyncio.sleep(DELAY)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nDone. {len(results)}/{total} technologies saved to {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
