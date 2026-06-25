"""
Crawler: DOST-TAPI Philippines technology transfer portal
https://tapitechtransfer.dost.gov.ph/technologies

Run from the apctt-gateway directory:
    python scripts/crawl_dost_tapi.py

Requirements: httpx, beautifulsoup4
"""

import asyncio
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

BASE = "https://tapitechtransfer.dost.gov.ph"
LIST_URL = f"{BASE}/technologies"
OUT_PATH = Path(__file__).parent.parent / "backend" / "sources" / "data" / "dost_tapi.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; APCTT-Gateway-Crawler/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}
CONCURRENCY = 4
DELAY = 0.5


CATEGORY_SLUGS = [
    "agricultural-productivity",
    "it-development",
    "msme-competitiveness",
    "quality-healthcare",
    "disaster-resilience",
]

async def _get_tech_urls_from_category(client: httpx.AsyncClient, cat_slug: str) -> list[str]:
    """Paginate a single category page and return individual tech URLs."""
    urls = []
    page = 0
    cat_url = f"{LIST_URL}/{cat_slug}"
    cat_prefix = f"{cat_url}/"

    while True:
        paged = f"{cat_url}?page={page}" if page > 0 else cat_url
        try:
            r = await client.get(paged, headers=HEADERS, timeout=30)
            r.raise_for_status()
        except Exception as e:
            print(f"    Category {cat_slug} page {page} failed — {e}")
            break

        soup = BeautifulSoup(r.text, "html.parser")
        found = []

        for a in soup.find_all("a", href=True):
            href = a["href"]
            full = urljoin(BASE, href)
            # Individual tech pages sit one level deeper than the category
            if full.startswith(cat_prefix) and "?" not in full and full not in urls:
                found.append(full)

        if not found:
            # Fallback: any /node/ links
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if re.match(r"^/node/\d+$", href):
                    full = urljoin(BASE, href)
                    if full not in urls and full not in found:
                        found.append(full)

        urls.extend(found)
        print(f"    [{cat_slug}] page {page}: +{len(found)} techs (total {len(urls)})")

        next_link = soup.select_one("a[rel='next'], .pager__item--next a, li.next a")
        if not next_link or not found:
            break
        page += 1
        await asyncio.sleep(DELAY)

    return list(dict.fromkeys(urls))


async def get_all_tech_urls(client: httpx.AsyncClient) -> list[str]:
    """Walk all 5 category pages and collect individual tech URLs."""
    all_urls = []
    for cat in CATEGORY_SLUGS:
        print(f"  Category: {cat}")
        cat_urls = await _get_tech_urls_from_category(client, cat)
        all_urls.extend(cat_urls)
        await asyncio.sleep(DELAY)
    return list(dict.fromkeys(all_urls))


def _detect_sector(text: str) -> str:
    mapping = [
        ("Agriculture", ["agri", "crop", "farm", "soil", "fertiliz", "seed", "plant", "rice", "coconut", "fish", "aqua"]),
        ("Health", ["health", "medic", "pharma", "drug", "clinic", "diagnos", "therapeut", "disease"]),
        ("Food", ["food", "nutrition", "processing", "beverage", "ferment", "postharvest"]),
        ("Energy", ["energy", "solar", "wind", "biofuel", "biomass", "power", "renewable"]),
        ("Environment", ["environment", "waste", "water", "pollution", "recycl", "sustainab"]),
        ("ICT", ["software", "digital", "ict", "app", "system", "data", "sensor", "iot"]),
        ("Materials", ["material", "composite", "ceramic", "polymer", "textile", "fabric", "nano"]),
        ("Manufacturing", ["manufactur", "machin", "equipment", "tool", "process", "industrial"]),
    ]
    low = text.lower()
    for sector, keywords in mapping:
        if any(k in low for k in keywords):
            return sector
    return "Technology"


def parse_tech_page(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    body = soup.get_text(" ", strip=True)

    # ID from URL slug
    slug = url.rstrip("/").split("/")[-1]
    tech_id = slug

    # Title
    title = ""
    for sel in ["h1.page-title", "h1.title", "h1", ".field--name-title", ".node__title"]:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            title = el.get_text(strip=True)
            break
    if not title:
        title = soup.title.get_text(strip=True) if soup.title else slug.replace("-", " ").title()

    # Summary — body field paragraphs
    summary = ""
    for sel in [".field--name-body", ".field--name-field-description",
                ".field--name-field-technology-description", "article .field"]:
        el = soup.select_one(sel)
        if el:
            paras = [p.get_text(" ", strip=True) for p in el.find_all("p") if len(p.get_text(strip=True)) > 20]
            if paras:
                summary = " ".join(paras[:3])
                break
    if not summary:
        paras = [p.get_text(" ", strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 30]
        summary = " ".join(paras[:3])

    # Institute — usually DOST agency
    institute = "DOST-TAPI"
    m = re.search(r"(DOST[-\s]?[\w\s]+(?:Institute|Center|Centre|Laboratory|Research|Agency|Office)[\w\s]*|ITDI|PCAARRD|PCHRD|PCIEERD|ASTI|FNRI|PHIVOLCS|PAGASA|MIRDC|PTRI|FPRDI|BIOTECH)", body)
    if m:
        institute = m.group(1).strip()

    # TRL
    trl = ""
    m_trl = re.search(r"TRL[-\s]*(\d)", body, re.IGNORECASE)
    if m_trl:
        trl = f"TRL-{m_trl.group(1)}"

    sector = _detect_sector(title + " " + summary)

    # Keywords from slug
    stop = {"and", "the", "for", "with", "from", "into", "using", "based"}
    keywords = [w for w in slug.replace("-", " ").split() if len(w) > 3 and w not in stop]

    return {
        "id": f"dost_tapi_{tech_id}",
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
        r = await client.get(url, headers=HEADERS, timeout=25)
        r.raise_for_status()
        rec = parse_tech_page(r.text, url)
        print(f"  [{idx}/{total}] {rec['title'][:70]}")
        return rec
    except Exception as e:
        print(f"  [{idx}/{total}] FAILED {url} — {e}")
        return None


async def main():
    results = []
    async with httpx.AsyncClient(follow_redirects=True) as client:
        print("=== DOST-TAPI Philippines Crawler ===")
        urls = await get_all_tech_urls(client)
        total = len(urls)
        print(f"\nFound {total} technology URLs. Crawling detail pages…\n")

        for i in range(0, total, CONCURRENCY):
            batch = urls[i:i + CONCURRENCY]
            tasks = [crawl_one(client, u, i + j + 1, total) for j, u in enumerate(batch)]
            records = await asyncio.gather(*tasks)
            results.extend([r for r in records if r])
            await asyncio.sleep(DELAY)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nDone. {len(results)}/{total} technologies saved to {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
