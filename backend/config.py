"""Configuration and environment settings for Cloud Cost Optimization Agent."""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment and .env file."""
    
    # LLM Settings
    LLM_API_KEY: Optional[str] = None
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TIMEOUT_SECONDS: float = 10.0
    
    # Server & Environment
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    ENVIRONMENT: str = "development"
    
    # Directory paths
    REPORTS_DIR: str = "reports"
    
    # Default Policy Constraints
    DEFAULT_MAX_OBSERVATION_AGE_SECONDS: int = 900
    DEFAULT_MAX_SCALE_STEP: int = 2
    DEFAULT_LATENCY_SAFETY_MARGIN_PERCENT: float = 20.0
    DEFAULT_MINIMUM_AVAILABILITY_PERCENT: float = 99.0
    DEFAULT_COOLDOWN_SECONDS: int = 300
    DEFAULT_MAX_ACTION_RETRIES: int = 1

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def reports_path(self) -> Path:
        """Resolve and ensure reports directory path exists."""
        path = Path(self.REPORTS_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
