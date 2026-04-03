"""
Serviço de classificação de intenção usando Ollama (modelos locais).
RTX 4060 → qwen2.5:7b ou similar.
"""
import json
from datetime import date
from typing import Optional

import httpx
from app.core.config import settings

SYSTEM_PROMPT = """Você é um assistente de diário de obra (RDO). Analise a mensagem e classifique em UMA das categorias, extraindo dados estruturados.

CATEGORIAS:
1. atividade - Início de atividade/serviço novo
2. conclusao - Conclusão de atividade já em andamento
3. efetivo - Mão de obra/pessoal presente
4. material - Entrada, saída ou pendência de material
5. equipamento - Entrada, saída ou uso de equipamento
6. clima - Condição climática e impacto no trabalho
7. anotacao - Observação, ocorrência, pendência ou alerta geral
8. foto - Registro fotográfico (quando acompanhado de imagem)
9. consulta - Pergunta sobre dados já registrados

Responda APENAS com JSON válido:
{
  "intent": "categoria",
  "confidence": 0.0 a 1.0,
  "data": { ... campos extraídos ... },
  "requires_confirmation": false,
  "confirmation_message": null
}

REGRAS DE EXTRAÇÃO POR CATEGORIA:

ATIVIDADE (início):
{"descricao": "texto técnico da atividade", "local": "onde", "etapa": "qual etapa da obra"}
IMPORTANTE: Reescreva a descrição em linguagem técnica de engenharia civil. Exemplo:
- Usuário: "começamos a bater laje do segundo andar"
- Descrição: "Execução de concretagem da laje do 2º pavimento tipo"

CONCLUSAO (fim de atividade):
{"descricao": "palavras-chave da atividade para buscar no banco"}

EFETIVO (pode ter múltiplos):
{"registros": [{"funcao": "...", "quantidade": N, "empresa": "própria ou nome"}]}

MATERIAL:
{"tipo": "entrada|saída|pendente", "material": "...", "quantidade": N, "unidade": "...", "fornecedor": "...", "nota_fiscal": "...", "responsavel": "próprio|cliente", "data_prevista": "YYYY-MM-DD se pendente"}

EQUIPAMENTO:
{"tipo": "entrada|saída|manutenção", "equipamento": "...", "quantidade": N, "horas_trabalhadas": N, "operador": "..."}

CLIMA:
{"periodo": "manhã|tarde|noite", "condicao": "sol|nublado|chuva|chuvoso|tempestade", "temperatura": N, "impacto_trabalho": "...", "dia_improdutivo": true/false}
REGRA: Se o clima impediu trabalho total ou parcialmente, dia_improdutivo = true.

ANOTACAO:
{"tipo": "observação|ocorrência|pendência|alerta", "descricao": "...", "prioridade": "baixa|normal|alta|urgente"}

CONSULTA:
{"pergunta": "...", "filtros": {}}

Omita campos não mencionados. Se ambíguo, requires_confirmation = true.
Hoje: """ + str(date.today())


async def classify_intent(text: str, obra_id: Optional[int] = None) -> dict:
    """Classifica intenção usando Ollama (modelo local)."""

    url = f"{settings.ollama_base_url}/api/chat"

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json={
            "model": settings.ollama_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 512
            }
        })
        response.raise_for_status()
        result = response.json()

    content = result.get("message", {}).get("content", "{}")
    parsed = json.loads(content)
    parsed["original_text"] = text

    if obra_id:
        parsed.setdefault("data", {})["obra_id"] = obra_id

    return parsed


async def rewrite_technical(text: str) -> str:
    """Reescreve descrição de atividade em linguagem técnica."""

    prompt = f"""Reescreva esta descrição de atividade de obra em linguagem técnica de engenharia civil.
Seja conciso (1 linha). Não invente informações, apenas melhore a linguagem.

Original: {text}
Técnico:"""

    url = f"{settings.ollama_base_url}/api/generate"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json={
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 100}
        })
        response.raise_for_status()
        result = response.json()

    return result.get("response", text).strip()
