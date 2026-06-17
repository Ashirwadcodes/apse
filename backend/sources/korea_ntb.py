import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import unquote

from backend.sources.base import BaseSource
from backend.models.technology import Technology
from backend.config import settings


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
            url=self.url,
            fetched_at=datetime.utcnow(),
            org_name=f("orgName"),
            transfer_type=f("transType"),
            dev_status=f("devStatusName"),
            reg_date=f("regDate"),
            sub_sector=f("tcateNamem"),
        )

    async def search(self, query: str, filters: dict) -> tuple[list[Technology], int]:
        params: dict = {
            "serviceKey": unquote(settings.KOREA_NTB_API_KEY),
            "numOfRows": "20",
            "pageNo": "1",
        }
        if query:
            params["techName"] = query
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
