"""
Gráfico Pluviométrico — Disco Mensal SVG.

Estrutura visual:
  - Disco dividido em 31 fatias (dias do mês)
  - Cada fatia: 3 anéis concêntricos (de fora para dentro: manhã, tarde, noite)
  - 5 cores por status pluviométrico

Uso:
    from app.services.grafico_pluviometrico import gerar_disco_mensal
    svg = gerar_disco_mensal(obra_id=1, ano=2026, mes=4, db=session)
    with open("disco.svg", "w") as f:
        f.write(svg)
"""
import math
import calendar
from datetime import date
from typing import Optional
from sqlalchemy.orm import Session

from app.models import Clima, StatusPluviometrico

# ─── Paleta de cores ─────────────────────────────────────────────────────────

CORES: dict[Optional[str], str] = {
    StatusPluviometrico.SECO_PRODUTIVO.value:    "#27AE60",  # verde
    StatusPluviometrico.SECO_IMPRODUTIVO.value:  "#F39C12",  # âmbar
    StatusPluviometrico.CHUVA_PRODUTIVA.value:   "#3498DB",  # azul claro
    StatusPluviometrico.CHUVA_IMPRODUTIVA.value: "#1A5276",  # azul escuro
    StatusPluviometrico.SEM_EXPEDIENTE.value:    "#BDC3C7",  # cinza
    None: "#27AE60",  # padrão = seco produtivo
}

COR_FUNDO_VAZIO = "#ECF0F1"   # cinza muito claro — dia futuro / sem dado
COR_BORDA       = "#FFFFFF"
COR_LABEL       = "#2C3E50"
COR_LEGENDA_BG  = "#F8F9FA"

PERIODOS = ["manhã", "tarde", "noite"]  # de fora para dentro

# ─── Geometria ───────────────────────────────────────────────────────────────

CX, CY = 260, 260          # centro do disco
R_ANEIS = [260, 200, 150, 95]  # [externo_manha, manha/tarde, tarde/noite, buraco]
R_LABEL = 280              # raio dos números dos dias
GAP_GRAUS = 0.8            # espaço entre fatias

# ─── Helpers SVG ─────────────────────────────────────────────────────────────

def _polar(cx: float, cy: float, r: float, angulo_deg: float) -> tuple[float, float]:
    """Converte coordenadas polares (ângulo 0° = topo, sentido horário) para cartesianas."""
    rad = math.radians(angulo_deg - 90)
    return cx + r * math.cos(rad), cy + r * math.sin(rad)


def _segmento(cx, cy, r_ext, r_int, a_ini, a_fim, cor) -> str:
    """Retorna <path> SVG para um segmento de anel (fatia de donut)."""
    large = 1 if (a_fim - a_ini) > 180 else 0

    p1 = _polar(cx, cy, r_ext, a_ini)
    p2 = _polar(cx, cy, r_ext, a_fim)
    p3 = _polar(cx, cy, r_int, a_fim)
    p4 = _polar(cx, cy, r_int, a_ini)

    d = (
        f"M {p1[0]:.2f},{p1[1]:.2f} "
        f"A {r_ext},{r_ext} 0 {large},1 {p2[0]:.2f},{p2[1]:.2f} "
        f"L {p3[0]:.2f},{p3[1]:.2f} "
        f"A {r_int},{r_int} 0 {large},0 {p4[0]:.2f},{p4[1]:.2f} Z"
    )
    return f'  <path d="{d}" fill="{cor}" stroke="{COR_BORDA}" stroke-width="0.6"/>'


def _label_dia(cx, cy, r, angulo_deg, texto, tamanho=8) -> str:
    x, y = _polar(cx, cy, r, angulo_deg)
    return (
        f'  <text x="{x:.1f}" y="{y:.1f}" '
        f'text-anchor="middle" dominant-baseline="middle" '
        f'font-size="{tamanho}" font-family="Arial,sans-serif" fill="{COR_LABEL}" '
        f'transform="rotate({angulo_deg:.1f},{x:.1f},{y:.1f})">'
        f'{texto}</text>'
    )


