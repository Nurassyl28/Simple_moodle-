import time

import pytest
from sduhub_common.fileref import FileRefError, make_ref, read_ref

KEY = "internal-key"
STUDENT = "6f1c2a70-0000-4000-8000-000000000001"
URL = (
    "https://moodle.sdu.edu.kz/webservice/pluginfile.php/123/mod_resource"
    "/content/1/лекция 1.pdf?forcedownload=1"
)


def test_roundtrip_keeps_url():
    assert read_ref(KEY, STUDENT, make_ref(KEY, STUDENT, URL)) == URL


def test_ref_does_not_leak_token():
    """Главное свойство: в ссылке для браузера нет ни токена, ни ключа."""
    ref = make_ref(KEY, STUDENT, URL + "&token=a1b2c3d4e5f60718293a4b5c6d7e8f90")
    assert KEY not in ref


def test_other_student_rejected():
    ref = make_ref(KEY, STUDENT, URL)
    with pytest.raises(FileRefError):
        read_ref(KEY, "6f1c2a70-0000-4000-8000-000000000002", ref)


def test_wrong_key_rejected():
    with pytest.raises(FileRefError):
        read_ref("другой-ключ", STUDENT, make_ref(KEY, STUDENT, URL))


def test_tampered_url_rejected():
    """Подменить адрес файла, оставив подпись, нельзя."""
    ref = make_ref(KEY, STUDENT, URL)
    url_part, rest = ref.split(".", 1)
    with pytest.raises(FileRefError):
        read_ref(KEY, STUDENT, f"{url_part}X.{rest}")


def test_expired_rejected():
    with pytest.raises(FileRefError):
        read_ref(KEY, STUDENT, make_ref(KEY, STUDENT, URL, ttl=-1))


def test_still_valid_before_expiry():
    ref = make_ref(KEY, STUDENT, URL, ttl=60)
    assert read_ref(KEY, STUDENT, ref) == URL
    assert int(ref.split(".")[2]) > time.time()


def test_garbage_rejected():
    with pytest.raises(FileRefError):
        read_ref(KEY, STUDENT, "мусор")
