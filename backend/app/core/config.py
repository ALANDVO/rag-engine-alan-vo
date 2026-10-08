import os
from pathlib import Path
from pydantic_settings import BaseSettings


def _get_version() -> str:
    version_file = Path(__file__).resolve().parent.parent.parent.parent / "VERSION"
    if version_file.is_file():
        return version_file.read_text(encoding="utf-8").strip()
    return "1.0.0"


class Settings(BaseSettings):
    app_name: str = "rag-engine-alan-vo"
    app_version: str = _get_version()
    environment: str = "development"
    demo_mode: bool = True
    host: str = "127.0.0.1"
    port: int = 8000
    database_url: str = "sqlite:///./data/rag.db"

    # OIDC Keycloak settings
    oidc_issuer_url: str = "http://localhost:8080/realms/rag-realm"
    oidc_client_id: str = "rag-engine"
    oidc_audience: str = "rag-engine"
    jwt_secret: str = "dev-secret-key-change-in-production-32bytes"

    # LLM Settings (LLM_API_KEY is the only secret)
    llm_api_key: str = ""
    llm_provider: str = "openai-compatible"
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_timeout: float = 30.0

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

    def validate_environment(self) -> None:
        if self.demo_mode and self.environment.lower() == "production":
            raise ValueError("Demo mode cannot be enabled in production environment.")


settings = Settings()
settings.validate_environment()
