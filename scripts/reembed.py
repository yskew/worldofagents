"""Re-embed stored agent signature vectors with the active encoding (RFC 0002).

The signature_vector column is a derived cache of the signature JSONB. When the
vector encoding changes (VECTOR_ENCODING_V2), persisted vectors become stale.
This script recomputes every agent's vector from its signature and stamps
signature_version with the active encoding.

Idempotent: re-running produces the same result. Live verification does not
depend on this (it recomputes from JSONB at compare time) -- this backfill keeps
the persisted column consistent for inspection and future ANN search.

Usage:
    docker compose exec api python scripts/reembed.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.agent import Agent
from app.services.agent_service import _current_vector_version
from app.services.signature_engine import features_to_vector


async def reembed() -> None:
    target_version = _current_vector_version()
    print(f"Active vector encoding: v{target_version} "
          f"(VECTOR_ENCODING_V2={settings.VECTOR_ENCODING_V2})")

    engine = create_async_engine(settings.async_database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    updated = 0
    skipped_no_sig = 0
    async with session_factory() as db:
        agents = (await db.execute(select(Agent))).scalars().all()
        for agent in agents:
            if not agent.signature:
                skipped_no_sig += 1
                continue
            agent.signature_vector = features_to_vector(agent.signature)
            agent.signature_version = target_version
            updated += 1
        await db.commit()

    await engine.dispose()
    print(f"Re-embedded {updated} agent(s) to v{target_version}; "
          f"skipped {skipped_no_sig} without a signature.")


if __name__ == "__main__":
    asyncio.run(reembed())