# ─── Geração principal ───────────────────────────────────────────────────────

def gerar_disco_mensal(
    obra_id: int,
    ano: int,
    mes: int,
    db: Session,
    largura: int = 640,
    altura: int = 640,
) -> str:
    """
    Gera o SVG do disco pluviométrico mensal.

    Args:
        obra_id: ID da obra
        ano, mes: mês de referência
        db: sessão SQLAlchemy
        largura, altura: dimensões do SVG em px

    Returns:
        String SVG completa
    """
    dias_no_mes = calendar.monthrange(ano, mes)[1]
    graus_por_dia = 360 / dias_no_mes
    graus_fatia = graus_por_dia - GAP_GRAUS
    hoje = date.today()

    # Buscar todos os registros de clima do mês
    registros = db.query(Clima).filter(
        Clima.obra_id == obra_id,
        Clima.data >= date(ano, mes, 1),
        Clima.data <= date(ano, mes, dias_no_mes),
    ).all()

    # Indexar por (dia, periodo)
    index: dict[tuple[int, str], str] = {}
    for cl in registros:
        chave = (cl.data.day, cl.periodo)
        index[chave] = cl.status_pluviometrico.value if cl.status_pluviometrico else None

    nome_mes = _nome_mes(mes)
    paths = []

    for dia in range(1, dias_no_mes + 1):
        a_ini = (dia - 1) * graus_por_dia + GAP_GRAUS / 2
        a_mid = a_ini + graus_fatia / 2  # ângulo central da fatia
        a_fim = a_ini + graus_fatia

        data_dia = date(ano, mes, dia)
        dia_futuro = data_dia > hoje

        for i, periodo in enumerate(PERIODOS):
            r_ext = R_ANEIS[i]
            r_int = R_ANEIS[i + 1]

            status = index.get((dia, periodo))

            if dia_futuro:
                cor = COR_FUNDO_VAZIO
            else:
                cor = CORES.get(status, CORES[None])

            paths.append(_segmento(CX, CY, r_ext, r_int, a_ini, a_fim, cor))

        # Label do dia no ângulo central
        paths.append(_label_dia(CX, CY, R_LABEL, a_mid, str(dia)))

    # Círculo central com mês/ano
    centro_texto = [
        f'  <circle cx="{CX}" cy="{CY}" r="{R_ANEIS[3]}" fill="white" stroke="#DDD" stroke-width="1"/>',
        f'  <text x="{CX}" y="{CY - 8}" text-anchor="middle" font-size="14" '
        f'font-family="Arial,sans-serif" font-weight="bold" fill="{COR_LABEL}">{nome_mes}</text>',
        f'  <text x="{CX}" y="{CY + 10}" text-anchor="middle" font-size="11" '
        f'font-family="Arial,sans-serif" fill="{COR_LABEL}">{ano}</text>',
    ]

    legenda = _gerar_legenda(CX, 540)

    offset_x = (largura - (CX * 2 + R_LABEL * 2 + 20)) // 2

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{largura}" height="{altura}" '
        f'viewBox="-30 -20 {CX*2 + R_LABEL*2 + 60} {CY*2 + R_LABEL*2 + 100}">',
        f'  <rect width="100%" height="100%" fill="white"/>',
        *paths,
        *centro_texto,
        *legenda,
        '</svg>',
    ]

    return "\n".join(svg)


