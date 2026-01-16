from typing import Any

import aioboto3

from configs.settings import get_settings

s3_boto_session: aioboto3.Session | None = None
s3_client: Any | None = None


async def init_s3_session() -> None:
    global s3_boto_session, s3_client
    settings = get_settings()
    s3_boto_session = aioboto3.Session(
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
    )
    s3_client = s3_boto_session.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
    )


async def shutdown_s3_session() -> None:
    global s3_boto_session, s3_client
    s3_boto_session = None
    s3_client = None


async def get_s3_client() -> Any:
    global s3_client
    if s3_client is None:
        raise RuntimeError("S3 Client is not initialized")
    return s3_client
