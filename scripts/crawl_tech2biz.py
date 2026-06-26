"""
Crawler: Tech2Biz Thailand — technology transfer platform
https://www.tech2biz.net/content/inventor

~656 technologies across 41 pages. Content is in Thai.
Titles are translated to English via MyMemory API during crawl.

Run from the apctt-gateway directory:
    python scripts/crawl_tech2biz.py

Requirements: httpx, beautifulsoup4
"""

import asyncio
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, unquote

import httpx
from bs4 import BeautifulSoup

BASE = "https://www.tech2biz.net"
LIST_URL = f"{BASE}/content/inventor"
OUT_PATH = Path(__file__).parent.parent / "backend" / "sources" / "data" / "tech2biz.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; APCTT-Gateway-Crawler/1.0)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9,th;q=0.8",
}
CONCURRENCY = 3
PAGE_DELAY = 0.6   # between listing pages
TECH_DELAY = 0.4   # between tech pages
TRANSLATE_DELAY = 0.5  # between translation calls


async def translate_th_en(client: httpx.AsyncClient, text: str) -> str:
    """Translate Thai to English via MyMemory (free, no key required)."""
    if not text or not text.strip():
        return text
    try:
        url = f"https://api.mymemory.translated.net/get"
        r = await client.get(url, params={
            "q": text[:400],
            "langpair": "th|en",
        }, timeout=10)
        data = r.json()
        translated = data.get("responseData", {}).get("translatedText", "")
        # MyMemory returns original text if quota exceeded
        if translated and translated.lower() != text.lower():
            return translated
    except Exception:
        pass
    return text


async def get_tech_urls_page(client: httpx.AsyncClient, page: int) -> list[str]:
    url = f"{LIST_URL}?page={page}" if page > 1 else LIST_URL
    r = await client.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    urls = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Pattern: /content/{id}-{thai-slug}
        if re.match(r"^/content/\d+-", href) or re.match(r"^https?://www\.tech2biz\.net/content/\d+-", href):
            full = urljoin(BASE, href)
            if full not in urls:
                urls.append(full)
    return urls


def _detect_sector(text: str) -> str:
    mapping = [
        ("Agriculture", ["agri", "crop", "farm", "soil", "fertiliz", "seed", "plant", "rice",
                         "fish", "aqua", "food safety", "pesticide", "herb"]),
        ("Health", ["health", "medic", "pharma", "drug", "diagnos", "therapeut", "disease",
                    "pathogen", "antibacter", "antiviral", "wound", "hospital"]),
        ("Food", ["food", "nutrition", "beverage", "ferment", "postharvest", "cooking", "flour"]),
        ("Energy", ["energy", "solar", "battery", "fuel", "biomass", "biofuel", "power"]),
        ("Environment", ["water", "waste", "environ", "recycl", "pollution", "treatment"]),
        ("Materials", ["material", "composite", "coating", "polymer", "textile", "fabric",
                       "nano", "rubber", "adhesive", "paint"]),
        ("ICT", ["software", "app", "digital", "iot", "sensor", "data", "system", "platform"]),
        ("Manufacturing", ["manufactur", "machin", "equipment", "tool", "process", "industrial"]),
    ]
    low = text.lower()
    for sector, keywords in mapping:
        if any(k in low for k in keywords):
            return sector
    return "Technology"


def extract_id(url: str) -> str:
    m = re.search(r"/content/(\d+)-", url)
    return m.group(1) if m else url.split("/")[-1]


