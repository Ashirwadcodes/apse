from backend.sources.base import BaseSource
from backend.models.technology import Technology


class IndiaTIFACSource(BaseSource):
    id = "india_tifac"
    name = "India TIFAC TechMonitor"
    country = "India"
    institution = "Technology Information, Forecasting and Assessment Council (TIFAC)"
    status = "Search redirect"
    url = "https://tifac.org.in/techmonitor"
    ttl_seconds = 86400

    async def search(self, query: str, filters: dict) -> tuple[list[Technology], int]:
        return [], 0

    def is_healthy(self) -> bool:
        return True
