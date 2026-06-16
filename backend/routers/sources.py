from fastapi import APIRouter
from backend.sources.registry import SOURCES
from backend.models.technology import Source

router = APIRouter()


@router.get("/sources", response_model=list[Source])
def get_sources():
    return [s.to_source_model() for s in SOURCES]
