import asyncio
import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.database import init_db
from app.routes import (
    empresas, obras, usuarios, servicos, efetivo,
    anotacoes, materiais, equipamentos, clima, fotos,
    rdo, telegram_webhook, whatsapp_webhook
)
from app.routes import auth as auth_routes
from app.routes import painel as painel_routes
from app.routes import diario as diario_routes
from app.routes import alertas as alertas_routes
from app.routes import auditoria as auditoria_routes
from app.routes import dashboard as dashboard_routes

app = FastAPI(
    title=settings.app_name,
    description="Diário de Obra por Voz — Registre ocorrências via WhatsApp/Telegram",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Auth (sem prefixo /api para o tokenUrl funcionar direto) ---
app.include_router(auth_routes.router, prefix="/api")

# --- API routes (prefixo /api/) ---
app.include_router(painel_routes.router, prefix="/api")
app.include_router(diario_routes.router, prefix="/api")
app.include_router(alertas_routes.router, prefix="/api")
app.include_router(auditoria_routes.router, prefix="/api")
app.include_router(dashboard_routes.router, prefix="/api")

# CRUD routes
app.include_router(empresas.router, prefix="/api")
app.include_router(obras.router, prefix="/api")
app.include_router(usuarios.router, prefix="/api")
app.include_router(servicos.router, prefix="/api")
app.include_router(efetivo.router, prefix="/api")
app.include_router(anotacoes.router, prefix="/api")
app.include_router(materiais.router, prefix="/api")
app.include_router(equipamentos.router, prefix="/api")
app.include_router(clima.router, prefix="/api")
app.include_router(fotos.router, prefix="/api")
app.include_router(rdo.router, prefix="/api")

# Webhook routes (sem /api — são endpoints públicos para bots)
app.include_router(telegram_webhook.router)
app.include_router(whatsapp_webhook.router)


@app.on_event("startup")
async def startup():
    init_db()
    _check_required_settings()
    asyncio.create_task(_expire_states_loop())


async def _expire_states_loop():
    """Loop que executa a expiração de estados a cada 15 minutos."""
    from app.tasks.expire_states import run_expire_states
    while True:
        try:
            await run_expire_states()
        except Exception as e:
            logging.getLogger("rdo.expire_states").exception(
                "Error in expire_states loop: %s", e
            )
        await asyncio.sleep(900)  # 15 minutos


def _check_required_settings():
    log = logging.getLogger("rdo.startup")
    warns = []
    if not settings.telegram_bot_token:
        warns.append("TELEGRAM_BOT_TOKEN não configurado — bot Telegram inativo")
    if not (settings.whisper_api_key or settings.openai_api_key):
        warns.append("OPENAI_API_KEY / WHISPER_API_KEY não configurados — transcrição de áudio inativa")
    for w in warns:
        log.warning("⚠️  %s", w)
    if not warns:
        log.info("✅ Configuração OK")


@app.get("/api/status")
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# --- SPA fallback: serve frontend se existir ---
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="static-assets")

    # Arquivos estáticos raiz (favicon, icons, etc.)
    _STATIC_ROOT_FILES = {"favicon.svg", "icons.svg"}

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        # Não intercepta rotas da API, docs, ou webhooks
        if full_path.startswith(("api/", "docs", "redoc", "openapi", "health")):
            raise HTTPException(404)
        # Arquivos estáticos da raiz
        if full_path in _STATIC_ROOT_FILES:
            f = os.path.join(STATIC_DIR, full_path)
            if os.path.isfile(f):
                return FileResponse(f)
        # SPA — tudo o mais serve o index.html
        index = os.path.join(STATIC_DIR, "index.html")
        if os.path.isfile(index):
            return FileResponse(index)
        raise HTTPException(404)
