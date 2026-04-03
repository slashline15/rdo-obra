from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional


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
