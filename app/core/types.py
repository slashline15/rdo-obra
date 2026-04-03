"""
Tipos base compartilhados entre todos os módulos.
Qualquer mensagem de qualquer canal é normalizada para IncomingMessage.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Literal
from enum import Enum


class Canal(str, Enum):
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    WEB = "web"
    API = "api"


class TipoMensagem(str, Enum):
    TEXTO = "texto"
    AUDIO = "audio"
    FOTO = "foto"
    DOCUMENTO = "documento"
    LOCALIZACAO = "localizacao"


class IncomingMessage(BaseModel):
    """Formato interno normalizado. Todo adapter converte pra isso."""
    canal: Canal
    telefone: str
    tipo: TipoMensagem = TipoMensagem.TEXTO
    texto: Optional[str] = None
    audio_path: Optional[str] = None
    foto_path: Optional[str] = None
    legenda: Optional[str] = None
    timestamp: datetime = datetime.utcnow()
    raw_data: Optional[dict] = None  # dados brutos do canal, se precisar


class OutgoingMessage(BaseModel):
    """Resposta normalizada. Adapter converte pro formato do canal."""
    texto: str
    canal: Canal
    telefone: str
    tipo: Literal["texto", "foto", "documento", "botoes"] = "texto"
    arquivo_path: Optional[str] = None
    botoes: Optional[list] = None  # para Telegram inline buttons
    reply_markup: Optional[dict] = None


class IntentType(str, Enum):
    ATIVIDADE = "atividade"
    EFETIVO = "efetivo"
    MATERIAL = "material"
    EQUIPAMENTO = "equipamento"
    CLIMA = "clima"
    ANOTACAO = "anotacao"
    FOTO = "foto"
    CONSULTA = "consulta"
    CONCLUSAO = "conclusao"  # finalizar atividade
    DESCONHECIDO = "desconhecido"


class IntentResult(BaseModel):
    """Resultado da classificação de intenção."""
    intent: IntentType
    confidence: float
    data: dict
    original_text: str
    requires_confirmation: bool = False
    confirmation_message: Optional[str] = None


class AtividadeStatus(str, Enum):
    INICIADA = "iniciada"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"
    PAUSADA = "pausada"
    CANCELADA = "cancelada"
