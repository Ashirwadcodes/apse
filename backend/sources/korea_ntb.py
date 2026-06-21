import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import unquote

from backend.sources.base import BaseSource
from backend.models.technology import Technology
from backend.config import settings

_KO_CHARS = set("가나다라마바사아자차카타파하")


def _is_korean(text: str) -> bool:
    return any("가" <= ch <= "힣" for ch in text)


async def _translate_to_korean(query: str) -> str:
    if not query or _is_korean(query):
        return query
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(
                "https://api.mymemory.translated.net/get",
                params={"q": query[:400], "langpair": "en|ko"},
            )
        translated = r.json().get("responseData", {}).get("translatedText", "")
        if translated and translated.lower() != query.lower():
            return translated
    except Exception:
        pass
    return query


class KoreaNTBSource(BaseSource):
    id = "korea_ntb"
    name = "Korea National Technology Bank"
    country = "Republic of Korea"
    institution = "Korea Institute for Advancement of Technology (KIAT)"
    status = "Metadata search"
    url = "https://www.ntb.kr"
    ttl_seconds = 86400

    def _normalize(self, item: ET.Element) -> Technology:
        def f(tag: str) -> str:
            return (item.findtext(tag) or "").strip()

        tech_id = f("stechNum")
        sector = f("tcateNamep") or f("tcateNamem") or "Uncategorized"

        kw_raw = f("keyword")
        app_fld = f("appFld")
        keywords = [k.strip() for k in kw_raw.split(";") if k.strip()]
        if app_fld:
            keywords += [k.strip() for k in app_fld.split(",") if k.strip()]

        return Technology(
            id=f"ntb_{tech_id}",
            title=f("techName") or "Untitled",
            summary=f("summary"),
            sector=sector,
            language="Korean",
            keywords=keywords,
            country="Republic of Korea",
            source_id=self.id,
            source_name=self.name,
            url=f"https://www.ntb.kr/market/selectFullTechAndRecommend.do?techKey=&stechNum={tech_id}" if tech_id else self.url,
            fetched_at=datetime.utcnow(),
            org_name=f("orgName"),
            transfer_type=f("transType"),
            dev_status=f("devStatusName"),
            reg_date=f("regDate"),
            sub_sector=f("tcateNamem"),
        )

    async def search(self, query: str, filters: dict) -> tuple[list[Technology], int]:
        # Use pre-translated query from search.py (avoids eating per-source timeout)
        ntb_query = filters.get("ntb_query") or (await _translate_to_korean(query) if query else "")

        page = int(filters.get("page", 1))
        params: dict = {
            "serviceKey": unquote(settings.KOREA_NTB_API_KEY),
            "numOfRows": "20",
            "pageNo": str(page),
        }
        if ntb_query:
            params["techName"] = ntb_query
        if filters.get("sector"):
            params["tcateNamep"] = filters["sector"]

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(settings.KOREA_NTB_BASE_URL, params=params)
                r.raise_for_status()
        except Exception:
            return [], 0

        try:
            root = ET.fromstring(r.text)
        except ET.ParseError:
            return [], 0

        if (root.findtext(".//resultCode") or "") != "00":
            return [], 0

        total_count = int(root.findtext(".//totalCount") or "0")
        items = [self._normalize(item) for item in root.findall(".//item")]
        return items, total_count

    def is_healthy(self) -> bool:
        return True
