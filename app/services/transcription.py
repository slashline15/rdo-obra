"""
Serviço de transcrição de áudio (Whisper).
Suporta OpenAI Whisper API ou whisper.cpp local.
"""
import os
import httpx

WHISPER_BASE_URL = os.getenv("WHISPER_BASE_URL", "https://api.openai.com/v1")
WHISPER_API_KEY = os.getenv("WHISPER_API_KEY", os.getenv("OPENAI_API_KEY", ""))
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-1")


async def transcribe_audio(audio_path: str, language: str = "pt") -> str:
    """Transcreve arquivo de áudio para texto usando Whisper."""

    async with httpx.AsyncClient(timeout=60.0) as client:
        with open(audio_path, "rb") as audio_file:
            response = await client.post(
                f"{WHISPER_BASE_URL}/audio/transcriptions",
                headers={"Authorization": f"Bearer {WHISPER_API_KEY}"},
                files={"file": (os.path.basename(audio_path), audio_file)},
                data={
                    "model": WHISPER_MODEL,
                    "language": language,
                    "response_format": "text"
                }
            )
            response.raise_for_status()

    return response.text.strip()
