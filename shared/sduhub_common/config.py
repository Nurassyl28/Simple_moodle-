"""Конфигурация из переменных окружения. Секретов в коде нет — только имена."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    """Общие настройки. Каждый сервис наследуется и добавляет своё."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    moodle_site: str = "https://moodle.sdu.edu.kz"

    # Ключ шифрования токенов Moodle (Fernet, base64). Обязателен.
    token_encryption_key: str

    # Общий секрет для вызовов между сервисами внутри docker-сети.
    internal_api_key: str

    session_ttl_hours: int = Field(default=720, ge=1)

    log_level: str = "INFO"

    @property
    def dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
