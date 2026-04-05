"""
Serviço de auditoria — registra alterações campo a campo.
Uma row por campo alterado no audit_log.
"""
import json
from datetime import date

from sqlalchemy.orm import Session
from app.models import AuditLog


def log_changes(
    db: Session,
    obra_id: int,
    data_ref: date,
    tabela: str,
    registro_id: int,
    old_values: dict,
    new_values: dict,
    usuario_id: int,
):
    """Compara old e new, cria uma row de AuditLog por campo alterado."""
    for campo, novo in new_values.items():
        antigo = old_values.get(campo)
        if antigo != novo:
            db.add(AuditLog(
                obra_id=obra_id,
                data_ref=data_ref,
                tabela=tabela,
                registro_id=registro_id,
                campo=campo,
                valor_anterior=json.dumps(antigo, default=str) if antigo is not None else None,
                valor_novo=json.dumps(novo, default=str) if novo is not None else None,
                usuario_id=usuario_id,
            ))
    db.flush()
