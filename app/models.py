"""
Models SQLAlchemy — PostgreSQL.
Relações lógicas entre tabelas documentadas nos comentários.
"""
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, Date, DateTime,
    ForeignKey, JSON, Enum as SAEnum, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime, date
import enum

from app.database import Base


# === Enums ===
class AtividadeStatus(str, enum.Enum):
    INICIADA = "iniciada"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"
    PAUSADA = "pausada"
    CANCELADA = "cancelada"


class MovimentacaoTipo(str, enum.Enum):
    ENTRADA = "entrada"
    SAIDA = "saída"


class StatusPluviometrico(str, enum.Enum):
    SECO_PRODUTIVO = "seco_produtivo"
    SECO_IMPRODUTIVO = "seco_improdutivo"
    CHUVA_PRODUTIVA = "chuva_produtiva"
    CHUVA_IMPRODUTIVA = "chuva_improdutiva"
    SEM_EXPEDIENTE = "sem_expediente"


class AnotacaoTipo(str, enum.Enum):
    OBSERVACAO = "observação"
    OCORRENCIA = "ocorrência"
    PENDENCIA = "pendência"
    ALERTA = "alerta"
    ATRASO = "atraso"  # gerado automaticamente pelo relation engine


class Prioridade(str, enum.Enum):
    BAIXA = "baixa"
    NORMAL = "normal"
    ALTA = "alta"
    URGENTE = "urgente"


class TipoEfetivo(str, enum.Enum):
    PROPRIO = "proprio"        # mão de obra da própria empresa
    EMPREITEIRO = "empreiteiro"  # empresa terceirizada


# === Empresa ===
class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    cnpj = Column(String(18), unique=True)
    logo = Column(String(500))
    template_pdf = Column(String(100), default="rdo_default.html")
    config = Column(JSON, default={})  # cores, layout, campos extras
    created_at = Column(DateTime, default=datetime.utcnow)

    obras = relationship("Obra", back_populates="empresa")


# === Obra ===
class Obra(Base):
    __tablename__ = "obras"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    endereco = Column(Text)
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    responsavel = Column(String(255))
    data_inicio = Column(Date)
    data_fim_prevista = Column(Date)
    status = Column(String(20), default="ativa")
    config = Column(JSON, default={})  # configurações específicas da obra
    usuario_admin = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    # Horário padrão do expediente (HH:MM) — override diário via Expediente
    hora_inicio_padrao = Column(String(5), default="07:00")
    hora_termino_padrao = Column(String(5), default="17:00")

    created_at = Column(DateTime, default=datetime.utcnow)

    empresa = relationship("Empresa", back_populates="obras")
    admin = relationship("Usuario", foreign_keys=[usuario_admin])
    usuarios = relationship("Usuario", back_populates="obra")
    atividades = relationship("Atividade", back_populates="obra")
    efetivo = relationship("Efetivo", back_populates="obra")
    anotacoes = relationship("Anotacao", back_populates="obra")
    materiais = relationship("Material", back_populates="obra")
    equipamentos = relationship("Equipamento", back_populates="obra")
    climas = relationship("Clima", back_populates="obra")
    fotos = relationship("Foto", back_populates="obra")
    dias_improdutivos = relationship("DiaImprodutivo", back_populates="obra")
    expedientes = relationship("Expediente", back_populates="obra")


# === Usuário ===
class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    telefone = Column(String(20), unique=True, nullable=False)
    obra_id = Column(Integer, ForeignKey("obras.id"))
    role = Column(String(20), default="estagiario")
    ativo = Column(Boolean, default=True)
    canal_preferido = Column(String(20), default="whatsapp")  # whatsapp, telegram
    telegram_chat_id = Column(String(50))  # para envio direto no Telegram
    created_at = Column(DateTime, default=datetime.utcnow)

    obra = relationship("Obra", back_populates="usuarios")


