"""Endpoint consolidado — retorna todos os dados de um dia em uma chamada."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.auth import get_current_user
from app.models import (
    Obra, Empresa, Atividade, Efetivo, Anotacao, Material,
    Equipamento, Clima, Foto, Expediente, DiarioDia, Alerta,
    AtividadeStatus, DiarioStatus, TipoEfetivo
)
from app.services.alert_engine import avaliar_alertas

router = APIRouter(prefix="/painel", tags=["Painel"])


@router.get("/{obra_id}/{data_ref}")
def painel_diario(obra_id: int, data_ref: date, db: Session = Depends(get_db),
                  current_user=Depends(get_current_user)):
    """Retorna TUDO de um dia para o painel de revisão."""
    obra = db.query(Obra).filter(Obra.id == obra_id).first()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra não encontrada")

    empresa = db.query(Empresa).filter(Empresa.id == obra.empresa_id).first() if obra.empresa_id else None

    # Auto-criar diário como rascunho se não existir
    diario = db.query(DiarioDia).filter(
        DiarioDia.obra_id == obra_id, DiarioDia.data == data_ref
    ).first()
    if not diario:
        diario = DiarioDia(obra_id=obra_id, data=data_ref, status=DiarioStatus.RASCUNHO)
        db.add(diario)
        db.commit()
        db.refresh(diario)

    # Atividades em 3 grupos
    iniciadas = db.query(Atividade).filter(
        Atividade.obra_id == obra_id, Atividade.data_inicio == data_ref
    ).all()

    em_andamento = db.query(Atividade).filter(
        Atividade.obra_id == obra_id,
        Atividade.data_inicio < data_ref,
        Atividade.status.in_([AtividadeStatus.INICIADA, AtividadeStatus.EM_ANDAMENTO]),
        (Atividade.data_fim_real == None) | (Atividade.data_fim_real > data_ref)
    ).all()

    concluidas = db.query(Atividade).filter(
        Atividade.obra_id == obra_id, Atividade.data_fim_real == data_ref
    ).all()

    efetivo = db.query(Efetivo).filter(
        Efetivo.obra_id == obra_id, Efetivo.data == data_ref
    ).all()

    climas = db.query(Clima).filter(
        Clima.obra_id == obra_id, Clima.data == data_ref
    ).order_by(Clima.periodo).all()

    materiais = db.query(Material).filter(
        Material.obra_id == obra_id, Material.data == data_ref
    ).all()

    equipamentos = db.query(Equipamento).filter(
        Equipamento.obra_id == obra_id, Equipamento.data == data_ref
    ).all()

    anotacoes = db.query(Anotacao).filter(
        Anotacao.obra_id == obra_id, Anotacao.data == data_ref
    ).all()

    fotos = db.query(Foto).filter(
        Foto.obra_id == obra_id, Foto.data == data_ref
    ).all()

    expediente = db.query(Expediente).filter(
        Expediente.obra_id == obra_id, Expediente.data == data_ref
    ).first()

    # Efetivo totais
    total_proprio = sum(e.quantidade for e in efetivo if e.tipo == TipoEfetivo.PROPRIO)
    total_empreiteiro = sum(e.quantidade for e in efetivo if e.tipo == TipoEfetivo.EMPREITEIRO)

    # Avaliar alertas (lazy)
    alertas = avaliar_alertas(db, obra_id, data_ref)

    def _serialize_atividade(a):
        return {
            "id": a.id, "descricao": a.descricao, "local": a.local, "etapa": a.etapa,
            "status": a.status.value if hasattr(a.status, 'value') else a.status,
            "percentual_concluido": a.percentual_concluido, "dias_atraso": a.dias_atraso,
            "data_inicio": str(a.data_inicio) if a.data_inicio else None,
            "data_fim_prevista": str(a.data_fim_prevista) if a.data_fim_prevista else None,
            "observacoes": a.observacoes, "registrado_por": a.registrado_por,
        }

    def _serialize_efetivo(e):
        return {
            "id": e.id, "tipo": e.tipo.value if hasattr(e.tipo, 'value') else e.tipo,
            "funcao": e.funcao, "quantidade": e.quantidade, "empresa": e.empresa,
            "observacoes": e.observacoes, "registrado_por": e.registrado_por,
        }

    def _serialize_clima(c):
        return {
            "id": c.id, "periodo": c.periodo, "condicao": c.condicao,
            "anotacao_rdo": c.anotacao_rdo,
            "status_pluviometrico": c.status_pluviometrico.value if hasattr(c.status_pluviometrico, 'value') else c.status_pluviometrico,
            "temperatura": c.temperatura, "impacto_trabalho": c.impacto_trabalho,
        }

    def _serialize_material(m):
        return {
            "id": m.id, "tipo": m.tipo, "material": m.material,
            "quantidade": m.quantidade, "unidade": m.unidade,
            "fornecedor": m.fornecedor, "nota_fiscal": m.nota_fiscal,
            "data_prevista": str(m.data_prevista) if m.data_prevista else None,
            "observacoes": m.observacoes, "registrado_por": m.registrado_por,
        }

    def _serialize_equipamento(eq):
        return {
            "id": eq.id, "tipo": eq.tipo, "equipamento": eq.equipamento,
            "quantidade": eq.quantidade, "horas_trabalhadas": eq.horas_trabalhadas,
            "operador": eq.operador, "observacoes": eq.observacoes,
            "registrado_por": eq.registrado_por,
        }

    def _serialize_anotacao(a):
        return {
            "id": a.id, "tipo": a.tipo, "descricao": a.descricao,
            "prioridade": a.prioridade, "resolvida": a.resolvida,
            "auto_gerada": a.auto_gerada, "registrado_por": a.registrado_por,
        }

    def _serialize_foto(f):
        return {
            "id": f.id, "arquivo": f.arquivo, "descricao": f.descricao,
            "categoria": f.categoria, "registrado_por": f.registrado_por,
        }

    def _serialize_alerta(al):
        return {
            "id": al.id, "regra": al.regra,
            "severidade": al.severidade.value if hasattr(al.severidade, 'value') else al.severidade,
            "mensagem": al.mensagem, "resolvido": al.resolvido,
            "dados_contexto": al.dados_contexto,
        }

    return {
        "obra": {
            "id": obra.id, "nome": obra.nome, "endereco": obra.endereco,
            "responsavel": obra.responsavel, "status": obra.status,
            "hora_inicio_padrao": obra.hora_inicio_padrao,
            "hora_termino_padrao": obra.hora_termino_padrao,
        },
        "empresa": {"id": empresa.id, "nome": empresa.nome, "cnpj": empresa.cnpj} if empresa else None,
        "data": str(data_ref),
        "diario": {
            "id": diario.id, "status": diario.status.value if hasattr(diario.status, 'value') else diario.status,
            "submetido_por_id": diario.submetido_por_id,
            "submetido_em": str(diario.submetido_em) if diario.submetido_em else None,
            "aprovado_por_id": diario.aprovado_por_id,
            "aprovado_em": str(diario.aprovado_em) if diario.aprovado_em else None,
            "observacao_aprovacao": diario.observacao_aprovacao,
            "pdf_path": diario.pdf_path,
        },
        "atividades": {
            "iniciadas": [_serialize_atividade(a) for a in iniciadas],
            "em_andamento": [_serialize_atividade(a) for a in em_andamento],
            "concluidas": [_serialize_atividade(a) for a in concluidas],
        },
        "efetivo": [_serialize_efetivo(e) for e in efetivo],
        "total_efetivo": {
            "proprio": total_proprio,
            "empreiteiro": total_empreiteiro,
            "geral": total_proprio + total_empreiteiro,
        },
        "clima": [_serialize_clima(c) for c in climas],
        "materiais": [_serialize_material(m) for m in materiais],
        "equipamentos": [_serialize_equipamento(eq) for eq in equipamentos],
        "anotacoes": [_serialize_anotacao(a) for a in anotacoes],
        "fotos": [_serialize_foto(f) for f in fotos],
        "expediente": {
            "hora_inicio": expediente.hora_inicio if expediente else obra.hora_inicio_padrao,
            "hora_termino": expediente.hora_termino if expediente else obra.hora_termino_padrao,
            "motivo": expediente.motivo if expediente else None,
            "is_override": expediente is not None,
        },
        "alertas": [_serialize_alerta(al) for al in alertas],
    }
