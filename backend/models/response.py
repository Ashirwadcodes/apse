from pydantic import BaseModel
from backend.models.technology import Technology


class SearchResponse(BaseModel):
    query: str
    total: int
    sources_hit: int
    results: list[Technology]
    cached: bool
    source_totals: dict[str, int] = {}
