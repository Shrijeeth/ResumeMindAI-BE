import base64

from cryptography.fernet import Fernet

from configs.settings import get_settings


def get_encryption_key() -> bytes:
    settings = get_settings()
    key = settings.APP_SECRET
    if not key:
        raise ValueError("APP_SECRET must be set in environment")
    key_bytes = key.encode()
    if len(key_bytes) < 32:
        key_bytes = key_bytes.ljust(32, b"0")
    else:
        key_bytes = key_bytes[:32]
    return base64.urlsafe_b64encode(key_bytes)


def encrypt_api_key(api_key: str) -> bytes:
    fernet = Fernet(get_encryption_key())
    return fernet.encrypt(api_key.encode())


def decrypt_api_key(encrypted_key: bytes) -> str:
    fernet = Fernet(get_encryption_key())
    return fernet.decrypt(encrypted_key).decode()
