from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List


# === Empresa ===
class EmpresaBase(BaseModel):
    nome: str
    cnpj: Optional[str] = None
    logo: Optional[str] = None
    template_pdf: Optional[str] = None
    config: Optional[dict] = {}

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaResponse(EmpresaBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# === Obra ===
class ObraBase(BaseModel):
    nome: str
    endereco: Optional[str] = None
    empresa_id: Optional[int] = None
    responsavel: Optional[str] = None
    data_inicio: Optional[date] = None
    data_fim_prevista: Optional[date] = None
    status: Optional[str] = "ativa"
    usuario_admin: Optional[int] = None

class ObraCreate(ObraBase):
    pass

class ObraResponse(ObraBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# === Usuario ===
class UsuarioBase(BaseModel):
    nome: str
    telefone: str
    obra_id: Optional[int] = None
    role: Optional[str] = "estagiario"
    ativo: Optional[bool] = True

class UsuarioCreate(UsuarioBase):
    pass

class UsuarioResponse(UsuarioBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# === Servico ===
class ServicoBase(BaseModel):
    obra_id: int
    data: Optional[date] = None
    descricao: str
    local: Optional[str] = None
    etapa: Optional[str] = None
    percentual_concluido: Optional[float] = 0.0
    observacoes: Optional[str] = None
    registrado_por: Optional[str] = None
    texto_original: Optional[str] = None

class ServicoCreate(ServicoBase):
    pass

class ServicoResponse(ServicoBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# === Efetivo ===
class EfetivoBase(BaseModel):
    obra_id: int
    data: Optional[date] = None
    funcao: str
    quantidade: int
    empresa: Optional[str] = "própria"
    observacoes: Optional[str] = None
    registrado_por: Optional[str] = None
    texto_original: Optional[str] = None

class EfetivoCreate(EfetivoBase):
    pass

class EfetivoResponse(EfetivoBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# === Anotacao ===
class AnotacaoBase(BaseModel):
    obra_id: int
    data: Optional[date] = None
    tipo: Optional[str] = "observação"
    descricao: str
    prioridade: Optional[str] = "normal"
    registrado_por: Optional[str] = None
    texto_original: Optional[str] = None

class AnotacaoCreate(AnotacaoBase):
    pass

class AnotacaoResponse(AnotacaoBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# === Material ===
class MaterialBase(BaseModel):
    obra_id: int
    data: Optional[date] = None
    tipo: str  # entrada ou saída
    material: str
    quantidade: Optional[float] = None
    unidade: Optional[str] = None
    fornecedor: Optional[str] = None
    nota_fiscal: Optional[str] = None
    observacoes: Optional[str] = None
    registrado_por: Optional[str] = None
    texto_original: Optional[str] = None

class MaterialCreate(MaterialBase):
    pass

class MaterialResponse(MaterialBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# === Equipamento ===
class EquipamentoBase(BaseModel):
    obra_id: int
    data: Optional[date] = None
    tipo: str  # entrada, saída, manutenção
    equipamento: str
    quantidade: Optional[int] = 1
    horas_trabalhadas: Optional[float] = None
    operador: Optional[str] = None
    observacoes: Optional[str] = None
    registrado_por: Optional[str] = None
    texto_original: Optional[str] = None

class EquipamentoCreate(EquipamentoBase):
    pass

class EquipamentoResponse(EquipamentoBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# === Clima ===
class ClimaBase(BaseModel):
    obra_id: int
    data: Optional[date] = None
    periodo: Optional[str] = None
    condicao: Optional[str] = None
    temperatura: Optional[float] = None
    impacto_trabalho: Optional[str] = None
    observacoes: Optional[str] = None
    texto_original: Optional[str] = None

class ClimaCreate(ClimaBase):
    pass

class ClimaResponse(ClimaBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# === Foto ===
class FotoBase(BaseModel):
    obra_id: int
    data: Optional[date] = None
    arquivo: str
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    registrado_por: Optional[str] = None
    texto_original: Optional[str] = None

class FotoCreate(FotoBase):
    pass

class FotoResponse(FotoBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# === Intent Classification (WhatsApp input) ===
class IntentResult(BaseModel):
    intent: str  # servico, efetivo, anotacao, material, equipamento, clima, foto, consulta
    confidence: float
    data: dict  # extracted structured data
    original_text: str
    requires_confirmation: bool = False
    confirmation_message: Optional[str] = None


# === WhatsApp Message ===
class WhatsAppMessage(BaseModel):
    telefone: str
    texto: Optional[str] = None
    audio_path: Optional[str] = None
    foto_path: Optional[str] = None
    legenda: Optional[str] = None


# === RDO (Relatório Diário de Obra) ===
class RDORequest(BaseModel):
    obra_id: int
    data: date
    formato: Optional[str] = "pdf"  # pdf ou json


# === Update schemas (partial — todos os campos Optional) ===

class EfetivoUpdate(BaseModel):
    funcao: Optional[str] = None
    quantidade: Optional[int] = None
    empresa: Optional[str] = None
    tipo: Optional[str] = None
    observacoes: Optional[str] = None

class AtividadeUpdate(BaseModel):
    status: Optional[str] = None
    percentual_concluido: Optional[float] = None
    observacoes: Optional[str] = None
    local: Optional[str] = None
    etapa: Optional[str] = None
    descricao: Optional[str] = None

class MaterialUpdate(BaseModel):
    tipo: Optional[str] = None
    quantidade: Optional[float] = None
    unidade: Optional[str] = None
    data_prevista: Optional[date] = None
    observacoes: Optional[str] = None

class EquipamentoUpdate(BaseModel):
    tipo: Optional[str] = None
    equipamento: Optional[str] = None
    quantidade: Optional[int] = None
    horas_trabalhadas: Optional[float] = None
    operador: Optional[str] = None
    observacoes: Optional[str] = None

class ClimaUpdate(BaseModel):
    condicao: Optional[str] = None
    temperatura: Optional[float] = None
    impacto_trabalho: Optional[str] = None
    status_pluviometrico: Optional[str] = None
    anotacao_rdo: Optional[str] = None

class AnotacaoUpdate(BaseModel):
    descricao: Optional[str] = None
    tipo: Optional[str] = None
    prioridade: Optional[str] = None
    resolvida: Optional[bool] = None


# === Workflow ===

class TransicaoDiario(BaseModel):
    acao: str  # submeter, aprovar, rejeitar, reabrir
    observacao: Optional[str] = None

class DiarioDiaResponse(BaseModel):
    id: int
    obra_id: int
    data: date
    status: str
    submetido_por_id: Optional[int] = None
    submetido_em: Optional[datetime] = None
    aprovado_por_id: Optional[int] = None
    aprovado_em: Optional[datetime] = None
    observacao_aprovacao: Optional[str] = None
    pdf_path: Optional[str] = None
    class Config:
        from_attributes = True


# === Alertas ===

class AlertaResponse(BaseModel):
    id: int
    regra: str
    severidade: str
    mensagem: str
    resolvido: bool
    dados_contexto: Optional[dict] = None
    created_at: datetime
    class Config:
        from_attributes = True


# === Audit ===

class AuditLogResponse(BaseModel):
    id: int
    tabela: str
    registro_id: int
    campo: str
    valor_anterior: Optional[str] = None
    valor_novo: Optional[str] = None
    usuario_id: int
    created_at: datetime
    class Config:
        from_attributes = True


# === Dashboard ===

class DashboardKPIs(BaseModel):
    produtividade_media: float
    dias_improdutivos: int
    atividades_atrasadas: int
    tempo_medio_aprovacao_horas: float
    total_efetivo_periodo: int
    materiais_pendentes: int

class InsightResponse(BaseModel):
    texto: str
    severidade: str  # info, atencao, critico
    data_ref: Optional[date] = None
    evidencia: str
