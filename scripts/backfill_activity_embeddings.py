"""
Backfill dos embeddings de atividades.

Uso:
    python -m scripts.backfill_activity_embeddings
    python -m scripts.backfill_activity_embeddings --obra-id 12
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal
from app.models import Atividade, AtividadeStatus
from app.services.activity_semantics import ActivitySemanticSearch


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill dos embeddings de atividades")
    parser.add_argument("--obra-id", type=int, default=None, help="Filtra uma única obra")
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> int:
    db = SessionLocal()
    service = ActivitySemanticSearch(db)
    total = 0
    falhas = 0

    try:
        query = db.query(Atividade).filter(Atividade.status != AtividadeStatus.CONCLUIDA)
        if args.obra_id is not None:
            query = query.filter(Atividade.obra_id == args.obra_id)

        atividades = query.order_by(Atividade.obra_id, Atividade.id).all()
        for atividade in atividades:
            try:
                await service.upsert_activity_embedding(atividade)
                total += 1
                print(f"[ok] atividade={atividade.id} obra={atividade.obra_id}")
            except Exception as exc:
                falhas += 1
                print(f"[erro] atividade={atividade.id} obra={atividade.obra_id}: {exc}")

        print(f"Backfill concluído: {total} atividades atualizadas, {falhas} falhas.")
        return 0 if falhas == 0 else 1
    finally:
        db.close()


def main() -> int:
    return asyncio.run(_run(_parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
