from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import datetime
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.db.base import Base
from app.db.session import engine
from app.api.routes import (
    auth,
    air_quality,
    forecasts,
    profiles,
    recommendations,
    exposure,
    chat,
    telemetry,
    facilities,
    alerts,
    work_orders,
    reports
)

# Auto-create tables for local development database
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoint
@app.get(f"{settings.API_V1_STR}/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "version": settings.VERSION,
        "environment": settings.ENV,
        "pilot_region": "Mumbai Metropolitan Region (MMR)"
    }

# Register B2C and Core routes
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}", tags=["Auth & Sessions"])
app.include_router(air_quality.router, prefix=f"{settings.API_V1_STR}/air", tags=["Air Quality"])
app.include_router(forecasts.router, prefix=f"{settings.API_V1_STR}/air", tags=["Forecasts"])
app.include_router(profiles.router, prefix=f"{settings.API_V1_STR}/profile", tags=["Profiles"])
app.include_router(recommendations.router, prefix=f"{settings.API_V1_STR}", tags=["Recommendations"])
app.include_router(exposure.router, prefix=f"{settings.API_V1_STR}", tags=["Exposure & Impact"])
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat", tags=["AI Assistant"])

# Register Phase 2 Institutional Telemetry & Facility routes
app.include_router(telemetry.router, prefix=f"{settings.API_V1_STR}/telemetry", tags=["IoT Ingestion & Telemetry"])
app.include_router(facilities.router, prefix=f"{settings.API_V1_STR}/facilities", tags=["Institutional Facilities & Zones"])
app.include_router(alerts.router, prefix=f"{settings.API_V1_STR}/alerts", tags=["Operational Alerts"])
app.include_router(work_orders.router, prefix=f"{settings.API_V1_STR}", tags=["Work Orders & Interventions"])
app.include_router(reports.router, prefix=f"{settings.API_V1_STR}", tags=["Institutional Reports & Compliance"])

# Serve Web Frontend PWA from root
web_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "apps", "web"))
if os.path.exists(web_dir):
    app.mount("/static", StaticFiles(directory=web_dir), name="static")

    @app.get("/")
    def serve_frontend_index():
        return FileResponse(os.path.join(web_dir, "index.html"))

    @app.get("/app.js")
    def serve_frontend_js():
        return FileResponse(os.path.join(web_dir, "app.js"))
