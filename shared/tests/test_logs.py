import logging

from sduhub_common.logs import mask_secret, setup_logging

TOKEN = "a1b2c3d4e5f60718293a4b5c6d7e8f90"


def test_masks_bare_token():
    assert TOKEN not in mask_secret(f"ответ для токена {TOKEN}")


def test_masks_token_in_url():
    url = f"https://moodle.sdu.edu.kz/webservice/rest/server.php?wstoken={TOKEN}&wsfunction=x"
    masked = mask_secret(url)
    assert TOKEN not in masked
    assert "wsfunction=x" in masked


def test_masks_password_query():
    masked = mask_secret("/login/token.php?username=u&password=s3cret&service=m")
    assert "s3cret" not in masked
    assert "username=u" in masked


def test_masks_privatetoken():
    assert "abc" not in mask_secret("privatetoken=abc")


def test_keeps_ordinary_text():
    assert mask_secret("курсов: 1, дедлайнов: 0") == "курсов: 1, дедлайнов: 0"


def test_logger_masks_message(caplog):
    """Главное: маскирует сам логгер, а не вызывающий код."""
    setup_logging("INFO", "test")
    log = logging.getLogger("test")
    with caplog.at_level(logging.INFO):
        log.info("токен %s получен", TOKEN)
    assert TOKEN not in caplog.text


def test_uvicorn_logs_not_duplicated():
    """Без propagate=False каждая строка uvicorn писалась бы дважды."""
    setup_logging("INFO", "test")
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logger = logging.getLogger(name)
        assert logger.propagate is False
        assert len(logger.handlers) == 1
