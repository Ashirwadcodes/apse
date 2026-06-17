from backend.sources.base import BaseSource
from backend.models.technology import Technology

# WIPO PATENTSCOPE requires OAuth credentials for its REST API.
# Currently configured as a Search redirect — users are sent directly to
# a pre-filtered PATENTSCOPE search for their query.
# Upgrade path: when credentials are available, restore live metadata search
# by implementing _normalize() and an authenticated search() call.


class WIPOPatentscopeSource(BaseSource):
    id = "wipo_patentscope"
    name = "WIPO PATENTSCOPE"
    country = "International"
    institution = "World Intellectual Property Organization (WIPO)"
    status = "Search redirect"
    url = "https://patentscope.wipo.int/search/en/search.jsf"
    ttl_seconds = 86400

    async def search(self, query: str, filters: dict) -> list[Technology]:
        return []

    def is_healthy(self) -> bool:
        return True
