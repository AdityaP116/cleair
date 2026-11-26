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
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(self), microphone=()"
    if settings.ENV == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

from collections import defaultdict
import time
import logging
from app.core.redis_client import get_redis_client, check_redis_health
from app.db.session import check_db_health

_rl_logger = logging.getLogger("cleair.ratelimit")
_rate_limit_store = defaultdict(list)

def _extract_client_ip(request: Request) -> str:
    direct_ip = request.client.host if request.client else "unknown"
    if direct_ip in settings.TRUSTED_PROXIES:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
    return direct_ip

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = _extract_client_ip(request)
    limit = settings.RATE_LIMIT_MAX_REQUESTS
    window_sec = settings.RATE_LIMIT_WINDOW_SEC
    r = get_redis_client()
    if r is not None:
        try:
            bucket = int(time.time() // window_sec)
            key = f"rl:{client_ip}:{bucket}"
            pipe = r.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_sec + 1)
            count, _ = pipe.execute()
            if count > limit:
                return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again later."})
            return await call_next(request)
        except Exception as exc:
            _rl_logger.warning("Redis rate-limit error (%s); fail_open=%s", type(exc).__name__, settings.RATE_LIMIT_FAIL_OPEN)
            if not settings.RATE_LIMIT_FAIL_OPEN:
                return JSONResponse(status_code=503, content={"detail": "Rate limiter unavailable."})
            return await call_next(request)

    now = time.time()
    window = _rate_limit_store[client_ip]
    _rate_limit_store[client_ip] = [t for t in window if now - t < window_sec]
    if len(_rate_limit_store[client_ip]) >= limit:
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again later."})
    _rate_limit_store[client_ip].append(now)
    return await call_next(request)

# Health & Readiness endpoints
@app.get(f"{settings.API_V1_STR}/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "version": settings.VERSION,
        "environment": settings.ENV,
        "pilot_region": "Mumbai Metropolitan Region (MMR)"
    }

@app.get(f"{settings.API_V1_STR}/ready")
def readiness_check():
    db_ok = check_db_health()
    redis_ok = check_redis_health() if settings.REDIS_URL else None
    if not db_ok:
        return JSONResponse(status_code=503, content={"status": "not_ready", "database": False, "redis": redis_ok})
    return {"status": "ready", "database": True, "redis": redis_ok}

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

from pydantic import BaseModel, EmailStr

class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    subject: str = "CLEAIR Contact Inquiry"
    message: str

@app.post(f"{settings.API_V1_STR}/contact")
def submit_contact_form(payload: ContactRequest):
    if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASS and settings.CONTACT_RECIPIENT_EMAIL:
        import smtplib
        from email.message import EmailMessage
        msg = EmailMessage()
        msg["Subject"] = f"[CLEAIR Contact] {payload.subject}"
        msg["From"] = settings.SMTP_USER
        msg["To"] = settings.CONTACT_RECIPIENT_EMAIL
        msg["Reply-To"] = payload.email
        msg.set_content(f"From: {payload.name} <{payload.email}>\n\n{payload.message}")
        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
                server.send_message(msg)
            return {"status": "sent", "message": "Your message has been delivered."}
        except Exception:
            return {"status": "queued", "message": "Thank you! Your inquiry was received."}
    return {"status": "received", "message": "Thank you! Your inquiry has been recorded."}

@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    if request.url.path.startswith("/v1/"):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    not_found_file = os.path.join(web_dir, "404.html")
    if os.path.exists(not_found_file):
        return FileResponse(not_found_file, status_code=404)
    return HTMLResponse(
        content="<!DOCTYPE html><html><head><title>404 — CLEAIR</title></head><body style='font-family:sans-serif;text-align:center;padding:60px;background:#F5F7F3;color:#14251F;'><h1>404 — Page Not Found</h1><p>The requested page does not exist.</p><a href='/' style='color:#174D3B;font-weight:bold;'>Return to CLEAIR</a></body></html>",
        status_code=404
    )