def _gerar_legenda(cx: float, y_base: float) -> list[str]:
    """Gera bloco de legenda abaixo do disco."""
    itens = [
        (CORES[StatusPluviometrico.SECO_PRODUTIVO.value],    "Seco produtivo"),
        (CORES[StatusPluviometrico.SECO_IMPRODUTIVO.value],  "Seco improdutivo"),
        (CORES[StatusPluviometrico.CHUVA_PRODUTIVA.value],   "Chuva produtiva"),
        (CORES[StatusPluviometrico.CHUVA_IMPRODUTIVA.value], "Chuva improdutiva"),
        (CORES[StatusPluviometrico.SEM_EXPEDIENTE.value],    "Sem expediente"),
        (COR_FUNDO_VAZIO,                                    "Dia futuro"),
    ]

    col_w = 160
    n_cols = 3
    box = 10
    pad = 4
    linha_h = 18
    total_w = n_cols * col_w
    x_start = cx - total_w / 2

    elementos = [
        f'  <text x="{cx}" y="{y_base - 8}" text-anchor="middle" font-size="10" '
        f'font-family="Arial,sans-serif" font-weight="bold" fill="{COR_LABEL}">Legenda</text>',
    ]

    for i, (cor, label) in enumerate(itens):
        col = i % n_cols
        lin = i // n_cols
        x = x_start + col * col_w
        y = y_base + lin * linha_h
        elementos += [
            f'  <rect x="{x:.0f}" y="{y:.0f}" width="{box}" height="{box}" '
            f'fill="{cor}" stroke="#CCC" stroke-width="0.5" rx="2"/>',
            f'  <text x="{x + box + pad:.0f}" y="{y + box - 1:.0f}" '
            f'font-size="9" font-family="Arial,sans-serif" fill="{COR_LABEL}">{label}</text>',
        ]

    return elementos


def _gerar_legenda_periodos(cx: float, y: float) -> list[str]:
    """Legenda visual dos anéis (manhã=externo, tarde=meio, noite=interno)."""
    return [
        f'  <text x="{cx - 80}" y="{y}" font-size="8" font-family="Arial,sans-serif" '
        f'fill="#7F8C8D">← externo: manhã  |  meio: tarde  |  interno: noite →</text>',
    ]


def _nome_mes(mes: int) -> str:
    nomes = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
             "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    return nomes[mes - 1]


# ─── Endpoint helper ─────────────────────────────────────────────────────────

def status_do_mes(obra_id: int, ano: int, mes: int, db: Session) -> dict:
    """
    Retorna resumo dos status pluviométricos do mês para uso em relatórios.

    Returns:
        {
          "total_dias": 30,
          "seco_produtivo": 18,
          "seco_improdutivo": 2,
          "chuva_produtiva": 5,
          "chuva_improdutiva": 3,
          "sem_expediente": 2,
          "dias_chuva": 8,
          "dias_improdutivos": 5,
        }
    """
    dias_no_mes = calendar.monthrange(ano, mes)[1]

    registros = db.query(Clima).filter(
        Clima.obra_id == obra_id,
        Clima.data >= date(ano, mes, 1),
        Clima.data <= date(ano, mes, dias_no_mes),
        Clima.periodo == "manhã",  # um registro por dia para o resumo
    ).all()

    contagem: dict[str, int] = {s.value: 0 for s in StatusPluviometrico}

    for cl in registros:
        chave = cl.status_pluviometrico.value if cl.status_pluviometrico else StatusPluviometrico.SECO_PRODUTIVO.value
        contagem[chave] = contagem.get(chave, 0) + 1

    dias_com_registro = len(registros)
    dias_sem_registro = dias_no_mes - dias_com_registro
    contagem[StatusPluviometrico.SECO_PRODUTIVO.value] += dias_sem_registro  # padrão

    return {
        "total_dias": dias_no_mes,
        **contagem,
        "dias_chuva": contagem[StatusPluviometrico.CHUVA_PRODUTIVA.value] + contagem[StatusPluviometrico.CHUVA_IMPRODUTIVA.value],
        "dias_improdutivos": contagem[StatusPluviometrico.SECO_IMPRODUTIVO.value] + contagem[StatusPluviometrico.CHUVA_IMPRODUTIVA.value],
    }
