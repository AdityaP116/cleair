from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import datetime

from app.config import settings
from app.api.routes import (
    auth,
    air_quality,
    forecasts,
    profiles,
    recommendations,
    exposure,
    chat
)

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
        "environment": settings.ENV
    }

# Register all routes with standard prefixes
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}", tags=["Auth & Sessions"])
app.include_router(air_quality.router, prefix=f"{settings.API_V1_STR}/air", tags=["Air Quality"])
app.include_router(forecasts.router, prefix=f"{settings.API_V1_STR}/air", tags=["Forecasts"])
app.include_router(profiles.router, prefix=f"{settings.API_V1_STR}/profile", tags=["Profiles"])
app.include_router(recommendations.router, prefix=f"{settings.API_V1_STR}", tags=["Recommendations"])
app.include_router(exposure.router, prefix=f"{settings.API_V1_STR}", tags=["Exposure & Impact"])
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat", tags=["AI Assistant"])
