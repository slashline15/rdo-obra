"""
Gateway WhatsApp → Processamento de mensagens.
Recebe texto/áudio, classifica intenção, registra no banco.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date

from app.database import get_db
from app.models import (
    Usuario, Servico, Efetivo, Anotacao, Material,
    Equipamento, Clima, Foto
)
from app.schemas import WhatsAppMessage
from app.services.intent import classify_intent
from app.services.transcription import transcribe_audio

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Gateway"])


@router.post("/webhook")
async def processar_mensagem(msg: WhatsAppMessage, db: Session = Depends(get_db)):
    """
    Endpoint principal: recebe mensagem do WhatsApp e processa.
    Fluxo: áudio→transcrição→classificação→registro→resposta
    """
    # 1. Identificar usuário pelo telefone
    usuario = db.query(Usuario).filter(Usuario.telefone == msg.telefone).first()
    if not usuario:
        return {
            "resposta": "❌ Número não cadastrado. Peça ao responsável para te adicionar.",
            "registrado": False
        }

    if not usuario.obra_id:
        return {
            "resposta": "⚠️ Você não está vinculado a nenhuma obra. Fale com o responsável.",
            "registrado": False
        }

    obra_id = usuario.obra_id

    # 2. Obter texto (transcrever áudio se necessário)
    texto = msg.texto
    if msg.audio_path and not texto:
        try:
            texto = await transcribe_audio(msg.audio_path)
        except Exception as e:
            return {
                "resposta": f"❌ Erro ao transcrever áudio: {str(e)}",
                "registrado": False
            }

    if not texto and msg.foto_path:
        texto = msg.legenda or "Foto registrada"

    if not texto:
        return {
            "resposta": "🤔 Não entendi. Mande texto ou áudio descrevendo o que aconteceu na obra.",
            "registrado": False
        }

    # 3. Classificar intenção
    try:
        intent_result = await classify_intent(texto, obra_id)
    except Exception as e:
        return {
            "resposta": f"❌ Erro ao processar mensagem: {str(e)}",
            "registrado": False
        }

    intent = intent_result.get("intent", "")
    data = intent_result.get("data", {})
    confidence = intent_result.get("confidence", 0)
    requires_confirmation = intent_result.get("requires_confirmation", False)

    # 4. Se confiança baixa ou precisa confirmação, pedir
    if confidence < 0.6 or requires_confirmation:
        confirm_msg = intent_result.get("confirmation_message", "")
        return {
            "resposta": f"🤔 {confirm_msg or 'Não tenho certeza. Pode repetir de outra forma?'}",
            "registrado": False,
            "intent": intent,
            "confidence": confidence
        }

    # 5. Registrar conforme a intenção
    try:
        resposta = await _registrar(intent, data, obra_id, usuario.nome, texto, msg.foto_path, db)
    except Exception as e:
        return {
            "resposta": f"❌ Erro ao registrar: {str(e)}",
            "registrado": False
        }

    return {
        "resposta": resposta,
        "registrado": True,
        "intent": intent,
        "confidence": confidence
    }


async def _registrar(intent: str, data: dict, obra_id: int, registrado_por: str, texto_original: str, foto_path: str = None, db: Session = None) -> str:
    """Registra os dados no banco conforme a intenção classificada."""

    hoje = date.today()

    if intent == "servico":
        servico = Servico(
            obra_id=obra_id,
            data=hoje,
            descricao=data.get("descricao", texto_original),
            local=data.get("local"),
            etapa=data.get("etapa"),
            percentual_concluido=data.get("percentual_concluido", 0),
            observacoes=data.get("observacoes"),
            registrado_por=registrado_por,
            texto_original=texto_original
        )
        db.add(servico)
        db.commit()
        return f"✅ Serviço registrado: {servico.descricao}"

    elif intent == "efetivo":
        registros = data.get("registros", [])
        if not registros:
            # Tenta usar dados diretamente
            registros = [data]

        nomes = []
        for reg in registros:
            ef = Efetivo(
                obra_id=obra_id,
                data=hoje,
                funcao=reg.get("funcao", "Geral"),
                quantidade=reg.get("quantidade", 1),
                empresa=reg.get("empresa", "própria"),
                registrado_por=registrado_por,
                texto_original=texto_original
            )
            db.add(ef)
            nomes.append(f"{ef.quantidade} {ef.funcao}")
        db.commit()
        return f"✅ Efetivo registrado: {', '.join(nomes)}"

    elif intent == "material":
        mat = Material(
            obra_id=obra_id,
            data=hoje,
            tipo=data.get("tipo", "entrada"),
            material=data.get("material", "Material não especificado"),
            quantidade=data.get("quantidade"),
            unidade=data.get("unidade"),
            fornecedor=data.get("fornecedor"),
            nota_fiscal=data.get("nota_fiscal"),
            registrado_por=registrado_por,
            texto_original=texto_original
        )
        db.add(mat)
        db.commit()
        return f"✅ Material registrado: {mat.tipo} de {mat.quantidade or ''} {mat.unidade or ''} {mat.material}"

    elif intent == "equipamento":
        equip = Equipamento(
            obra_id=obra_id,
            data=hoje,
            tipo=data.get("tipo", "entrada"),
            equipamento=data.get("equipamento", "Equipamento não especificado"),
            quantidade=data.get("quantidade", 1),
            horas_trabalhadas=data.get("horas_trabalhadas"),
            operador=data.get("operador"),
            registrado_por=registrado_por,
            texto_original=texto_original
        )
        db.add(equip)
        db.commit()
        return f"✅ Equipamento registrado: {equip.tipo} - {equip.equipamento}"

    elif intent == "clima":
        cl = Clima(
            obra_id=obra_id,
            data=hoje,
            periodo=data.get("periodo"),
            condicao=data.get("condicao"),
            temperatura=data.get("temperatura"),
            impacto_trabalho=data.get("impacto_trabalho"),
            texto_original=texto_original
        )
        db.add(cl)
        db.commit()
        cond = cl.condicao or "registrado"
        return f"✅ Clima registrado: {cl.periodo or 'geral'} - {cond}"

    elif intent == "anotacao":
        anot = Anotacao(
            obra_id=obra_id,
            data=hoje,
            tipo=data.get("tipo", "observação"),
            descricao=data.get("descricao", texto_original),
            prioridade=data.get("prioridade", "normal"),
            registrado_por=registrado_por,
            texto_original=texto_original
        )
        db.add(anot)
        db.commit()
        return f"✅ Anotação registrada: {anot.descricao[:50]}..."

    elif intent == "foto" and foto_path:
        foto = Foto(
            obra_id=obra_id,
            data=hoje,
            arquivo=foto_path,
            descricao=data.get("descricao", texto_original),
            categoria=data.get("categoria"),
            registrado_por=registrado_por,
            texto_original=texto_original
        )
        db.add(foto)
        db.commit()
        return f"✅ Foto registrada: {foto.descricao or 'sem descrição'}"

    elif intent == "consulta":
        # TODO: implementar query builder
        return f"🔍 Consulta recebida. Funcionalidade em desenvolvimento."

    else:
        return f"🤔 Não entendi a intenção '{intent}'. Tente reformular."
