"""Шифрование токенов Moodle.

По SECURITY.md токен = секрет уровня пароля. В БД он лежит только зашифрованным,
ключ приходит из переменной окружения TOKEN_ENCRYPTION_KEY и в коде отсутствует.
"""

from cryptography.fernet import Fernet, InvalidToken


class TokenDecryptionError(RuntimeError):
    """Токен не расшифровывается — обычно сменили ключ. Студенту нужен новый вход."""


class TokenCipher:
    def __init__(self, key: str) -> None:
        if not key:
            raise ValueError("TOKEN_ENCRYPTION_KEY не задан")
        try:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as exc:  # ключ не того формата/длины
            raise ValueError("TOKEN_ENCRYPTION_KEY невалиден: нужен Fernet-ключ") from exc

    def encrypt(self, token: str) -> bytes:
        """Возвращает bytes — ровно то, что кладём в колонку BYTEA."""
        return self._fernet.encrypt(token.encode())

    def decrypt(self, blob: bytes | memoryview) -> str:
        try:
            return self._fernet.decrypt(bytes(blob)).decode()
        except InvalidToken as exc:
            # Наружу не отдаём ни ключ, ни содержимое — только факт неудачи.
            raise TokenDecryptionError("не удалось расшифровать токен") from exc

    @staticmethod
    def generate_key() -> str:
        return Fernet.generate_key().decode()
