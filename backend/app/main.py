from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import cost, regressions, telemetry, traces

app = FastAPI(title="AgentTrace API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (traces.router, cost.router, regressions.router, telemetry.router):
    app.include_router(router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
