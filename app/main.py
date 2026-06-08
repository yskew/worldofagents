from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agents, health, verify, wellknown
from app.config import settings


def create_app() -> FastAPI:
    application = FastAPI(
        title="AgentVerify",
        description="Identity verification layer for AI agents",
        version="0.1.0",
    )
    # RFC 0007: credentialed CORS with a wildcard origin is a spec violation and a
    # real vulnerability. Use the configured allow-list; only permit credentials
    # when origins are explicit (not "*").
    origins = settings.allowed_origins_list
    allow_wildcard = origins == ["*"]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=not allow_wildcard,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health.router)
    application.include_router(agents.router)
    application.include_router(verify.router)
    application.include_router(wellknown.router)
    return application


app = create_app()
