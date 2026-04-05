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
from datetime import date
from sqlalchemy.orm import Session

from app.core.types import IncomingMessage, OutgoingMessage, IntentType, TipoMensagem
from app.core.relations import RelationEngine
from app.models import (
    Usuario, Atividade, Efetivo, Anotacao, Material,
    Equipamento, Clima, Foto, Expediente, Obra,
    AtividadeStatus, StatusPluviometrico, TipoEfetivo
)
from app.services.intent import classify_intent
from app.services.transcription import transcribe_audio


# Textos pendentes por chat_id (aguardando escolha de botão)
# Em memória — suficiente pro MVP, depois migra pra Redis/banco
_textos_pendentes: dict[str, str] = {}


class Orchestrator:
    """Processa mensagens de qualquer canal e orquestra o registro."""

    def __init__(self, db: Session):
        self.db = db
        self.relations = RelationEngine(db)

    def _salvar_texto_pendente(self, telefone: str, texto: str):
        _textos_pendentes[telefone] = texto

    @staticmethod
    def _recuperar_texto_pendente(telefone: str) -> str:
        return _textos_pendentes.pop(telefone, "")

    async def processar(self, msg: IncomingMessage) -> OutgoingMessage:
        """Ponto de entrada único para todas as mensagens."""

        # 1. Identificar usuário
        usuario = self.db.query(Usuario).filter(
            Usuario.telefone == msg.telefone
        ).first()

        if not usuario:
            return self._resposta(msg, "❌ Número não cadastrado. Peça ao responsável para te adicionar no sistema.")

        if not usuario.obra_id:
            return self._resposta(msg, "⚠️ Você não está vinculado a nenhuma obra.")

        obra_id = usuario.obra_id

        # 2. Obter texto
        texto = msg.texto
        if msg.tipo == TipoMensagem.AUDIO and msg.audio_path:
            try:
                texto = await transcribe_audio(msg.audio_path)
            except Exception as e:
                return self._resposta(msg, f"❌ Erro na transcrição: {str(e)}")

        if not texto and msg.foto_path:
            texto = msg.legenda or "Foto registrada no canteiro"

        if not texto:
            return self._resposta(msg, "🤔 Não entendi. Mande texto ou áudio sobre o que aconteceu na obra.")

        # 3. Classificar intenção
        try:
            intent = await classify_intent(texto, obra_id)
        except Exception as e:
            return self._resposta(msg, f"❌ Erro ao processar: {str(e)}")

        intent_type = intent.get("intent", "desconhecido")
        data = intent.get("data", {})
        confidence = intent.get("confidence", 0)

        # 4. Confiança baixa → botões para escolher, não pedir reformulação
        if confidence < 0.6:
            candidates = intent.get("candidates", [])
            if not candidates:
                candidates = ["atividade", "efetivo", "clima", "material", "anotacao"]

            # Guardar texto original na sessão do orchestrator para recuperar no callback
            # callback_data do Telegram tem limite de 64 bytes
            self._salvar_texto_pendente(msg.telefone, texto)

            return self._resposta(msg, "📋 O que você quer registrar?", botoes=[
                {"text": label, "data": f"forcar:{cat}"}
                for cat, label in self._botoes_para_candidatos(candidates)
            ])

        # 5. Confirmar se necessário
        if intent.get("requires_confirmation"):
            confirm = intent.get("confirmation_message", "Confirma o registro?")
            return self._resposta(msg, f"❓ {confirm}", botoes=[
                {"text": "✅ Sim", "data": f"confirmar:{intent_type}"},
                {"text": "❌ Não", "data": "cancelar"}
            ])

        # 6. Registrar
        try:
            resposta = await self._registrar(
                intent_type, data, obra_id,
                usuario.nome, texto, msg.foto_path
            )
        except Exception as e:
            return self._resposta(msg, f"❌ Erro ao registrar: {str(e)}")

        return self._resposta(msg, resposta)

    async def _registrar(self, intent: str, data: dict, obra_id: int,
                         registrado_por: str, texto_original: str,
                         foto_path: str = None) -> str:
        """Registra dados conforme intenção e dispara Relation Engine."""

        hoje = date.today()

        if intent == "atividade":
            return self._registrar_atividade(data, obra_id, registrado_por, texto_original, hoje)
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

    def _registrar_atividade(self, data, obra_id, registrado_por, texto_original, hoje):
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
        return f"✅ Atividade iniciada: {ativ.descricao}"

    def _concluir_atividade(self, data, obra_id, registrado_por, texto_original):
        # Buscar atividade em andamento que mais se parece
        descricao_busca = data.get("descricao", texto_original)
        atividades = self.db.query(Atividade).filter(
            Atividade.obra_id == obra_id,
            Atividade.status.in_([AtividadeStatus.INICIADA, AtividadeStatus.EM_ANDAMENTO])
        ).all()

        if not atividades:
            return "⚠️ Não há atividades em andamento para concluir."

        # TODO: usar embeddings para matching semântico
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
            exp.hora_inicio = hora_inicio
            exp.hora_termino = hora_termino
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

        motivo_str = f" — {exp.motivo}" if exp.motivo else ""
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
        if mat.tipo == "pendente":
            self.relations.processar_material_pendente(mat)

        qtd = f"{mat.quantidade} {mat.unidade} " if mat.quantidade else ""
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
            cl.status_pluviometrico = StatusPluviometrico(status_pluv)
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

    INTENT_LABELS = {
        "atividade": "🏗️ Atividade",
        "conclusao": "✅ Conclusão",
        "efetivo": "👷 Efetivo",
        "material": "📦 Material",
        "equipamento": "🔧 Equipamento",
        "clima": "☁️ Clima",
        "anotacao": "📝 Anotação",
        "foto": "📷 Foto",
    }

    def _botoes_para_candidatos(self, candidates: list) -> list:
        """Retorna lista de (intent, label) para os botões."""
        return [(c, self.INTENT_LABELS.get(c, c)) for c in candidates if c in self.INTENT_LABELS]

    async def processar_callback(self, callback_data: str, telefone: str,
                                  usuario_nome: str, obra_id: int) -> str:
        """Processa clique em botão inline (forcar:intent)."""
        parts = callback_data.split(":", 2)
        if len(parts) < 2 or parts[0] != "forcar":
            return "❌ Ação inválida."

        intent_type = parts[1]
        texto_original = self._recuperar_texto_pendente(telefone)
        if not texto_original:
            return "⚠️ Mensagem expirou. Mande de novo."

        # Re-classificar com hint forçado para extrair dados
        try:
            from app.services.intent import _call_ollama
            llm_data = await _call_ollama(texto_original, hint=intent_type)
            data = llm_data.get("data", {})
        except Exception:
            data = {}

        hoje = date.today()
        return self._registrar_sync(intent_type, data, obra_id, usuario_nome, texto_original, hoje)

    def _registrar_sync(self, intent: str, data: dict, obra_id: int,
                        registrado_por: str, texto_original: str, hoje=None) -> str:
        """Versão síncrona do registro (para callbacks)."""
        hoje = hoje or date.today()

        if intent == "atividade":
            return self._registrar_atividade(data, obra_id, registrado_por, texto_original, hoje)
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
        else:
            return f"🤔 Categoria '{intent}' não suportada."

    def _resposta(self, msg: IncomingMessage, texto: str, botoes: list = None) -> OutgoingMessage:
        return OutgoingMessage(
            texto=texto,
            canal=msg.canal,
            telefone=msg.telefone,
            botoes=botoes
        )
