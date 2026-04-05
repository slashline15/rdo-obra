"""
Seed — dados de exemplo realistas.
Roda com: python -m app.seed
"""
from datetime import date, timedelta
from app.database import SessionLocal, init_db
from app.models import (
    Empresa, Obra, Usuario, Atividade, AtividadeHistorico, Efetivo,
    Anotacao, Material, Equipamento, Clima, DiaImprodutivo, Foto,
    Expediente, AtividadeStatus, TipoEfetivo, StatusPluviometrico
)


def seed():
    init_db()
    db = SessionLocal()

    # Limpar — ordem respeita FKs (dependentes primeiro)
    for model in [AtividadeHistorico, DiaImprodutivo, Foto, Anotacao, Clima, Expediente, Equipamento, Material, Efetivo, Atividade, Usuario, Obra, Empresa]:
        db.query(model).delete()
    db.commit()

    # Empresa
    empresa = Empresa(
        nome="Construtora Exemplo Ltda",
        cnpj="12.345.678/0001-90",
        template_pdf="rdo_default.html",
        config={"cor_primaria": "#2c3e50", "cor_secundaria": "#3498db"}
    )
    db.add(empresa)
    db.commit()
    db.refresh(empresa)

    # Obra
    obra = Obra(
        nome="Edifício Residencial Aurora",
        endereco="Rua das Palmeiras, 500 - Manaus/AM",
        empresa_id=empresa.id,
        responsavel="Eng. Daniel Silva",
        data_inicio=date(2026, 1, 15),
        data_fim_prevista=date(2027, 6, 30),
        status="ativa",
        hora_inicio_padrao="07:00",
        hora_termino_padrao="17:00",
    )
    db.add(obra)
    db.commit()
    db.refresh(obra)

    # Usuários
    usuarios = [
        Usuario(nome="Daniel Silva", telefone="5592999990001", obra_id=obra.id, role="responsavel"),
        Usuario(nome="Carlos Encarregado", telefone="5592999990002", obra_id=obra.id, role="encarregado"),
        Usuario(nome="Maria Estagiária", telefone="5592999990003", obra_id=obra.id, role="estagiario"),
    ]
    db.add_all(usuarios)
    db.commit()

    hoje = date.today()
    ontem = hoje - timedelta(days=1)
    anteontem = hoje - timedelta(days=2)

    # Atividades (com estados diferentes)
    atividades = [
        Atividade(
            obra_id=obra.id,
            descricao="Execução de concretagem da laje do 2º pavimento tipo",
            local="2º Pavimento", etapa="Estrutura",
            data_inicio=anteontem, data_fim_prevista=hoje,
            status=AtividadeStatus.EM_ANDAMENTO,
            percentual_concluido=70.0,
            registrado_por="Carlos Encarregado",
            texto_original="Começamos a bater a laje do segundo andar"
        ),
        Atividade(
            obra_id=obra.id,
            descricao="Execução de instalações elétricas — tubulação seca no pavimento térreo",
            local="Térreo", etapa="Instalações Elétricas",
            data_inicio=ontem,
            status=AtividadeStatus.INICIADA,
            percentual_concluido=30.0,
            registrado_por="Maria Estagiária"
        ),
        Atividade(
            obra_id=obra.id,
            descricao="Montagem de fôrmas de madeira para vigas V1 a V5 do 3º pavimento",
            local="3º Pavimento", etapa="Estrutura",
            data_inicio=hoje,
            status=AtividadeStatus.INICIADA,
            registrado_por="Carlos Encarregado"
        ),
    ]
    db.add_all(atividades)

    # Clima
    climas = [
        Clima(obra_id=obra.id, data=hoje, periodo="manhã", condicao="sol", temperatura=32.0,
              anotacao_rdo="sol", status_pluviometrico=StatusPluviometrico.SECO_PRODUTIVO),
        Clima(obra_id=obra.id, data=hoje, periodo="tarde", condicao="nublado", temperatura=28.0,
              anotacao_rdo="chuva", status_pluviometrico=StatusPluviometrico.CHUVA_PRODUTIVA,
              impacto_trabalho="Chuva rápida às 14h, pausa de 30min"),
    ]
    db.add_all(climas)

    # Efetivo — própria empresa (cargos padronizados)
    efetivos = [
        Efetivo(obra_id=obra.id, data=hoje, tipo=TipoEfetivo.PROPRIO, funcao="Pedreiro", quantidade=8, registrado_por="Carlos Encarregado"),
        Efetivo(obra_id=obra.id, data=hoje, tipo=TipoEfetivo.PROPRIO, funcao="Servente", quantidade=4, registrado_por="Carlos Encarregado"),
        Efetivo(obra_id=obra.id, data=hoje, tipo=TipoEfetivo.PROPRIO, funcao="Armador", quantidade=3, registrado_por="Carlos Encarregado"),
        Efetivo(obra_id=obra.id, data=hoje, tipo=TipoEfetivo.PROPRIO, funcao="Carpinteiro", quantidade=2, registrado_por="Carlos Encarregado"),
        # Empreiteiras (total por empresa)
        Efetivo(obra_id=obra.id, data=hoje, tipo=TipoEfetivo.EMPREITEIRO, empresa="Elétrica Norte", quantidade=2, registrado_por="Carlos Encarregado"),
    ]
    db.add_all(efetivos)

    # Expediente do dia (mesmo que o padrão — apenas para ter dado no seed)
    expediente = Expediente(
        obra_id=obra.id, data=hoje,
        hora_inicio="07:00", hora_termino="17:00",
        registrado_por="Carlos Encarregado"
    )
    db.add(expediente)

    # Materiais
    materiais = [
        Material(obra_id=obra.id, data=hoje, tipo="entrada", material="Cimento CP-II", quantidade=500, unidade="sacos",
                 fornecedor="Votorantim", nota_fiscal="NF-2026-12345", registrado_por="Maria Estagiária",
                 texto_original="Chegaram 500 sacos de cimento da Votorantim, nota fiscal 12345"),
        Material(obra_id=obra.id, data=hoje, tipo="entrada", material="Concreto usinado fck 30 MPa", quantidade=12, unidade="m³",
                 fornecedor="Supermix", registrado_por="Carlos Encarregado"),
        Material(obra_id=obra.id, data=hoje, tipo="pendente", material="Porcelanato 60x60", quantidade=200, unidade="m²",
                 responsavel="cliente", data_prevista=hoje + timedelta(days=3),
                 registrado_por="Maria Estagiária"),
    ]
    db.add_all(materiais)

    # Equipamentos
    equipamentos = [
        Equipamento(obra_id=obra.id, data=hoje, tipo="entrada", equipamento="Retroescavadeira CAT 416F",
                    quantidade=1, horas_trabalhadas=6.0, operador="João Operador", registrado_por="Carlos Encarregado"),
        Equipamento(obra_id=obra.id, data=hoje, tipo="saída", equipamento="Betoneira 400L",
                    quantidade=1, observacoes="Devolvida para a locadora", registrado_por="Carlos Encarregado"),
    ]
    db.add_all(equipamentos)

    # Anotações
    anotacoes = [
        Anotacao(obra_id=obra.id, data=hoje, tipo="ocorrência",
                 descricao="Reclamação de vizinho sobre ruído. Providenciar instalação de manta acústica no tapume lateral.",
                 prioridade="alta", registrado_por="Daniel Silva",
                 texto_original="O vizinho reclamou do barulho, precisa colocar manta acústica no tapume"),
        Anotacao(obra_id=obra.id, data=hoje, tipo="pendência",
                 descricao="Solicitar renovação de alvará de construção junto à SEMMAS.",
                 prioridade="normal", registrado_por="Maria Estagiária"),
    ]
    db.add_all(anotacoes)

    db.commit()

    total_ef = sum(e.quantidade for e in efetivos)
    print("✅ Seed executado!")
    print(f"   Empresa: {empresa.nome}")
    print(f"   Obra: {obra.nome}")
    print(f"   Usuários: {len(usuarios)}")
    print(f"   Atividades: {len(atividades)}")
    print(f"   Efetivo: {total_ef} profissionais")
    print(f"   Materiais: {len(materiais)}")
    print(f"   Equipamentos: {len(equipamentos)}")
    print(f"   Anotações: {len(anotacoes)}")
    print(f"   Clima: {len(climas)} registros")

    db.close()


if __name__ == "__main__":
    seed()
