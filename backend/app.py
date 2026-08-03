import os
import pathlib
from dotenv import load_dotenv

_BACKEND_DIR = pathlib.Path(__file__).resolve().parent
load_dotenv(_BACKEND_DIR / ".env")
load_dotenv(_BACKEND_DIR / ".env.local", override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import traceback
from fastapi.responses import JSONResponse
from fastapi import Request

from core.database.models import init_db
from security.authentication.api import router as auth_router
from modules.consultation.api import router as consultation_router
from modules.voice.api import router as voice_router
from modules.voice.api_streaming import router as streaming_router
from modules.dashboard.api import router as telemetry_router
from modules.feedback.api import router as feedback_router
from modules.profile.api import router as profile_router
from providers.sarvam.voice_client import close_http_client

import asyncio

from core.logger.terminal import CommandCenter
import time

def global_async_exception_handler(loop, context):
    exc = context.get("exception")
    msg = exc or context.get("message")
    err = f"[GLOBAL ASYNC SHIELD] Caught unhandled exception: {msg}"
    CommandCenter.log_error(f"Async Error: {msg}", exc=exc if isinstance(exc, Exception) else None)
    with open("backend_errors.log", "a") as f:
        f.write(err + "\n")

@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(global_async_exception_handler)
    app.state.shutdown_event = asyncio.Event()
    
    with CommandCenter.create_progress() as progress:
        task1 = progress.add_task("[cyan]Initializing Core Backend...", total=100)
        task2 = progress.add_task("[magenta]Connecting to Database...", total=100)
        task3 = progress.add_task("[yellow]Validating Providers...", total=100)
        
        progress.update(task1, advance=50)
        
        # DB init
        for attempt in range(1, 6):
            try:
                init_db()
                CommandCenter.set_health("Database", "Healthy")
                progress.update(task2, completed=100)
                break
            except Exception as e:
                CommandCenter.log_error(f"DB Init Failed: {e}")
                progress.update(task2, advance=20)
                if attempt < 5:
                    await asyncio.sleep(1)
                else:
                    CommandCenter.set_health("Database", "Failed")

        progress.update(task3, advance=50)
        # Defer heavy model loading until first use to avoid startup worker bloat.
        CommandCenter.log_info("Deferred model loading for emotion detection until first request.")

        # If configured, build the RAG knowledge base in the background so the app can bind quickly.
        if os.getenv("RAG_AUTO_BUILD", "false").lower() in {"1", "true", "yes"}:
            try:
                from rag.knowledge.retriever import ensure_knowledge_base_ready, is_knowledge_base_ready
                if not is_knowledge_base_ready():
                    CommandCenter.log_info("RAG knowledge base missing. Starting background build.")
                    CommandCenter.set_health("Brain", "Starting")

                    async def background_rag_build():
                        success = await asyncio.to_thread(ensure_knowledge_base_ready, True)
                        CommandCenter.set_health("Brain", "Healthy" if success else "Failed")
                        CommandCenter.log_info("RAG background build completed." if success else "RAG background build failed.")

                    asyncio.create_task(background_rag_build())
                else:
                    CommandCenter.set_health("Brain", "Healthy")
            except Exception as e:
                CommandCenter.log_error(f"RAG background build setup failed: {e}")
                CommandCenter.set_health("Brain", "Failed")
        else:
            CommandCenter.set_health("Brain", "Healthy")

        # Assume providers are healthy for now
        CommandCenter.set_health("Firebase", "Healthy")
        CommandCenter.set_health("Sarvam", "Healthy")
        progress.update(task3, completed=100)
        
        progress.update(task1, completed=100)
        
    CommandCenter.set_health("API Server", "Healthy")
    CommandCenter.start_dashboard()
    
    yield
    
    CommandCenter.stop_dashboard()
    print("[SHUTDOWN] Signal received. Setting shutdown event...")
    app.state.shutdown_event.set()
    await close_http_client()
    await asyncio.sleep(0.2)
    print("[SHUTDOWN] Cleanup complete.")


app = FastAPI(
    title="MindBridge API",
    description="AI Mental Health Support — Voice + Text — Powered by Sarvam AI",
    version="3.0.0",
    lifespan=lifespan,
)

cors_origins_env = os.getenv("CORS_ORIGINS", "")
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
]
if cors_origins_env:
    allowed_origins.extend([o.strip() for o in cors_origins_env.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.onrender\.com|https://.*\.vercel\.app|http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.middleware.trustedhost import TrustedHostMiddleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "*.pinggy.link", "*.vercel.app", "*.onrender.com"])

from core.middleware.security import SecurityMiddleware
app.add_middleware(SecurityMiddleware, max_payload_bytes=10 * 1024 * 1024)

from core.middleware.audit import AuditLoggerMiddleware
app.add_middleware(AuditLoggerMiddleware)

@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start_time = time.time()
    CommandCenter.increment_active_requests(1)
    try:
        response = await call_next(request)
        duration = (time.time() - start_time) * 1000  # ms
        if request.url.path not in ["/", "/health", "/favicon.ico"]:
            try:
                CommandCenter.log_api(request.method, request.url.path, response.status_code, duration)
            except Exception as e:
                print(f"[LOG_API_ERR] {e}")
        return response
    except Exception as exc:
        duration = (time.time() - start_time) * 1000
        CommandCenter.log_error(f"Middleware uncaught exception: {exc}")
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error", "message": str(exc)})
    finally:
        CommandCenter.increment_active_requests(-1)


app.include_router(auth_router)
app.include_router(consultation_router)
app.include_router(voice_router)
app.include_router(streaming_router)
app.include_router(telemetry_router)
app.include_router(feedback_router)
app.include_router(profile_router)

from modules.feature_flags.api import router as features_router
app.include_router(features_router)


from core.exceptions import register_exception_handlers
register_exception_handlers(app)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi import Response
    return Response(status_code=204)

@app.api_route("/health", methods=["GET", "HEAD", "POST"], include_in_schema=False)
def health():
    return {
        "status": "ok",
        "service": "MindBridge",
        "version": "3.0.0",
        "features": ["text-chat", "voice-stt", "voice-tts", "rag", "emotion-detection"],
        "ai": "sarvam-105b + saarika + bulbul",
    }

@app.api_route("/ready", methods=["GET", "HEAD"], include_in_schema=False)
def readiness():
    unhealthy = [component for component, status in CommandCenter.health_status.items() if status != "Healthy"]
    if unhealthy:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "unhealthy_components": unhealthy,
                "health": CommandCenter.health_status,
            },
        )

    return {
        "status": "ready",
        "health": CommandCenter.health_status,
    }


@app.get("/up", include_in_schema=False)
def up():
    return {
        "status": "up",
        "service": "MindBridge API",
        "version": "3.0.0",
    }


@app.get("/")
def root():
    return {"message": "MindBridge API v3 running", "docs": "/docs"}


from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os

# Mount the static telemetry files
telemetry_dir = os.path.join(os.path.dirname(__file__), "modules", "telemetry_ui")
if os.path.exists(telemetry_dir):
    app.mount("/telemetry_ui", StaticFiles(directory=telemetry_dir, html=True), name="telemetry_ui")
