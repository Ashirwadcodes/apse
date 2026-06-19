import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import search, sources
from backend.config import settings

logging.basicConfig(level=logging.INFO)

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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/debug/ip-australia")
async def debug_ip_australia():
    import traceback
    from backend.sources.registry import SOURCE_MAP
    result = {"client_id_set": bool(settings.IP_AUSTRALIA_CLIENT_ID)}
    try:
        src = SOURCE_MAP.get("ip_australia")
        if not src:
            result["error"] = "ip_australia not in SOURCE_MAP"
            return result
        result["source_found"] = True
        items, total = await src.search("solar", {})
        result["items_returned"] = len(items)
        result["total"] = total
        result["first_title"] = items[0].title if items else None
    except Exception:
        result["error"] = traceback.format_exc()
    return result
