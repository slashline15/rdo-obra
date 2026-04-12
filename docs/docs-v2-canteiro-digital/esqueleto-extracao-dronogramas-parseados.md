---
Criado: 2026-04-11
tags:
  - rdo-digital
  - ideia
  - cronograma
  - orçamento
  - v2
Status:
  - A definir
---
## Resumo

---
## Resumo rápido


|Tarefa|Solução “off‑the‑shelf” que cabe em ≤ 8 GB VRAM|Onde encontrar|Comentário chave|
|---|---|---|---|
|OCR + extração de layout (texto + caixas + tabelas)|LiteParse – parser PDF/IMG que devolve JSON com bounding‑boxes e OCR opcional (Tesseract, EasyOCR, PaddleOCR).|GitHub / npm `@llamaindex/liteparse`[[9]](http://github.com/run-llama/liteparse "github.com")|100 % local, sem LLMs, usa apenas OCR.|
|Modelo visual‑document‑understanding (sem OCR)|Donut‑small (≈ 200 M parâmetros) – VLM que recebe a imagem do documento e gera texto/JSON direto.|HuggingFace `Bennet1996/donut‑small`[6]|Muito leve; pode ser quantizado para < 2 GB.|
|Modelo de entendimento de layout + classificação de campos|LayoutLMv3‑small (≈ 100 M parâmetros) – token‑classification com boxes.|HF `EslamAhmed/LayoutLMv3‑DocLayNet‑small`[5]|Boa para extrair “atividade”, “data‑início”, “custo”, etc., quando treinado com anotações de bounding‑box.|
|LLM geral para gerar JSON a partir de texto livre|Phi‑4‑mini / Phi‑2 (2.7 – 3.8 B parâmetros) – roda em 4 GB (quantizado Q4_K_M) e pode ser afinado com LoRA/QLoRA.|Ollama `phi4‑mini` ou HF `microsoft/phi‑2`[[10]](https://dev.to/vikrant_bagal_afae3e25ca7/local-llm-integration-in-net-running-phi-4-llama-3-mistral-with-onnx-runtime-367f "dev.to")|Usa‑se quando o texto extraído tem estrutura livre (observações, descrições, notas).|
|Fine‑tuning leve|LoRA / QLoRA (bitsandbytes 4‑bit) – acrescenta < 200 MB ao modelo e permite treinar em 8 GB VRAM.|HF `peft` e `bitsandbytes`|Não exige re‑treinar todo o modelo.|

Com essas peças você pode montar um pipeline totalmente local que:

1. Converte qualquer entrada (PDF, planilha exportada, foto de planilha, .mpp exportado como CSV/PNG) em imagens ou texto bruto.
2. Usa OCR + layout (LiteParse) ou modelo visual‑document (Donut‑small) para obter texto posicionado (x, y, w, h).
3. Alimenta um modelo LayoutLMv3‑small (token‑classification) para rotular cada caixa com a entidade do seu dicionário (atividade, data, recurso, custo, etc.).
4. Quando o campo é descrito em linguagem livre (ex.: “Observação: Troca de tubo”), passa‑se o trecho para um Phi‑4‑mini afinado que devolve um JSON já no formato final da base de dados.
5. O _output_ final é um JSON padronizado que pode ser inserido direto no seu banco de dados ou enviado ao módulo de planejamento.

A seguir, um plano de ação passo‑a‑passo com detalhes técnicos, fontes e exemplos de código.

---

## 1. Coleta e rotulação de dados (≈ 1 sem‑a‑2 semanas)

|O que fazer|Por quê|Dicas práticas|
|---|---|---|
|Reunir ~ 50‑200 documentos reais (cronogramas MS‑Project exportados como PDF/PNG, orçamentos em planilha escaneada, PDFs de propostas).|Serve de base para treinamento e avaliação.|Misture PDFs “digitais” (text layer) e “escaneados” para que o pipeline seja robusto.|
|Extrair caixas e texto com LiteParse (com OCR ativado). Salve como `doc_id.json`.|Gera rapidamente rótulos “bbox → texto”.|`lit parse file.pdf --format json -o out.json`.|
|Anotar manualmente as entidades (ex.: `"atividade": "Fundação", "inicio": "2024‑09‑01", "custo": 145000`). Use ferramentas como doccano, Label Studio ou planilhas CSV.|Cria o conjunto de treinamento de classificação de layout.|Converta os `bbox` de LiteParse para o formato esperado por LayoutLMv3 (`tokens`, `bbox`).|
|Opcional – gerar dados sintéticos com SynthDoG (parte do repositório Donut) para aumentar variações de layout.|Reduz a necessidade de milhares de documentos reais.|`python synthdog.py --num 5000 --output synthetic/`.|

### Ferramentas úteis

- LiteParse – CLI rápida, exporta JSON com `text, bbox, confidence`.
- doccano – web UI para marcar entidades em trechos com posição.
- Pandas – para gerar pares “texto → JSON” para o fine‑tune do Phi‑4‑mini.

---

## 2. Pré‑processamento (OCR + layout)

bash

```
# Instalação (uma única linha)
npm i -g @llamaindex/liteparse   # ou brew install llamaindex-liteparse
```

```
# Instalação (uma única linha)
npm i -g @llamaindex/liteparse   # ou brew install llamaindex-liteparse
```

bash

```
# Exemplo de uso
lit parse cronograma.pdf --format json -o cronograma.json
```

```
# Exemplo de uso
lit parse cronograma.pdf --format json -o cronograma.json
```

O arquivo resultante tem a forma:

json

```
{
  "pages": [
    {
      "page_num": 1,
      "words": [
        {"text":"Atividade","bbox":[12,45,78,60],"conf":0.98},
        {"text":"Fundação","bbox":[85,45,150,60],"conf":0.94},
        ...
      ]
    },
    ...
  ]
}
```

```
{
  "pages": [
    {
      "page_num": 1,
      "words": [
        {"text":"Atividade","bbox":[12,45,78,60],"conf":0.98},
        {"text":"Fundação","bbox":[85,45,150,60],"conf":0.94},
        ...
      ]
    },
    ...
  ]
}
```

_Se o PDF já contém texto pesquisável, basta pular OCR (`--no-ocr`)._

Para tabelas complexas (orçamentos) pode‑se usar a detecção de tabelas de PaddleOCR (já integrada ao LiteParse) ou Camelot se o PDF for “digital”.

bash

```
lit parse orcamento.pdf --format json --ocr-table true -o orcamento.json
```

```
lit parse orcamento.pdf --format json --ocr-table true -o orcamento.json
```

---

## 3. Modelo de extração de campos (LayoutLMv3‑small)

### 3.1. Preparar dataset no formato HF

python

```
from datasets import Dataset
import json, pathlib

def load_liteparse(path):
    data = json.load(open(path))
    # converte cada palavra em token + bbox (x0, y0, x1, y1)
    tokens, boxes, labels = [], [], []
    for word in data["pages"][0]["words"]:
        tokens.append(word["text"])
        x0, y0, x1, y1 = word["bbox"]
        boxes.append([x0, y0, x1, y1])
        # label manual (ex.: "B-ACTIVITY", "I-ACTIVITY", "O")
        # aqui se usa o CSV de anotações
    return {"tokens": tokens, "bboxes": boxes, "labels": labels}

raw = load_liteparse("cronograma.json")
ds = Dataset.from_dict(raw)
```

```
from datasets import Dataset
import json, pathlib

def load_liteparse(path):
    data = json.load(open(path))
    # converte cada palavra em token + bbox (x0, y0, x1, y1)
    tokens, boxes, labels = [], [], []
    for word in data["pages"][0]["words"]:
        tokens.append(word["text"])
        x0, y0, x1, y1 = word["bbox"]
        boxes.append([x0, y0, x1, y1])
        # label manual (ex.: "B-ACTIVITY", "I-ACTIVITY", "O")
        # aqui se usa o CSV de anotações
    return {"tokens": tokens, "bboxes": boxes, "labels": labels}

raw = load_liteparse("cronograma.json")
ds = Dataset.from_dict(raw)
```

### 3.2. Fine‑tune (≈ 1 h em 8 GB)

bash

```
pip install transformers peft bitsandbytes
```

```
pip install transformers peft bitsandbytes
```

python

```
from transformers import AutoTokenizer, AutoModelForTokenClassification, Trainer, TrainingArguments
from peft import LoraConfig, get_peft_model

model_name = "EslamAhmed/layoutlmv3-doclaynet-small"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForTokenClassification.from_pretrained(model_name, num_labels=NUM_LABELS)

# LoRA (<< 200 MB)
config = LoraConfig(r=8, lora_alpha=16, target_modules=["query", "value", "key"])
model = get_peft_model(model, config)

args = TrainingArguments(
    output_dir="./layoutlmv3-loRA",
    per_device_train_batch_size=4,
    num_train_epochs=3,
    learning_rate=5e-4,
    fp16=True,               # usa menos VRAM
)

trainer = Trainer(
    model=model,
    args=args,
    train_dataset=ds,
    tokenizer=tokenizer,
)

trainer.train()
model.save_pretrained("./layoutlmv3-loRA")
```

```
from transformers import AutoTokenizer, AutoModelForTokenClassification, Trainer, TrainingArguments
from peft import LoraConfig, get_peft_model

model_name = "EslamAhmed/layoutlmv3-doclaynet-small"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForTokenClassification.from_pretrained(model_name, num_labels=NUM_LABELS)

# LoRA (<< 200 MB)
config = LoraConfig(r=8, lora_alpha=16, target_modules=["query", "value", "key"])
model = get_peft_model(model, config)

args = TrainingArguments(
    output_dir="./layoutlmv3-loRA",
    per_device_train_batch_size=4,
    num_train_epochs=3,
    learning_rate=5e-4,
    fp16=True,               # usa menos VRAM
)

trainer = Trainer(
    model=model,
    args=args,
    train_dataset=ds,
    tokenizer=tokenizer,
)

trainer.train()
model.save_pretrained("./layoutlmv3-loRA")
```

> Resultado: modelo que, a partir de `tokens` + `bboxes`, devolve a sequência de rótulos. O tamanho final (com LoRA) fica < 300 MB, portanto cabe tranquilamente em 8 GB junto com o tokenizer e a GPU para inferência.

### 3.3. Inferência

python

```
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

tokenizer = AutoTokenizer.from_pretrained("./layoutlmv3-loRA")
model = AutoModelForTokenClassification.from_pretrained("./layoutlmv3-loRA")
nlp = pipeline("token-classification", model=model, tokenizer=tokenizer, aggregation_strategy="simple")

def extract_fields(lite_json):
    txt = " ".join([w["text"] for w in lite_json["pages"][0]["words"]])
    # cria tokens e bboxes (exemplo simplificado)
    result = nlp(txt)
    # converte rótulos em dicionário estruturado
    return result
```

```
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

tokenizer = AutoTokenizer.from_pretrained("./layoutlmv3-loRA")
model = AutoModelForTokenClassification.from_pretrained("./layoutlmv3-loRA")
nlp = pipeline("token-classification", model=model, tokenizer=tokenizer, aggregation_strategy="simple")

def extract_fields(lite_json):
    txt = " ".join([w["text"] for w in lite_json["pages"][0]["words"]])
    # cria tokens e bboxes (exemplo simplificado)
    result = nlp(txt)
    # converte rótulos em dicionário estruturado
    return result
```

---

## 4. LLM para campos de texto livre (Phi‑4‑mini ou Phi‑2)

### 4.1. Por que usar um LLM?

- Algumas linhas de orçamento têm observações ou unidades não‑tabuladas (ex.: “_Nota: 5% de risco_”).
- O modelo de classificação pode extrair o _segmento_ de texto, mas a normalização (converter “R$ 1,2 mi” → `1200000`) é mais simples com um pequeno LLM que entende regras numéricas.

### 4.2. Preparar dataset “prompt → JSON”

json

```
{
  "prompt": "Texto: \"Nota: 5% de risco, prazo adicional de 2 dias\"\nExtrair: {\"risco_percentual\": ?, \"dias_adicionais\": ?}",
  "completion": "{\"risco_percentual\": 5, \"dias_adicionais\": 2}"
}
```

```
{
  "prompt": "Texto: \"Nota: 5% de risco, prazo adicional de 2 dias\"\nExtrair: {\"risco_percentual\": ?, \"dias_adicionais\": ?}",
  "completion": "{\"risco_percentual\": 5, \"dias_adicionais\": 2}"
}
```

Crie ~ 2 000 pares a partir dos documentos já anotados (pode ser script que concatena o texto bruto da caixa com a estrutura alvo).

### 4.3. Fine‑tune com QLoRA (4‑bit) – roda em 8 GB

bash

```
pip install trl peft bitsandbytes accelerate
```

```
pip install trl peft bitsandbytes accelerate
```

python

```
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTTrainer
from peft import LoraConfig

model_name = "microsoft/phi-2"          # 2.7 B
tokenizer = AutoTokenizer.from_pretrained(model_name)

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    load_in_4bit=True,                # 4‑bit quantization
    device_map="auto",
)

lora_cfg = LoraConfig(r=16, lora_alpha=32, target_modules=["q_proj","v_proj"])
model = get_peft_model(model, lora_cfg)

trainer = SFTTrainer(
    model=model,
    train_dataset=prompt_dataset,
    tokenizer=tokenizer,
    args=TrainingArguments(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        num_train_epochs=2,
        learning_rate=5e-5,
        fp16=True,
    ),
)
trainer.train()
model.save_pretrained("./phi2-loRA")
```

```
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTTrainer
from peft import LoraConfig

model_name = "microsoft/phi-2"          # 2.7 B
tokenizer = AutoTokenizer.from_pretrained(model_name)

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    load_in_4bit=True,                # 4‑bit quantization
    device_map="auto",
)

lora_cfg = LoraConfig(r=16, lora_alpha=32, target_modules=["q_proj","v_proj"])
model = get_peft_model(model, lora_cfg)

trainer = SFTTrainer(
    model=model,
    train_dataset=prompt_dataset,
    tokenizer=tokenizer,
    args=TrainingArguments(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        num_train_epochs=2,
        learning_rate=5e-5,
        fp16=True,
    ),
)
trainer.train()
model.save_pretrained("./phi2-loRA")
```

> Resultado: modelo < 4 GB (4‑bit) que converte trechos de texto em JSON estruturado. Pode ser servido via Ollama ou vLLM.

### 4.4. Inferência (exemplo com Ollama)

bash

```
ollama pull phi4-mini   # < 4 GB, roda em 4 GB GPU
ollama run phi4-mini "Texto: 'Nota: 5% de risco, prazo adicional de 2 dias' → JSON"
```

```
ollama pull phi4-mini   # < 4 GB, roda em 4 GB GPU
ollama run phi4-mini "Texto: 'Nota: 5% de risco, prazo adicional de 2 dias' → JSON"
```

---

## 5. Orquestração final (pipeline)

mermaid

```
flowchart TD
    A[Entrada (PDF / PNG / CSV)] --> B[LiteParse (OCR + bbox JSON)]
    B --> C{Documento digital?}
    C -- Sim --> D[Extrair texto puro (pdfminer)]
    C -- Não --> D
    D --> E[LayoutLMv3‑small → entidades estruturadas]
    E --> F{Campo livre?}
    F -- Sim --> G[Phi‑4‑mini (QLoRA) → JSON]
    F -- Não --> H[Montar JSON final]
    G --> H
    H --> I[Salvar no banco / enviar ao módulo de planejamento]
```

```
flowchart TD
    A[Entrada (PDF / PNG / CSV)] --> B[LiteParse (OCR + bbox JSON)]
    B --> C{Documento digital?}
    C -- Sim --> D[Extrair texto puro (pdfminer)]
    C -- Não --> D
    D --> E[LayoutLMv3‑small → entidades estruturadas]
    E --> F{Campo livre?}
    F -- Sim --> G[Phi‑4‑mini (QLoRA) → JSON]
    F -- Não --> H[Montar JSON final]
    G --> H
    H --> I[Salvar no banco / enviar ao módulo de planejamento]
```

- Componentes são executados como processos independentes (Docker ou scripts Python).
- Cada módulo pode ser testado separadamente; falhas de OCR são mitigadas usando o modelo visual Donut‑small como “fallback” (recebe a página como imagem e devolve texto).
- O pipeline inteiro cabe em uma máquina com GPU ≥ 8 GB (ex.: RTX 3060‑12 GB ou RTX 3070‑8 GB).

### Exemplo de script de orquestração (Python)

python

```
import subprocess, json, pathlib, torch
from transformers import pipeline

# 1 – OCR + layout
def parse_with_lite(file_path):
    out = subprocess.check_output(
        ["lit", "parse", file_path, "--format", "json", "--no-progress"]
    )
    return json.loads(out)

# 2 – classificação de campos
layout_token_classifier = pipeline(
    "token-classification",
    model="./layoutlmv3-loRA",
    tokenizer="./layoutlmv3-loRA",
    aggregation_strategy="simple",
)

def extract_structured(lite_json):
    txt = " ".join([w["text"] for w in lite_json["pages"][0]["words"]])
    return {ent["entity_group"]: ent["word"] for ent in layout_token_classifier(txt)}

# 3 – LLM para campos livres
phi_llm = pipeline("text-generation", model="./phi2-loRA", tokenizer="microsoft/phi-2", 
                  device=0, max_new_tokens=200)

def free_text_to_json(fragment):
    prompt = f"Texto: \"{fragment}\" → JSON"
    out = phi_llm(prompt)[0]["generated_text"]
    # tenta converter de string para dict
    try:
        return json.loads(out.split("JSON")[-1])
    except:
        return {}

# 4 – montagem final
def process(file_path):
    doc = parse_with_lite(file_path)
    fields = extract_structured(doc)

    # exemplo de campo livre: "observação"
    if "observação" in fields:
        fields["observação"] = free_text_to_json(fields["observação"])

    return fields

if __name__ == "__main__":
    result = process("cronograma.pdf")
    print(json.dumps(result, indent=2, ensure_ascii=False))
```

```
import subprocess, json, pathlib, torch
from transformers import pipeline

# 1 – OCR + layout
def parse_with_lite(file_path):
    out = subprocess.check_output(
        ["lit", "parse", file_path, "--format", "json", "--no-progress"]
    )
    return json.loads(out)

# 2 – classificação de campos
layout_token_classifier = pipeline(
    "token-classification",
    model="./layoutlmv3-loRA",
    tokenizer="./layoutlmv3-loRA",
    aggregation_strategy="simple",
)

def extract_structured(lite_json):
    txt = " ".join([w["text"] for w in lite_json["pages"][0]["words"]])
    return {ent["entity_group"]: ent["word"] for ent in layout_token_classifier(txt)}

# 3 – LLM para campos livres
phi_llm = pipeline("text-generation", model="./phi2-loRA", tokenizer="microsoft/phi-2", 
                  device=0, max_new_tokens=200)

def free_text_to_json(fragment):
    prompt = f"Texto: \"{fragment}\" → JSON"
    out = phi_llm(prompt)[0]["generated_text"]
    # tenta converter de string para dict
    try:
        return json.loads(out.split("JSON")[-1])
    except:
        return {}

# 4 – montagem final
def process(file_path):
    doc = parse_with_lite(file_path)
    fields = extract_structured(doc)

    # exemplo de campo livre: "observação"
    if "observação" in fields:
        fields["observação"] = free_text_to_json(fields["observação"])

    return fields

if __name__ == "__main__":
    result = process("cronograma.pdf")
    print(json.dumps(result, indent=2, ensure_ascii=False))
```

---

## 6. Avaliação e iteração

|Métrica|Como medir|
|---|---|
|Precisão de OCR|Comparar texto extraído com versão “ground‑truth” (levenshtein).|
|F1‑score de classificação de layout|Usar a avaliação padrão de token‑classification (BIO) nos conjuntos de teste.|
|Exact‑match JSON|Comparar JSON gerado com o rótulo esperado (caso‑sensitive e ordem de chaves).|
|Tempo de inferência|Medir latência por página (objetivo ≤ 300 ms).|

Comece com 10 % dos documentos como conjunto de teste, ajuste o número de LoRA‑ranks ou o tamanho do batch até atingir F1 > 0,90 nas entidades mais críticas (atividade, data, custo).

---

## 7. Checklist de recursos (para iniciar hoje)

|Ferramenta|Instalação (uma linha)|VRAM mínima|
|---|---|---|
|LiteParse|`npm i -g @llamaindex/liteparse`|0 GB (CPU)|
|Donut‑small|`ollama pull donut-small` (ou HF)|2 GB (quantizado)|
|LayoutLMv3‑small|`pip install transformers datasets` + download HF model|3 GB (FP16)|
|Phi‑4‑mini (ou Phi‑2)|`ollama pull phi4-mini`|4 GB (Q4_K_M)|
|bitsandbytes + peft|`pip install bitsandbytes peft`|– (necessita GPU)|
|Docker (opcional)|`docker run ...`|–|

---

## 8. Próximos passos recomendados

1. Instalar e testar LiteParse em alguns PDFs reais. Verifique se a saída JSON já contém a maioria das colunas das tabelas de orçamento.
2. Criar um pequeno dataset (≈ 100 documentos) com as anotações de entidades que seu sistema realmente precisa (atividade, data‑início, data‑fim, recurso, custo, unidade).
3. Fine‑tune LayoutLMv3‑small usando LoRA (≈ 1 h). Avalie F1.
4. Treinar o Phi‑4‑mini apenas para os campos livres – use QLoRA (4‑bit) para economizar VRAM.
5. Montar o script de orquestração (exemplo acima) e rodar em lote.
6. Medir latência; se precisar de mais velocidade, quantize LayoutLMv3‑small para 8‑bit (`bitsandbytes` `load_in_8bit=True`).

Com esse caminho, você tem:

- Custo zero de API (tudo roda localmente).
- Privacidade total (dados de obras não saem da rede).
- Modelo pequeno (≤ 8 GB VRAM) que ainda entrega mais de 90 % de acurácia para campos estruturados e boa robustez para texto livre.

---

### Links úteis (para copiar‑colar)

|Recurso|URL|
|---|---|
|LiteParse (repo + docs)|[https://github.com/run-llama/liteparse](https://github.com/run-llama/liteparse)|
|Donut‑small (HF)|[https://huggingface.co/Bennet1996/donut-small](https://huggingface.co/Bennet1996/donut-small)|
|LayoutLMv3‑small (DocLayNet)|[https://huggingface.co/EslamAhmed/LayoutLMv3-DocLayNet-small](https://huggingface.co/EslamAhmed/LayoutLMv3-DocLayNet-small)|
|Phi‑2 (2.7 B)|[https://huggingface.co/microsoft/phi-2](https://huggingface.co/microsoft/phi-2)|
|Phi‑4‑mini (Ollama)|[https://ollama.com/library/phi4-mini](https://ollama.com/library/phi4-mini)|
|PEFT / LoRA docs|[https://huggingface.co/docs/peft/main/en/index](https://huggingface.co/docs/peft/main/en/index)|
|QLoRA tutorial (bitsandbytes)|[https://github.com/artidoro/qlora](https://github.com/artidoro/qlora)|

---

### Conclusão

Sim, já existem modelos pequenos que rodam em GPUs de até 8 GB e que podem ser combinados com um OCR / layout parser para transformar cronogramas e orçamentos não‑padronizados em JSON estruturado.

A estratégia mais prática é:

1. OCR + layout → LiteParse (ou Donut‑small).
2. Classificação de campos → LayoutLMv3‑small afinado com LoRA.
3. Normalização de texto livre → Phi‑4‑mini / Phi‑2 afinado com QLoRA.

Todo o fluxo pode ser orquestrado localmente, sem depender de APIs externas, mantendo custos baixos e cumprindo requisitos de confidencialidade típicos de projetos de engenharia civil. Boa implementação! 🚀

---

-> Ver [[Modulo de Cronograma]]