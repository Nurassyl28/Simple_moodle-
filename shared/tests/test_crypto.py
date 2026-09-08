import pytest

from sduhub_common.crypto import TokenCipher, TokenDecryptionError


def test_roundtrip():
    cipher = TokenCipher(TokenCipher.generate_key())
    token = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
    assert cipher.decrypt(cipher.encrypt(token)) == token


def test_ciphertext_hides_token():
    """В БД не должно быть видно исходный токен."""
    cipher = TokenCipher(TokenCipher.generate_key())
    token = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
    assert token.encode() not in cipher.encrypt(token)


def test_encrypt_returns_bytes_for_bytea():
    cipher = TokenCipher(TokenCipher.generate_key())
    assert isinstance(cipher.encrypt("x"), bytes)


def test_wrong_key_gives_clear_error():
    """Смена TOKEN_ENCRYPTION_KEY делает старые токены нечитаемыми — это ожидаемо."""
    blob = TokenCipher(TokenCipher.generate_key()).encrypt("token")
    other = TokenCipher(TokenCipher.generate_key())
    with pytest.raises(TokenDecryptionError):
        other.decrypt(blob)


def test_empty_key_rejected():
    with pytest.raises(ValueError):
        TokenCipher("")


def test_garbage_key_rejected():
    with pytest.raises(ValueError):
        TokenCipher("не-fernet-ключ")


def test_decrypts_memoryview():
    """asyncpg отдаёт BYTEA как memoryview, а не bytes."""
    cipher = TokenCipher(TokenCipher.generate_key())
    blob = cipher.encrypt("token")
    assert cipher.decrypt(memoryview(blob)) == "token"
