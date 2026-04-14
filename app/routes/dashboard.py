"""Dashboard executivo — KPIs e insights."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.core.auth import get_current_user
from app.core.permissions import ensure_obra_access
from app.models import (
    Atividade, AtividadeStatus, Efetivo, Material,
    DiaImprodutivo, DiarioDia, DiarioStatus, Usuario, Obra
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/{obra_id}")
def dashboard_kpis(obra_id: int,
                   data_inicio: date = None, data_fim: date = None,
                   db: Session = Depends(get_db),
                   current_user: Usuario = Depends(get_current_user)):
    """6 KPIs para o dashboard executivo."""
    ensure_obra_access(current_user, obra_id, required_level=3)
    obra = db.query(Obra).filter(Obra.id == obra_id).first()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra não encontrada")

    if not data_fim:
        data_fim = date.today()
    if not data_inicio:
        data_inicio = data_fim - timedelta(days=30)

    dias_periodo = max((data_fim - data_inicio).days + 1, 1)

    # 1. Produtividade: atividades concluídas no período / dias
    concluidas = db.query(Atividade).filter(
        Atividade.obra_id == obra_id,
        Atividade.data_fim_real >= data_inicio,
        Atividade.data_fim_real <= data_fim,
        Atividade.status == AtividadeStatus.CONCLUIDA,
    ).count()
    produtividade = round(concluidas / dias_periodo, 2)

    # 2. Dias improdutivos no período
    dias_improdutivos = db.query(DiaImprodutivo).filter(
        DiaImprodutivo.obra_id == obra_id,
        DiaImprodutivo.data >= data_inicio,
        DiaImprodutivo.data <= data_fim,
    ).count()

    # 3. Atividades atrasadas (current)
    atividades_atrasadas = db.query(Atividade).filter(
        Atividade.obra_id == obra_id,
        Atividade.status.in_([AtividadeStatus.INICIADA, AtividadeStatus.EM_ANDAMENTO]),
        Atividade.dias_atraso > 0,
    ).count()

    # 4. Tempo médio até aprovação (horas)
    diarios_aprovados = db.query(DiarioDia).filter(
        DiarioDia.obra_id == obra_id,
        DiarioDia.status == DiarioStatus.APROVADO,
        DiarioDia.submetido_em.isnot(None),
        DiarioDia.aprovado_em.isnot(None),
        DiarioDia.data >= data_inicio,
        DiarioDia.data <= data_fim,
    ).all()
    if diarios_aprovados:
        total_horas = sum(
            (d.aprovado_em - d.submetido_em).total_seconds() / 3600
            for d in diarios_aprovados
        )
        tempo_medio = round(total_horas / len(diarios_aprovados), 1)
    else:
        tempo_medio = 0.0

    # 5. Total efetivo no período
    total_efetivo = db.query(func.coalesce(func.sum(Efetivo.quantidade), 0)).filter(
        Efetivo.obra_id == obra_id,
        Efetivo.data >= data_inicio,
        Efetivo.data <= data_fim,
    ).scalar()

    # 6. Materiais pendentes (current)
    materiais_pendentes = db.query(Material).filter(
        Material.obra_id == obra_id,
        Material.tipo == "pendente",
    ).count()

    # Tendências: efetivo diário
    efetivo_diario = db.query(
        Efetivo.data, func.sum(Efetivo.quantidade).label("total")
    ).filter(
        Efetivo.obra_id == obra_id,
        Efetivo.data >= data_inicio,
        Efetivo.data <= data_fim,
    ).group_by(Efetivo.data).order_by(Efetivo.data).all()

    # Tendências: atividades concluídas por dia
    atividades_diario = db.query(
        Atividade.data_fim_real.label("data"), func.count(Atividade.id).label("total")
    ).filter(
        Atividade.obra_id == obra_id,
        Atividade.data_fim_real >= data_inicio,
        Atividade.data_fim_real <= data_fim,
        Atividade.status == AtividadeStatus.CONCLUIDA,
    ).group_by(Atividade.data_fim_real).order_by(Atividade.data_fim_real).all()

    return {
        "obra": {"id": obra.id, "nome": obra.nome},
        "periodo": {"inicio": str(data_inicio), "fim": str(data_fim), "dias": dias_periodo},
        "kpis": {
            "produtividade_media": produtividade,
            "dias_improdutivos": dias_improdutivos,
            "atividades_atrasadas": atividades_atrasadas,
            "tempo_medio_aprovacao_horas": tempo_medio,
            "total_efetivo_periodo": total_efetivo,
            "materiais_pendentes": materiais_pendentes,
        },
        "tendencias": {
            "efetivo_diario": [{"data": str(d.data), "total": d.total} for d in efetivo_diario],
            "atividades_diario": [{"data": str(d.data), "total": d.total} for d in atividades_diario],
        },
    }


@router.get("/{obra_id}/insights")
def dashboard_insights(obra_id: int,
                       data_inicio: date = None, data_fim: date = None,
                       db: Session = Depends(get_db),
                       current_user: Usuario = Depends(get_current_user)):
    """Insights em linguagem natural — template-based, sem LLM."""
    ensure_obra_access(current_user, obra_id, required_level=3)
    if not data_fim:
        data_fim = date.today()
    if not data_inicio:
        data_inicio = data_fim - timedelta(days=30)

    insights = []

    # Insight 1: Dias improdutivos por chuva
    dias_chuva = db.query(DiaImprodutivo).filter(
        DiaImprodutivo.obra_id == obra_id,
        DiaImprodutivo.data >= data_inicio,
        DiaImprodutivo.data <= data_fim,
        DiaImprodutivo.motivo.ilike("%chuva%"),
    ).count()
    if dias_chuva > 0:
        # Contar atividades impactadas
        atrasadas = db.query(Atividade).filter(
            Atividade.obra_id == obra_id,
            Atividade.dias_atraso > 0,
        ).count()
        insights.append({
            "texto": f"Nos últimos {(data_fim - data_inicio).days + 1} dias, {dias_chuva} dia(s) foram improdutivos por chuva, impactando {atrasadas} atividade(s).",
            "severidade": "atencao" if dias_chuva >= 3 else "info",
            "data_ref": None,
            "evidencia": f"{dias_chuva} registros de DiaImprodutivo com motivo 'chuva'",
        })

    # Insight 2: Materiais atrasados
    mat_atrasados = db.query(Material).filter(
        Material.obra_id == obra_id,
        Material.tipo == "pendente",
        Material.data_prevista < data_fim,
    ).all()
    if mat_atrasados:
        pior = max(mat_atrasados, key=lambda m: (data_fim - m.data_prevista).days if m.data_prevista else 0)
        dias_atraso = (data_fim - pior.data_prevista).days if pior.data_prevista else 0
        insights.append({
            "texto": f"{len(mat_atrasados)} material(ais) pendente(s) atrasado(s). Maior atraso: {pior.material} ({dias_atraso} dias).",
            "severidade": "critico" if dias_atraso > 7 else "atencao",
            "data_ref": str(pior.data_prevista) if pior.data_prevista else None,
            "evidencia": f"{len(mat_atrasados)} registros de Material com tipo='pendente' e data_prevista vencida",
        })

    # Insight 3: Tendência de efetivo
    efetivo_semana = db.query(func.sum(Efetivo.quantidade)).filter(
        Efetivo.obra_id == obra_id,
        Efetivo.data >= data_fim - timedelta(days=7),
        Efetivo.data <= data_fim,
    ).scalar() or 0

    efetivo_semana_anterior = db.query(func.sum(Efetivo.quantidade)).filter(
        Efetivo.obra_id == obra_id,
        Efetivo.data >= data_fim - timedelta(days=14),
        Efetivo.data < data_fim - timedelta(days=7),
    ).scalar() or 0

    if efetivo_semana_anterior > 0:
        variacao = ((efetivo_semana - efetivo_semana_anterior) / efetivo_semana_anterior) * 100
        if abs(variacao) > 20:
            direcao = "aumentou" if variacao > 0 else "caiu"
            insights.append({
                "texto": f"Efetivo médio {direcao} {abs(variacao):.0f}% na última semana em relação à anterior.",
                "severidade": "atencao" if variacao < -20 else "info",
                "data_ref": None,
                "evidencia": f"Semana atual: {efetivo_semana}, semana anterior: {efetivo_semana_anterior}",
            })

    # Insight 4: Atividades concluídas
    concluidas = db.query(Atividade).filter(
        Atividade.obra_id == obra_id,
        Atividade.data_fim_real >= data_inicio,
        Atividade.data_fim_real <= data_fim,
        Atividade.status == AtividadeStatus.CONCLUIDA,
    ).count()
    em_andamento = db.query(Atividade).filter(
        Atividade.obra_id == obra_id,
        Atividade.status.in_([AtividadeStatus.INICIADA, AtividadeStatus.EM_ANDAMENTO]),
    ).count()
    if concluidas > 0 or em_andamento > 0:
        insights.append({
            "texto": f"{concluidas} atividade(s) concluída(s) no período. {em_andamento} em andamento.",
            "severidade": "info",
            "data_ref": None,
            "evidencia": f"Atividades com status='concluida' e data_fim_real no período",
        })

    return insights
