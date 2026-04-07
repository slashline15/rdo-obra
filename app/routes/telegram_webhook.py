"""Webhook route para Telegram Bot API."""
from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.adapters.telegram import TelegramAdapter
from app.core.orchestrator import Orchestrator
from app.core.time import utc_now
from app.core.types import Canal, OutgoingMessage
from app.models import Obra, SolicitacaoCadastro, Usuario

router = APIRouter(prefix="/telegram", tags=["Telegram"])

_cadastros_pendentes: dict[str, dict] = {}
_TTL_SOLICITACAO = timedelta(hours=24)


def _nome_solicitante(message: dict) -> str:
    """Monta nome amigável a partir do payload do Telegram."""
    user = message.get("from", {}) or {}
    primeiro = (user.get("first_name") or "").strip()
    ultimo = (user.get("last_name") or "").strip()
    username = (user.get("username") or "").strip()
    nome = f"{primeiro} {ultimo}".strip()
    if nome:
        return nome
    if username:
        return f"@{username}"
    return "Usuário Telegram"


def _limpar_solicitacoes_expiradas():
    """Remove solicitações antigas para evitar acúmulo em memória."""
    agora = utc_now()
    expiradas = [
        chat_id for chat_id, dados in _cadastros_pendentes.items()
        if agora - dados.get("created_at", agora) > _TTL_SOLICITACAO
    ]
    for chat_id in expiradas:
        _cadastros_pendentes.pop(chat_id, None)


def _extrair_obra_id(callback_data: str) -> int | None:
    try:
        _, _, obra_id = callback_data.split(":", 2)
        return int(obra_id)
    except (ValueError, IndexError):
        return None


async def _solicitar_aprovacao_cadastro(adapter: TelegramAdapter, db: Session, message: dict, chat_id: str):
    """Cria solicitação de cadastro e notifica admins da(s) obra(s)."""
    _limpar_solicitacoes_expiradas()
    nome = _nome_solicitante(message)
    _cadastros_pendentes[chat_id] = {
        "chat_id": chat_id,
        "nome": nome,
        "username": (message.get("from", {}) or {}).get("username"),
        "created_at": utc_now()
    }

    obras_com_admin = db.query(Obra).filter(Obra.usuario_admin.isnot(None)).all()
    if not obras_com_admin:
        await adapter.send_message_raw(chat_id, "⚠️ Não há obra com administrador configurado. Solicite cadastro ao suporte.")
        return

    notificou = False
    for obra in obras_com_admin:
        admin = db.query(Usuario).filter(Usuario.id == obra.usuario_admin).first()
        if not admin or not admin.telefone:
            continue

        notificou = True
        texto = (
            f"📥 Solicitação de cadastro\n"
            f"Obra: <b>{obra.nome}</b> (ID {obra.id})\n"
            f"Nome informado: {nome}\n"
            f"Chat ID: <code>{chat_id}</code>\n\n"
            f"Deseja aprovar este usuário para a obra?"
        )
        await adapter.send_message(OutgoingMessage(
            texto=texto,
            canal=Canal.TELEGRAM,
            telefone=admin.telefone,
            botoes=[
                {"text": "✅ Aprovar", "data": f"cadastro_aprovar:{chat_id}:{obra.id}"},
                {"text": "❌ Rejeitar", "data": f"cadastro_rejeitar:{chat_id}:{obra.id}"}
            ]
        ))

    if notificou:
        await adapter.send_message_raw(
            chat_id,
            "⏳ Seu cadastro foi enviado para aprovação do responsável técnico. Você receberá retorno aqui."
        )
    else:
        await adapter.send_message_raw(chat_id, "⚠️ Não foi possível localizar admin ativo para aprovação.")


def _nome_solicitante(message: dict) -> str:
    """Monta nome amigável a partir do payload do Telegram."""
    user = message.get("from", {}) or {}
    primeiro = (user.get("first_name") or "").strip()
    ultimo = (user.get("last_name") or "").strip()
    username = (user.get("username") or "").strip()
    nome = f"{primeiro} {ultimo}".strip()
    if nome:
        return nome
    if username:
        return f"@{username}"
    return "Usuário Telegram"


