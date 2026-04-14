"""
Configuração centralizada. Tudo vem de variáveis de ambiente / .env
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://rdo:rdo@localhost:5432/rdo_digital"
    redis_url: str = "redis://localhost:6379/0"

    # Ollama (LLM local)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    embedding_model: str = "qwen3-embedding:0.6b"

    # OpenAI
    openai_api_key: Optional[str] = None

    # Whisper (STT)
    whisper_mode: str = "local"  # local | api | groq
    whisper_model: str = "base"
    whisper_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None

    # Telegram
    telegram_bot_token: Optional[str] = None
    telegram_webhook_url: Optional[str] = None

    # WhatsApp (Evolution API)
    evolution_api_url: Optional[str] = None
    evolution_api_key: Optional[str] = None
    evolution_instance: Optional[str] = None  # legado; multi-instância usa WhatsAppInstancia

    # URL pública do backend — usada para registrar webhooks nas instâncias
    public_url: str = "https://rdo.engdaniel.org"

    # Storage
    upload_dir: str = "./uploads"
    output_dir: str = "./output"

    # Conversational state / semantic search
    state_ttl_hours_whatsapp: int = 48
    state_ttl_hours_telegram: int = 24
    state_ttl_hours_default: int = 24
    semantic_match_threshold: float = 0.80
    semantic_match_margin: float = 0.05
    embedding_dimensions: int = 1024

    # JWT Auth
    jwt_secret: str = "rdo-digital-secret-change-in-production"
    legacy_bootstrap_token: Optional[str] = None
    invite_token_ttl_hours: int = 72

    # App
    app_name: str = "RDO Digital"
    app_version: str = "0.2.0"
    debug: bool = False
    tz: str = "America/Manaus"

    model_config = {
        "env_file": ".env",
        "extra": "allow"
    }


settings = Settings()
