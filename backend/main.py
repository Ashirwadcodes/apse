from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import search, sources

app = FastAPI(
    title="APCTT Technology Gateway API",
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
