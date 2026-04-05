"""
Rota de Atividades (ex-Serviços).
Agora com estados: Iniciada → Em Andamento → Concluída
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.database import get_db
from app.models import Atividade, AtividadeStatus
from app.schemas import AtividadeUpdate
from app.core.auth import get_current_user
from app.core.diary_lock import check_diary_editable
from app.services.audit import log_changes

from pydantic import BaseModel


class AtividadeCreate(BaseModel):
    obra_id: int
    descricao: str
    local: Optional[str] = None
    etapa: Optional[str] = None
    data_inicio: Optional[date] = None
    data_fim_prevista: Optional[date] = None
    atividade_pai_id: Optional[int] = None
    observacoes: Optional[str] = None
    registrado_por: Optional[str] = None
    texto_original: Optional[str] = None


class AtividadeResponse(BaseModel):
    id: int
    obra_id: int
    descricao: str
    local: Optional[str]
    etapa: Optional[str]
    data_inicio: date
    data_fim_prevista: Optional[date]
    data_fim_real: Optional[date]
    status: str
    percentual_concluido: float
    dias_atraso: int
    observacoes: Optional[str]
    registrado_por: Optional[str]

    class Config:
        from_attributes = True


router = APIRouter(prefix="/atividades", tags=["Atividades"])


@router.post("/", response_model=AtividadeResponse)
def criar_atividade(ativ: AtividadeCreate, db: Session = Depends(get_db)):
    data = ativ.model_dump()
    if not data.get("data_inicio"):
        data["data_inicio"] = date.today()
    db_ativ = Atividade(**data, status=AtividadeStatus.INICIADA)
    db.add(db_ativ)
    db.commit()
    db.refresh(db_ativ)
    return db_ativ


@router.get("/", response_model=List[AtividadeResponse])
def listar_atividades(
    obra_id: int = None,
    status: str = None,
    data_ref: date = None,
    db: Session = Depends(get_db)
):
    query = db.query(Atividade)
    if obra_id:
        query = query.filter(Atividade.obra_id == obra_id)
    if status:
        query = query.filter(Atividade.status == status)
    if data_ref:
        # Atividades ativas nesta data (inicio <= data E (fim >= data OU fim é null))
        query = query.filter(
            Atividade.data_inicio <= data_ref,
            (Atividade.data_fim_real >= data_ref) | (Atividade.data_fim_real == None)
        )
    return query.order_by(Atividade.data_inicio.desc()).all()


@router.get("/rdo/{obra_id}/{data_ref}")
def atividades_para_rdo(obra_id: int, data_ref: date, db: Session = Depends(get_db)):
    """
    Retorna atividades organizadas para o RDO:
    - Iniciadas: data_inicio == data_ref
    - Em Andamento: data_inicio < data_ref AND (data_fim_real is null OR data_fim_real > data_ref)
    - Concluídas: data_fim_real == data_ref
    """
    iniciadas = db.query(Atividade).filter(
        Atividade.obra_id == obra_id,
        Atividade.data_inicio == data_ref
    ).all()

    em_andamento = db.query(Atividade).filter(
        Atividade.obra_id == obra_id,
        Atividade.data_inicio < data_ref,
        Atividade.status.in_([AtividadeStatus.INICIADA, AtividadeStatus.EM_ANDAMENTO]),
        (Atividade.data_fim_real == None) | (Atividade.data_fim_real > data_ref)
    ).all()

    concluidas = db.query(Atividade).filter(
        Atividade.obra_id == obra_id,
        Atividade.data_fim_real == data_ref
    ).all()

    return {
        "data": str(data_ref),
        "iniciadas": [{"descricao": a.descricao, "local": a.local, "etapa": a.etapa} for a in iniciadas],
        "em_andamento": [{"descricao": a.descricao, "local": a.local, "etapa": a.etapa, "dias_atraso": a.dias_atraso} for a in em_andamento],
        "concluidas": [{"descricao": a.descricao, "local": a.local, "etapa": a.etapa} for a in concluidas],
        "totais": {
            "iniciadas": len(iniciadas),
            "em_andamento": len(em_andamento),
            "concluidas": len(concluidas)
        }
    }


@router.get("/{atividade_id}", response_model=AtividadeResponse)
def buscar_atividade(atividade_id: int, db: Session = Depends(get_db)):
    ativ = db.query(Atividade).filter(Atividade.id == atividade_id).first()
    if not ativ:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")
    return ativ


@router.put("/{atividade_id}", response_model=AtividadeResponse)
def atualizar_atividade(atividade_id: int, dados: AtividadeUpdate, db: Session = Depends(get_db),
                        current_user=Depends(get_current_user)):
    ativ = db.query(Atividade).filter(Atividade.id == atividade_id).first()
    if not ativ:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")
    check_diary_editable(db, ativ.obra_id, ativ.data_inicio)
    updates = dados.model_dump(exclude_unset=True)
    # Converter status string para enum
    if "status" in updates and isinstance(updates["status"], str):
        updates["status"] = AtividadeStatus(updates["status"])
    old = {k: getattr(ativ, k) for k in updates}
    # Serializar enums para string antes de logar
    old_str = {k: (v.value if hasattr(v, 'value') else v) for k, v in old.items()}
    new_str = {k: (v.value if hasattr(v, 'value') else v) for k, v in updates.items()}
    log_changes(db, ativ.obra_id, ativ.data_inicio, "atividades", ativ.id, old_str, new_str, current_user.id)
    for key, value in updates.items():
        setattr(ativ, key, value)
    db.commit()
    db.refresh(ativ)
    return ativ


@router.put("/{atividade_id}/concluir")
def concluir_atividade(atividade_id: int, db: Session = Depends(get_db)):
    """Marca atividade como concluída e dispara Relation Engine."""
    from app.core.relations import RelationEngine

    ativ = db.query(Atividade).filter(Atividade.id == atividade_id).first()
    if not ativ:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")

    relations = RelationEngine(db)
    result = relations.processar_conclusao_atividade(ativ)
    return result


@router.delete("/{atividade_id}")
def deletar_atividade(atividade_id: int, db: Session = Depends(get_db)):
    ativ = db.query(Atividade).filter(Atividade.id == atividade_id).first()
    if not ativ:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")
    db.delete(ativ)
    db.commit()
    return {"detail": "Atividade removida"}
