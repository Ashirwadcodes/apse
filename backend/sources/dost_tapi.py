import json
import logging
from datetime import datetime
from pathlib import Path

from backend.sources.base import BaseSource
from backend.models.technology import Technology

logger = logging.getLogger(__name__)

_DATA_PATH = Path(__file__).parent / "data" / "dost_tapi.json"


class DOSTTAPISource(BaseSource):
    id = "dost_tapi"
    name = "DOST-TAPI Philippines"
    country = "Philippines"
    institution = "Department of Science and Technology — Technology Application and Promotion Institute"
    status = "Metadata search"
    url = "https://tapitechtransfer.dost.gov.ph/technologies"
    ttl_seconds = 86400

    def __init__(self):
        self._records: list[dict] = []
        self._loaded = False

    def _load(self):
        if self._loaded:
            return
        if not _DATA_PATH.exists():
            logger.warning("DOST-TAPI: data file NOT FOUND at %s", _DATA_PATH)
            self._records = []
        else:
            with open(_DATA_PATH, encoding="utf-8-sig") as f:
                self._records = json.load(f)
            logger.info("DOST-TAPI: loaded %d records from %s", len(self._records), _DATA_PATH)
        self._loaded = True

    def _to_technology(self, rec: dict) -> Technology:
        return Technology(
            id=rec["id"],
            title=rec["title"],
            summary=rec.get("summary", ""),
            sector=rec.get("sector", "Technology"),
            language="en",
            keywords=rec.get("keywords", []),
            country="Philippines",
            source_id=self.id,
            source_name=self.name,
            url=rec["url"],
            fetched_at=datetime.utcnow(),
            org_name=rec.get("institute", "DOST-TAPI"),
            transfer_type="Technology transfer / licensing",
            dev_status=rec.get("trl", ""),
            reg_date="",
            sub_sector="",
        )

    async def search(self, query: str, filters: dict) -> tuple[list[Technology], int]:
        self._load()
        page = int(filters.get("page", 1))
        page_size = 20

        q = query.lower()
        sector_filter = (filters.get("sector") or "").lower()

        matched = []
        for rec in self._records:
            if sector_filter and sector_filter not in rec.get("sector", "").lower():
                continue
            if q:
                searchable = " ".join([
                    rec.get("title", ""),
                    rec.get("summary", ""),
                    rec.get("institute", ""),
                    " ".join(rec.get("keywords", [])),
                ]).lower()
                if q not in searchable:
                    continue
            matched.append(rec)

        total = len(matched)
        page_slice = matched[(page - 1) * page_size: page * page_size]
        return [self._to_technology(r) for r in page_slice], total

    def is_healthy(self) -> bool:
        return _DATA_PATH.exists()
