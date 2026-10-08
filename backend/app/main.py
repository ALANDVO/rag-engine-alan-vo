from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import audit, auth, documents, evaluation, generate, search
from app.core.config import settings
from app.core.database import init_db
from app.models.schemas import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite tables on startup
    init_db()
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="RAG Engine Alan Vo",
        description="Retrieval-Augmented Generation engine with hybrid retrieval, citation verification, and faithfulness scoring.",
        version=settings.app_version,
        lifespan=lifespan,
    )

    # Configure CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @application.get("/api/health", response_model=HealthResponse, tags=["health"])
    async def health_check():
        return HealthResponse(
            status="healthy",
            version=settings.app_version,
            demo_mode=settings.demo_mode,
            llm_provider=settings.llm_provider,
            llm_configured=bool(settings.llm_api_key or settings.llm_provider == "ollama"),
        )

    # Include API Routers
    application.include_router(auth.router, prefix="/api")
    application.include_router(documents.router, prefix="/api")
    application.include_router(search.router, prefix="/api")
    application.include_router(generate.router, prefix="/api")
    application.include_router(evaluation.router, prefix="/api")
    application.include_router(audit.router, prefix="/api")

    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
