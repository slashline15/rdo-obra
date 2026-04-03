from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database import init_db
from app.routes import (
    empresas, obras, usuarios, servicos, efetivo,
    anotacoes, materiais, equipamentos, clima, fotos,
    rdo, telegram_webhook, whatsapp_webhook
)

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

# CRUD routes
app.include_router(empresas.router)
app.include_router(obras.router)
app.include_router(usuarios.router)
app.include_router(servicos.router)
app.include_router(efetivo.router)
app.include_router(anotacoes.router)
app.include_router(materiais.router)
app.include_router(equipamentos.router)
app.include_router(clima.router)
app.include_router(fotos.router)
app.include_router(rdo.router)

# Webhook routes
app.include_router(telegram_webhook.router)
app.include_router(whatsapp_webhook.router)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
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
