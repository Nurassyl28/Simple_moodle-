from sduhub_common import BaseConfig


class TrackerConfig(BaseConfig):
    service_name: str = "tracker-service"
    auth_service_url: str = "http://auth:8001"
    moodle_service_url: str = "http://moodle:8002"
    # «Сегодня» и «завтра» считаются в часовом поясе студента, а не в UTC:
    # иначе после 19:00 в Алматы задача на завтра уже показывалась бы на сегодня.
    timezone: str = "Asia/Almaty"
