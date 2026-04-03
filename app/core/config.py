"""
Configuração centralizada. Tudo vem de variáveis de ambiente / .env
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://rdo:rdo@localhost:5432/rdo_digital"

    # Ollama (LLM local)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"

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
    evolution_instance: Optional[str] = None

    # Storage
    upload_dir: str = "./uploads"
    output_dir: str = "./output"

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
