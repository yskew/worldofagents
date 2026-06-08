"""Seed the database with demo data for local development."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.human import Human
from app.models.agent import Agent
from app.models.verification_log import VerificationLog
from app.auth.agent_keys import create_agent_credentials
from app.services.agent_service import _current_vector_version
from app.services.signature_engine import extract_features, features_to_vector
from app.schemas.agent import TrajectoryStep


DEMO_HUMAN = {
    "clerk_id": "demo_user_001",
    "display_name": "Demo User",
    "email": "demo@worldofagents.dev",
}

AGENTS = [
    {
        "name": "code-assistant",
        "description": "A coding agent that searches, reads, edits files and runs tests",
        "trajectory": [
            TrajectoryStep(type="tool_call", name="search"),
            TrajectoryStep(type="tool_call", name="read_file"),
            TrajectoryStep(type="message", name="assistant", content="I found the relevant file. Let me read the implementation."),
            TrajectoryStep(type="tool_call", name="edit_file"),
            TrajectoryStep(type="message", name="assistant", content="I've applied the fix to the function. Running tests now."),
            TrajectoryStep(type="tool_call", name="run_tests"),
            TrajectoryStep(type="message", name="assistant", content="All 14 tests pass. The bug is fixed."),
        ],
    },
    {
        "name": "devops-deployer",
        "description": "Handles deployments, health checks, and rollbacks",
        "trajectory": [
            TrajectoryStep(type="action", name="deploy"),
            TrajectoryStep(type="action", name="health_check"),
            TrajectoryStep(type="action", name="monitor"),
            TrajectoryStep(type="message", name="system", content="Deployment to staging complete. All health checks pass."),
            TrajectoryStep(type="action", name="promote_to_prod"),
            TrajectoryStep(type="message", name="system", content="Production deployment successful."),
        ],
    },
    {
        "name": "research-analyst",
        "description": "Searches the web, synthesizes findings, and writes reports",
        "trajectory": [
            TrajectoryStep(type="tool_call", name="web_search"),
            TrajectoryStep(type="tool_call", name="web_search"),
            TrajectoryStep(type="tool_call", name="read_page"),
            TrajectoryStep(type="tool_call", name="web_search"),
            TrajectoryStep(type="message", name="assistant", content="Based on my research across 12 sources, here are the key findings on agent identity protocols."),
            TrajectoryStep(type="tool_call", name="write_file"),
            TrajectoryStep(type="message", name="assistant", content="Research report saved to report.md."),
        ],
    },
    {
        "name": "data-pipeline",
        "description": "ETL agent that extracts, transforms, and loads data",
        "trajectory": [
            TrajectoryStep(type="tool_call", name="query_database"),
            TrajectoryStep(type="tool_call", name="transform_data"),
            TrajectoryStep(type="tool_call", name="validate_schema"),
            TrajectoryStep(type="message", name="assistant", content="Schema validation passed. 4,231 rows processed."),
            TrajectoryStep(type="tool_call", name="load_warehouse"),
            TrajectoryStep(type="message", name="assistant", content="Data loaded to warehouse. Pipeline complete."),
        ],
    },
    {
        "name": "security-scanner",
        "description": "Scans repositories for vulnerabilities and misconfigurations",
        "trajectory": [
            TrajectoryStep(type="tool_call", name="clone_repo"),
            TrajectoryStep(type="tool_call", name="scan_dependencies"),
            TrajectoryStep(type="tool_call", name="scan_secrets"),
            TrajectoryStep(type="tool_call", name="scan_iac"),
            TrajectoryStep(type="message", name="assistant", content="Scan complete. Found 2 high-severity dependency vulnerabilities and 1 exposed API key."),
            TrajectoryStep(type="tool_call", name="create_report"),
        ],
    },
]

VERIFICATION_COUNTS = [8, 3, 12, 5, 6]


async def seed():
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        # check if already seeded
        from sqlalchemy import select, func
        count = (await db.execute(select(func.count(Agent.id)))).scalar()
        if count and count > 0:
            print(f"Database already has {count} agents. Skipping seed.")
            print("To re-seed, run: docker compose exec api python -c \"")
            print("  from sqlalchemy import text")
            print("  ... truncate tables first\"")
            await engine.dispose()
            return

        # create demo human
        human = Human(**DEMO_HUMAN)
        db.add(human)
        await db.commit()
        await db.refresh(human)
        print(f"Created demo user: {human.display_name} ({human.id})")

        # create agents
        created = []
        for i, agent_data in enumerate(AGENTS):
            plain_key, key_hash, key_salt = create_agent_credentials()
            signature = extract_features(agent_data["trajectory"])
            sig_vector = features_to_vector(signature)

            agent = Agent(
                human_id=human.id,
                name=agent_data["name"],
                description=agent_data["description"],
                key_hash=key_hash,
                key_salt=key_salt,
                signature=signature,
                signature_vector=sig_vector,
                signature_version=_current_vector_version(),
                status="active",
            )
            db.add(agent)
            await db.commit()
            await db.refresh(agent)
            created.append((agent, plain_key))
            print(f"  Agent: {agent.name} ({agent.id})")
            print(f"    Key:  {plain_key}")

        # add verification logs
        import random
        for (agent, _), vcount in zip(created, VERIFICATION_COUNTS):
            for _ in range(vcount):
                score = round(random.uniform(0.75, 0.99), 4)
                log = VerificationLog(
                    agent_id=agent.id,
                    similarity_score=score,
                    passed=True,
                    ip_address="127.0.0.1",
                )
                db.add(log)
            await db.commit()
            print(f"    Added {vcount} verification logs for {agent.name}")

        # revoke one agent to show mixed state
        last_agent = created[-1][0]
        last_agent.status = "revoked"
        await db.commit()
        print(f"  Revoked: {last_agent.name} (for demo purposes)")

    await engine.dispose()

    print("\n--- Seed complete ---")
    print(f"  {len(AGENTS)} agents created ({len(AGENTS)-1} active, 1 revoked)")
    print(f"  {sum(VERIFICATION_COUNTS)} verification log entries")
    print("\n  Demo credentials (for /verify):")
    for agent, key in created:
        if agent.status == "active":
            print(f"    {agent.name}: id={agent.id}  key={key}")


if __name__ == "__main__":
    asyncio.run(seed())
