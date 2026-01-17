import pytest

from services import encryption


def test_get_encryption_key_raises_when_missing(monkeypatch):
    monkeypatch.setenv("APP_SECRET", "")
    encryption.get_settings.cache_clear()
    with pytest.raises(ValueError, match="APP_SECRET must be set"):
        encryption.get_encryption_key()


def test_encrypt_decrypt_roundtrip(monkeypatch):
    monkeypatch.setenv("APP_SECRET", "short-key")
    encryption.get_settings.cache_clear()
    original = "my-secret"

    encrypted = encryption.encrypt_api_key(original)
    decrypted = encryption.decrypt_api_key(encrypted)

    assert decrypted == original


def test_get_encryption_key_truncates_long_secret(monkeypatch):
    long_secret = "x" * 64
    monkeypatch.setenv("APP_SECRET", long_secret)
    encryption.get_settings.cache_clear()

    key = encryption.get_encryption_key()

    assert len(key) == 44  # base64-encoded 32 bytes
