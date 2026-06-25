"""
Crawler: SLINTEC Sri Lanka — Ready-to-go Technologies
https://www.slintec.lk/what-we-offer/ready-to-go-technologies/

Single static page with ~28 technology cards.

Run from the apctt-gateway directory:
    python scripts/crawl_slintec.py

Requirements: httpx, beautifulsoup4
"""

import asyncio
import json
import re
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

PAGE_URL = "https://www.slintec.lk/what-we-offer/ready-to-go-technologies/"
BASE = "https://www.slintec.lk"
OUT_PATH = Path(__file__).parent.parent / "backend" / "sources" / "data" / "slintec.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; APCTT-Gateway-Crawler/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _detect_sector(text: str) -> str:
    mapping = [
        ("Agriculture", ["agri", "crop", "farm", "soil", "fertiliz", "plant", "nano fertiliz"]),
        ("Health", ["health", "medic", "diagnos", "disease", "therapeut", "pharma", "antiviral", "antibacterial"]),
        ("Food", ["food", "nutrition", "beverage", "packaging", "preservation"]),
        ("Energy", ["energy", "solar", "battery", "fuel", "power"]),
        ("Environment", ["water", "waste", "environment", "recycl", "pollution", "treatment"]),
        ("Materials", ["material", "nano", "composite", "coating", "polymer", "textile", "rubber", "graphene"]),
        ("ICT", ["software", "digital", "sensor", "iot", "data", "monitoring"]),
    ]
    low = text.lower()
    for sector, keywords in mapping:
        if any(k in low for k in keywords):
            return sector
    return "Technology"


def parse_listing_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    records = []

    # SLINTEC uses WordPress/standard CMS — look for tech items
    # Try: article cards, accordion items, div.entry-content items, table rows
    candidates = []

    # Option A: repeated article/div cards
    for sel in ["article", ".tech-item", ".technology-item", ".service-item",
                ".wpb_content_element", ".vc_column_text"]:
        items = soup.select(sel)
        if len(items) >= 5:
            candidates = items
            break

    # Option B: headings as tech titles (h3, h4 inside content area)
    if not candidates:
        content = soup.select_one(".entry-content, .page-content, main, #main-content")
        if content:
            headings = content.find_all(["h2", "h3", "h4"])
            if len(headings) >= 5:
                # Treat each heading + following paragraphs as one record
                for i, h in enumerate(headings):
                    title = h.get_text(strip=True)
                    if len(title) < 5:
                        continue
                    # Collect following sibling paragraphs until next heading
                    paras = []
                    for sib in h.find_next_siblings():
                        if sib.name in ["h2", "h3", "h4"]:
                            break
                        if sib.name in ["p", "div"] and sib.get_text(strip=True):
                            paras.append(sib.get_text(" ", strip=True))
                    summary = " ".join(paras[:3])

                    # Look for a link
                    link = h.find("a")
                    url = urljoin(BASE, link["href"]) if link and link.get("href") else PAGE_URL

                    slug = _slug(title)
                    sector = _detect_sector(title + " " + summary)
                    stop = {"and", "the", "for", "with", "from", "into", "using", "based", "that"}
                    keywords = [w for w in re.split(r"\W+", title.lower()) if len(w) > 3 and w not in stop]

                    records.append({
                        "id": f"slintec_{slug[:40]}",
                        "tech_id": slug[:40],
                        "title": title,
                        "summary": summary[:800],
                        "institute": "SLINTEC",
                        "trl": "",
                        "sector": sector,
                        "keywords": keywords[:10],
                        "url": url,
                    })
                return records

    # Option C: fallback — parse table rows
    if not candidates:
        rows = soup.select("table tr")
        if len(rows) >= 5:
            for row in rows[1:]:  # skip header
                cells = row.find_all(["td", "th"])
                if not cells:
                    continue
                title = cells[0].get_text(strip=True)
                summary = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                link = row.find("a")
                url = urljoin(BASE, link["href"]) if link and link.get("href") else PAGE_URL
                slug = _slug(title)
                records.append({
                    "id": f"slintec_{slug[:40]}",
                    "tech_id": slug[:40],
                    "title": title,
                    "summary": summary[:800],
                    "institute": "SLINTEC",
                    "trl": "",
                    "sector": _detect_sector(title + " " + summary),
                    "keywords": [w for w in re.split(r"\W+", title.lower()) if len(w) > 3][:10],
                    "url": url,
                })
        return records

    # Parse candidate elements
    for el in candidates:
        title_el = el.find(["h2", "h3", "h4", "strong"])
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if len(title) < 5:
            continue

        paras = [p.get_text(" ", strip=True) for p in el.find_all("p") if len(p.get_text(strip=True)) > 15]
        summary = " ".join(paras[:3])

        link = el.find("a")
        url = urljoin(BASE, link["href"]) if link and link.get("href") else PAGE_URL

        slug = _slug(title)
        sector = _detect_sector(title + " " + summary)
        stop = {"and", "the", "for", "with", "from", "into", "using", "based"}
        keywords = [w for w in re.split(r"\W+", title.lower()) if len(w) > 3 and w not in stop]

        records.append({
            "id": f"slintec_{slug[:40]}",
            "tech_id": slug[:40],
            "title": title,
            "summary": summary[:800],
            "institute": "SLINTEC",
            "trl": "",
            "sector": sector,
            "keywords": keywords[:10],
            "url": url,
        })

    return records


async def main():
    async with httpx.AsyncClient(follow_redirects=True) as client:
        print("=== SLINTEC Sri Lanka Crawler ===")
        print(f"Fetching: {PAGE_URL}")
        r = await client.get(PAGE_URL, headers=HEADERS, timeout=30)
        r.raise_for_status()

    records = parse_listing_page(r.text)

    # Deduplicate by id
    seen = set()
    unique = []
    for rec in records:
        if rec["id"] not in seen:
            seen.add(rec["id"])
            unique.append(rec)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)

    print(f"Done. {len(unique)} technologies saved to {OUT_PATH}")
    for rec in unique[:5]:
        print(f"  • {rec['title'][:70]}")


if __name__ == "__main__":
    asyncio.run(main())
