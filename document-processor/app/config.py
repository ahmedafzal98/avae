"""Configuration settings for the document processing system"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # AWS Configuration
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "us-east-1"
    s3_bucket_name: str
    sqs_queue_url: str
    # Optional: use separate queue for local dev (avoids deployed workers stealing messages)
    sqs_queue_url_local: Optional[str] = None
    
    # LlamaCloud Configuration
    llama_cloud_api_key: str
    
    # OpenAI Configuration (for RAG embeddings and chat)
    openai_api_key: Optional[str] = None

    # AVAE External API Keys (Phase 2 verification)
    companies_house_api_key: Optional[str] = None
    epc_api_email: Optional[str] = None
    epc_api_key: Optional[str] = None
    land_registry_username: Optional[str] = None
    land_registry_password: Optional[str] = None

    # PostgreSQL — individual params (used locally)
    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5433
    postgres_db: str = "document_processor"
    postgres_user: str = "docuser"
    postgres_password: str = "docpass_dev_2026"

    # Redis — individual params (used locally)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # Database settings
    debug_sql: bool = False
    
    # Storage Configuration
    storage_path: str = "./storage/uploads"
    max_file_size_mb: int = 50
    max_files_per_request: int = 100
    
    # Celery Configuration (deprecated)
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # Rate Limiting
    rate_limit_requests: int = 10
    rate_limit_window: int = 60
    
    # AVAE Extraction (Task 4.5: parallel page extraction)
    extraction_max_workers: int = 6

    # Task Configuration
    task_result_ttl: int = 3600

    # HITL Checkpoint TTL (Task 5.5): expire PENDING_HUMAN_REVIEW after N days
    hitl_checkpoint_ttl_days: int = 7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra env vars (e.g. SQS_DLQ_URL, PGADMIN_*) not defined in Settings

    @property
    def database_url(self) -> str:
        """Return sync PostgreSQL URL — prefers DATABASE_URL env var if set."""
        url = os.environ.get("DATABASE_URL")
        if url:
            return url.replace("postgres://", "postgresql://", 1)
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def async_database_url(self) -> str:
        """Return async PostgreSQL URL — prefers DATABASE_URL env var if set.
        asyncpg does not accept ?sslmode= in the URL; SSL is passed via connect_args.
        """
        url = os.environ.get("DATABASE_URL")
        if url:
            url = url.replace("postgres://", "postgresql://", 1)
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            # Strip query string — asyncpg handles SSL via connect_args, not URL params
            if "?" in url:
                url = url.split("?")[0]
            return url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def requires_ssl(self) -> bool:
        """True when connecting to a cloud database that requires SSL."""
        url = os.environ.get("DATABASE_URL", "")
        return "sslmode=require" in url or "neon.tech" in url or ".fly.io" in url

    @property
    def redis_url_override(self) -> Optional[str]:
        """Return REDIS_URL from environment if set."""
        return os.environ.get("REDIS_URL")

    @property
    def redis_url(self) -> str:
        """Return Redis URL — prefers REDIS_URL env var if set."""
        url = os.environ.get("REDIS_URL")
        if url:
            return url
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def ensure_storage_path(self):
        """Create storage directory if it doesn't exist"""
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)

    @property
    def effective_sqs_queue_url(self) -> str:
        """Queue URL to use — prefers SQS_QUEUE_URL_LOCAL for local dev."""
        return self.sqs_queue_url_local or self.sqs_queue_url


# Global settings instance
settings = Settings()
settings.ensure_storage_path()
