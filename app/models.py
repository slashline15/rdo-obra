"""
Models SQLAlchemy — PostgreSQL.
Relações lógicas entre tabelas documentadas nos comentários.
"""
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, Date, DateTime,
    ForeignKey, JSON, Enum as SAEnum, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import date
import enum

from app.database import Base
from app.core.time import utc_now
from app.core.vector import VectorEmbeddingType


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


class TipoVinculo(str, enum.Enum):
    CLT = "clt"
    TERCEIRIZADO = "terceirizado"
    TEMPORARIO = "temporario"
    AUTONOMO = "autonomo"


class DiarioStatus(str, enum.Enum):
    RASCUNHO = "rascunho"
    EM_REVISAO = "em_revisao"
    APROVADO = "aprovado"
    REABERTO = "reaberto"


class AlertaSeveridade(str, enum.Enum):
    ALTA = "alta"
    MEDIA = "media"
    BAIXA = "baixa"


# === Empresa ===
class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    cnpj = Column(String(18), unique=True)
    logo = Column(String(500))
    template_pdf = Column(String(100), default="rdo_default.html")
    config = Column(JSON, default={})  # cores, layout, campos extras
    created_at = Column(DateTime, default=utc_now)

    obras = relationship("Obra", back_populates="empresa")
    funcoes = relationship("Funcao", back_populates="empresa")


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
    usuario_admin = Column(
        Integer,
        ForeignKey("usuarios.id", use_alter=True, name="fk_obras_usuario_admin"),
        nullable=True,
    )

    # Horário padrão do expediente (HH:MM) — override diário via Expediente
    hora_inicio_padrao = Column(String(5), default="07:00")
    hora_termino_padrao = Column(String(5), default="17:00")

    created_at = Column(DateTime, default=utc_now)

    empresa = relationship("Empresa", back_populates="obras")
    admin = relationship("Usuario", foreign_keys=[usuario_admin])
    usuarios = relationship("Usuario", back_populates="obra", foreign_keys="Usuario.obra_id")
    atividades = relationship("Atividade", back_populates="obra")
    efetivo = relationship("Efetivo", back_populates="obra")
    anotacoes = relationship("Anotacao", back_populates="obra")
    materiais = relationship("Material", back_populates="obra")
    equipamentos = relationship("Equipamento", back_populates="obra")
    climas = relationship("Clima", back_populates="obra")
    fotos = relationship("Foto", back_populates="obra")
    dias_improdutivos = relationship("DiaImprodutivo", back_populates="obra")
    expedientes = relationship("Expediente", back_populates="obra")
    solicitacoes_cadastro = relationship("SolicitacaoCadastro", back_populates="obra")


# === Usuário ===
class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    telefone = Column(String(20), unique=True, nullable=False)
    obra_id = Column(Integer, ForeignKey("obras.id"))
    email = Column(String(255), nullable=True, unique=True)
    senha_hash = Column(String(255), nullable=True)
    role = Column(String(20), default="estagiario")
    nivel_acesso = Column(Integer, nullable=False, default=3)
    pode_aprovar_diario = Column(Boolean, default=False)
    registro_profissional = Column(String(255), nullable=True)
    empresa_vinculada = Column(String(255), nullable=True)
    ativo = Column(Boolean, default=True)
    canal_preferido = Column(String(20), default="whatsapp")  # whatsapp, telegram
    telegram_chat_id = Column(String(50))  # para envio direto no Telegram
    created_at = Column(DateTime, default=utc_now)

    obra = relationship("Obra", back_populates="usuarios", foreign_keys=[obra_id])


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
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    obra = relationship("Obra", back_populates="atividades")
    atividade_pai = relationship("Atividade", remote_side=[id])
    historico = relationship("AtividadeHistorico", back_populates="atividade")


class AtividadeEmbedding(Base):
    __tablename__ = "atividade_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    obra_id = Column(Integer, ForeignKey("obras.id"), nullable=False, index=True)
    atividade_id = Column(Integer, ForeignKey("atividades.id"), nullable=False, unique=True)
    texto_canonico = Column(Text, nullable=False)
    embedding = Column(VectorEmbeddingType(1024), nullable=True)
    embedding_model = Column(String(100), nullable=False, default="qwen3-embedding:0.6b")
    embedding_dim = Column(Integer, nullable=False, default=1024)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    atividade = relationship("Atividade")


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
    created_at = Column(DateTime, default=utc_now)

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
    created_at = Column(DateTime, default=utc_now)

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
    created_at = Column(DateTime, default=utc_now)

    obra = relationship("Obra", back_populates="expedientes")

    __table_args__ = (
        UniqueConstraint("obra_id", "data", name="uq_expediente_dia"),
    )


