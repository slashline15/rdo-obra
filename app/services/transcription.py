"""
Serviço de transcrição de áudio (Whisper).
Suporta OpenAI Whisper API ou whisper.cpp local.
"""
import os
import httpx

from app.core.config import settings

WHISPER_BASE_URL = "https://api.openai.com/v1"
WHISPER_MODEL = "whisper-1"


async def transcribe_audio(audio_path: str, language: str = "pt") -> str:
    """Transcreve arquivo de áudio para texto usando Whisper."""

    api_key = settings.whisper_api_key or settings.openai_api_key
    if not api_key:
        raise RuntimeError("WHISPER_API_KEY ou OPENAI_API_KEY não configurada no .env")

    async with httpx.AsyncClient(timeout=60.0) as client:
        with open(audio_path, "rb") as audio_file:
            response = await client.post(
                f"{WHISPER_BASE_URL}/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (os.path.basename(audio_path), audio_file)},
                data={
                    "model": WHISPER_MODEL,
                    "language": language,
                    "response_format": "text"
                }
            )
            response.raise_for_status()

    return response.text.strip()
