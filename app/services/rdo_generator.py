"""
Gerador de PDF do Relatório Diário de Obra (RDO).
Usa Jinja2 para template HTML + WeasyPrint para PDF.
"""
import os
from datetime import date

from sqlalchemy.orm import Session
from jinja2 import Environment, FileSystemLoader

from app.models import (
    Obra, Empresa, Atividade, Efetivo, Anotacao,
    Material, Equipamento, Clima, Foto, AtividadeStatus
)

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output/rdos")


def gerar_rdo_data(obra_id: int, data_ref: date, db: Session) -> dict:
    """Coleta todos os dados do dia para gerar o RDO."""

    obra = db.query(Obra).filter(Obra.id == obra_id).first()
    if not obra:
        raise ValueError(f"Obra {obra_id} não encontrada")

    empresa = db.query(Empresa).filter(Empresa.id == obra.empresa_id).first() if obra.empresa_id else None

    # Atividades em 3 grupos
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

    efetivo = db.query(Efetivo).filter(
        Efetivo.obra_id == obra_id, Efetivo.data == data_ref
    ).all()

    anotacoes = db.query(Anotacao).filter(
        Anotacao.obra_id == obra_id, Anotacao.data == data_ref
    ).all()

    materiais = db.query(Material).filter(
        Material.obra_id == obra_id, Material.data == data_ref
    ).all()

    equipamentos = db.query(Equipamento).filter(
        Equipamento.obra_id == obra_id, Equipamento.data == data_ref
    ).all()

    climas = db.query(Clima).filter(
        Clima.obra_id == obra_id, Clima.data == data_ref
    ).all()

    fotos = db.query(Foto).filter(
        Foto.obra_id == obra_id, Foto.data == data_ref
    ).all()

    total_efetivo = sum(e.quantidade for e in efetivo)

    return {
        "obra": obra,
        "empresa": empresa,
        "data": data_ref,
        "iniciadas": iniciadas,
        "em_andamento": em_andamento,
        "concluidas": concluidas,
        "efetivo": efetivo,
        "total_efetivo": total_efetivo,
        "anotacoes": anotacoes,
        "materiais": materiais,
        "equipamentos": equipamentos,
        "climas": climas,
        "fotos": fotos,
    }


def gerar_rdo_html(rdo_data: dict, template_name: str = "rdo_default.html") -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template(template_name)
    return template.render(**rdo_data)


def gerar_rdo_pdf(obra_id: int, data_ref: date, db: Session, template_name: str = "rdo_default.html") -> str:
    try:
        from weasyprint import HTML
    except ImportError:
        raise RuntimeError("WeasyPrint não instalado. pip install weasyprint")

    rdo_data = gerar_rdo_data(obra_id, data_ref, db)
    html_content = gerar_rdo_html(rdo_data, template_name)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    obra_nome = rdo_data["obra"].nome.replace(" ", "_")
    filename = f"RDO_{obra_nome}_{data_ref.isoformat()}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    HTML(string=html_content).write_pdf(filepath)
    return filepath
