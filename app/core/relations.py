"""
Relation Engine — Lógica de negócio que conecta as tabelas.

Responsabilidades:
1. Clima improdutivo → marca atraso nas atividades em andamento
2. Material pendente do cliente → gera anotação/pendência
3. Atividade concluída → verifica dependências
4. Atividades entre data_inicio e data_fim → auto status "em_andamento"
"""
from datetime import date
from sqlalchemy.orm import Session

from app.models import (
    Atividade, AtividadeHistorico, Anotacao, Material,
    Clima, DiaImprodutivo, AtividadeStatus
)


class RelationEngine:
    """Orquestra as relações lógicas entre registros."""

    def __init__(self, db: Session):
        self.db = db

    # === CLIMA → ATRASO ===
    def processar_clima_improdutivo(self, clima: Clima):
        """
        Se o clima indica dia improdutivo:
        1. Cria registro de DiaImprodutivo
        2. Incrementa dias_atraso em todas atividades em andamento
        3. Cria anotação automática
        """
        if not clima.dia_improdutivo:
            return

        # Verificar se já existe dia improdutivo para esta data
        existente = self.db.query(DiaImprodutivo).filter(
            DiaImprodutivo.obra_id == clima.obra_id,
            DiaImprodutivo.data == clima.data
        ).first()

        if not existente:
            dia = DiaImprodutivo(
                obra_id=clima.obra_id,
                data=clima.data,
                motivo=f"Clima: {clima.condicao}",
                clima_id=clima.id,
                impacto=clima.impacto_trabalho
            )
            self.db.add(dia)

        # Atualizar atividades em andamento
        atividades_ativas = self.db.query(Atividade).filter(
            Atividade.obra_id == clima.obra_id,
            Atividade.status.in_([
                AtividadeStatus.INICIADA,
                AtividadeStatus.EM_ANDAMENTO
            ])
        ).all()

        for ativ in atividades_ativas:
            ativ.dias_atraso = (ativ.dias_atraso or 0) + 1

            # Registrar no histórico
            hist = AtividadeHistorico(
                atividade_id=ativ.id,
                data=clima.data,
                status_anterior=ativ.status.value if isinstance(ativ.status, AtividadeStatus) else ativ.status,
                status_novo=ativ.status.value if isinstance(ativ.status, AtividadeStatus) else ativ.status,
                motivo=f"Atraso por clima ({clima.condicao}): {clima.impacto_trabalho or 'dia improdutivo'}",
                registrado_por="Sistema"
            )
            self.db.add(hist)

        # Anotação automática
        anotacao = Anotacao(
            obra_id=clima.obra_id,
            data=clima.data,
            tipo="atraso",
            descricao=f"Dia improdutivo por clima ({clima.condicao}). "
                      f"{len(atividades_ativas)} atividade(s) impactada(s). "
                      f"{clima.impacto_trabalho or ''}",
            prioridade="alta",
            auto_gerada=True,
            registrado_por="Sistema"
        )
        self.db.add(anotacao)
        self.db.commit()

        return {
            "dia_improdutivo": True,
            "atividades_impactadas": len(atividades_ativas),
            "anotacao_criada": True
        }

    # === MATERIAL PENDENTE → ANOTAÇÃO ===
    def processar_material_pendente(self, material: Material):
        """
        Se material é responsabilidade do cliente e está pendente/atrasado:
        1. Cria anotação/pendência automática
        2. Se atrasado (data_prevista < hoje), prioridade alta
        """
        if material.tipo != "pendente":
            return

        hoje = date.today()
        atrasado = material.data_prevista and material.data_prevista < hoje
        prioridade = "alta" if atrasado else "normal"

        descricao = f"Material pendente: {material.material}"
        if material.quantidade and material.unidade:
            descricao += f" ({material.quantidade} {material.unidade})"
        if material.responsavel and material.responsavel != "próprio":
            descricao += f" — responsabilidade do {material.responsavel}"
        if atrasado:
            dias = (hoje - material.data_prevista).days
            descricao += f" — ATRASADO {dias} dia(s)"

        anotacao = Anotacao(
            obra_id=material.obra_id,
            data=hoje,
            tipo="pendência",
            descricao=descricao,
            prioridade=prioridade,
            material_id=material.id,
            auto_gerada=True,
            registrado_por="Sistema"
        )
        self.db.add(anotacao)
        self.db.commit()

        return {"anotacao_criada": True, "atrasado": atrasado}

    # === ATIVIDADE CONCLUÍDA → VERIFICAR DEPENDÊNCIAS ===
    def processar_conclusao_atividade(self, atividade: Atividade):
        """
        Quando atividade é concluída:
        1. Registra data_fim_real
        2. Verifica se há atividades dependentes que podem iniciar
        3. Cria anotação se havia atraso
        """
        hoje = date.today()
        atividade.data_fim_real = hoje
        atividade.status = AtividadeStatus.CONCLUIDA
        atividade.percentual_concluido = 100.0

        # Histórico
        hist = AtividadeHistorico(
            atividade_id=atividade.id,
            data=hoje,
            status_anterior="em_andamento",
            status_novo="concluida",
            registrado_por=atividade.registrado_por or "Sistema"
        )
        self.db.add(hist)

        # Verificar dependentes
        dependentes = self.db.query(Atividade).filter(
            Atividade.atividade_pai_id == atividade.id,
            Atividade.status == AtividadeStatus.PAUSADA
        ).all()

        for dep in dependentes:
            dep.status = AtividadeStatus.INICIADA
            dep.data_inicio = hoje

        # Anotação se concluiu com atraso
        if atividade.dias_atraso and atividade.dias_atraso > 0:
            anotacao = Anotacao(
                obra_id=atividade.obra_id,
                data=hoje,
                tipo="observação",
                descricao=f"Atividade concluída com {atividade.dias_atraso} dia(s) de atraso: {atividade.descricao}",
                auto_gerada=True,
                registrado_por="Sistema"
            )
            self.db.add(anotacao)

        self.db.commit()

        return {
            "concluida": True,
            "dependentes_liberadas": len(dependentes),
            "atraso_total": atividade.dias_atraso or 0
        }

    # === ATUALIZAR STATUS DIÁRIO ===
    def atualizar_status_atividades(self, obra_id: int):
        """
        Roda diariamente (ou ao gerar RDO):
        - Atividades com data_inicio <= hoje e sem data_fim_real → em_andamento
        - Atividades com data_fim_prevista < hoje e não concluídas → incrementa atraso
        """
        hoje = date.today()

        # Iniciadas que já passaram do primeiro dia → em_andamento
        atividades = self.db.query(Atividade).filter(
            Atividade.obra_id == obra_id,
            Atividade.status == AtividadeStatus.INICIADA,
            Atividade.data_inicio < hoje
        ).all()

        for ativ in atividades:
            ativ.status = AtividadeStatus.EM_ANDAMENTO

        # Em andamento com data_fim_prevista vencida → marcar atraso
        atrasadas = self.db.query(Atividade).filter(
            Atividade.obra_id == obra_id,
            Atividade.status == AtividadeStatus.EM_ANDAMENTO,
            Atividade.data_fim_prevista != None,
            Atividade.data_fim_prevista < hoje
        ).all()

        for ativ in atrasadas:
            dias = (hoje - ativ.data_fim_prevista).days
            ativ.dias_atraso = dias

        self.db.commit()

        return {
            "promovidas_em_andamento": len(atividades),
            "atrasadas": len(atrasadas)
        }
