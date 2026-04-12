from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.types import Canal, IncomingMessage, OutgoingMessage
from app.database import Base, get_db
from app.routes import whatsapp_webhook


class FakeWhatsAppAdapter:
    def __init__(self):
        self.parsed = []
        self.sent = []

    async def parse_incoming(self, raw_data: dict) -> IncomingMessage:
        self.parsed.append(raw_data)
        return IncomingMessage(
            canal=Canal.WHATSAPP,
            telefone="5511999990001",
            texto="olá",
            raw_data=raw_data,
        )

    async def send_message(self, msg: OutgoingMessage) -> bool:
        self.sent.append(msg)
        return True

    async def send_document(self, telefone: str, file_path_arg: str, caption: str | None = None) -> bool:
        return True

    async def download_media(self, media_id: str, save_path: str) -> str:
        return save_path


class FakeOrchestrator:
    received = []

    def __init__(self, db):
        self.db = db

    async def processar(self, msg: IncomingMessage) -> OutgoingMessage:
        self.received.append(msg)
        return OutgoingMessage(texto=f"ok:{msg.texto}", canal=msg.canal, telefone=msg.telefone)


def _build_client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    app = FastAPI()
    app.include_router(whatsapp_webhook.router)

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    fake_adapter = FakeWhatsAppAdapter()
    monkeypatch.setattr(whatsapp_webhook, "adapter", fake_adapter)
    monkeypatch.setattr(whatsapp_webhook, "Orchestrator", FakeOrchestrator)
    FakeOrchestrator.received = []

    return TestClient(app), db, engine, fake_adapter


def test_whatsapp_webhook_aceita_evento_em_maiusculas(monkeypatch):
    client, db, engine, adapter = _build_client(monkeypatch)
    try:
        resp = client.post(
            "/whatsapp/webhook",
            json={
                "event": "MESSAGES_UPSERT",
                "data": {
                    "key": {
                        "remoteJid": "5511999990001@s.whatsapp.net",
                        "fromMe": False,
                        "id": "abc",
                    },
                    "message": {"conversation": "oi"},
                },
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        assert len(adapter.parsed) == 1
        assert len(adapter.sent) == 1
        assert FakeOrchestrator.received[0].texto == "olá"
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_whatsapp_webhook_ignora_from_me_em_payload_com_lista(monkeypatch):
    client, db, engine, adapter = _build_client(monkeypatch)
    try:
        resp = client.post(
            "/whatsapp/webhook",
            json={
                "event": "messages-upsert",
                "data": {
                    "messages": [
                        {
                            "key": {
                                "remoteJid": "5511999990001@s.whatsapp.net",
                                "fromMe": True,
                                "id": "abc",
                            },
                            "message": {"conversation": "eco"},
                        }
                    ]
                },
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        assert len(adapter.parsed) == 0
        assert len(adapter.sent) == 0
        assert FakeOrchestrator.received == []
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
