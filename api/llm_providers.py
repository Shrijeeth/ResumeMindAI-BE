import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    ProviderCreate,
    ProviderOut,
    ProviderUpdate,
    SupportedProvider,
    TestConnectionRequest,
    TestConnectionResponse,
)
from api.schemas.llm_provider import (
    PROVIDER_COLOR_CLASSES,
    PROVIDER_DISPLAY_NAMES,
    PROVIDER_INITIALS,
)
from configs.postgres import get_db
from middlewares.auth import get_current_user
from models import EventStatus, EventType, LLMProvider, ProviderStatus, ProviderType
from services import encrypt_api_key, log_provider_event, test_provider_connection

logger = logging.getLogger(__name__)
router = APIRouter(tags=["llm-providers"])


@router.get("/supported", response_model=list[SupportedProvider])
@router.get(
    "/supported", response_model=list[SupportedProvider], include_in_schema=False
)
async def list_supported_providers(
    current_user=Depends(get_current_user),
) -> list[SupportedProvider]:
    providers = []
    for ptype in ProviderType:
        providers.append(
            SupportedProvider(
                provider_type=ptype,
                provider_name=PROVIDER_DISPLAY_NAMES.get(ptype, ptype.value),
                logo_initials=PROVIDER_INITIALS.get(ptype, "??"),
                logo_color_class=PROVIDER_COLOR_CLASSES.get(ptype, ""),
            )
        )
    return providers


@router.get("/", response_model=list[ProviderOut])
async def list_providers(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[ProviderOut]:
    user_id = current_user.id
    result = await session.execute(
        select(LLMProvider).where(LLMProvider.user_id == user_id)
    )
    providers = result.scalars().all()
    return [ProviderOut.from_orm_model(p) for p in providers]


@router.post("/", response_model=ProviderOut, status_code=status.HTTP_201_CREATED)
async def create_provider(
    provider_data: ProviderCreate,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProviderOut:
    user_id = current_user.id

    encrypted_key = encrypt_api_key(provider_data.api_key)

    new_provider = LLMProvider(
        user_id=user_id,
        provider_type=provider_data.provider_type.value,
        model_name=provider_data.model_name,
        base_url=provider_data.base_url,
        api_key_encrypted=encrypted_key,
        status=ProviderStatus.INACTIVE.value,
    )

    session.add(new_provider)

    try:
        await session.flush()
        await log_provider_event(
            session,
            user_id,
            new_provider.id,
            EventType.CREATED.value,
            EventStatus.SUCCESS.value,
        )
        await session.commit()
        await session.refresh(new_provider)
    except IntegrityError as e:
        await session.rollback()
        logger.error(f"Integrity error creating provider: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Provider with this type and model already exists for this user",
        )
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating provider: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create provider",
        )

    return ProviderOut.from_orm_model(new_provider)


@router.patch("/{provider_id}", response_model=ProviderOut)
async def update_provider(
    provider_id: UUID,
    provider_data: ProviderUpdate,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProviderOut:
    user_id = current_user.id

    result = await session.execute(
        select(LLMProvider).where(
            LLMProvider.id == provider_id, LLMProvider.user_id == user_id
        )
    )
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found"
        )

    if provider_data.model_name is not None:
        provider.model_name = provider_data.model_name
    if provider_data.base_url is not None:
        provider.base_url = provider_data.base_url
    if provider_data.api_key is not None:
        provider.api_key_encrypted = encrypt_api_key(provider_data.api_key)
    if provider_data.status is not None:
        provider.status = provider_data.status.value
    if provider_data.latency_ms is not None:
        provider.latency_ms = provider_data.latency_ms
    if provider_data.error_message is not None:
        provider.error_message = provider_data.error_message

    try:
        await log_provider_event(
            session,
            user_id,
            provider.id,
            EventType.UPDATED.value,
            EventStatus.SUCCESS.value,
        )
        await session.commit()
        await session.refresh(provider)
    except IntegrityError as e:
        await session.rollback()
        logger.error(f"Integrity error updating provider: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Provider with this type and model already exists for this user",
        )
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating provider: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update provider",
        )

    return ProviderOut.from_orm_model(provider)


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: UUID,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    user_id = current_user.id

    result = await session.execute(
        select(LLMProvider).where(
            LLMProvider.id == provider_id, LLMProvider.user_id == user_id
        )
    )
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found"
        )

    try:
        await log_provider_event(
            session,
            user_id,
            provider.id,
            EventType.DELETED.value,
            EventStatus.SUCCESS.value,
        )
        await session.delete(provider)
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting provider: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete provider",
        )


@router.post("/{provider_id}/test-connection", response_model=TestConnectionResponse)
async def test_connection(
    provider_id: UUID,
    test_data: TestConnectionRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TestConnectionResponse:
    user_id = current_user.id

    result = await session.execute(
        select(LLMProvider).where(
            LLMProvider.id == provider_id, LLMProvider.user_id == user_id
        )
    )
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found"
        )

    test_status, latency_ms, error_message = await test_provider_connection(
        provider,
        override_api_key=test_data.api_key,
        override_base_url=test_data.base_url,
        override_model_name=test_data.model_name,
    )

    provider.status = test_status.value
    provider.latency_ms = latency_ms
    provider.error_message = error_message

    try:
        event_status = (
            EventStatus.SUCCESS.value
            if test_status == ProviderStatus.CONNECTED
            else EventStatus.FAILURE.value
        )
        await log_provider_event(
            session,
            user_id,
            provider.id,
            EventType.TESTED.value,
            event_status,
            error_message,
        )
        await session.commit()
        await session.refresh(provider)
    except Exception as e:
        await session.rollback()
        logger.error(f"Error testing connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test connection",
        )

    return TestConnectionResponse(
        status=test_status,
        latency_ms=latency_ms,
        error_message=error_message,
        provider=ProviderOut.from_orm_model(provider),
    )
