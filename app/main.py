from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import engine, Base
from app.routes import auth, profile, check
from app.middleware.rate_limiter import limiter, rate_limit_handler as rl_handler
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from app.middleware.security_headers import SecurityHeadersMiddleware
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Иностатус API",
    description="API для проверки текста на совпадения с реестрами госорганов",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(SecurityHeadersMiddleware)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return await rl_handler(request, exc)

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0",
    }

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(check.router)

@app.get("/", tags=["Root"])
async def root():
    return {
        "name": "Иностатус API",
        "description": "API для проверки текста на совпадения с реестрами госорганов",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }
