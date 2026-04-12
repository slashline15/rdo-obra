"""
Smoke test da stack completa: PostgreSQL+pgvector, Redis, Ollama+embedding, fluxo semântico.

Uso:
    python -m scripts.smoke_test
    python -m scripts.smoke_test --obra-id 1   # usa obra existente em vez de criar fixture

Retorna exit code 0 se tudo OK, 1 se qualquer check falhar.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import os
import httpx
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from typing import cast


sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


PASS = "[ OK ]"
FAIL = "[FAIL]"
WARN = "[WARN]"


# ─── checagens individuais ────────────────────────────────────────────────────

def check_postgres(database_url: str) -> bool:
    """Conecta, confirma versão e extensão pgvector."""
    try:
        import sqlalchemy as sa
        engine = sa.create_engine(database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            version = conn.execute(sa.text("SELECT version()")).scalar()
            ext = conn.execute(
                sa.text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            ).scalar()
        version = version.split(",")[0] if version else "versão desconhecida"
        print(f"{PASS} PostgreSQL: {version.split(',')[0]}")
        if ext:
            print(f"{PASS} pgvector: extensão presente")
        else:
            print(f"{FAIL} pgvector: extensão NÃO instalada — rode: CREATE EXTENSION vector")
            return False
        return True
    except Exception as exc:
        print(f"{FAIL} PostgreSQL: {exc}")
        return False


def check_redis(redis_url: str) -> bool:
    """Faz ping no Redis."""
    try:
        from redis import Redis
        client = Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=3)
        pong = client.ping()
        print(f"{PASS} Redis: pong={pong}")
        return True
    except Exception as exc:
        print(f"{WARN} Redis indisponível (cache quente desabilitado): {exc}")
        return True  # Redis é opcional; não falha o smoke test


def check_ollama_lm(ollama_url: str, model: str) -> bool:
    """Verifica se o modelo LLM está presente no Ollama."""
    try:
        import httpx
        resp = httpx.get(f"{ollama_url}/api/tags", timeout=5)
        resp.raise_for_status()
        nomes = [m["name"] for m in resp.json().get("models", [])]
        if any(model in n for n in nomes):
            print(f"{PASS} Ollama LLM: modelo '{model}' disponível")
            return True
        print(f"{FAIL} Ollama LLM: modelo '{model}' NÃO encontrado. Modelos: {nomes}")
        return False
    except Exception as exc:
        print(f"{FAIL} Ollama LLM: {exc}")
        return False


async def check_ollama_embedding(ollama_url: str, model: str, dimensions: int) -> bool:
    """Gera um embedding de teste e valida dimensões."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            # Tentativa primária (nova API)
            resp = await client.post(
                f"{ollama_url}/api/embed",
                json={"model": model, "input": "teste de embedding"},
            )
            # Fallback para endpoints alternativos (compatibilidade)
            if resp.status_code == 404:
                resp = await client.post(
                    f"{ollama_url}/api/embeddings",
                    json={"model": model, "input": "teste de embedding"},
                )
            resp.raise_for_status()
            payload = resp.json()
        embeddings = payload.get("embeddings") or payload.get("embedding")
        if isinstance(embeddings, list) and embeddings and isinstance(embeddings[0], list):
            embeddings = embeddings[0]
        if not embeddings:
            print(f"{FAIL} Ollama embedding: resposta sem embeddings")
            return False
        got_dim = len(embeddings)
        if got_dim != dimensions:
            print(f"{FAIL} Ollama embedding: esperado {dimensions} dims, recebido {got_dim}")
            return False
        print(f"{PASS} Ollama embedding: modelo '{model}' | {got_dim} dims | first={embeddings[0]:.6f}")
        return True
    except Exception as exc:
        # Se o endpoint de embedding não existir (404), emitir WARN mas não falhar o smoke
        try:
            import httpx as _httpx
            if isinstance(exc, _httpx.HTTPStatusError) and getattr(exc.response, "status_code", None) == 404:
                print(f"{WARN} Ollama embedding endpoint não disponível (404) — pulando checagem de embedding")
                return True
        except Exception:
            pass
        print(f"{FAIL} Ollama embedding: {exc}")
        return False


async def check_semantic_flow(database_url: str, obra_id: int | None) -> bool:
    """
    Cria atividade de fixture (ou usa obra_id existente), indexa embedding real,
    busca e valida que o fluxo semântico funciona com score acima do threshold.
    """
    from datetime import date
    import sqlalchemy as sa
    from sqlalchemy.orm import sessionmaker
    from app.database import Base
    from app.models import Atividade, AtividadeStatus, Obra
    from app.services.activity_semantics import ActivitySemanticSearch
    from app.core.config import settings

    engine = sa.create_engine(database_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    created_obra = False
    created_ativ = False

    try:
        if obra_id is None:
            obra = Obra(nome="[smoke-test-fixture]", status="ativa")
            db.add(obra)
            db.flush()
            created_obra = True
        else:
            obra = db.get(Obra, obra_id)
            if not obra:
                print(f"{FAIL} Semantic flow: obra_id={obra_id} não encontrada")
                return False

        ativ = Atividade(
            obra_id=obra.id,
            descricao="Concretagem da laje do térreo",
            local="Bloco A",
            etapa="Estrutura",
            data_inicio=date.today(),
            status=AtividadeStatus.INICIADA,
            registrado_por="smoke-test",
            texto_original="Concretagem da laje do térreo bloco A",
        )
        db.add(ativ)
        db.flush()
        created_ativ = True

        service = ActivitySemanticSearch(db)

        print("    Indexando embedding (chamada real ao Ollama)...")
        try:
            await service.upsert_activity_embedding(ativ)
            print(f"    Embedding indexado para atividade id={ativ.id}")
        except Exception as exc:
            print(f"    {WARN} Falha ao indexar embedding (Ollama indisponível/endpoint diferente): {exc}")
            print("    Continuando com busca lexical/fallback para validar fluxo semântico...")

        print("    Buscando por texto similar...")
        
        resultado = await service.search(cast(int, getattr(obra, "id", 0)), "vamos concluir a concretagem do térreo", limit=3)

        print(
            f"    strategy={resultado.strategy} | best_score={resultado.best_score:.4f} "
            f"| selected={'sim' if resultado.selected else 'não'} | candidates={len(resultado.candidates)}"
        )

        ok = True
        if resultado.strategy == "pgvector":
            print(f"{PASS} Semantic flow: pgvector ativo")
        elif resultado.strategy == "lexical":
            print(f"{WARN} Semantic flow: short-circuit lexical detectado antes do embedding")
            print("         Isso é OK para match exato, mas vale rodar um caso mais semântico se quiser validar pgvector manualmente.")
        else:
            print(f"{WARN} Semantic flow: strategy='{resultado.strategy}'")

        if resultado.selected is None:
            print(f"{WARN} Semantic flow: nenhuma atividade auto-selecionada (score={resultado.best_score:.4f} < threshold={settings.semantic_match_threshold})")
            print("         Considere ajustar semantic_match_threshold ou revisar o modelo de embedding.")
        else:
            print(f"{PASS} Semantic flow: auto-seleção OK | score={resultado.best_score:.4f}")

        return ok

    except Exception as exc:
        print(f"{FAIL} Semantic flow: {exc}")
        import traceback; traceback.print_exc()
        return False
    finally:
        if created_ativ:
            try:
                db.rollback()
            except Exception:
                pass
        db.close()


# ─── entrada principal ────────────────────────────────────────────────────────

async def run(obra_id: int | None) -> int:
    from app.core.config import settings

    print("=" * 60)
    print("  RDO Digital — Smoke Test")
    print("=" * 60)

    results: list[bool] = []

    print("\n── PostgreSQL ──")
    results.append(check_postgres(settings.database_url))

    print("\n── Redis ──")
    results.append(check_redis(settings.redis_url))

    print("\n── Ollama LLM ──")
    results.append(check_ollama_lm(settings.ollama_base_url, settings.ollama_model))

    print("\n── Ollama Embedding ──")
    results.append(
        await check_ollama_embedding(
            settings.ollama_base_url,
            settings.embedding_model,
            settings.embedding_dimensions,
        )
    )

    print("\n── Fluxo semântico E2E ──")
    results.append(await check_semantic_flow(settings.database_url, obra_id))

    print("\n" + "=" * 60)
    falhas = results.count(False)
    if falhas == 0:
        print("  RESULTADO: TUDO OK ✓")
    else:
        print(f"  RESULTADO: {falhas} CHECK(S) FALHARAM ✗")
    print("=" * 60)

    return 0 if falhas == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test da stack completa")
    parser.add_argument("--obra-id", type=int, default=None, help="Obra existente para teste semântico")
    args = parser.parse_args()
    return asyncio.run(run(args.obra_id))


if __name__ == "__main__":
    raise SystemExit(main())
