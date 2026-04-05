import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import Base, get_db
from app.models import Obra, SolicitacaoCadastro, Usuario
from app.routes import telegram_webhook


class FakeTelegramAdapter:
    sent_messages = []
    sent_raw = []
    callbacks = []

    def __init__(self):
        pass

    async def answer_callback(self, callback_query_id: str):
        self.callbacks.append(callback_query_id)
        return True

    async def send_message(self, msg):
        self.sent_messages.append(msg)
        return True

    async def send_message_raw(self, chat_id: str, text: str):
        self.sent_raw.append((str(chat_id), text))
        return True

    @classmethod
    def reset(cls):
        cls.sent_messages = []
        cls.sent_raw = []
        cls.callbacks = []


def _build_client_and_session(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()

    app = FastAPI()
    app.include_router(telegram_webhook.router)

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(telegram_webhook, "TelegramAdapter", FakeTelegramAdapter)

    return TestClient(app), db


def _seed_admin(db):
    admin = Usuario(nome="Admin Obra", telefone="999", role="admin", ativo=True, canal_preferido="telegram")
    db.add(admin)
    db.flush()

    obra = Obra(nome="Obra A", usuario_admin=admin.id)
    db.add(obra)
    db.flush()

    admin.obra_id = obra.id
    db.commit()
    return admin, obra


def test_start_cria_solicitacao_e_notifica_admin(monkeypatch):
    FakeTelegramAdapter.reset()
    client, db = _build_client_and_session(monkeypatch)
    _seed_admin(db)

    resp = client.post(
        "/telegram/webhook",
        json={
            "message": {
                "text": "/start",
                "chat": {"id": 123},
                "from": {"first_name": "João", "username": "joao"},
            }
        },
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    solicitacoes = db.query(SolicitacaoCadastro).all()
    assert len(solicitacoes) == 1
    assert solicitacoes[0].solicitante_chat_id == "123"
    assert solicitacoes[0].status == "pendente"

    assert len(FakeTelegramAdapter.sent_messages) == 1
    assert FakeTelegramAdapter.sent_messages[0].telefone == "999"
    assert FakeTelegramAdapter.sent_messages[0].botoes[0]["data"].startswith("cadastro_aprovar:")


def test_start_repetido_nao_duplica_solicitacao_pendente(monkeypatch):
    FakeTelegramAdapter.reset()
    client, db = _build_client_and_session(monkeypatch)
    _seed_admin(db)

    payload = {
        "message": {
            "text": "/start",
            "chat": {"id": 123},
            "from": {"first_name": "João", "username": "joao"},
        }
    }

    client.post("/telegram/webhook", json=payload)
    client.post("/telegram/webhook", json=payload)

    pendentes = db.query(SolicitacaoCadastro).filter(SolicitacaoCadastro.status == "pendente").all()
    assert len(pendentes) == 1


def test_callback_aprovar_cria_usuario_e_fecha_solicitacao(monkeypatch):
    FakeTelegramAdapter.reset()
    client, db = _build_client_and_session(monkeypatch)
    admin, obra = _seed_admin(db)

    solicitacao = SolicitacaoCadastro(
        obra_id=obra.id,
        solicitante_chat_id="123",
        solicitante_nome="João",
        status="pendente",
    )
    db.add(solicitacao)
    db.commit()
    db.refresh(solicitacao)

    resp = client.post(
        "/telegram/webhook",
        json={
            "callback_query": {
                "id": "cb-1",
                "data": f"cadastro_aprovar:{solicitacao.id}",
                "message": {"chat": {"id": int(admin.telefone)}},
            }
        },
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    usuario = db.query(Usuario).filter(Usuario.telefone == "123").first()
    assert usuario is not None
    assert usuario.obra_id == obra.id

    db.refresh(solicitacao)
    assert solicitacao.status == "aprovado"
    assert solicitacao.admin_decisor_id == admin.id

    assert any(chat_id == "123" and "Cadastro aprovado" in texto for chat_id, texto in FakeTelegramAdapter.sent_raw)
