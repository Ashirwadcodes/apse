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
    page: int = 1,
):
    query = q or ""
    filters = {k: v for k, v in {"country": country, "sector": sector, "page": page}.items() if v}

    key = _cache_key({"q": query, "country": country, "sector": sector,
                       "source": source, "language": language, "page": page})
    cached = cache.get(key)
    if cached is not None:
        results, source_totals = cached
        return SearchResponse(
            query=query,
            total=len(results),
            sources_hit=len({r.source_id for r in results}),
            results=results,
            cached=True,
            source_totals=source_totals,
        )

    active_sources = SOURCES
    if source:
        active_sources = [s for s in SOURCES if s.id == source]
    if country:
        active_sources = [s for s in active_sources if s.country == country or s.country == "Global"]

    async def safe_search(src):
        try:
            return src.id, await asyncio.wait_for(src.search(query, filters), timeout=10.0)
        except Exception:
            return src.id, ([], 0)

    raw = await asyncio.gather(*[safe_search(s) for s in active_sources])

    results = []
    source_totals = {}
    for src_id, (items, total_count) in raw:
        results.extend(items)
        if total_count > 0:
            source_totals[src_id] = total_count

    if language:
        results = [r for r in results if r.language.lower() == language.lower()]

    cache.set(key, (results, source_totals), ttl=settings.CACHE_TTL_SECONDS)

    return SearchResponse(
        query=query,
        total=len(results),
        sources_hit=len({r.source_id for r in results}),
        results=results,
        cached=False,
        source_totals=source_totals,
    )
