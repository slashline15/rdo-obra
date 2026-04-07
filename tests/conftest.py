import os
import sys
from pathlib import Path
from datetime import date

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_bootstrap.db")
os.environ.setdefault("JWT_SECRET", "test-secret")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import create_access_token, hash_password
from app.database import Base, get_db
from app.models import (
    Anotacao,
    Atividade,
    AtividadeStatus,
    Clima,
    ConviteAcesso,
    DiarioDia,
    DiarioStatus,
    DiaImprodutivo,
    Efetivo,
    Material,
    Obra,
    TipoEfetivo,
    Usuario,
)
from app.routes import (
    alertas,
    anotacoes,
    auth,
    auditoria,
    dashboard,
    diario,
    efetivo,
    materiais,
    usuarios,
    obras,
    painel,
    servicos,
    telegram_webhook,
)


def build_test_app(db_session) -> FastAPI:
    app = FastAPI()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    app.include_router(auth.router, prefix="/api")
    app.include_router(painel.router, prefix="/api")
    app.include_router(diario.router, prefix="/api")
    app.include_router(alertas.router, prefix="/api")
    app.include_router(auditoria.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(obras.router, prefix="/api")
    app.include_router(usuarios.router, prefix="/api")
    app.include_router(servicos.router, prefix="/api")
    app.include_router(efetivo.router, prefix="/api")
    app.include_router(anotacoes.router, prefix="/api")
    app.include_router(materiais.router, prefix="/api")
    app.include_router(telegram_webhook.router)
    return app


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
      yield session
    finally:
      session.close()
      Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    app = build_test_app(db_session)
    return TestClient(app)


@pytest.fixture
def seeded_data(db_session):
    admin = Usuario(
        nome="Admin Obra",
        telefone="5511999990001",
        email="admin@obra.com",
        senha_hash=hash_password("senha123"),
        role="admin",
        nivel_acesso=1,
        pode_aprovar_diario=True,
        ativo=True,
    )
    engenheiro = Usuario(
        nome="Engenheira Teste",
        telefone="5511999990002",
        email="engenheira@obra.com",
        senha_hash=hash_password("senha123"),
        role="engenheiro",
        nivel_acesso=2,
        ativo=True,
    )
    operacional = Usuario(
        nome="Encarregado Campo",
        telefone="5511999990003",
        email="encarregado@obra.com",
        senha_hash=hash_password("senha123"),
        role="encarregado",
        nivel_acesso=3,
        ativo=True,
    )
    db_session.add_all([admin, engenheiro, operacional])
    db_session.flush()

    obra = Obra(
        nome="Obra Teste",
        endereco="Rua Principal, 100",
        usuario_admin=admin.id,
        responsavel="Eng. Admin",
        status="ativa",
    )
    db_session.add(obra)
    db_session.flush()

    admin.obra_id = obra.id
    engenheiro.obra_id = obra.id
    operacional.obra_id = obra.id

    outra_obra = Obra(
        nome="Obra Secundária",
        endereco="Av. Secundária, 200",
        responsavel="Eng. Secundário",
        status="ativa",
    )
    db_session.add(outra_obra)
    db_session.flush()

    engenheiro_outra_obra = Usuario(
        nome="Engenheiro Externo",
        telefone="5511999990004",
        email="externo@obra.com",
        senha_hash=hash_password("senha123"),
        role="engenheiro",
        nivel_acesso=2,
        obra_id=outra_obra.id,
        ativo=True,
    )
    db_session.add(engenheiro_outra_obra)

    data_ref = date(2026, 4, 5)
    atividade = Atividade(
        obra_id=obra.id,
        descricao="Concretagem da laje",
        local="Bloco A",
        etapa="Estrutura",
        data_inicio=data_ref,
        status=AtividadeStatus.INICIADA,
        percentual_concluido=40,
    )
    efetivo_item = Efetivo(
        obra_id=obra.id,
        data=data_ref,
        tipo=TipoEfetivo.PROPRIO,
        funcao="Pedreiro",
        quantidade=6,
        empresa="própria",
    )
    material = Material(
        obra_id=obra.id,
        data=data_ref,
        tipo="pendente",
        material="Cimento CP-II",
        quantidade=50,
        unidade="sacos",
        data_prevista=date(2026, 4, 3),
    )
    anotacao = Anotacao(
        obra_id=obra.id,
        data=data_ref,
        tipo="ocorrência",
        descricao="Equipe aguardando liberação da betoneira.",
        prioridade="normal",
    )
    clima = Clima(
        obra_id=obra.id,
        data=data_ref,
        periodo="manhã",
        condicao="chuva",
        temperatura=24,
        impacto_trabalho="Ritmo reduzido",
    )
    diario = DiarioDia(
        obra_id=obra.id,
        data=data_ref,
        status=DiarioStatus.RASCUNHO,
    )
    dia_improdutivo = DiaImprodutivo(
        obra_id=obra.id,
        data=date(2026, 4, 2),
        motivo="Chuva forte no período da manhã",
        horas_perdidas=4,
    )

    db_session.add_all([atividade, efetivo_item, material, anotacao, clima, diario, dia_improdutivo])
    db_session.commit()
    db_session.refresh(admin)
    db_session.refresh(engenheiro)
    db_session.refresh(operacional)
    db_session.refresh(obra)
    db_session.refresh(outra_obra)
    db_session.refresh(engenheiro_outra_obra)
    db_session.refresh(atividade)
    db_session.refresh(efetivo_item)
    db_session.refresh(diario)

    return {
        "admin": admin,
        "engenheiro": engenheiro,
        "operacional": operacional,
        "obra": obra,
        "outra_obra": outra_obra,
        "engenheiro_outra_obra": engenheiro_outra_obra,
        "data_ref": data_ref,
        "atividade": atividade,
        "efetivo": efetivo_item,
        "diario": diario,
    }


@pytest.fixture
def auth_headers():
    def _factory(user: Usuario):
        token = create_access_token({"sub": str(user.id)})
        return {"Authorization": f"Bearer {token}"}

    return _factory