# === Função ===
# Catálogo normalizado de funções (pedreiro, servente, carpinteiro…).
# Evita divergência de nomes nos lançamentos de efetivo.
class Funcao(Base):
    __tablename__ = "funcoes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    ativa = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    empresa = relationship("Empresa")
    colaboradores = relationship("Colaborador", back_populates="funcao_ref")

    __table_args__ = (
        UniqueConstraint("nome", "empresa_id", name="uq_funcao_empresa"),
    )


# === Colaborador ===
# Cadastro individual de mão de obra. Isolado no MVP — preenchimento via
# IA/QR-code/Telegram será adicionado depois. FKs nullable para não bloquear
# o lançamento por grupo que o MVP usa.
class Colaborador(Base):
    __tablename__ = "colaboradores"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    apelido = Column(String(100), nullable=True)

    funcao_id = Column(Integer, ForeignKey("funcoes.id"), nullable=True)
    obra_id = Column(Integer, ForeignKey("obras.id"), nullable=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)

    tipo_vinculo = Column(
        SAEnum(TipoVinculo, values_callable=lambda x: [e.value for e in x]),
        nullable=True
    )

    ativo = Column(Boolean, default=True)
    observacoes = Column(Text, nullable=True)       # notas internas, sem registro no diário
    qrcode_hash = Column(String(64), nullable=True)  # futuro: leitura de QR-code

    # Rateio entre obras — nullable, pós-MVP
    rateio_obra_ids = Column(JSON, nullable=True)    # ex: [{"obra_id": 2, "pct": 50}, ...]

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    funcao_ref = relationship("Funcao", back_populates="colaboradores")
    obra = relationship("Obra")
    empresa = relationship("Empresa")


# === Efetivo ===
# Lançamento diário de mão de obra por grupo (quantidade × função).
# Dividido em dois tipos:
#   proprio     → subtotais por função
#   empreiteiro → subtotais por empresa terceirizada
#
# No RDO:
#   Total empresa      = sum(proprio)
#   Total empreiteiras = sum(empreiteiro, group_by empresa)
#   Total geral        = total empresa + total empreiteiras
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

    # --- função ---
    # funcao (string) mantida para compatibilidade com dados existentes
    # funcao_id (FK) é a referência normalizada — transição gradual
    funcao = Column(String(100))
    funcao_id = Column(Integer, ForeignKey("funcoes.id"), nullable=True)

    quantidade = Column(Integer, nullable=False)
    empresa = Column(String(255))  # null = própria empresa

    # Colaborador individual — nullable, pós-MVP (lançamento por indivíduo)
    colaborador_id = Column(Integer, ForeignKey("colaboradores.id"), nullable=True)

    # Observação pública (vai pro RDO) vs interna (apenas gestão)
    observacoes = Column(Text)
    observacao_interna = Column(Text, nullable=True)  # ex: "fiscal viu problema na armação"

    registrado_por = Column(String(255))
    texto_original = Column(Text)
    created_at = Column(DateTime, default=utc_now)

    obra = relationship("Obra", back_populates="efetivo")
    funcao_ref = relationship("Funcao")
    colaborador = relationship("Colaborador")


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
    created_at = Column(DateTime, default=utc_now)

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
    created_at = Column(DateTime, default=utc_now)

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
    created_at = Column(DateTime, default=utc_now)

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
    created_at = Column(DateTime, default=utc_now)

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
    created_at = Column(DateTime, default=utc_now)

    obra = relationship("Obra", back_populates="fotos")


class SolicitacaoCadastro(Base):
    __tablename__ = "solicitacoes_cadastro"

    id = Column(Integer, primary_key=True, index=True)
    obra_id = Column(Integer, ForeignKey("obras.id"), nullable=False)
    solicitante_chat_id = Column(String(20), nullable=False, index=True)
    solicitante_nome = Column(String(255))
    solicitante_username = Column(String(255))
    status = Column(String(20), nullable=False, default="pendente")  # pendente, aprovado, rejeitado
    admin_decisor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    observacao = Column(Text)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    obra = relationship("Obra", back_populates="solicitacoes_cadastro")


