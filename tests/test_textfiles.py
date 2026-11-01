import pytest

from api.errors import ApiError
from api.textfiles import extract_text


def test_txt_decodes_utf8_and_windows_1252():
    assert extract_text("a.txt", "café".encode("utf-8")) == "café"
    assert extract_text("a.txt", "café".encode("cp1252")) == "café"


def test_empty_and_unknown_files_are_explained():
    with pytest.raises(ApiError) as e:
        extract_text("a.txt", b"   ")
    assert e.value.code == "no_text"
    with pytest.raises(ApiError) as e:
        extract_text("a.png", b"x")
    assert e.value.code == "unsupported_file" and ".docx" in e.value.detail
