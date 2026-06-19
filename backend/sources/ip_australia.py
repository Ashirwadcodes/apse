import time
import threading
import httpx
from backend.sources.base import BaseSource
from backend.models.technology import Technology
from backend.config import settings


class IPAustraliaSource(BaseSource):
    id = "ip_australia"
    name = "IP Australia Patent Search"
    country = "Australia"
    institution = "IP Australia"
    status = "Metadata search"
    url = "https://www.ipaustralia.gov.au/patents"
    ttl_seconds = 86400

    _BASE = "https://test.api.ipaustralia.gov.au/public/australian-patent-search-api/v1"
    _TOKEN_URL = "https://test.api.ipaustralia.gov.au/public/external-token-api/v1/access_token"

    def __init__(self):
        self._token: str | None = None
        self._token_expiry: float = 0.0
        self._lock = threading.Lock()

    # ── OAuth2 client-credentials token management ────────────────────────────

    def _get_token(self) -> str:
        with self._lock:
            if self._token and time.time() < self._token_expiry - 30:
                return self._token

            client_id = settings.IP_AUSTRALIA_CLIENT_ID
            client_secret = settings.IP_AUSTRALIA_CLIENT_SECRET

            r = httpx.post(
                self._TOKEN_URL,
                data={"grant_type": "client_credentials"},
                auth=(client_id, client_secret),
                timeout=15,
            )
            r.raise_for_status()
            body = r.json()
            self._token = body["access_token"]
            self._token_expiry = time.time() + int(body.get("expires_in", 3600))
            return self._token

    # ── Search ────────────────────────────────────────────────────────────────

    async def search(self, query: str, filters: dict) -> tuple[list[Technology], int]:
        if not query:
            return [], 0

        token = self._get_token()
        payload = {
            "query": query,
            "searchType": "DETAILS",
            "searchMode": "QUICK_NO_ABSTRACT",
            "pageSize": 20,
            "pageNumber": 0,
            "sort": {"field": "FILING_DATE", "direction": "DESC"},
        }

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                f"{self._BASE}/search/quick",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            r.raise_for_status()

        data = r.json()
        total = int(data.get("totalHits") or 0)
        items = []
        for hit in data.get("results") or []:
            items.append(self._normalize(hit))
        return items, total

    def _normalize(self, hit: dict) -> Technology:
        titles = hit.get("title") or []
        title = titles[0] if titles else (hit.get("applicationNumber") or "Untitled")

        applicants = hit.get("applicants") or []
        org = applicants[0] if applicants else ""

        filing_date = hit.get("filingDate") or ""
        # filingDate comes as YYYYMMDD string
        if len(filing_date) == 8:
            filing_date = f"{filing_date[:4]}-{filing_date[4:6]}-{filing_date[6:]}"

        app_num = hit.get("applicationNumber") or ""

        return Technology(
            id=f"ipau_{app_num}",
            source_id=self.id,
            source_name=self.name,
            title=title,
            summary=f"Australian patent application {app_num}. Filed: {filing_date}. Status: {hit.get('applicationStatus') or 'Unknown'}.",
            sector="Patents",
            country="Australia",
            language="en",
            org_name=org,
            transfer_type="Patent licence",
            dev_status=hit.get("applicationStatus") or "",
            reg_date=filing_date,
            keywords=[],
            sub_sector="",
            url=f"https://pericles.ipaustralia.gov.au/ols/auspat/applicationDetails.do?applicationNo={app_num}",
        )

    def is_healthy(self) -> bool:
        try:
            self._get_token()
            return True
        except Exception:
            return False