class ConversationState(Base):
    __tablename__ = "conversation_states"

    id = Column(Integer, primary_key=True, index=True)
    channel = Column(String(20), nullable=False, index=True)
    scope_key = Column(String(120), nullable=False, unique=True, index=True)
    state_type = Column(String(50), nullable=False, index=True)
    state_token = Column(String(64), nullable=False, unique=True, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    text_original = Column(Text, nullable=True)
    source_message_id = Column(String(120), nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    consumed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


# === Diário do Dia ===
# Representa um dia de uma obra como unidade revisável/aprovável.
# Auto-criado como rascunho no primeiro acesso via painel.
class DiarioDia(Base):
    __tablename__ = "diarios_dia"

    id = Column(Integer, primary_key=True, index=True)
    obra_id = Column(Integer, ForeignKey("obras.id"), nullable=False)
    data = Column(Date, nullable=False)
    status = Column(
        SAEnum(DiarioStatus, values_callable=lambda x: [e.value for e in x]),
        default=DiarioStatus.RASCUNHO
    )
    submetido_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    submetido_em = Column(DateTime, nullable=True)
    aprovado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    aprovado_em = Column(DateTime, nullable=True)
    observacao_aprovacao = Column(Text, nullable=True)
    pdf_path = Column(String(500), nullable=True)
    deletado_em = Column(DateTime, nullable=True)
    deletado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    motivo_exclusao = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    obra = relationship("Obra")
    submetido_por = relationship("Usuario", foreign_keys=[submetido_por_id])
    aprovado_por = relationship("Usuario", foreign_keys=[aprovado_por_id])
    deletado_por = relationship("Usuario", foreign_keys=[deletado_por_id])

    __table_args__ = (
        UniqueConstraint("obra_id", "data", name="uq_diario_dia"),
    )


# === Audit Log ===
# Uma row por campo alterado. Genérico para qualquer entidade.
class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    obra_id = Column(Integer, ForeignKey("obras.id"), nullable=False)
    data_ref = Column(Date, nullable=False)
    tabela = Column(String(50), nullable=False)
    registro_id = Column(Integer, nullable=False)
    campo = Column(String(100), nullable=False)
    valor_anterior = Column(Text, nullable=True)
    valor_novo = Column(Text, nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    created_at = Column(DateTime, default=utc_now)

    usuario = relationship("Usuario")


# === Alertas ===
# Alertas materializados pelo alert engine, avaliados lazy no GET /painel.
class Alerta(Base):
    __tablename__ = "alertas"

    id = Column(Integer, primary_key=True, index=True)
    obra_id = Column(Integer, ForeignKey("obras.id"), nullable=False)
    data = Column(Date, nullable=False)
    regra = Column(String(50), nullable=False)
    severidade = Column(
        SAEnum(AlertaSeveridade, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    mensagem = Column(Text, nullable=False)
    resolvido = Column(Boolean, default=False)
    resolvido_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    resolvido_em = Column(DateTime, nullable=True)
    dados_contexto = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    obra = relationship("Obra")
    resolvido_por = relationship("Usuario")


class ConviteAcesso(Base):
    __tablename__ = "convites_acesso"

    id = Column(Integer, primary_key=True, index=True)
    obra_id = Column(Integer, ForeignKey("obras.id"), nullable=True)
    email = Column(String(255), nullable=False)
    telefone = Column(String(20), nullable=True)
    role = Column(String(50), nullable=False, default="encarregado")
    nivel_acesso = Column(Integer, nullable=False, default=3)
    pode_aprovar_diario = Column(Boolean, default=False)
    cargo = Column(String(255), nullable=True)
    token_hash = Column(String(64), nullable=False, unique=True)
    status = Column(String(20), nullable=False, default="pendente")
    request_metadata = Column(JSON, default={})
    criado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    usado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    expira_em = Column(DateTime, nullable=False)
    usado_em = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    obra = relationship("Obra")
    criado_por = relationship("Usuario", foreign_keys=[criado_por_id])
    usado_por = relationship("Usuario", foreign_keys=[usado_por_id])


# === WhatsApp Instância ===
class WhatsAppInstancia(Base):
    """Cada usuário possui no máximo uma instância no Evolution API.
    O nome da instância é o número de telefone normalizado (apenas dígitos).
    O escopo das mensagens recebidas se limita às obras associadas a esse usuário.
    """
    __tablename__ = "whatsapp_instancias"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), unique=True, nullable=False)

    # Nome da instância no Evolution API (= telefone normalizado, ex: "5511999998888")
    nome_instancia = Column(String(50), unique=True, nullable=False)

    # Número de telefone do bot/número cadastrado para esta instância
    numero_bot = Column(String(20), nullable=True)  # preenchido após conexão

    # Status: pending | connecting | open | close
    status = Column(String(20), default="pending", nullable=False)

    # Webhook configurado nesta instância no Evolution
    webhook_configurado = Column(Boolean, default=False)

    # Data de criação e última atualização de status
    criado_em = Column(DateTime, default=utc_now)
    atualizado_em = Column(DateTime, default=utc_now, onupdate=utc_now)

    usuario = relationship("Usuario", backref="whatsapp_instancia")
