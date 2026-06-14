from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agents, attestation, health, verify, wellknown


def create_app() -> FastAPI:
    application = FastAPI(
        title="AgentVerify",
        description="Identity verification layer for AI agents",
        version="0.1.0",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health.router)
    application.include_router(agents.router)
    application.include_router(verify.router)
    application.include_router(attestation.router)
    application.include_router(wellknown.router)
    return application


app = create_app()
