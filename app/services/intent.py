"""
Serviço de classificação de intenção usando Ollama (modelos locais).
Inclui pré-filtro por palavras-chave para casos óbvios.
"""
import json
import re
from datetime import date
from typing import Optional

import httpx
from app.core.config import settings

# ─── Pré-filtro por palavras-chave ───────────────────────────────────
# Pega os casos óbvios sem depender do LLM. O cara fala rápido no canteiro,
# as frases seguem padrões bem claros.

KEYWORD_PATTERNS = {
    "clima": [
        r"\b(chuv[ao]|chuvoso|chovendo|temporal|tempestade|sol\b|nublado|garoa|trovoada)",
        r"\b(tempo|clima)\b.*\b(manhã|tarde|noite|dia)\b",
        r"\bparalis[ao]|paramos|parad[ao]\b.*\b(chuva|tempo|clima)\b",
        r"\b(chuva|tempo)\b.*\bparalis|parad|paramos\b",
        r"\bdia improdutivo\b",
    ],
    "efetivo": [
        r"\b\d+\s*(pedreiro|servente|carpinteiro|armador|eletricista|encanador|pintor|gesseiro|mestre|encarregado|ajudante|operador|soldador|bombeiro|serralheiro|vidraceiro|impermeabilizador)",
        r"\b(chegou|chegaram|vieram|veio|presente|efetivo)\b.*\b\d+\b",
        r"\b\d+\b.*\b(chegou|chegaram|vieram|presente)\b",
        r"\b(mão de obra|equipe|turma|pessoal)\b",
    ],
    "atividade": [
        r"\b(começamos|iniciamos|iniciou|começou|partimos|arrancamos)\b",
        r"\b(início|inicio)\s*(da|do|de)\b",
        r"\b(concretagem|armação|forma|fundação|alvenaria|reboco|chapisco|contrapiso|impermeabilização|pintura|escavação|terraplanagem)\b",
    ],
    "conclusao": [
        r"\b(terminamos|concluímos|finalizamos|acabamos|pronto|concluído|finalizado|terminado|acabou)\b",
        r"\b(fim|final)\s*(da|do|de)\b",
    ],
    "material": [
        r"\b(chegou|chegaram|recebemos|entregaram|falta|faltando|acabou|acabando)\b.*\b(cimento|areia|brita|ferro|aço|tijolo|bloco|tinta|tubo|madeira|prego|tela|saco|metro|tonelada)\b",
        r"\b(cimento|areia|brita|ferro|aço|tijolo|bloco|tinta|tubo|madeira)\b.*\b(chegou|chegaram|recebemos|falta|acabou)\b",
        r"\b(nota fiscal|NF|entrega|fornecedor|caminhão de)\b",
        r"\b(material|materiais)\b",
        r"\b\d+\s*(saco|metro|tonelada|kg|litro|m²|m³|unidade|peça|barra|rolo)\s",
    ],
    "equipamento": [
        r"\b(betoneira|grua|guincho|retroescavadeira|escavadeira|rolo|compactador|vibrador|serra|furadeira|andaime|gerador|bomba)\b",
        r"\b(equipamento|máquina|maquinário)\b",
    ],
    "anotacao": [
        r"\b(anotar?|observação|obs|ocorrência|pendência|lembrete|aviso|alerta|atenção)\b",
        r"\b(problema|defeito|reclamação|visita|fiscal|engenheiro veio)\b",
    ],
}


def keyword_classify(text: str) -> Optional[dict]:
    """Tenta classificar por palavras-chave. Retorna None se não tiver certeza."""
    text_lower = text.lower()
    scores = {}

    for intent, patterns in KEYWORD_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                scores[intent] = scores.get(intent, 0) + 1

    if not scores:
        return None

    # Pega o melhor e o segundo melhor
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_intent, best_score = ranked[0]

    # Se só um intent matchou, ou o melhor tem vantagem clara → confiante
    if len(ranked) == 1 or best_score > ranked[1][1]:
        return {"intent": best_intent, "confidence": min(0.85, 0.6 + best_score * 0.15)}

    # Ambíguo — retorna os candidatos para o orchestrator usar botões
    return {
        "intent": best_intent,
        "confidence": 0.5,
        "candidates": [r[0] for r in ranked[:3]]
    }


# ─── Prompt do LLM ──────────────────────────────────────────────────

