from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import search, sources
from backend.config import settings

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
    import httpx, traceback
    result = {"client_id_set": bool(settings.IP_AUSTRALIA_CLIENT_ID), "steps": []}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://test.api.ipaustralia.gov.au/public/external-token-api/v1/access_token",
                data={"grant_type": "client_credentials"},
                auth=(settings.IP_AUSTRALIA_CLIENT_ID, settings.IP_AUSTRALIA_CLIENT_SECRET),
            )
        result["token_status"] = r.status_code
        result["token_body"] = r.text[:300]
        if r.status_code == 200:
            token = r.json()["access_token"]
            result["steps"].append("token_ok")
            async with httpx.AsyncClient(timeout=15) as client:
                r2 = await client.post(
                    "https://test.api.ipaustralia.gov.au/public/australian-patent-search-api/v1/search/quick",
                    json={"query": "solar", "searchType": "DETAILS", "pageSize": 3, "pageNumber": 0},
                    headers={"Authorization": f"Bearer {token}"},
                )
            result["search_status"] = r2.status_code
            result["search_body"] = r2.text[:500]
    except Exception:
        result["error"] = traceback.format_exc()
    return result
