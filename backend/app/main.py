from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .api.routes import router
from .api.auth_routes import router as auth_router
from .api.import_routes import router as import_router
from .api.acs_routes import router as acs_router
from .api.remote_routes import router as remote_router
from .config import settings
from .database import async_session
from .services.auth import ensure_admin_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_session() as db:
        await ensure_admin_user(db)
    yield


app = FastAPI(
    title=settings.app_name,
    description="ACS Inteligente — coleta, normalização e diagnóstico automático de ONTs",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas públicas / ingestão
app.include_router(auth_router, prefix="/api/v1")
app.include_router(acs_router, prefix="/api/v1")

# Rotas protegidas JWT
app.include_router(router, prefix="/api/v1")
app.include_router(import_router, prefix="/api/v1")
app.include_router(remote_router, prefix="/api/v1")

_examples = Path(__file__).resolve().parent.parent / "examples"
if _examples.exists():
    app.mount("/examples", StaticFiles(directory=str(_examples)), name="examples")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "inspear-acs",
        "version": "0.3.0",
        "features": ["jwt", "csv-import", "genieacs", "remote-actions", "auto-sync"],
    }