SYSTEM_PROMPT = """Você é um classificador de mensagens de diário de obra (RDO).
Analise a mensagem do trabalhador e classifique em UMA categoria, extraindo dados.

CATEGORIAS VÁLIDAS (use exatamente estes nomes):
- atividade → início de serviço/atividade nova
- conclusao → atividade em andamento sendo finalizada
- efetivo → mão de obra presente no dia
- material → entrada, saída ou falta de material
- equipamento → entrada, saída ou uso de equipamento/máquina
- clima → condição do tempo e impacto no trabalho
- anotacao → observação geral, ocorrência, pendência
- foto → registro fotográfico
- consulta → pergunta sobre dados já registrados

RESPONDA APENAS com JSON neste formato exato:
{"intent": "nome_da_categoria", "confidence": 0.9, "data": {...}}

EXEMPLOS:

Mensagem: "chegaram 5 pedreiros e 3 serventes da empreiteira Silva"
{"intent": "efetivo", "confidence": 0.95, "data": {"registros": [{"funcao": "pedreiro", "quantidade": 5, "empresa": "Silva"}, {"funcao": "servente", "quantidade": 3, "empresa": "Silva"}]}}

Mensagem: "chuva forte a manhã toda, paramos tudo até meio dia"
{"intent": "clima", "confidence": 0.95, "data": {"periodo": "manhã", "condicao": "chuva", "impacto_trabalho": "paralisação total até meio dia", "dia_improdutivo": true}}

Mensagem: "começamos a concretagem da laje do segundo andar"
{"intent": "atividade", "confidence": 0.95, "data": {"descricao": "Execução de concretagem da laje do 2º pavimento tipo", "local": "2º pavimento", "etapa": "Estrutura"}}

Mensagem: "terminamos a alvenaria do térreo"
{"intent": "conclusao", "confidence": 0.9, "data": {"descricao": "alvenaria térreo"}}

Mensagem: "chegaram 200 sacos de cimento, NF 4521"
{"intent": "material", "confidence": 0.95, "data": {"tipo": "entrada", "material": "cimento", "quantidade": 200, "unidade": "sacos", "nota_fiscal": "4521"}}

REGRAS:
- Para atividade: reescreva a descrição em linguagem técnica de engenharia civil
- Para clima: se impediu trabalho, dia_improdutivo = true
- Para efetivo: sempre use "registros" como array, mesmo com um só registro
- Omita campos não mencionados na mensagem
- NÃO use "categoria" como valor de intent — use o nome real da categoria
- confidence deve refletir sua certeza real (0.0 a 1.0)

Data de hoje: """ + str(date.today())


async def classify_intent(text: str, obra_id: Optional[int] = None) -> dict:
    """Classifica intenção: primeiro tenta keywords, depois LLM."""

    # Pré-filtro por palavras-chave (rápido, sem LLM)
    kw_result = keyword_classify(text)

    # Se keywords deram match confiante, ainda manda pro LLM para extrair dados
    # mas já sabemos o intent — o LLM só estrutura
    hint = None
    if kw_result and kw_result["confidence"] >= 0.7:
        hint = kw_result["intent"]

    # Chamar LLM
    try:
        llm_result = await _call_ollama(text, hint)
    except Exception:
        # Ollama offline — usar só keywords
        if kw_result:
            llm_result = {"intent": kw_result["intent"], "confidence": kw_result["confidence"], "data": {}}
        else:
            return {"intent": "desconhecido", "confidence": 0, "data": {}}

    # Validar: se o LLM retornou "categoria" ou intent inválido, usar keywords
    valid_intents = {"atividade", "conclusao", "efetivo", "material", "equipamento", "clima", "anotacao", "foto", "consulta"}
    llm_intent = llm_result.get("intent", "")

    if llm_intent not in valid_intents:
        if kw_result and kw_result["confidence"] >= 0.5:
            llm_result["intent"] = kw_result["intent"]
            llm_result["confidence"] = kw_result["confidence"]
        else:
            llm_result["intent"] = "desconhecido"
            llm_result["confidence"] = 0

    # Adicionar candidatos se keywords detectou ambiguidade
    if kw_result and "candidates" in kw_result:
        llm_result["candidates"] = kw_result["candidates"]

    llm_result["original_text"] = text
    if obra_id:
        llm_result.setdefault("data", {})["obra_id"] = obra_id

    return llm_result


async def _call_ollama(text: str, hint: Optional[str] = None) -> dict:
    """Chama Ollama para classificação + extração de dados."""

    prompt = text
    if hint:
        prompt = f"[A categoria é: {hint}] {text}"

    url = f"{settings.ollama_base_url}/api/chat"

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json={
            "model": settings.ollama_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
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
    return json.loads(content)
