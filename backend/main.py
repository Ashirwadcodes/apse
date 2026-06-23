import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import search, sources
from backend.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="APSE Technology Gateway API",
    description="Federated search across Asia-Pacific technology transfer databases",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(search.router, prefix="/api/v1")
app.include_router(sources.router, prefix="/api/v1")


@app.on_event("startup")
def _preload_static_sources():
    from backend.sources.registry import SOURCE_MAP
    csir = SOURCE_MAP.get("csir_india")
    if csir:
        csir._load()


@app.get("/health")
def health():
    return {"status": "ok"}


