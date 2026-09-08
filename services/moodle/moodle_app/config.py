from sduhub_common import BaseConfig


class MoodleConfig(BaseConfig):
    service_name: str = "moodle-service"
    auth_service_url: str = "http://auth:8001"
    # Сколько живёт подписанная ссылка на файл.
    file_ref_ttl_seconds: int = 3600
    # Кэш ответов Moodle. Короткий: экран открывают часто, оценки меняются редко.
    cache_ttl_seconds: int = 60
