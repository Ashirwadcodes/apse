from fastapi import APIRouter
from backend.sources.registry import SOURCES
from backend.models.technology import Source

router = APIRouter()


@router.get("/sources", response_model=list[Source])
def get_sources():
    return [s.to_source_model() for s in SOURCES]


@router.get("/facets")
def get_facets():
    """Transfer type values as actually used across the registered sources,
    for the Transfer Type filter. Sources with no fixed transfer_type
    (e.g. Korea NTB, whose value varies per record) are excluded."""
    transfer_types = sorted({s.transfer_type for s in SOURCES if s.transfer_type})
    return {"transfer_types": transfer_types}