def _extrair_request_id(callback_data: str) -> int | None:
    try:
        return int(callback_data.split(":", 1)[1])
    except (ValueError, IndexError):
        return None


async def _solicitar_aprovacao_cadastro(adapter: TelegramAdapter, db: Session, message: dict, chat_id: str):
    """Cria solicitação de cadastro e notifica admins da(s) obra(s)."""
    nome = _nome_solicitante(message)
    username = (message.get("from", {}) or {}).get("username")

    obras_com_admin = db.query(Obra).filter(Obra.usuario_admin.isnot(None)).all()
    if not obras_com_admin:
        await adapter.send_message_raw(chat_id, "⚠️ Não há obra com administrador configurado. Solicite cadastro ao suporte.")
        return

    notificou = False
    for obra in obras_com_admin:
        admin = db.query(Usuario).filter(Usuario.id == obra.usuario_admin).first()
        if not admin or not admin.telefone:
            continue

        solicitacao = db.query(SolicitacaoCadastro).filter(
            SolicitacaoCadastro.obra_id == obra.id,
            SolicitacaoCadastro.solicitante_chat_id == chat_id,
            SolicitacaoCadastro.status == "pendente"
        ).first()

        if not solicitacao:
            solicitacao = SolicitacaoCadastro(
                obra_id=obra.id,
                solicitante_chat_id=chat_id,
                solicitante_nome=nome[:255],
                solicitante_username=username,
                status="pendente"
            )
            db.add(solicitacao)
            db.flush()

        notificou = True
        texto = (
            f"📥 Solicitação de cadastro\n"
            f"Obra: <b>{obra.nome}</b> (ID {obra.id})\n"
            f"Nome informado: {nome}\n"
            f"Chat ID: <code>{chat_id}</code>\n\n"
            f"Deseja aprovar este usuário para a obra?"
        )
        await adapter.send_message(OutgoingMessage(
            texto=texto,
            canal=Canal.TELEGRAM,
            telefone=admin.telefone,
            botoes=[
                {"text": "✅ Aprovar", "data": f"cadastro_aprovar:{solicitacao.id}"},
                {"text": "❌ Rejeitar", "data": f"cadastro_rejeitar:{solicitacao.id}"}
            ]
        ))

    db.commit()

    if notificou:
        await adapter.send_message_raw(
            chat_id,
            "⏳ Seu cadastro foi enviado para aprovação do responsável técnico. Você receberá retorno aqui."
        )
    else:
        await adapter.send_message_raw(chat_id, "⚠️ Não foi possível localizar admin ativo para aprovação.")


