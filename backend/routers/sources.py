from fastapi import APIRouter
from backend.sources.registry import SOURCES
from backend.models.technology import Source

router = APIRouter()


@router.get("/sources", response_model=list[Source])
def get_sources():
    return [s.to_source_model() for s in SOURCES]


@router.get("/facets")
def get_facets():
    """Distinct filter values scraped from every locally-loaded source's actual
    records, instead of a fixed generic bucket list that may not match the
    real sector strings each database uses."""
    sectors: set[str] = set()
    for src in SOURCES:
        load = getattr(src, "_load", None)
        records = getattr(src, "_records", None)
        if load is None or records is None:
            continue  # external/live sources (NTB, IP Australia) have no local records to scan
        load()
        for rec in records:
            sector = (rec.get("sector") or "").strip()
            if sector:
                sectors.add(sector)

    return {"sectors": sorted(sectors)}
