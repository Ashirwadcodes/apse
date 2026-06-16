import asyncio
import hashlib
import json
from typing import Optional

from fastapi import APIRouter
from backend.sources.registry import SOURCES, SOURCE_MAP
from backend.models.response import SearchResponse
from backend.cache.ttl_cache import cache
from backend.config import settings

router = APIRouter()


def _cache_key(params: dict) -> str:
    serialized = json.dumps(params, sort_keys=True)
    return hashlib.md5(serialized.encode()).hexdigest()


@router.get("/search", response_model=SearchResponse)
async def search(
    q: Optional[str] = None,
    country: Optional[str] = None,
    sector: Optional[str] = None,
    source: Optional[str] = None,
    language: Optional[str] = None,
):
    query = q or ""
    filters = {k: v for k, v in {"country": country, "sector": sector}.items() if v}

    key = _cache_key({"q": query, "country": country, "sector": sector,
                       "source": source, "language": language})
    cached = cache.get(key)
    if cached is not None:
        return SearchResponse(
            query=query,
            total=len(cached),
            sources_hit=len({r.source_id for r in cached}),
            results=cached,
            cached=True,
        )

    # Select sources to query
    active_sources = SOURCES
    if source:
        active_sources = [s for s in SOURCES if s.id == source]
    if country:
        active_sources = [s for s in active_sources if s.country == country or s.country == "Global"]

    async def safe_search(src):
        try:
            return await src.search(query, filters)
        except Exception:
            return []

    results_nested = await asyncio.gather(*[safe_search(s) for s in active_sources])
    results = [tech for batch in results_nested for tech in batch]

    # Post-fetch language filter
    if language:
        results = [r for r in results if r.language.lower() == language.lower()]

    cache.set(key, results, ttl=settings.CACHE_TTL_SECONDS)

    return SearchResponse(
        query=query,
        total=len(results),
        sources_hit=len({r.source_id for r in results}),
        results=results,
        cached=False,
    )


# Temporary debug endpoint — remove before deploy
@router.get("/debug/ntb-raw")
async def debug_ntb_raw(q: str = "solar"):
    from urllib.parse import unquote
    from backend.config import settings
    import httpx

    params = {
        "serviceKey": unquote(settings.KOREA_NTB_API_KEY),
        "numOfRows": "3",
        "pageNo": "1",
        "techName": q,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(settings.KOREA_NTB_BASE_URL, params=params)
        return r.json()