# === Atividade (ex-Serviço) ===
# REGRAS:
# - Tem data_inicio e data_fim (previsão + real)
# - Entre início e fim, aparece como "em_andamento" automaticamente
# - Descrição técnica é redigida pelo LLM e NÃO muda durante o andamento
# - No RDO aparece em 3 seções: Iniciadas | Em Andamento | Concluídas
# - Dia improdutivo → atraso automático via Relation Engine
class Atividade(Base):
    __tablename__ = "atividades"

    id = Column(Integer, primary_key=True, index=True)
    obra_id = Column(Integer, ForeignKey("obras.id"), nullable=False)

    # Descrição técnica (redigida pelo LLM, consistente entre diários)
    descricao = Column(Text, nullable=False)
    local = Column(String(255))  # ex: "2º Pavimento", "Bloco A"
    etapa = Column(String(100))  # ex: "Estrutura", "Acabamento"

    # Datas
    data_inicio = Column(Date, nullable=False)
    data_fim_prevista = Column(Date)
    data_fim_real = Column(Date)  # preenchido quando conclui

    # Status
    status = Column(
        SAEnum(AtividadeStatus, values_callable=lambda x: [e.value for e in x]),
        default=AtividadeStatus.INICIADA
    )

    # Progresso
    percentual_concluido = Column(Float, default=0.0)
    dias_atraso = Column(Integer, default=0)  # atualizado pelo Relation Engine

    # Dependências (atividade anterior que precisa terminar antes)
    atividade_pai_id = Column(Integer, ForeignKey("atividades.id"), nullable=True)

    # Metadados
    observacoes = Column(Text)
    registrado_por = Column(String(255))
    texto_original = Column(Text)  # fala original do usuário
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    obra = relationship("Obra", back_populates="atividades")
    atividade_pai = relationship("Atividade", remote_side=[id])
    historico = relationship("AtividadeHistorico", back_populates="atividade")


# === Histórico de Atividade ===
# Registra mudanças de status para auditoria
class AtividadeHistorico(Base):
    __tablename__ = "atividade_historico"

    id = Column(Integer, primary_key=True, index=True)
    atividade_id = Column(Integer, ForeignKey("atividades.id"), nullable=False)
    data = Column(Date, nullable=False)
    status_anterior = Column(String(20))
    status_novo = Column(String(20), nullable=False)
    motivo = Column(Text)  # ex: "Chuva", "Material pendente"
    registrado_por = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

    atividade = relationship("Atividade", back_populates="historico")


# === Dia Improdutivo ===
# RELAÇÃO: clima.improdutivo → registra aqui → impacta atividades em andamento
class DiaImprodutivo(Base):
    __tablename__ = "dias_improdutivos"

    id = Column(Integer, primary_key=True, index=True)
    obra_id = Column(Integer, ForeignKey("obras.id"), nullable=False)
    data = Column(Date, nullable=False)
    motivo = Column(Text, nullable=False)  # "Chuva", "Feriado", "Falta de material"
    clima_id = Column(Integer, ForeignKey("clima.id"), nullable=True)  # se causado por clima
    impacto = Column(Text)  # descrição do impacto
    horas_perdidas = Column(Float)  # horas efetivamente perdidas
    created_at = Column(DateTime, default=datetime.utcnow)

    obra = relationship("Obra", back_populates="dias_improdutivos")
    clima_ref = relationship("Clima")

    __table_args__ = (
        UniqueConstraint("obra_id", "data", name="uq_dia_improdutivo"),
    )


# === Expediente ===
# Override diário dos horários padrão da obra.
# Se não existir registro para o dia, usa obra.hora_inicio_padrao / hora_termino_padrao.
class Expediente(Base):
    __tablename__ = "expediente"

    id = Column(Integer, primary_key=True, index=True)
    obra_id = Column(Integer, ForeignKey("obras.id"), nullable=False)
    data = Column(Date, nullable=False)
    hora_inicio = Column(String(5), nullable=False)   # HH:MM
    hora_termino = Column(String(5), nullable=False)  # HH:MM
    motivo = Column(Text)  # ex: "concretagem estendida", "recuperar atraso"
    registrado_por = Column(String(255))
    texto_original = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    obra = relationship("Obra", back_populates="expedientes")

    __table_args__ = (
        UniqueConstraint("obra_id", "data", name="uq_expediente_dia"),
    )


