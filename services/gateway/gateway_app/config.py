from pydantic import field_validator
from sduhub_common import BaseConfig


class GatewayConfig(BaseConfig):
    service_name: str = "gateway"

    auth_service_url: str = "http://auth:8001"
    moodle_service_url: str = "http://moodle:8002"
    tracker_service_url: str = "http://tracker:8003"

    # Откуда фронту разрешено обращаться. Список через запятую.
    cors_origins: str = "http://localhost:5173"

    # Попытки входа: сколько и за какое окно. Считается и по адресу, и по логину.
    login_attempts: int = 5
    login_window_seconds: int = 900

    # Cookie с сессией. secure=False только для локальной разработки по http.
    cookie_name: str = "sduhub_session"
    cookie_secure: bool = True
    cookie_samesite: str = "lax"

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @field_validator("cookie_samesite")
    @classmethod
    def _check_samesite(cls, value: str) -> str:
        allowed = {"lax", "strict", "none"}
        if value.lower() not in allowed:
            raise ValueError(f"cookie_samesite должен быть одним из {allowed}")
        return value.lower()
