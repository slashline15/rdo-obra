"""
Alert Engine — 5 regras de alerta para o painel de revisão.
Stateless: roda regras, upsert alertas, auto-resolve os que não se aplicam.
"""
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    Alerta, AlertaSeveridade, Efetivo, Clima, Atividade,
    Material, AtividadeStatus
)


def avaliar_alertas(db: Session, obra_id: int, data_ref: date) -> list[Alerta]:
    """Avalia todas as regras e retorna alertas atualizados."""
    regras = [
        _regra_sem_efetivo,
        _regra_clima_incompleto,
        _regra_atividade_sem_progresso,
        _regra_material_atrasado,
        _regra_efetivo_anomalo,
    ]

    alertas_ativos = set()
    for regra_fn in regras:
        resultado = regra_fn(db, obra_id, data_ref)
        if resultado:
            regra, severidade, mensagem, contexto = resultado
            alertas_ativos.add(regra)
            _upsert_alerta(db, obra_id, data_ref, regra, severidade, mensagem, contexto)

    # Auto-resolver alertas que não se aplicam mais
    existentes = db.query(Alerta).filter(
        Alerta.obra_id == obra_id,
        Alerta.data == data_ref,
        Alerta.resolvido == False,
    ).all()
    for al in existentes:
        if al.regra not in alertas_ativos:
            al.resolvido = True

    db.commit()

    return db.query(Alerta).filter(
        Alerta.obra_id == obra_id,
        Alerta.data == data_ref,
    ).order_by(Alerta.severidade, Alerta.created_at).all()


def _upsert_alerta(db, obra_id, data_ref, regra, severidade, mensagem, contexto):
    """Cria ou atualiza alerta. Não duplica se já existe não-resolvido."""
    existente = db.query(Alerta).filter(
        Alerta.obra_id == obra_id,
        Alerta.data == data_ref,
        Alerta.regra == regra,
        Alerta.resolvido == False,
    ).first()

    if existente:
        existente.mensagem = mensagem
        existente.dados_contexto = contexto
    else:
        db.add(Alerta(
            obra_id=obra_id,
            data=data_ref,
            regra=regra,
            severidade=severidade,
            mensagem=mensagem,
            dados_contexto=contexto,
        ))
    db.flush()


# === REGRAS ===

def _regra_sem_efetivo(db, obra_id, data_ref):
    """ALTA: nenhum efetivo registrado."""
    count = db.query(Efetivo).filter(
        Efetivo.obra_id == obra_id, Efetivo.data == data_ref
    ).count()
    if count == 0:
        return ("sem_efetivo", AlertaSeveridade.ALTA,
                "Nenhum efetivo registrado para este dia.",
                {"count": 0})
    return None


def _regra_clima_incompleto(db, obra_id, data_ref):
    """MEDIA: menos de 2 períodos de clima registrados."""
    periodos = db.query(Clima.periodo).filter(
        Clima.obra_id == obra_id, Clima.data == data_ref
    ).distinct().all()
    periodos_list = [p[0] for p in periodos]

    if len(periodos_list) < 2:
        esperados = {"manhã", "tarde"}
        faltantes = esperados - set(periodos_list)
        return ("clima_incompleto", AlertaSeveridade.MEDIA,
                f"Clima registrado apenas para: {', '.join(periodos_list) or 'nenhum'}. "
                f"Falta: {', '.join(faltantes)}.",
                {"periodos_registrados": periodos_list, "faltantes": list(faltantes)})
    return None


def _regra_atividade_sem_progresso(db, obra_id, data_ref):
    """MEDIA: atividade em andamento sem atualização há 5+ dias."""
    limite = data_ref - timedelta(days=5)
    paradas = db.query(Atividade).filter(
        Atividade.obra_id == obra_id,
        Atividade.status.in_([AtividadeStatus.INICIADA, AtividadeStatus.EM_ANDAMENTO]),
        Atividade.updated_at < limite,
    ).all()

    if paradas:
        return ("atividade_sem_progresso", AlertaSeveridade.MEDIA,
                f"{len(paradas)} atividade(s) sem atualização há mais de 5 dias.",
                {"atividades": [{"id": a.id, "descricao": a.descricao[:80]} for a in paradas]})
    return None


def _regra_material_atrasado(db, obra_id, data_ref):
    """ALTA: material pendente com data_prevista vencida."""
    atrasados = db.query(Material).filter(
        Material.obra_id == obra_id,
        Material.tipo == "pendente",
        Material.data_prevista < data_ref,
    ).all()

    if atrasados:
        return ("material_atrasado", AlertaSeveridade.ALTA,
                f"{len(atrasados)} material(ais) pendente(s) atrasado(s).",
                {"materiais": [
                    {"id": m.id, "material": m.material,
                     "dias_atraso": (data_ref - m.data_prevista).days}
                    for m in atrasados
                ]})
    return None


def _regra_efetivo_anomalo(db, obra_id, data_ref):
    """BAIXA: efetivo hoje desvia >50% da média dos últimos 7 dias."""
    total_hoje = db.query(func.coalesce(func.sum(Efetivo.quantidade), 0)).filter(
        Efetivo.obra_id == obra_id, Efetivo.data == data_ref
    ).scalar()

    if total_hoje == 0:
        return None  # sem_efetivo já cobre esse caso

    inicio_media = data_ref - timedelta(days=7)

    # Calcular média por dia dos últimos 7 dias
    dias_com_efetivo = db.query(Efetivo.data, func.sum(Efetivo.quantidade).label("total")).filter(
        Efetivo.obra_id == obra_id,
        Efetivo.data >= inicio_media,
        Efetivo.data < data_ref,
    ).group_by(Efetivo.data).all()

    if not dias_com_efetivo:
        return None

    media = sum(d.total for d in dias_com_efetivo) / len(dias_com_efetivo)
    if media == 0:
        return None

    desvio = abs(total_hoje - media) / media
    if desvio > 0.5:
        return ("efetivo_anomalo", AlertaSeveridade.BAIXA,
                f"Efetivo hoje ({total_hoje}) diverge significativamente da média recente ({media:.0f}).",
                {"total_hoje": total_hoje, "media_7d": round(media, 1), "desvio_pct": round(desvio * 100)})
    return None