# === Efetivo ===
# Dividido em dois grupos:
#   proprio     → cargos padronizados da empresa, basta informar funcao + quantidade
#   empreiteiro → empresa terceirizada + total de funcionários
#
# No RDO:
#   Total empresa   = sum(proprio)
#   Total empreiteiras = sum(empreiteiro, group_by empresa)
#   Total geral     = total empresa + total empreiteiras  ← efetivo oficial
class Efetivo(Base):
    __tablename__ = "efetivo"

    id = Column(Integer, primary_key=True, index=True)
    obra_id = Column(Integer, ForeignKey("obras.id"), nullable=False)
    data = Column(Date, default=date.today)

    tipo = Column(
        SAEnum(TipoEfetivo, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=TipoEfetivo.PROPRIO
    )

    # Próprio: funcao obrigatória (pedreiro, servente, etc.)
    # Empreiteiro: funcao pode ser omitida (só conta o total por empresa)
    funcao = Column(String(100))
    quantidade = Column(Integer, nullable=False)
    empresa = Column(String(255))  # null = própria empresa

    observacoes = Column(Text)
    registrado_por = Column(String(255))
    texto_original = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    obra = relationship("Obra", back_populates="efetivo")


# === Anotação ===
# RELAÇÃO: pode ser gerada automaticamente pelo Relation Engine
# (ex: atraso por clima, material pendente do cliente)
class Anotacao(Base):
    __tablename__ = "anotacoes"

    id = Column(Integer, primary_key=True, index=True)
    obra_id = Column(Integer, ForeignKey("obras.id"), nullable=False)
    data = Column(Date, default=date.today)
    tipo = Column(String(20), default="observação")
    descricao = Column(Text, nullable=False)
    prioridade = Column(String(10), default="normal")
    resolvida = Column(Boolean, default=False)
    data_resolucao = Column(Date)

    # Relações opcionais (de onde veio esta anotação)
    atividade_id = Column(Integer, ForeignKey("atividades.id"), nullable=True)
    material_id = Column(Integer, ForeignKey("materiais.id"), nullable=True)
    auto_gerada = Column(Boolean, default=False)  # True = gerada pelo sistema

    registrado_por = Column(String(255))
    texto_original = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    obra = relationship("Obra", back_populates="anotacoes")


# === Material ===
# RELAÇÃO: material pendente/atrasado → gera anotação automática
class Material(Base):
    __tablename__ = "materiais"

    id = Column(Integer, primary_key=True, index=True)
    obra_id = Column(Integer, ForeignKey("obras.id"), nullable=False)
    data = Column(Date, default=date.today)
    tipo = Column(String(10), nullable=False)  # entrada, saída, pendente
    material = Column(String(255), nullable=False)
    quantidade = Column(Float)
    unidade = Column(String(50))
    fornecedor = Column(String(255))
    nota_fiscal = Column(String(100))
    responsavel = Column(String(50), default="próprio")  # próprio ou cliente
    data_prevista = Column(Date)  # quando pendente, data prevista de chegada
    observacoes = Column(Text)
    registrado_por = Column(String(255))
    texto_original = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    obra = relationship("Obra", back_populates="materiais")


# === Equipamento ===
class Equipamento(Base):
    __tablename__ = "equipamentos"

    id = Column(Integer, primary_key=True, index=True)
    obra_id = Column(Integer, ForeignKey("obras.id"), nullable=False)
    data = Column(Date, default=date.today)
    tipo = Column(String(30), nullable=False)  # entrada, saída, manutenção, aluguel
    equipamento = Column(String(255), nullable=False)
    quantidade = Column(Integer, default=1)
    horas_trabalhadas = Column(Float)
    operador = Column(String(255))
    observacoes = Column(Text)
    registrado_por = Column(String(255))
    texto_original = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    obra = relationship("Obra", back_populates="equipamentos")


# === Clima ===
# RELAÇÃO: se impacto_trabalho indica parada → gera DiaImprodutivo
# Um registro por período (manhã/tarde/noite) por dia.
# status_pluviometrico alimenta o gráfico de disco do RDO.
class Clima(Base):
    __tablename__ = "clima"

    id = Column(Integer, primary_key=True, index=True)
    obra_id = Column(Integer, ForeignKey("obras.id"), nullable=False)
    data = Column(Date, default=date.today)
    periodo = Column(String(10), nullable=False, default="manhã")  # manhã | tarde | noite

    # Condição atmosférica detalhada
    condicao = Column(String(20))  # sol, nublado, chuva, chuvoso, tempestade

    # Anotação simplificada para o RDO (cabeçalho do relatório)
    anotacao_rdo = Column(String(5), default="sol")  # sol | chuva

    # Status para o gráfico pluviométrico (disco mensal)
    status_pluviometrico = Column(
        SAEnum(StatusPluviometrico, values_callable=lambda x: [e.value for e in x]),
        default=StatusPluviometrico.SECO_PRODUTIVO
    )

    temperatura = Column(Float)
    impacto_trabalho = Column(Text)   # descrição livre do impacto
    dia_improdutivo = Column(Boolean, default=False)  # flag legado — mantido por compatibilidade
    observacoes = Column(Text)
    texto_original = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    obra = relationship("Obra", back_populates="climas")

    __table_args__ = (
        UniqueConstraint("obra_id", "data", "periodo", name="uq_clima_periodo"),
    )


# === Foto ===
class Foto(Base):
    __tablename__ = "fotos"

    id = Column(Integer, primary_key=True, index=True)
    obra_id = Column(Integer, ForeignKey("obras.id"), nullable=False)
    data = Column(Date, default=date.today)
    arquivo = Column(String(500), nullable=False)
    descricao = Column(Text)
    categoria = Column(String(50))
    atividade_id = Column(Integer, ForeignKey("atividades.id"), nullable=True)  # foto vinculada a atividade
    registrado_por = Column(String(255))
    texto_original = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    obra = relationship("Obra", back_populates="fotos")
