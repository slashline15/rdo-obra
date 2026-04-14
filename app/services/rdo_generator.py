"""
Gerador de PDF do Relatório Diário de Obra (RDO).
Usa Jinja2 para template HTML + WeasyPrint para PDF.
"""
import base64
import mimetypes
import os
from datetime import date
from urllib.parse import quote

from sqlalchemy.orm import Session
from jinja2 import Environment, FileSystemLoader

from app.core.config import settings
from app.models import (
    Obra, Empresa, Atividade, Efetivo, Anotacao,
    Material, Equipamento, Clima, Foto, AtividadeStatus,
    DiarioDia, DiarioStatus, Expediente
)
from app.services.grafico_pluviometrico import gerar_disco_mensal

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output/rdos")
WEEKDAY_LABELS = [
    "SEGUNDA-FEIRA",
    "TERÇA-FEIRA",
    "QUARTA-FEIRA",
    "QUINTA-FEIRA",
    "SEXTA-FEIRA",
    "SÁBADO",
    "DOMINGO",
]


def _to_data_uri(file_path: str | None) -> str | None:
    if not file_path:
        return None

    resolved = file_path
    if not os.path.isabs(resolved):
        resolved = os.path.abspath(os.path.join(settings.upload_dir, file_path))

    if not os.path.isfile(resolved):
        return None

    mime_type = mimetypes.guess_type(resolved)[0] or "application/octet-stream"
    with open(resolved, "rb") as file:
        encoded = base64.b64encode(file.read()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _truncate(text: str | None, limit: int) -> str:
    if not text:
        return "—"
    compact = " ".join(str(text).split())
    if len(compact) <= limit:
        return compact
    return compact[: max(limit - 1, 0)].rstrip() + "…"


def _build_atividade_card(atividade: Atividade, color: str) -> dict:
    return {
        "titulo": _truncate(atividade.descricao, 90),
        "descricao": _truncate(atividade.observacoes or atividade.descricao, 180),
        "local": atividade.local or "Local não informado",
        "etapa": atividade.etapa or "Etapa não informada",
        "progresso": round(atividade.percentual_concluido or 0),
        "color": color,
    }


def _build_anotacao_card(anotacao: Anotacao) -> dict:
    prioridade = (anotacao.prioridade or "normal").lower()
    return {
        "tipo": anotacao.tipo or "observação",
        "descricao": _truncate(anotacao.descricao, 280),
        "prioridade": prioridade,
        "priority_class": f"priority-{prioridade}",
    }


def _build_foto_card(foto: Foto) -> dict:
    return {
        "src": _to_data_uri(foto.arquivo),
        "descricao": foto.descricao or "Registro fotográfico",
        "categoria": foto.categoria or "obra",
        "arquivo_url": f"/api/fotos/arquivo/{quote(foto.arquivo)}",
    }


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

    total_proprio = sum(
        e.quantidade for e in efetivo
        if (hasattr(e.tipo, 'value') and e.tipo.value == "proprio")
        or e.tipo == "proprio"
        or (not e.empresa or str(e.empresa).lower() == "própria")
    )
    total_terceiros = sum(
        e.quantidade for e in efetivo
        if (hasattr(e.tipo, 'value') and e.tipo.value == "empreiteiro")
        or e.tipo == "empreiteiro"
    )
    total_efetivo = total_proprio + total_terceiros

    expediente = db.query(Expediente).filter(
        Expediente.obra_id == obra_id, Expediente.data == data_ref
    ).first()

    # Gráfico pluviométrico
    try:
        disco_svg = gerar_disco_mensal(obra_id, data_ref.year, data_ref.month, db)
    except Exception:
        disco_svg = ""

    materiais_entrada = [m for m in materiais if (m.tipo or "").lower() == "entrada"]
    materiais_saida = [m for m in materiais if (m.tipo or "").lower() != "entrada"]
    equipamentos_resumo = equipamentos[:3]
    fotos_cards = [_build_foto_card(f) for f in fotos]
    fotos_pdf = fotos_cards[:3]
    atividades_cards = {
        "iniciadas": [_build_atividade_card(a, "blue") for a in iniciadas[:4]],
        "em_andamento": [_build_atividade_card(a, "orange") for a in em_andamento[:4]],
        "concluidas": [_build_atividade_card(a, "green") for a in concluidas[:4]],
    }
    anotacoes_cards = [_build_anotacao_card(a) for a in anotacoes[:4]]

    expediente_inicio = expediente.hora_inicio if expediente else (obra.hora_inicio_padrao or "07:00")
    expediente_fim = expediente.hora_termino if expediente else (obra.hora_termino_padrao or "17:00")
    clima_turnos = {
        "manha": any((c.periodo or "").lower() == "manhã" for c in climas),
        "tarde": any((c.periodo or "").lower() == "tarde" for c in climas),
        "noite": any((c.periodo or "").lower() == "noite" for c in climas),
    }
    clima_resumo = climas[0].condicao if climas else "Sem registro climático"
    logo_src = _to_data_uri(empresa.logo if empresa else None)
    report_number = f"{obra_id:02d}{data_ref.strftime('%d')}"

    return {
        "obra": obra,
        "empresa": empresa,
        "data": data_ref,
        "data_extenso": data_ref.strftime("%d/%m/%Y"),
        "dia_semana": WEEKDAY_LABELS[data_ref.weekday()],
        "report_number": report_number,
        "iniciadas": iniciadas,
        "em_andamento": em_andamento,
        "concluidas": concluidas,
        "atividades_cards": atividades_cards,
        "efetivo": efetivo,
        "total_efetivo": total_efetivo,
        "total_proprio": total_proprio,
        "total_terceiros": total_terceiros,
        "anotacoes": anotacoes,
        "anotacoes_cards": anotacoes_cards,
        "materiais": materiais,
        "materiais_entrada": materiais_entrada[:4],
        "materiais_saida": materiais_saida[:4],
        "equipamentos": equipamentos,
        "equipamentos_resumo": equipamentos_resumo,
        "climas": climas,
        "clima_turnos": clima_turnos,
        "clima_resumo": clima_resumo,
        "fotos": fotos,
        "fotos_cards": fotos_cards,
        "fotos_pdf": fotos_pdf,
        "expediente": expediente,
        "expediente_inicio": expediente_inicio,
        "expediente_fim": expediente_fim,
        "disco_svg": disco_svg,
        "logo_src": logo_src,
    }


def gerar_rdo_html(rdo_data: dict, template_name: str = "rdo_default.html", modo: str = "web") -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template(template_name)
    return template.render(**rdo_data, modo=modo)


def gerar_rdo_pdf(obra_id: int, data_ref: date, db: Session, template_name: str = "rdo_default.html") -> str:
    try:
        from weasyprint import HTML
    except ImportError:
        raise RuntimeError("WeasyPrint não instalado. pip install weasyprint")

    rdo_data = gerar_rdo_data(obra_id, data_ref, db)
    html_content = gerar_rdo_html(rdo_data, template_name, modo="pdf")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    obra_nome = rdo_data["obra"].nome.replace(" ", "_")
    filename = f"RDO_{obra_nome}_{data_ref.isoformat()}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    HTML(string=html_content, base_url=os.path.abspath(".")) .write_pdf(filepath)
    return filepath
