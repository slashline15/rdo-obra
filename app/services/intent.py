"""
Serviço de classificação de intenção usando Ollama (modelos locais).
Inclui pré-filtro por palavras-chave para casos óbvios.
"""
import json
import re
from datetime import date, datetime
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
        r"\b\d+\s*(funcionário|trabalhador|homem|operário|pessoa)\b",
        r"\bda empreiteira\b|\bda empresa\b|\bdo pessoal\b",
    ],
    "expediente": [
        r"\b(começa(mos|r)?|inicia(mos|r)?|entrada)\b.*\b(\d{1,2})[h:]\b",
        r"\b(termina(mos|r)?|encerra(mos|r)?|saída|fim do expediente)\b.*\b(\d{1,2})[h:]\b",
        r"\bestend(emos|er)\b.*\b(\d{1,2})[h:]\b",
        r"\bhorário\b.*\b\d{1,2}[h:]\b",
        r"\brecuperando\s+atraso\b",
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

SYSTEM_PROMPT = """Você é o núcleo de inteligência de um Canteiro Digital (RDO).
Sua missão é processar mensagens de trabalhadores e engenheiros, extraindo múltiplas intenções e dados estruturados com alta precisão (meta > 80% confiança).

MENSAGENS PODEM CONTER VÁRIAS INFORMAÇÕES AO MESMO TEMPO.

CATEGORIAS VÁLIDAS:
- atividade, conclusao, efetivo, material, equipamento, clima, anotacao, expediente, foto, consulta

REGRAS CRÍTICAS:
1. USE O CONTEXTO: Você receberá "ATIVIDADES ATIVAS". Se a mensagem diz "terminamos o reboco", use o ID/Descrição da atividade correspondente no campo data.
2. INFIRA CONTEXTO: Se "parou tudo por causa da chuva", o clima deve ter dia_improdutivo: true.
3. PRECISÃO: Não invente dados.
4. TÉCNICO: Converta termos leigos para técnicos de engenharia civil.

RESPONDA APENAS com um JSON contendo uma lista de intenções:
{"intents": [{"intent": "nome", "confidence": 0.95, "data": {...}}]}

Data de hoje: """ + str(date.today())


async def classify_intent(
    text: str,
    obra_id: Optional[int] = None,
    forced_intent: Optional[str] = None,
    context: Optional[list] = None,
) -> dict:
    """Classifica intenções: suporta múltiplas intenções e contexto de obra.
    
    context: lista de atividades em andamento para ajudar a ligar pontos.
    """

    # Pré-filtro por palavras-chave (rápido, sem LLM)
    kw_result = None if forced_intent else keyword_classify(text)
    
    # Chamar LLM com contexto de atividades se disponível
    try:
        llm_result = await _call_ollama(text, forced_intent, context)
        if "intents" not in llm_result:
            if "intent" in llm_result:
                llm_result = {"intents": [llm_result]}
            else:
                # Fallback keywords
                if kw_result and kw_result["confidence"] >= 0.5:
                    llm_result = {"intents": [{"intent": kw_result["intent"], "confidence": kw_result["confidence"], "data": {}}]}
                else:
                    llm_result = {"intents": []}
    except Exception:
        if forced_intent:
            llm_result = {"intents": [{"intent": forced_intent, "confidence": 0.8, "data": {}}]}
        elif kw_result and kw_result["confidence"] >= 0.5:
            llm_result = {"intents": [{"intent": kw_result["intent"], "confidence": kw_result["confidence"], "data": {}}]}
        else:
            llm_result = {"intents": []}

    # Validação e Enriquecimento
    valid_intents = {"atividade", "conclusao", "efetivo", "material", "equipamento", "clima", "anotacao", "foto", "consulta", "expediente"}
    
    final_intents = []
    for item in llm_result.get("intents", []):
        intent_name = item.get("intent")
        if intent_name in valid_intents:
            item["confidence"] = float(item.get("confidence") or 0.5)
            
            # Enriquecimentos específicos
            data = item.setdefault("data", {})
            if obra_id:
                data["obra_id"] = obra_id
            
            if intent_name == "clima":
                _enrich_clima_data(data, text)
            
            final_intents.append(item)

    return {
        "intents": final_intents,
        "original_text": text,
        "candidates": kw_result.get("candidates") if not forced_intent and kw_result else []
    }



# ─── Enriquecimento de clima ──────────────────────────────────────────

_PERIODO_PATTERNS = [
    (r"\bmanhã\b|\bcedo\b|\bamanhecer\b|\bmadrugada\b", "manhã"),
    (r"\btarde\b|\bmei[o-]dia\b|\balmoço\b|\bpós-almoço\b", "tarde"),
    (r"\bnoite\b|\banoitecer\b|\bentardecer\b", "noite"),
]

_CHUVA_TERMS = r"chuv[ao]|chuvoso|chovendo|temporal|tempestade|garoa|trovoada|precipitação"
_IMPRODUTIVO_TERMS = r"parou|paramos|paralisou|paralisamos|parad[ao]|improdutiv|interromp|suspens|aguardando|sem condição|inviável|falta de|sem material|sem cinto|aguard"


def _detectar_periodo(text: str) -> str:
    """Extrai período da mensagem ou infere pelo horário atual."""
    text_lower = text.lower()
    for pattern, periodo in _PERIODO_PATTERNS:
        if re.search(pattern, text_lower):
            return periodo
    # Fallback: horário atual
    hora = datetime.now().hour
    if hora < 12:
        return "manhã"
    elif hora < 18:
        return "tarde"
    return "noite"


def _inferir_status_pluviometrico(text: str, condicao: str, improdutivo: bool) -> str:
    """
    Infere status para o gráfico pluviométrico a partir do texto e dados extraídos.
    Regras:
    - sem_expediente: menção explícita
    - chuva_improdutiva: chuva + parou
    - chuva_produtiva: chuva + continuou (sem menção de parada)
    - seco_improdutivo: sem chuva + parou por outro motivo
    - seco_produtivo: padrão
    """
    text_lower = text.lower()

    if re.search(r"\bsem expediente\b|\bferiado\b|\bdomingo\b|\bsábado sem\b|\bfolga\b", text_lower):
        return "sem_expediente"

    tem_chuva = bool(re.search(_CHUVA_TERMS, text_lower)) or (condicao or "").lower() in ("chuva", "chuvoso", "tempestade", "garoa")
    tem_parada = improdutivo or bool(re.search(_IMPRODUTIVO_TERMS, text_lower))

    if tem_chuva and tem_parada:
        return "chuva_improdutiva"
    if tem_chuva and not tem_parada:
        return "chuva_produtiva"
    if not tem_chuva and tem_parada:
        return "seco_improdutivo"
    return "seco_produtivo"


def _enrich_clima_data(data: dict, text: str):
    """Enriquece data de clima com período, anotacao_rdo e status_pluviometrico."""
    # Período
    if not data.get("periodo"):
        data["periodo"] = _detectar_periodo(text)

    # Anotação RDO simplificada
    condicao = data.get("condicao", "")
    if re.search(_CHUVA_TERMS, condicao.lower()) or re.search(_CHUVA_TERMS, text.lower()):
        data["anotacao_rdo"] = "chuva"
    else:
        data["anotacao_rdo"] = "sol"

    # Status pluviométrico
    if not data.get("status_pluviometrico"):
        data["status_pluviometrico"] = _inferir_status_pluviometrico(
            text, condicao, data.get("dia_improdutivo", False)
        )


async def _call_ollama(text: str, hint: Optional[str] = None, context: Optional[list] = None) -> dict:
    """Chama Ollama para classificação + extração de dados."""
    import logging
    _log = logging.getLogger(__name__)

    prompt_parts = []
    if hint:
        prompt_parts.append(f"INTENT_FIXA: {hint}")
    if context:
        prompt_parts.append(f"ATIVIDADES ATIVAS: {json.dumps(context, ensure_ascii=False)}")
    
    prompt_parts.append(f"MENSAGEM: {text}")
    full_prompt = "\n".join(prompt_parts)

    url = f"{settings.ollama_base_url}/api/chat"

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json={
            "model": settings.ollama_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": full_prompt}
            ],
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 512
            }
        })
        response.raise_for_status()
        result = response.json()

    content = result.get("message", {}).get("content", "{}")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        _log.warning("ollama_json_parse_error | raw=%r | hint=%r | text=%r", content[:200], hint, text[:80])
        raise
