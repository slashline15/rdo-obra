"""Rota para geração do RDO (PDF)."""
import os
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session
from datetime import date

from app.database import get_db
from app.core.auth import get_current_user
from app.models import DiarioDia, DiarioStatus, Usuario
from app.schemas import RDORequest
from app.services.rdo_generator import (
    OUTPUT_DIR,
    gerar_rdo_pdf,
    gerar_rdo_data,
    gerar_rdo_html,
)

router = APIRouter(prefix="/rdo", tags=["RDO - Relatório"])


@router.post("/gerar")
def gerar_rdo(request: RDORequest, db: Session = Depends(get_db),
              current_user: Usuario = Depends(get_current_user)):
    # Verificar se diário está aprovado (para PDF)
    if request.formato != "json":
        diario = db.query(DiarioDia).filter(
            DiarioDia.obra_id == request.obra_id,
            DiarioDia.data == request.data,
        ).first()
        if not diario or diario.status != DiarioStatus.APROVADO:
            raise HTTPException(
                status_code=403,
                detail="PDF só pode ser gerado após aprovação do diário."
            )

    try:
        if request.formato == "json":
            data = gerar_rdo_data(request.obra_id, request.data, db)
            return {
                "obra": data["obra"].nome,
                "data": str(data["data"]),
                "total_efetivo": data["total_efetivo"],
                "iniciadas": len(data["iniciadas"]),
                "em_andamento": len(data["em_andamento"]),
                "concluidas": len(data["concluidas"]),
                "materiais": len(data["materiais"]),
                "equipamentos": len(data["equipamentos"]),
                "anotacoes": len(data["anotacoes"]),
                "climas": len(data["climas"]),
                "fotos": len(data["fotos"]),
            }

        filepath = gerar_rdo_pdf(request.obra_id, request.data, db)

        # Salvar path no diário
        diario.pdf_path = filepath
        db.commit()

        return FileResponse(filepath, media_type="application/pdf", filename=filepath.split("/")[-1])
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preview/{obra_id}/{data_ref}")
def preview_rdo(obra_id: int, data_ref: date, db: Session = Depends(get_db),
                current_user: Usuario = Depends(get_current_user)):
    try:
        data = gerar_rdo_data(obra_id, data_ref, db)
        html = gerar_rdo_html(data)
        return HTMLResponse(content=html)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/download/{file_path:path}")
def download_rdo(file_path: str,
                 db: Session = Depends(get_db),
                 current_user: Usuario = Depends(get_current_user)):
    resolved_path = os.path.abspath(unquote(file_path))
    output_dir = os.path.abspath(OUTPUT_DIR)

    if not resolved_path.startswith(output_dir + os.sep):
        raise HTTPException(status_code=403, detail="Caminho de arquivo inválido")
    if not os.path.isfile(resolved_path):
        raise HTTPException(status_code=404, detail="PDF não encontrado")

    return FileResponse(
        resolved_path,
        media_type="application/pdf",
        filename=os.path.basename(resolved_path),
    )
