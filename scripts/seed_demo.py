"""
Seed de demo — cria dados realistas para 30 dias de obra.
Uso: python -m scripts.seed_demo
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import date, timedelta, datetime
import random

from app.database import SessionLocal, engine, Base
from app.models import (
    Empresa, Obra, Usuario, Atividade, AtividadeStatus,
    Efetivo, TipoEfetivo, Anotacao, Material, Equipamento,
    Clima, DiaImprodutivo, Expediente, DiarioDia, DiarioStatus,
)
from app.core.auth import hash_password


def seed():
    db = SessionLocal()
    try:
        # === Empresa ===
        empresa = db.query(Empresa).filter(
            (Empresa.nome == "Construtora Demo Ltda") | (Empresa.cnpj == "12.345.678/0001-90")
        ).first()
        if not empresa:
            empresa = Empresa(nome="Construtora Demo Ltda", cnpj="12.345.678/0001-90")
            db.add(empresa)
            db.flush()
        print(f"Empresa: {empresa.nome} (id={empresa.id})")

        # === Usuarios ===
        admin = _get_or_create_user(db, "Carlos Silva", "11999990001", "admin", empresa.id, "carlos@demo.com")
        eng = _get_or_create_user(db, "Ana Souza", "11999990002", "engenheiro", empresa.id, "ana@demo.com")
        est = _get_or_create_user(db, "Pedro Lima", "11999990003", "estagiario", empresa.id, "pedro@demo.com")

        # === Obras ===
        obra1 = _get_or_create_obra(db, "Edifício Aurora - 12 Pavimentos", "Rua das Flores, 100 - Centro", empresa.id, admin.id)
        obra2 = _get_or_create_obra(db, "Residencial Parque Verde", "Av. Brasil, 500 - Jardim América", empresa.id, admin.id)

        print(f"Obra 1: {obra1.nome} (id={obra1.id})")
        print(f"Obra 2: {obra2.nome} (id={obra2.id})")

        # === 30 dias de dados para Obra 1 ===
        hoje = date.today()
        inicio = hoje - timedelta(days=30)

        # Atividades (criadas uma vez, duram vários dias)
        atividades = _create_atividades(db, obra1.id, inicio)

        for dia_offset in range(31):
            d = inicio + timedelta(days=dia_offset)

            # Pular domingos
            if d.weekday() == 6:
                continue

            is_chuva = random.random() < 0.15  # 15% chance de chuva

            # Clima
            _create_clima(db, obra1.id, d, is_chuva)

            if is_chuva and random.random() < 0.7:
                # Dia improdutivo por chuva
                _get_or_create_dia_improdutivo(db, obra1.id, d)
                # Efetivo reduzido
                _create_efetivo(db, obra1.id, d, scale=0.3)
            else:
                _create_efetivo(db, obra1.id, d, scale=1.0)

            # Atualizar progresso de atividades
            _update_atividades(db, atividades, d, is_chuva)

            # Materiais (entrada esporádica)
            if random.random() < 0.3:
                _create_material(db, obra1.id, d)

            # Equipamentos
            _create_equipamentos(db, obra1.id, d)

            # Anotações
            if random.random() < 0.4:
                _create_anotacao(db, obra1.id, d, is_chuva)

            # Expediente
            _get_or_create_expediente(db, obra1.id, d, is_chuva)

            # DiarioDia — primeiros 20 dias aprovados, últimos 10 rascunho
            if dia_offset < 20:
                _create_diario(db, obra1.id, d, DiarioStatus.APROVADO, admin.id, eng.id)
            elif dia_offset < 25:
                _create_diario(db, obra1.id, d, DiarioStatus.EM_REVISAO, None, eng.id)
            else:
                _create_diario(db, obra1.id, d, DiarioStatus.RASCUNHO, None, None)

        # Materiais pendentes (atrasados — para gerar alertas)
        _create_materiais_pendentes(db, obra1.id, hoje)

        # === Dados básicos para Obra 2 ===
        for dia_offset in range(10):
            d = hoje - timedelta(days=dia_offset)
            if d.weekday() == 6:
                continue
            _create_clima(db, obra2.id, d, False)
            _create_efetivo(db, obra2.id, d, scale=0.6)

        db.commit()
        print("\nSeed completo!")
        print(f"  Admin login: carlos@demo.com / demo123")
        print(f"  Engenheiro: ana@demo.com / demo123")
        print(f"  Estagiário: pedro@demo.com / demo123")

    except Exception as e:
        db.rollback()
        print(f"Erro: {e}")
        raise
    finally:
        db.close()


def _get_or_create_user(db, nome, telefone, role, empresa_id, email):
    user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not user:
        user = Usuario(
            nome=nome, telefone=telefone, role=role,
            email=email, senha_hash=hash_password("demo123"),
        )
        db.add(user)
        db.flush()
    elif not user.senha_hash:
        user.senha_hash = hash_password("demo123")
        user.email = email
    return user


def _get_or_create_obra(db, nome, endereco, empresa_id, admin_id):
    obra = db.query(Obra).filter(Obra.nome == nome).first()
    if not obra:
        obra = Obra(
            nome=nome, endereco=endereco,
            empresa_id=empresa_id, usuario_admin=admin_id,
            data_inicio=date.today() - timedelta(days=60),
            data_fim_prevista=date.today() + timedelta(days=180),
            status="ativa",
        )
        db.add(obra)
        db.flush()
    return obra


ATIVIDADES_TEMPLATE = [
    ("Concretagem laje 5º pavimento", "5º Pavimento", "Estrutura", -28, -20),
    ("Alvenaria interna 4º pavimento", "4º Pavimento", "Alvenaria", -25, -10),
    ("Instalações hidráulicas 3º pavimento", "3º Pavimento", "Instalações", -20, -5),
    ("Reboco externo fachada norte", "Fachada Norte", "Acabamento", -18, None),
    ("Montagem de formas 6º pavimento", "6º Pavimento", "Estrutura", -15, None),
    ("Passagem de eletrodutos 4º pavimento", "4º Pavimento", "Instalações", -12, None),
    ("Contrapiso 3º pavimento", "3º Pavimento", "Acabamento", -8, None),
    ("Impermeabilização banheiros 2º pav", "2º Pavimento", "Impermeabilização", -5, None),
]


def _create_atividades(db, obra_id, inicio):
    atividades = []
    for descricao, local, etapa, start_offset, end_offset in ATIVIDADES_TEMPLATE:
        existing = db.query(Atividade).filter(
            Atividade.obra_id == obra_id, Atividade.descricao == descricao
        ).first()
        if existing:
            atividades.append(existing)
            continue

        data_inicio = inicio - timedelta(days=abs(start_offset)) if start_offset < 0 else inicio + timedelta(days=start_offset)
        a = Atividade(
            obra_id=obra_id, descricao=descricao, local=local, etapa=etapa,
            data_inicio=data_inicio,
            data_fim_prevista=data_inicio + timedelta(days=random.randint(8, 15)),
            status=AtividadeStatus.INICIADA,
            percentual_concluido=0.0,
        )
        db.add(a)
        db.flush()
        atividades.append(a)
    return atividades


def _update_atividades(db, atividades, current_date, is_chuva):
    for a in atividades:
        if a.status == AtividadeStatus.CONCLUIDA:
            continue
        if current_date < a.data_inicio:
            continue

        # Avançar progresso
        if a.status == AtividadeStatus.INICIADA:
            a.status = AtividadeStatus.EM_ANDAMENTO

        if not is_chuva:
            increment = random.uniform(3, 12)
            a.percentual_concluido = min(100, a.percentual_concluido + increment)

        if a.percentual_concluido >= 100:
            a.status = AtividadeStatus.CONCLUIDA
            a.data_fim_real = current_date
            a.percentual_concluido = 100

        # Calcular atraso
        if a.data_fim_prevista and current_date > a.data_fim_prevista and a.status != AtividadeStatus.CONCLUIDA:
            a.dias_atraso = (current_date - a.data_fim_prevista).days


FUNCOES = [
    ("Pedreiro", 4, 8), ("Servente", 6, 12), ("Eletricista", 1, 3),
    ("Encanador", 1, 2), ("Carpinteiro", 2, 4), ("Armador", 2, 5),
    ("Mestre de Obras", 1, 1), ("Engenheiro Civil", 1, 1),
]


def _create_efetivo(db, obra_id, d, scale=1.0):
    for funcao, min_q, max_q in FUNCOES:
        existing = db.query(Efetivo).filter(
            Efetivo.obra_id == obra_id, Efetivo.data == d, Efetivo.funcao == funcao
        ).first()
        if existing:
            continue
        qtd = max(1, int(random.randint(min_q, max_q) * scale))
        if scale < 0.5 and random.random() < 0.4:
            continue  # pular algumas funções em dias de chuva
        db.add(Efetivo(
            obra_id=obra_id, data=d, funcao=funcao, quantidade=qtd,
            empresa="própria", tipo=TipoEfetivo.PROPRIO,
        ))


def _create_clima(db, obra_id, d, is_chuva):
    for periodo in ["manhã", "tarde"]:
        existing = db.query(Clima).filter(
            Clima.obra_id == obra_id, Clima.data == d, Clima.periodo == periodo
        ).first()
        if existing:
            continue

        if is_chuva:
            condicao = random.choice(["Chuva forte", "Chuva moderada", "Chuva intermitente"])
            temp = random.uniform(18, 24)
            impacto = "Trabalho externo paralisado" if "forte" in condicao else "Ritmo reduzido"
        else:
            condicao = random.choice(["Ensolarado", "Nublado", "Parcialmente nublado"])
            temp = random.uniform(22, 32)
            impacto = None

        db.add(Clima(
            obra_id=obra_id, data=d, periodo=periodo,
            condicao=condicao, temperatura=round(temp, 1),
            impacto_trabalho=impacto,
        ))


MATERIAIS_ENTRADA = [
    ("Cimento CP-II", "saco", 50, 200),
    ("Areia média", "m³", 5, 20),
    ("Brita 1", "m³", 5, 15),
    ("Vergalhão CA-50 10mm", "barra", 50, 200),
    ("Tijolo cerâmico 9x19x29", "milheiro", 1, 5),
    ("Tubo PVC 100mm", "barra", 10, 30),
]


def _create_material(db, obra_id, d):
    mat, unidade, min_q, max_q = random.choice(MATERIAIS_ENTRADA)
    db.add(Material(
        obra_id=obra_id, data=d, tipo="entrada",
        material=mat, quantidade=random.randint(min_q, max_q),
        unidade=unidade, fornecedor=random.choice(["Leroy Merlin", "Votorantim", "Gerdau", "Tigre"]),
    ))


def _create_materiais_pendentes(db, obra_id, hoje):
    pendentes = [
        ("Porcelanato 60x60 Bege", "m²", 5),
        ("Esquadria alumínio 1.20x1.50", "un", 3),
        ("Tinta acrílica Branco Neve", "lata", 1),
    ]
    for mat, unidade, dias_atraso in pendentes:
        existing = db.query(Material).filter(
            Material.obra_id == obra_id, Material.material == mat, Material.tipo == "pendente"
        ).first()
        if existing:
            continue
        db.add(Material(
            obra_id=obra_id, data=hoje - timedelta(days=dias_atraso + 5),
            tipo="pendente", material=mat, quantidade=random.randint(10, 100),
            unidade=unidade, data_prevista=hoje - timedelta(days=dias_atraso),
        ))


EQUIPAMENTOS = [
    ("Betoneira 400L", "operação", 1), ("Vibrador de concreto", "operação", 1),
    ("Guincho de coluna", "operação", 1), ("Serra circular", "operação", 2),
]


def _create_equipamentos(db, obra_id, d):
    for eq, tipo, qtd in EQUIPAMENTOS:
        existing = db.query(Equipamento).filter(
            Equipamento.obra_id == obra_id, Equipamento.data == d, Equipamento.equipamento == eq
        ).first()
        if existing:
            continue
        if random.random() < 0.3:
            continue
        db.add(Equipamento(
            obra_id=obra_id, data=d, tipo=tipo,
            equipamento=eq, quantidade=qtd,
            horas_trabalhadas=round(random.uniform(4, 8), 1),
        ))


ANOTACOES = [
    ("Chuva forte paralisou concretagem às 14h", "ocorrência", "alta"),
    ("Falta de material: esquadrias ainda não entregues", "pendência", "alta"),
    ("Vizinho reclamou de barulho no horário de almoço", "ocorrência", "normal"),
    ("Concretagem executada conforme especificação", "observação", "normal"),
    ("Teste de estanqueidade hidráulica OK no 3º pav", "observação", "normal"),
    ("Necessário reforço de mão de obra na próxima semana", "pendência", "alta"),
    ("Equipe de elétrica iniciou passagem de eletrodutos", "observação", "baixa"),
]


def _create_anotacao(db, obra_id, d, is_chuva):
    if is_chuva:
        choices = [a for a in ANOTACOES if "chuva" in a[0].lower() or "ocorrência" in a[1]]
    else:
        choices = [a for a in ANOTACOES if "chuva" not in a[0].lower()]
    if not choices:
        choices = ANOTACOES
    desc, tipo, prio = random.choice(choices)
    db.add(Anotacao(
        obra_id=obra_id, data=d, descricao=desc,
        tipo=tipo, prioridade=prio,
    ))


def _get_or_create_dia_improdutivo(db, obra_id, d):
    existing = db.query(DiaImprodutivo).filter(
        DiaImprodutivo.obra_id == obra_id, DiaImprodutivo.data == d
    ).first()
    if existing:
        return
    db.add(DiaImprodutivo(
        obra_id=obra_id, data=d,
        motivo="Chuva forte impossibilitou trabalho externo",
        horas_perdidas=random.choice([4.0, 6.0, 8.0]),
    ))


def _get_or_create_expediente(db, obra_id, d, is_chuva):
    existing = db.query(Expediente).filter(
        Expediente.obra_id == obra_id, Expediente.data == d
    ).first()
    if existing:
        return
    db.add(Expediente(
        obra_id=obra_id, data=d,
        hora_inicio="07:00",
        hora_termino="16:00" if is_chuva else "17:00",
    ))


def _create_diario(db, obra_id, d, status, aprovado_por_id, submetido_por_id):
    existing = db.query(DiarioDia).filter(
        DiarioDia.obra_id == obra_id, DiarioDia.data == d
    ).first()
    if existing:
        return

    diario = DiarioDia(obra_id=obra_id, data=d, status=status)
    if submetido_por_id:
        diario.submetido_por_id = submetido_por_id
        diario.submetido_em = datetime.combine(d, datetime.min.time().replace(hour=17))
    if aprovado_por_id and status == DiarioStatus.APROVADO:
        diario.aprovado_por_id = aprovado_por_id
        diario.aprovado_em = datetime.combine(d + timedelta(days=1), datetime.min.time().replace(hour=9))
    db.add(diario)


if __name__ == "__main__":
    seed()
