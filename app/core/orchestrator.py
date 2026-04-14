"""
Orquestrador — Ponto central de processamento de mensagens.

Fluxo:
1. Recebe IncomingMessage (já normalizada pelo adapter)
2. Identifica usuário
3. Se áudio → transcreve
4. Classifica intenção (Ollama)
5. Roteia para módulo correto
6. Módulo registra no banco
7. Relation Engine valida impactos cruzados
8. Retorna OutgoingMessage
"""
import logging
from datetime import date
from typing import Optional, cast

logger = logging.getLogger(__name__)

from sqlalchemy.orm import Session

from app.core.relations import RelationEngine
from app.core.types import Canal, IncomingMessage, OutgoingMessage, TipoMensagem
from app.models import (
    Atividade,
    AtividadeStatus,
    Anotacao,
    Clima,
    Efetivo,
    Equipamento,
    Expediente,
    Foto,
    Material,
    Obra,
    StatusPluviometrico,
    TipoEfetivo,
    Usuario,
)
from app.services.activity_semantics import ActivitySemanticSearch
from app.services.conversation_state import ConversationStateService
from app.services.intent import classify_intent
from app.services.transcription import transcribe_audio


class Orchestrator:
    """Processa mensagens de qualquer canal e orquestra o registro."""

    INTENT_CONFIDENCE_THRESHOLD = 0.6
    STATE_KIND_INTENT = "intent_choice"
    STATE_KIND_CONFIRMATION = "confirmation"
    STATE_KIND_ACTIVITY = "activity_choice"

    INTENT_LABELS = {
        "atividade": "🏗️ Atividade",
        "conclusao": "✅ Conclusão",
        "efetivo": "👷 Efetivo",
        "material": "📦 Material",
        "equipamento": "🔧 Equipamento",
        "clima": "☁️ Clima",
        "anotacao": "📝 Anotação",
        "foto": "📷 Foto",
        "expediente": "⏱️ Expediente",
        "consulta": "🔎 Consulta",
    }

    DEFAULT_INTENT_CHOICES = [
        "atividade",
        "conclusao",
        "efetivo",
        "material",
        "equipamento",
        "clima",
        "anotacao",
        "expediente",
        "foto",
        "consulta",
    ]

    def __init__(self, db: Session):
        self.db = db
        self.relations = RelationEngine(db)
        self.state_service = ConversationStateService(db)
        self.semantic_search = ActivitySemanticSearch(db)

    @staticmethod
    def _variantes_telefone_br(telefone: str) -> list[str]:
        """Gera variantes de número brasileiro (com/sem nono dígito)."""
        variantes = [telefone]
        if not telefone.startswith("55") or len(telefone) not in (12, 13):
            return variantes
        ddd = telefone[2:4]
        if len(telefone) == 12:
            # sem nono dígito → adicionar
            variantes.append(f"55{ddd}9{telefone[4:]}")
        elif len(telefone) == 13 and telefone[4] == "9":
            # com nono dígito → remover
            variantes.append(f"55{ddd}{telefone[5:]}")
        return variantes

    async def processar(self, msg: IncomingMessage) -> OutgoingMessage:
        """Ponto de entrada único para todas as mensagens."""

        # 1. Identificar usuário (com normalização de nono dígito BR)
        variantes = self._variantes_telefone_br(msg.telefone)
        usuario = self.db.query(Usuario).filter(
            Usuario.telefone.in_(variantes)
        ).first()

        if not usuario:
            return self._resposta(msg, "❌ Número não cadastrado. Peça ao responsável para te adicionar no sistema.")

        obra_id = usuario.obra_id
        if obra_id is None:
            return self._resposta(msg, "⚠️ Você não está vinculado a nenhuma obra.")

        scope_key = self.state_service.build_scope_key(msg.canal.value, msg.telefone)

        # Normalize user props para evitar confusão de tipos do SQLAlchemy
        usuario_nome_val = cast(str, getattr(usuario, "nome", getattr(getattr(usuario, "usuario", None), "nome", "")))
        usuario_obra_id = cast(Optional[int], getattr(usuario, "obra_id", getattr(getattr(usuario, "usuario", None), "obra_id", None)))

        # 2. Se há um estado pendente para este canal, a próxima mensagem
        # resolve esse estado antes de qualquer nova classificação.
        pending_state = self.state_service.get_active_state(scope_key)
        if pending_state:
            texto_resposta = self._texto_de_resposta(msg)
            if not texto_resposta:
                return self._resposta(
                    msg,
                    "📋 Tenho uma escolha pendente aqui. Responda com o número da opção ou com um texto curto."
                )
            return await self._resolver_estado_pendente(
                msg=msg,
                usuario_nome=usuario_nome_val,
                obra_id=cast(int, usuario_obra_id),
                estado=pending_state,
                texto_resposta=texto_resposta,
            )

        # 3. Obter texto
        try:
            texto = await self._extrair_texto_principal(msg)
        except Exception as exc:
            return self._resposta(msg, f"❌ Erro na transcrição: {str(exc)}")
        if not texto:
            return self._resposta(msg, "🤔 Não entendi. Mande texto ou áudio sobre o que aconteceu na obra.")

        # 4. Classificar intenção
        try:
            intent = await classify_intent(texto, cast(Optional[int], obra_id))
        except Exception as e:
            return self._resposta(msg, f"❌ Erro ao processar: {str(e)}")

        # usuário já validado, obra_id não é None aqui — cast para int para o typechecker
        obra_id_val = cast(int, usuario.obra_id)
        return await self._processar_intent_resultado(
            msg=msg,
            usuario_nome=cast(str, usuario.nome),
            obra_id=obra_id_val,
            texto_original=texto,
            intent_result=intent,
            prompt_confianca_baixa=True,
            pode_confirmar=True,
        )

    async def _registrar(self, intent: str, data: dict, obra_id: int,
                         registrado_por: str, texto_original: str,
                         foto_path: str | None = None) -> str:
        """Registra dados conforme intenção e dispara Relation Engine."""

        hoje = date.today()

        if intent == "atividade":
            return await self._registrar_atividade(data, obra_id, registrado_por, texto_original, hoje)
        elif intent == "conclusao":
            return self._concluir_atividade(data, obra_id, registrado_por, texto_original)
        elif intent == "efetivo":
            return self._registrar_efetivo(data, obra_id, registrado_por, texto_original, hoje)
        elif intent == "material":
            return self._registrar_material(data, obra_id, registrado_por, texto_original, hoje)
        elif intent == "equipamento":
            return self._registrar_equipamento(data, obra_id, registrado_por, texto_original, hoje)
        elif intent == "clima":
            return self._registrar_clima(data, obra_id, texto_original, hoje)
        elif intent == "expediente":
            return self._registrar_expediente(data, obra_id, registrado_por, texto_original, hoje)
        elif intent == "anotacao":
            return self._registrar_anotacao(data, obra_id, registrado_por, texto_original, hoje)
        elif intent == "foto" and foto_path:
            return self._registrar_foto(data, obra_id, registrado_por, texto_original, foto_path, hoje)
        elif intent == "consulta":
            return "🔍 Consultas em desenvolvimento."
        else:
            return f"🤔 Não entendi '{intent}'. Tente reformular."

    async def _registrar_atividade(self, data, obra_id, registrado_por, texto_original, hoje):
        ativ = Atividade(
            obra_id=obra_id,
            descricao=data.get("descricao", texto_original),
            local=data.get("local"),
            etapa=data.get("etapa"),
            data_inicio=hoje,
            data_fim_prevista=data.get("data_fim_prevista"),
            status=AtividadeStatus.INICIADA,
            registrado_por=registrado_por,
            texto_original=texto_original
        )
        self.db.add(ativ)
        self.db.commit()
        try:
            await self.semantic_search.upsert_activity_embedding(ativ)
        except Exception:
            # A atividade continua registrada mesmo se o embedding falhar.
            pass
        return f"✅ Atividade iniciada: {ativ.descricao}"

    def _concluir_atividade(self, data, obra_id, registrado_por, texto_original):
        # Fallback legado: busca por palavras-chave quando o fluxo semântico
        # não estiver disponível.
        descricao_busca = data.get("descricao", texto_original)
        atividades = self.db.query(Atividade).filter(
            Atividade.obra_id == obra_id,
            Atividade.status.in_([AtividadeStatus.INICIADA, AtividadeStatus.EM_ANDAMENTO])
        ).all()

        if not atividades:
            return "⚠️ Não há atividades em andamento para concluir."

        # Por agora, pega a primeira que contém palavras-chave
        melhor = atividades[0]
        for ativ in atividades:
            palavras = descricao_busca.lower().split()
            if any(p in ativ.descricao.lower() for p in palavras if len(p) > 3):
                melhor = ativ
                break

        result = self.relations.processar_conclusao_atividade(melhor)
        return (
            f"✅ Atividade concluída: {melhor.descricao}\n"
            f"{'⚠️ Com ' + str(result['atraso_total']) + ' dia(s) de atraso' if result['atraso_total'] > 0 else ''}"
            f"{'🔓 ' + str(result['dependentes_liberadas']) + ' atividade(s) dependente(s) liberada(s)' if result['dependentes_liberadas'] > 0 else ''}"
        ).strip()

    def _registrar_efetivo(self, data, obra_id, registrado_por, texto_original, hoje):
        registros = data.get("registros", [data])
        proprios, empreiteiros = [], []

        for reg in registros:
            tipo_str = reg.get("tipo", "proprio")
            try:
                tipo = TipoEfetivo(tipo_str)
            except ValueError:
                tipo = TipoEfetivo.PROPRIO

            ef = Efetivo(
                obra_id=obra_id, data=hoje,
                tipo=tipo,
                funcao=reg.get("funcao"),
                quantidade=reg.get("quantidade", 1),
                empresa=reg.get("empresa"),
                registrado_por=registrado_por,
                texto_original=texto_original
            )
            self.db.add(ef)

            if tipo == TipoEfetivo.PROPRIO:
                label = f"{ef.quantidade} {ef.funcao or 'geral'}"
                proprios.append(label)
            else:
                label = f"{ef.quantidade} ({ef.empresa or 'empreiteira'})"
                empreiteiros.append(label)

        self.db.commit()

        total_proprio = sum(r.get("quantidade", 1) for r in registros if r.get("tipo", "proprio") == "proprio")
        total_emp = sum(r.get("quantidade", 1) for r in registros if r.get("tipo") == "empreiteiro")
        total_geral = total_proprio + total_emp

        linhas = ["✅ Efetivo registrado:"]
        if proprios:
            linhas.append(f"  Empresa: {', '.join(proprios)} (total: {total_proprio})")
        if empreiteiros:
            linhas.append(f"  Empreiteiras: {', '.join(empreiteiros)} (total: {total_emp})")
        linhas.append(f"  Total geral: {total_geral}")
        return "\n".join(linhas)

    def _registrar_expediente(self, data, obra_id, registrado_por, texto_original, hoje):
        """Registra ou atualiza o horário do dia. Usa padrão da obra se campos faltarem."""
        obra = self.db.query(Obra).filter(Obra.id == obra_id).first()

        hora_inicio = data.get("hora_inicio") or (obra.hora_inicio_padrao if obra else "07:00")
        hora_termino = data.get("hora_termino") or (obra.hora_termino_padrao if obra else "17:00")

        exp = self.db.query(Expediente).filter(
            Expediente.obra_id == obra_id,
            Expediente.data == hoje
        ).first()

        if exp:
            setattr(exp, "hora_inicio", hora_inicio)
            setattr(exp, "hora_termino", hora_termino)
            exp.motivo = data.get("motivo") or exp.motivo
            exp.texto_original = texto_original
        else:
            exp = Expediente(
                obra_id=obra_id, data=hoje,
                hora_inicio=hora_inicio,
                hora_termino=hora_termino,
                motivo=data.get("motivo"),
                registrado_por=registrado_por,
                texto_original=texto_original
            )
            self.db.add(exp)

        self.db.commit()

        motivo = getattr(exp, "motivo", None)
        motivo_str = f" — {motivo}" if motivo else ""
        return f"✅ Expediente: {exp.hora_inicio}–{exp.hora_termino}{motivo_str}"

    def _registrar_material(self, data, obra_id, registrado_por, texto_original, hoje):
        mat = Material(
            obra_id=obra_id, data=hoje,
            tipo=data.get("tipo", "entrada"),
            material=data.get("material", "Não especificado"),
            quantidade=data.get("quantidade"),
            unidade=data.get("unidade"),
            fornecedor=data.get("fornecedor"),
            nota_fiscal=data.get("nota_fiscal"),
            responsavel=data.get("responsavel", "próprio"),
            data_prevista=data.get("data_prevista"),
            registrado_por=registrado_por,
            texto_original=texto_original
        )
        self.db.add(mat)
        self.db.commit()

        # Relation Engine: material pendente?
        if getattr(mat, "tipo", "") == "pendente":
            self.relations.processar_material_pendente(mat)

        quantidade = getattr(mat, "quantidade", None)
        unidade = getattr(mat, "unidade", "")
        qtd = f"{quantidade} {unidade} " if quantidade else ""
        return f"✅ Material ({mat.tipo}): {qtd}{mat.material}"

    def _registrar_equipamento(self, data, obra_id, registrado_por, texto_original, hoje):
        tipos_validos = {"entrada", "saída", "saida", "manutenção", "manutencao", "aluguel"}
        tipo = data.get("tipo", "entrada").lower()
        equipamento = data.get("equipamento", "Não especificado")

        # LLM às vezes inverte tipo/equipamento — corrigir
        if tipo not in tipos_validos:
            if equipamento.lower() in tipos_validos:
                tipo, equipamento = equipamento.lower(), tipo
            else:
                # tipo contém o nome do equipamento
                equipamento = tipo
                tipo = "entrada"

        equip = Equipamento(
            obra_id=obra_id, data=hoje,
            tipo=tipo[:30],
            equipamento=equipamento,
            quantidade=data.get("quantidade", 1),
            horas_trabalhadas=data.get("horas_trabalhadas"),
            operador=data.get("operador"),
            registrado_por=registrado_por,
            texto_original=texto_original
        )
        self.db.add(equip)
        self.db.commit()
        return f"✅ Equipamento ({equip.tipo}): {equip.quantidade}x {equip.equipamento}"

    def _registrar_clima(self, data, obra_id, texto_original, hoje):
        periodo = data.get("periodo", "manhã")
        dia_improdutivo = data.get("dia_improdutivo", False)
        status_pluv = data.get("status_pluviometrico", "seco_produtivo")

        # Upsert: se já existe registro para este período, atualiza
        cl = self.db.query(Clima).filter(
            Clima.obra_id == obra_id,
            Clima.data == hoje,
            Clima.periodo == periodo
        ).first()

        if cl:
            cl.condicao = data.get("condicao") or cl.condicao
            cl.anotacao_rdo = data.get("anotacao_rdo", cl.anotacao_rdo)
            # usar setattr para evitar conflito de tipos estáticos do SQLAlchemy
            setattr(cl, "status_pluviometrico", StatusPluviometrico(status_pluv))
            cl.temperatura = data.get("temperatura") or cl.temperatura
            cl.impacto_trabalho = data.get("impacto_trabalho") or cl.impacto_trabalho
            cl.dia_improdutivo = dia_improdutivo
            cl.texto_original = texto_original
        else:
            cl = Clima(
                obra_id=obra_id, data=hoje,
                periodo=periodo,
                condicao=data.get("condicao"),
                anotacao_rdo=data.get("anotacao_rdo", "sol"),
                status_pluviometrico=StatusPluviometrico(status_pluv),
                temperatura=data.get("temperatura"),
                impacto_trabalho=data.get("impacto_trabalho"),
                dia_improdutivo=dia_improdutivo,
                texto_original=texto_original
            )
            self.db.add(cl)

        self.db.commit()

        # Herança de status para período seguinte se for improdutivo e tarde ainda vazia
        if dia_improdutivo and periodo == "manhã":
            self._herdar_status_tarde(obra_id, hoje, cl)

        # Relation Engine: dia improdutivo?
        result = self.relations.processar_clima_improdutivo(cl)

        resp = f"✅ Clima ({cl.periodo}): {cl.condicao or 'registrado'} — {cl.status_pluviometrico.value.replace('_', ' ')}"
        if result and result.get("dia_improdutivo"):
            resp += f"\n⚠️ Dia improdutivo — {result['atividades_impactadas']} atividade(s) impactada(s)"
        return resp

    def _herdar_status_tarde(self, obra_id: int, data, clima_manha: Clima):
        """Se manhã foi improdutiva e tarde não tem registro, cria herança."""
        existe_tarde = self.db.query(Clima).filter(
            Clima.obra_id == obra_id,
            Clima.data == data,
            Clima.periodo == "tarde"
        ).first()
        if not existe_tarde:
            tarde = Clima(
                obra_id=obra_id, data=data,
                periodo="tarde",
                condicao=clima_manha.condicao,
                anotacao_rdo=clima_manha.anotacao_rdo,
                status_pluviometrico=clima_manha.status_pluviometrico,
                dia_improdutivo=clima_manha.dia_improdutivo,
                texto_original="[herdado da manhã — confirmar]"
            )
            self.db.add(tarde)
            self.db.commit()

    def _registrar_anotacao(self, data, obra_id, registrado_por, texto_original, hoje):
        anot = Anotacao(
            obra_id=obra_id, data=hoje,
            tipo=data.get("tipo", "observação"),
            descricao=data.get("descricao", texto_original),
            prioridade=data.get("prioridade", "normal"),
            registrado_por=registrado_por,
            texto_original=texto_original
        )
        self.db.add(anot)
        self.db.commit()
        return f"✅ Anotação: {anot.descricao[:60]}..."

    def _registrar_foto(self, data, obra_id, registrado_por, texto_original, foto_path, hoje):
        foto = Foto(
            obra_id=obra_id, data=hoje,
            arquivo=foto_path,
            descricao=data.get("descricao", texto_original),
            categoria=data.get("categoria"),
            registrado_por=registrado_por,
            texto_original=texto_original
        )
        self.db.add(foto)
        self.db.commit()
        return f"✅ Foto registrada: {foto.descricao or 'sem descrição'}"

    def _texto_de_resposta(self, msg: IncomingMessage) -> Optional[str]:
        if msg.texto:
            return msg.texto
        if msg.tipo == TipoMensagem.FOTO and msg.legenda:
            return msg.legenda
        return None

    async def _extrair_texto_principal(self, msg: IncomingMessage) -> Optional[str]:
        texto = msg.texto
        if msg.tipo == TipoMensagem.AUDIO and msg.audio_path:
            try:
                texto = await transcribe_audio(msg.audio_path)
            except Exception as exc:
                raise RuntimeError(str(exc)) from exc
        if not texto and msg.foto_path:
            texto = msg.legenda or "Foto registrada no canteiro"
        return texto

    @staticmethod
    def _opcoes_por_intents(candidates: list[str]) -> list[dict]:
        opcoes = []
        vistos = set()
        for intent in candidates:
            if intent in vistos:
                continue
            vistos.add(intent)
            opcoes.append({
                "value": intent,
                "label": Orchestrator.INTENT_LABELS.get(intent, intent),
            })
        return opcoes

    @staticmethod
    def _opcoes_confirmacao() -> list[dict]:
        return [
            {"value": "yes", "label": "✅ Sim"},
            {"value": "no", "label": "❌ Não"},
        ]

    @staticmethod
    def _opcoes_por_atividades(matches: list[dict]) -> list[dict]:
        opcoes = []
        for match in matches:
            descricao = match.get("descricao") or "Atividade"
            local = match.get("local")
            etapa = match.get("etapa")
            partes = [descricao]
            detalhes = [parte for parte in [local, etapa] if parte]
            if detalhes:
                partes.append(" - ".join(detalhes))
            label = " | ".join(partes)
            opcoes.append({"value": str(match.get("atividade_id")), "label": label[:120]})
        return opcoes

    @staticmethod
    def _botoes_estado(state_token: str, choices: list[dict]) -> list[dict]:
        return [
            {"text": choice["label"], "data": f"state:{state_token}:{choice['value']}"}
            for choice in choices
        ]

    @staticmethod
    def _selecionar_opcao(texto: str, choices: list[dict]) -> Optional[dict]:
        texto_normalizado = (texto or "").strip().lower()
        if not texto_normalizado:
            return None

        if texto_normalizado.isdigit():
            indice = int(texto_normalizado) - 1
            if 0 <= indice < len(choices):
                return choices[indice]

        aliases_sim = {"sim", "s", "yes", "y", "confirmar", "confirmo", "ok", "okay"}
        aliases_nao = {"nao", "não", "n", "no", "cancelar", "cancela", "cancelado", "não confirma"}

        for choice in choices:
            value = str(choice.get("value", "")).lower()
            label = str(choice.get("label", "")).lower()
            if texto_normalizado == value or texto_normalizado == label:
                return choice
            if texto_normalizado in label or label in texto_normalizado:
                return choice
            if value == "yes" and texto_normalizado in aliases_sim:
                return choice
            if value == "no" and texto_normalizado in aliases_nao:
                return choice
        return None

    def _resposta(self, msg: IncomingMessage, texto: str, botoes: list | None = None) -> OutgoingMessage:
        return OutgoingMessage(
            texto=texto,
            canal=msg.canal,
            telefone=msg.telefone,
            botoes=botoes,
        )

    @staticmethod
    def _resposta_canal(canal: Canal, telefone: str, texto: str, botoes: list | None = None) -> OutgoingMessage:
        return OutgoingMessage(
            texto=texto,
            canal=canal,
            telefone=telefone,
            botoes=botoes,
        )

    def _resumo_conclusao(self, atividade: Atividade, result: dict) -> str:
        partes = [f"✅ Atividade concluída: {atividade.descricao}"]
        if result.get("atraso_total", 0) > 0:
            partes.append(f"⚠️ Com {result['atraso_total']} dia(s) de atraso")
        if result.get("dependentes_liberadas", 0) > 0:
            partes.append(f"🔓 {result['dependentes_liberadas']} atividade(s) dependente(s) liberada(s)")
        return "\n".join(partes)

    async def _processar_intent_resultado(
        self,
        msg: IncomingMessage,
        usuario_nome: str,
        obra_id: int,
        texto_original: str,
        intent_result: dict,
        *,
        prompt_confianca_baixa: bool = True,
        pode_confirmar: bool = True,
    ) -> OutgoingMessage:
        intent_type = intent_result.get("intent", "desconhecido")
        data = intent_result.get("data", {}) or {}
        confidence = float(intent_result.get("confidence") or 0)

        if prompt_confianca_baixa and confidence < self.INTENT_CONFIDENCE_THRESHOLD:
            candidates = intent_result.get("candidates") or self.DEFAULT_INTENT_CHOICES
            opcoes = self._opcoes_por_intents(candidates)
            state = self.state_service.set_state(
                channel=msg.canal.value,
                identifier=msg.telefone,
                state_type=self.STATE_KIND_INTENT,
                payload={
                    "text_original": texto_original,
                    "choices": opcoes,
                },
                text_original=texto_original,
                source_message_id=msg.message_id,
            )
            return self._resposta(
                msg,
                "📋 O que você quer registrar?",
                botoes=self._botoes_estado(state.state_token, opcoes),
            )

        if pode_confirmar and intent_result.get("requires_confirmation"):
            confirm = intent_result.get("confirmation_message", "Confirma o registro?")
            state = self.state_service.set_state(
                channel=msg.canal.value,
                identifier=msg.telefone,
                state_type=self.STATE_KIND_CONFIRMATION,
                payload={
                    "text_original": texto_original,
                    "intent_result": intent_result,
                    "choices": self._opcoes_confirmacao(),
                },
                text_original=texto_original,
                source_message_id=msg.message_id,
            )
            return self._resposta(
                msg,
                f"❓ {confirm}",
                botoes=self._botoes_estado(state.state_token, self._opcoes_confirmacao()),
            )

        if intent_type == "conclusao":
            return await self._resolver_conclusao_semantica(
                msg=msg,
                obra_id=obra_id,
                usuario_nome=usuario_nome,
                texto_original=texto_original,
                data=data,
            )

        try:
            resposta = await self._registrar(
                intent_type,
                data,
                obra_id,
                usuario_nome,
                texto_original,
                msg.foto_path,
            )
        except Exception as exc:
            return self._resposta(msg, f"❌ Erro ao registrar: {str(exc)}")

        return self._resposta(msg, resposta)

    async def _resolver_estado_pendente(
        self,
        msg: IncomingMessage,
        usuario_nome: str,
        obra_id: int,
        estado,
        texto_resposta: str,
    ) -> OutgoingMessage:
        choices = estado.payload.get("choices") or []
        escolha = self._selecionar_opcao(texto_resposta, choices)
        if not escolha:
            if estado.state_type == self.STATE_KIND_CONFIRMATION:
                return self._resposta(
                    msg,
                    "❓ Responda com 1 para confirmar ou 2 para cancelar.",
                    botoes=self._botoes_estado(estado.state_token, self._opcoes_confirmacao()),
                )
            if estado.state_type == self.STATE_KIND_ACTIVITY:
                return self._resposta(
                    msg,
                    "🎯 Responda com o número da atividade que você quer concluir.",
                    botoes=self._botoes_estado(estado.state_token, choices),
                )
            return self._resposta(
                msg,
                "📋 Responda com o número da opção ou escreva o nome da categoria.",
                botoes=self._botoes_estado(estado.state_token, choices),
            )

        estado_consumido = self.state_service.consume_state(state_token=estado.state_token)
        if not estado_consumido:
            return self._resposta(msg, "⚠️ Essa escolha expirou. Mande a mensagem de novo.")

        if estado.state_type == self.STATE_KIND_INTENT:
            intent_result = await classify_intent(
                estado.payload.get("text_original") or texto_resposta,
                obra_id,
                forced_intent=escolha["value"],
            )
            return await self._processar_intent_resultado(
                msg=msg,
                usuario_nome=usuario_nome,
                obra_id=obra_id,
                texto_original=estado.payload.get("text_original") or texto_resposta,
                intent_result=intent_result,
                prompt_confianca_baixa=False,
                pode_confirmar=True,
            )

        if estado.state_type == self.STATE_KIND_CONFIRMATION:
            if escolha["value"] == "no":
                return self._resposta(msg, "❌ Cancelado.")

            intent_result = estado.payload.get("intent_result") or {}
            return await self._processar_intent_resultado(
                msg=msg,
                usuario_nome=usuario_nome,
                obra_id=obra_id,
                texto_original=estado.payload.get("text_original") or texto_resposta,
                intent_result=intent_result,
                prompt_confianca_baixa=False,
                pode_confirmar=False,
            )

        if estado.state_type == self.STATE_KIND_ACTIVITY:
            atividade = self.db.query(Atividade).filter(
                Atividade.id == int(escolha["value"]),
                Atividade.obra_id == obra_id,
            ).first()
            if not atividade:
                return self._resposta(msg, "⚠️ Atividade não encontrada. Tente novamente.")

            result = self.relations.processar_conclusao_atividade(atividade)
            return self._resposta(msg, self._resumo_conclusao(atividade, result))

        return self._resposta(msg, "❌ Estado pendente não reconhecido.")

    async def _resolver_conclusao_semantica(
        self,
        msg: IncomingMessage,
        obra_id: int,
        usuario_nome: str,
        texto_original: str,
        data: dict,
    ) -> OutgoingMessage:
        texto_busca = data.get("descricao") or texto_original

        try:
            resultado = await self.semantic_search.search(obra_id, texto_busca, limit=3)
        except Exception as exc:
            logger.warning(
                "semantic_search falhou, usando fallback keyword | obra_id=%s erro=%s",
                obra_id, exc,
            )
            return self._resposta(
                msg,
                self._concluir_atividade(data, obra_id, usuario_nome, texto_original),
            )

        logger.info(
            "semantic_search | obra_id=%s strategy=%s best_score=%.4f second_score=%.4f "
            "selected=%s candidates=%d query=%r",
            obra_id,
            resultado.strategy,
            resultado.best_score,
            resultado.second_score,
            resultado.selected.atividade_id if resultado.selected else None,
            len(resultado.candidates),
            texto_busca[:80],
        )

        if resultado.selected:
            atividade = self.semantic_search.get_activity(resultado.selected.atividade_id)
            if atividade:
                result = self.relations.processar_conclusao_atividade(atividade)
                return self._resposta(msg, self._resumo_conclusao(atividade, result))

        if resultado.candidates:
            matches = [
                {
                    "atividade_id": match.atividade_id,
                    "descricao": match.descricao,
                    "local": match.local,
                    "etapa": match.etapa,
                    "score": match.score,
                }
                for match in resultado.candidates
            ]
            choices = self._opcoes_por_atividades(matches)
            state = self.state_service.set_state(
                channel=msg.canal.value,
                identifier=msg.telefone,
                state_type=self.STATE_KIND_ACTIVITY,
                payload={
                    "text_original": texto_original,
                    "matches": matches,
                    "choices": choices,
                },
                text_original=texto_original,
                source_message_id=msg.message_id,
            )
            return self._resposta(
                msg,
                "🎯 Encontrei mais de uma atividade parecida. Qual você quer concluir?",
                botoes=self._botoes_estado(state.state_token, choices),
            )

        return self._resposta(
            msg,
            self._concluir_atividade(data, obra_id, usuario_nome, texto_original),
        )

    async def processar_callback(self, callback_data: str, telefone: str,
                                 usuario_nome: str, obra_id: int) -> OutgoingMessage:
        """Processa clique em botão inline ou callback legado."""
        scope_key = self.state_service.build_scope_key(Canal.TELEGRAM.value, telefone)

        if callback_data.startswith("state:"):
            partes = callback_data.split(":", 2)
            if len(partes) < 3:
                return self._resposta_canal(Canal.TELEGRAM, telefone, "❌ Ação inválida.")
            state = self.state_service.get_state_by_token(partes[1])
            if not state or state.scope_key != scope_key:
                return self._resposta_canal(Canal.TELEGRAM, telefone, "⚠️ Mensagem expirou. Mande de novo.")
            return await self._resolver_estado_callback(
                state=state,
                choice_value=partes[2],
                telefone=telefone,
                usuario_nome=usuario_nome,
                obra_id=obra_id,
            )

        if callback_data.startswith("forcar:"):
            state = self.state_service.get_active_state(scope_key)
            if not state:
                return self._resposta_canal(Canal.TELEGRAM, telefone, "⚠️ Mensagem expirou. Mande de novo.")
            return await self._resolver_estado_callback(
                state=state,
                choice_value=callback_data.split(":", 1)[1],
                telefone=telefone,
                usuario_nome=usuario_nome,
                obra_id=obra_id,
            )

        if callback_data.startswith("confirmar:"):
            state = self.state_service.get_active_state(scope_key)
            if not state:
                return self._resposta_canal(Canal.TELEGRAM, telefone, "⚠️ Mensagem expirou. Mande de novo.")
            return await self._resolver_estado_callback(
                state=state,
                choice_value="yes",
                telefone=telefone,
                usuario_nome=usuario_nome,
                obra_id=obra_id,
            )

        if callback_data == "cancelar":
            state = self.state_service.get_active_state(scope_key)
            if state:
                self.state_service.consume_state(state_token=state.state_token)
            return self._resposta_canal(Canal.TELEGRAM, telefone, "❌ Cancelado.")

        return self._resposta_canal(Canal.TELEGRAM, telefone, "❌ Ação inválida.")

    async def _resolver_estado_callback(
        self,
        state,
        choice_value: str,
        telefone: str,
        usuario_nome: str,
        obra_id: int,
    ) -> OutgoingMessage:
        choices = state.payload.get("choices") or []
        escolha = self._selecionar_opcao(choice_value, choices)
        if not escolha and state.state_type == self.STATE_KIND_CONFIRMATION:
            if choice_value.lower() in {"yes", "sim", "s", "1"}:
                escolha = {"value": "yes", "label": "✅ Sim"}
            elif choice_value.lower() in {"no", "nao", "não", "n", "2"}:
                escolha = {"value": "no", "label": "❌ Não"}

        if not escolha:
            return self._resposta_canal(Canal.TELEGRAM, telefone, "⚠️ Escolha inválida.")

        estado_consumido = self.state_service.consume_state(state_token=state.state_token)
        if not estado_consumido:
            return self._resposta_canal(Canal.TELEGRAM, telefone, "⚠️ Mensagem expirou. Mande de novo.")

        if state.state_type == self.STATE_KIND_INTENT:
            intent_result = await classify_intent(
                state.payload.get("text_original") or "",
                obra_id,
                forced_intent=escolha["value"],
            )
            msg = IncomingMessage(
                canal=Canal.TELEGRAM,
                telefone=telefone,
            )
            return await self._processar_intent_resultado(
                msg=msg,
                usuario_nome=usuario_nome,
                obra_id=obra_id,
                texto_original=state.payload.get("text_original") or "",
                intent_result=intent_result,
                prompt_confianca_baixa=False,
                pode_confirmar=True,
            )

        if state.state_type == self.STATE_KIND_CONFIRMATION:
            if escolha["value"] == "no":
                return self._resposta_canal(Canal.TELEGRAM, telefone, "❌ Cancelado.")

            intent_result = state.payload.get("intent_result") or {}
            msg = IncomingMessage(
                canal=Canal.TELEGRAM,
                telefone=telefone,
            )
            return await self._processar_intent_resultado(
                msg=msg,
                usuario_nome=usuario_nome,
                obra_id=obra_id,
                texto_original=state.payload.get("text_original") or "",
                intent_result=intent_result,
                prompt_confianca_baixa=False,
                pode_confirmar=False,
            )

        if state.state_type == self.STATE_KIND_ACTIVITY:
            atividade = self.db.query(Atividade).filter(
                Atividade.id == int(escolha["value"]),
                Atividade.obra_id == obra_id,
            ).first()
            if not atividade:
                return self._resposta_canal(Canal.TELEGRAM, telefone, "⚠️ Atividade não encontrada. Tente novamente.")
            result = self.relations.processar_conclusao_atividade(atividade)
            return self._resposta_canal(Canal.TELEGRAM, telefone, self._resumo_conclusao(atividade, result))

        return self._resposta_canal(Canal.TELEGRAM, telefone, "❌ Estado pendente não reconhecido.")

    # método `_resposta_canal` está definido mais acima como `@staticmethod`.
    # Removido aqui para evitar duplicação que confunde o typechecker.