@router.post("/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """Recebe updates do Telegram Bot API."""
    raw_data = await request.json()
    adapter = TelegramAdapter()

    # ─── Callback query (botão inline pressionado) ───
    if "callback_query" in raw_data:
        callback = raw_data["callback_query"]
        chat_id = str(callback["message"]["chat"]["id"])
        callback_data = callback.get("data", "")
        callback_id = callback["id"]

        # Responder o callback (tira o "loading" do botão)
        await adapter.answer_callback(callback_id)

        if callback_data == "cancelar":
            await adapter.send_message_raw(chat_id, "❌ Cancelado.")
            return {"ok": True}

        if callback_data.startswith("cadastro_aprovar:") or callback_data.startswith("cadastro_rejeitar:"):
            user = db.query(Usuario).filter(Usuario.telefone == chat_id).first()
            if not user:
                await adapter.send_message_raw(chat_id, "❌ Somente usuários cadastrados podem aprovar solicitações.")
                return {"ok": True}

            request_id = _extrair_request_id(callback_data)
            solicitacao = db.query(SolicitacaoCadastro).filter(SolicitacaoCadastro.id == request_id).first() if request_id else None
            if not solicitacao:
                await adapter.send_message_raw(chat_id, "⚠️ Solicitação não encontrada.")
                return {"ok": True}

            obra = db.query(Obra).filter(Obra.id == solicitacao.obra_id).first()
            if not obra or obra.usuario_admin != user.id:
                await adapter.send_message_raw(chat_id, "❌ Você não tem permissão para esta aprovação.")
                return {"ok": True}

            if solicitacao.status != "pendente":
                await adapter.send_message_raw(chat_id, f"⚠️ Solicitação já foi {solicitacao.status}.")
                return {"ok": True}

            solicitante_chat_id = solicitacao.solicitante_chat_id
            nome_solicitante = solicitacao.solicitante_nome or f"Usuário {solicitante_chat_id}"

            if callback_data.startswith("cadastro_aprovar:"):
                existente = db.query(Usuario).filter(Usuario.telefone == solicitante_chat_id).first()
                if existente:
                    existente.obra_id = obra.id
                    existente.canal_preferido = "telegram"
                    existente.ativo = True
                    novo = False
                else:
                    db.add(Usuario(
                        nome=nome_solicitante[:255],
                        telefone=solicitante_chat_id,
                        obra_id=obra.id,
                        role="estagiario",
                        ativo=True,
                        canal_preferido="telegram",
                    ))
                    novo = True

                solicitacao.status = "aprovado"
                solicitacao.admin_decisor_id = user.id

                outras = db.query(SolicitacaoCadastro).filter(
                    SolicitacaoCadastro.solicitante_chat_id == solicitante_chat_id,
                    SolicitacaoCadastro.id != solicitacao.id,
                    SolicitacaoCadastro.status == "pendente"
                ).all()
                for req in outras:
                    req.status = "rejeitado"
                    req.observacao = "Encerrada automaticamente após aprovação em outra obra."

                db.commit()
                await adapter.send_message_raw(
                    solicitante_chat_id,
                    f"✅ Cadastro aprovado para a obra <b>{obra.nome}</b>. Você já pode enviar registros."
                )
                acao = "cadastrado" if novo else "atualizado"
                await adapter.send_message_raw(chat_id, f"✅ Usuário {nome_solicitante} {acao} com sucesso.")
            else:
                solicitacao.status = "rejeitado"
                solicitacao.admin_decisor_id = user.id
                db.commit()

                ainda_pendente = db.query(SolicitacaoCadastro).filter(
                    SolicitacaoCadastro.solicitante_chat_id == solicitante_chat_id,
                    SolicitacaoCadastro.status == "pendente"
                ).first()

                contato_admin = user.nome or "administrador"
                if not ainda_pendente:
                    await adapter.send_message_raw(
                        solicitante_chat_id,
                        f"❌ Cadastro não aprovado. Procure o responsável técnico da obra ({contato_admin})."
                    )
                await adapter.send_message_raw(chat_id, f"🚫 Solicitação de {nome_solicitante} rejeitada.")

            return {"ok": True}

        # Identificar usuário
        user = db.query(Usuario).filter(Usuario.telefone == chat_id).first()
        if not user or not user.obra_id:
            await adapter.send_message_raw(chat_id, "❌ Usuário não cadastrado.")
            return {"ok": True}

        orchestrator = Orchestrator(db)
        resposta = await orchestrator.processar_callback(callback_data, chat_id, user.nome, user.obra_id)
        await adapter.send_message_raw(chat_id, resposta)
        return {"ok": True}

    # ─── Mensagem normal ───
    if "message" not in raw_data:
        return {"ok": True}

    message = raw_data.get("message", {})
    text = message.get("text", "")
    chat_id = str(message.get("chat", {}).get("id", ""))

    if text.strip() == "/start":
        user = db.query(Usuario).filter(Usuario.telefone == chat_id).first()
        if user:
            await adapter.send_message_raw(chat_id, f"✅ Já cadastrado como {user.nome}.")
        else:
            await _solicitar_aprovacao_cadastro(adapter, db, message, chat_id)
        return {"ok": True}

    # Mensagem de usuário não cadastrado: abre solicitação para admin
    user = db.query(Usuario).filter(Usuario.telefone == chat_id).first()
    if not user:
        await _solicitar_aprovacao_cadastro(adapter, db, message, chat_id)
        return {"ok": True}

    # Parsear e processar
    msg = await adapter.parse_incoming(raw_data)
    orchestrator = Orchestrator(db)
    resposta = await orchestrator.processar(msg)
    await adapter.send_message(resposta)

    return {"ok": True}
