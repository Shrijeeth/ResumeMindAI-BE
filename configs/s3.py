from typing import Any

import aioboto3

from configs.settings import get_settings

s3_boto_session: aioboto3.Session | None = None


async def init_s3_session() -> None:
    global s3_boto_session, s3_client
    settings = get_settings()
    s3_boto_session = aioboto3.Session(
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
    )


async def shutdown_s3_session() -> None:
    global s3_boto_session, s3_client
    s3_boto_session = None


async def get_s3_client() -> Any:
    """Get a new S3 client instance.

    Returns a context manager that creates a new client each time.
    """
    global s3_boto_session
    if s3_boto_session is None:
        raise RuntimeError("S3 Session is not initialized")
    return s3_boto_session.client(
        "s3",
        endpoint_url=get_settings().S3_ENDPOINT_URL,
    )
