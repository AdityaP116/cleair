from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import datetime
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse, Response, HTMLResponse, JSONResponse

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

# Sliding-window rate-limiting middleware (120 req/min per client IP)
from collections import defaultdict
import time
_rate_limit_store = defaultdict(list)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = _rate_limit_store[client_ip]
    _rate_limit_store[client_ip] = [t for t in window if now - t < 60]
    if len(_rate_limit_store[client_ip]) >= 120:
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again later."})
    _rate_limit_store[client_ip].append(now)
    return await call_next(request)

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

# Serve CLEAIR 2.0 Web Frontend
web_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "apps", "web"))
if os.path.exists(web_dir):
    app.mount("/static", StaticFiles(directory=web_dir), name="static")

    @app.get("/")
    def serve_frontend_index():
        return FileResponse(os.path.join(web_dir, "index.html"))

@app.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt():
    return "User-agent: *\nAllow: /\nSitemap: http://127.0.0.1:8000/sitemap.xml\n"

@app.get("/sitemap.xml")
def sitemap_xml():
    xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>http://127.0.0.1:8000/</loc></url></urlset>'
    return Response(content=xml, media_type="application/xml")

@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    if request.url.path.startswith("/v1/"):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return HTMLResponse(
        content="<!DOCTYPE html><html><head><title>404 — Cleair</title></head><body style='font-family:sans-serif;text-align:center;padding:60px;background:#F4F8F6;color:#102A26;'><h1>404 — Page Not Found</h1><p>The requested page does not exist.</p><a href='/' style='color:#0F766E;font-weight:bold;'>Return to Cleair Dashboard</a></body></html>",
        status_code=404
    )
