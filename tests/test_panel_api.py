from datetime import datetime

from app.models import AuditLog, DiarioDia, DiarioStatus


def test_login_with_email_and_me_endpoint(client, seeded_data):
    response = client.post(
        "/api/auth/login",
        data={"username": seeded_data["admin"].email, "password": "senha123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["usuario"]["email"] == seeded_data["admin"].email
    assert payload["access_token"]

    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["nome"] == seeded_data["admin"].nome


def test_painel_consolidates_day_data_and_generates_alerts(client, seeded_data, auth_headers):
    obra = seeded_data["obra"]
    data_ref = seeded_data["data_ref"]

    response = client.get(
        f"/api/painel/{obra.id}/{data_ref.isoformat()}",
        headers=auth_headers(seeded_data["engenheiro"]),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["obra"]["nome"] == obra.nome
    assert payload["diario"]["status"] == "rascunho"
    assert payload["atividades"]["iniciadas"][0]["descricao"] == "Concretagem da laje"
    assert payload["total_efetivo"]["geral"] == 6
    assert any(alerta["regra"] == "clima_incompleto" for alerta in payload["alertas"])
    assert any(alerta["regra"] == "material_atrasado" for alerta in payload["alertas"])


def test_auditoria_is_recorded_and_diary_locks_after_approval(client, db_session, seeded_data, auth_headers):
    obra = seeded_data["obra"]
    data_ref = seeded_data["data_ref"]
    efetivo = seeded_data["efetivo"]

    update_response = client.put(
        f"/api/efetivo/{efetivo.id}",
        json={"quantidade": 8},
        headers=auth_headers(seeded_data["engenheiro"]),
    )
    assert update_response.status_code == 200
    assert update_response.json()["quantidade"] == 8

    logs = db_session.query(AuditLog).filter(AuditLog.registro_id == efetivo.id).all()
    assert len(logs) == 1
    assert logs[0].campo == "quantidade"

    listar_auditoria = client.get(
        f"/api/auditoria/{obra.id}/{data_ref.isoformat()}",
        headers=auth_headers(seeded_data["engenheiro"]),
    )
    assert listar_auditoria.status_code == 200
    assert listar_auditoria.json()[0]["campo"] == "quantidade"

    submeter = client.post(
        f"/api/diario/{obra.id}/{data_ref.isoformat()}/transicao",
        json={"acao": "submeter"},
        headers=auth_headers(seeded_data["engenheiro"]),
    )
    assert submeter.status_code == 200
    assert submeter.json()["status"] == "em_revisao"

    aprovar = client.post(
        f"/api/diario/{obra.id}/{data_ref.isoformat()}/transicao",
        json={"acao": "aprovar"},
        headers=auth_headers(seeded_data["admin"]),
    )
    assert aprovar.status_code == 200
    assert aprovar.json()["status"] == "aprovado"

    diario = db_session.query(DiarioDia).filter(
        DiarioDia.obra_id == obra.id,
        DiarioDia.data == data_ref,
    ).first()
    assert diario.status == DiarioStatus.APROVADO
    assert isinstance(diario.aprovado_em, datetime)

    blocked_update = client.put(
        f"/api/efetivo/{efetivo.id}",
        json={"quantidade": 10},
        headers=auth_headers(seeded_data["engenheiro"]),
    )
    assert blocked_update.status_code == 423
    assert "edição bloqueada" in blocked_update.json()["detail"]


def test_dashboard_returns_kpis_and_insights(client, seeded_data, auth_headers):
    obra = seeded_data["obra"]
    response = client.get(
        f"/api/dashboard/{obra.id}?data_inicio=2026-04-01&data_fim=2026-04-05",
        headers=auth_headers(seeded_data["admin"]),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["obra"]["id"] == obra.id
    assert payload["kpis"]["dias_improdutivos"] == 1
    assert payload["kpis"]["materiais_pendentes"] == 1

    insights = client.get(
        f"/api/dashboard/{obra.id}/insights?data_inicio=2026-04-01&data_fim=2026-04-05",
        headers=auth_headers(seeded_data["admin"]),
    )
    assert insights.status_code == 200
    textos = [item["texto"] for item in insights.json()]
    assert any("improdutivos por chuva" in texto for texto in textos)
    assert any("material(ais) pendente(s) atrasado(s)" in texto for texto in textos)


def test_obras_requires_authentication_and_admin_for_mutation(client, seeded_data, auth_headers):
    sem_token = client.get("/api/obras/")
    assert sem_token.status_code == 401

    como_engenheiro = client.post(
        "/api/obras/",
        json={"nome": "Nova Obra"},
        headers=auth_headers(seeded_data["engenheiro"]),
    )
    assert como_engenheiro.status_code == 403

    como_admin = client.post(
        "/api/obras/",
        json={"nome": "Nova Obra"},
        headers=auth_headers(seeded_data["admin"]),
    )
    assert como_admin.status_code == 200
    assert como_admin.json()["nome"] == "Nova Obra"
