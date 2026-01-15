import logging

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

from configs.supabase import get_supabase_client

logger = logging.getLogger(__name__)
security = HTTPBearer()


async def get_current_user(credentials=Depends(security)):
    token = credentials.credentials
    supabase = await get_supabase_client()

    try:
        # Verify token with Supabase
        user = supabase.auth.get_user(token)
        return user.user
    except Exception as e:
        logger.error(f"Supabase connection error: {e}")
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials"
        )