async def crawl_tech_page(client: httpx.AsyncClient, url: str, idx: int, total: int) -> dict | None:
    try:
        r = await client.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except Exception as e:
        print(f"  [{idx}/{total}] FAILED {url} — {e}")
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    tech_id = extract_id(url)

    # Title — h1 or first prominent heading
    title_th = ""
    for sel in ["h1", "h2.title", ".content-title", "h2", ".card-title"]:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True) and len(el.get_text(strip=True)) > 2:
            title_th = el.get_text(strip=True)
            break
    if not title_th:
        title_th = f"Technology {tech_id}"

    # Description — paragraphs in main content
    paras = []
    for p in soup.find_all("p"):
        t = p.get_text(" ", strip=True)
        if len(t) > 20:
            paras.append(t)
    summary_th = " ".join(paras[:3])

    # TRL — look for "ระดับ" (level) pattern
    trl = ""
    body_text = soup.get_text(" ")
    if "ต้นแบบ" in body_text or "prototype" in body_text.lower():
        trl = "Prototype"
    elif "TRL" in body_text:
        m = re.search(r"TRL[-\s]*(\d)", body_text, re.IGNORECASE)
        if m:
            trl = f"TRL-{m.group(1)}"

    # Institute — h5 near the title area
    institute = "Tech2Biz Thailand"
    h5s = soup.find_all("h5")
    for h5 in h5s[1:3]:  # skip first (likely title)
        t = h5.get_text(strip=True)
        if t and len(t) > 3:
            institute = t
            break

    return {
        "tech_id": tech_id,
        "title_th": title_th,
        "summary_th": summary_th[:600],
        "trl": trl,
        "institute": institute,
        "url": url,
    }


async def main():
    results = []

    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Step 1: collect all tech URLs from listing pages
        print("=== Tech2Biz Thailand Crawler ===")
        print("Step 1: Collecting technology URLs...")

        all_urls = []
        # Find total pages first
        r = await client.get(LIST_URL, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, "html.parser")

        # Find last page number from pagination
        last_page = 1
        for a in soup.find_all("a", href=True):
            m = re.search(r"page=(\d+)", a["href"])
            if m:
                last_page = max(last_page, int(m.group(1)))

        print(f"  Found {last_page} pages")

        for page in range(1, last_page + 1):
            urls = await get_tech_urls_page(client, page)
            all_urls.extend(urls)
            print(f"  Page {page}/{last_page}: +{len(urls)} URLs (total {len(all_urls)})")
            await asyncio.sleep(PAGE_DELAY)

        all_urls = list(dict.fromkeys(all_urls))
        total = len(all_urls)
        print(f"\nStep 2: Crawling {total} technology pages...\n")

        # Step 2: crawl each tech page in batches
        raw_records = []
        for i in range(0, total, CONCURRENCY):
            batch = all_urls[i:i + CONCURRENCY]
            tasks = [crawl_tech_page(client, u, i + j + 1, total) for j, u in enumerate(batch)]
            records = await asyncio.gather(*tasks)
            raw_records.extend([r for r in records if r])
            await asyncio.sleep(TECH_DELAY)

        print(f"\nStep 3: Translating {len(raw_records)} titles to English...\n")

        # Step 3: translate titles (batch with delays to respect rate limit)
        final = []
        for i, rec in enumerate(raw_records):
            title_en = await translate_th_en(client, rec["title_th"])
            summary_en = await translate_th_en(client, rec["summary_th"][:300])

            sector = _detect_sector(title_en + " " + summary_en)
            stop = {"that", "the", "and", "for", "with", "from", "into", "using", "based"}
            keywords = [w.lower() for w in re.split(r"\W+", title_en) if len(w) > 3 and w.lower() not in stop]

            final.append({
                "id": f"tech2biz_{rec['tech_id']}",
                "tech_id": rec["tech_id"],
                "title": title_en or rec["title_th"],
                "summary": summary_en or rec["summary_th"],
                "institute": rec["institute"],
                "trl": rec["trl"],
                "sector": sector,
                "keywords": keywords[:10],
                "url": rec["url"],
            })

            if (i + 1) % 10 == 0:
                print(f"  Translated {i + 1}/{len(raw_records)}")
            await asyncio.sleep(TRANSLATE_DELAY)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    print(f"\nDone. {len(final)}/{total} technologies saved to {OUT_PATH}")
    for rec in final[:5]:
        print(f"  • [{rec['sector']}] {rec['title'][:70]}")


if __name__ == "__main__":
    asyncio.run(main())
