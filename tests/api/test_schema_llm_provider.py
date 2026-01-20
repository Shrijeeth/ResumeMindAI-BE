import uuid
from datetime import datetime

import pytest

from api.schemas.llm_provider import ProviderOut
from models.llm_provider import ProviderStatus, ProviderType


def test_provider_type_validator_rejects_invalid_str():
    with pytest.raises(ValueError, match="Invalid provider_type"):
        ProviderOut(
            id=uuid.uuid4(),
            provider_type="invalid-provider",
            model_name="m1",
            base_url=None,
            status=ProviderStatus.INACTIVE,
            is_active=False,
            latency_ms=None,
            error_message=None,
            logo_initials="?",
            logo_color_class="",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )


def test_status_validator_rejects_invalid_str():
    with pytest.raises(ValueError, match="Invalid status"):
        ProviderOut(
            id=uuid.uuid4(),
            provider_type=ProviderType.OPENAI,
            model_name="m1",
            base_url=None,
            status="not-a-status",
            is_active=False,
            latency_ms=None,
            error_message=None,
            logo_initials="OA",
            logo_color_class="",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )


def test_provider_type_validator_accepts_enum():
    out = ProviderOut(
        id=uuid.uuid4(),
        provider_type=ProviderType.OPENAI,
        model_name="m1",
        base_url=None,
        status=ProviderStatus.INACTIVE,
        is_active=False,
        latency_ms=None,
        error_message=None,
        logo_initials="OA",
        logo_color_class="",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    assert out.provider_type == ProviderType.OPENAI


def test_status_validator_accepts_enum():
    out = ProviderOut(
        id=uuid.uuid4(),
        provider_type=ProviderType.ANTHROPIC,
        model_name="m1",
        base_url=None,
        status=ProviderStatus.CONNECTED,
        is_active=False,
        latency_ms=None,
        error_message=None,
        logo_initials="AN",
        logo_color_class="",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    assert out.status == ProviderStatus.CONNECTED


def test_validate_provider_type_passes_enum_through():
    result = ProviderOut.validate_provider_type(ProviderType.OPENAI)
    assert result == ProviderType.OPENAI


def test_validate_status_passes_enum_through():
    result = ProviderOut.validate_status(ProviderStatus.ERROR)
    assert result == ProviderStatus.ERROR


def test_validate_provider_type_raises_on_invalid_str():
    with pytest.raises(ValueError, match="Invalid provider_type"):
        ProviderOut.validate_provider_type("not-a-provider")


def test_validate_status_raises_on_invalid_str():
    with pytest.raises(ValueError, match="Invalid status"):
        ProviderOut.validate_status("not-a-status")


def test_validate_provider_type_raises_on_invalid_data_type():
    with pytest.raises(ValueError, match="Invalid provider_type"):
        ProviderOut.validate_provider_type(1)


def test_validate_status_raises_on_invalid_data_type():
    with pytest.raises(ValueError, match="Invalid status"):
        ProviderOut.validate_status(1)


def test_from_orm_model_converts_strings_and_defaults():
    class Provider:
        def __init__(self):
            self.id = uuid.uuid4()
            self.provider_type = ProviderType.ANTHROPIC.value
            self.model_name = "claude-3"
            self.base_url = None
            self.status = ProviderStatus.CONNECTED.value
            self.is_active = False
            self.latency_ms = 120
            self.error_message = None
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

    provider = Provider()

    out = ProviderOut.from_orm_model(provider)

    assert out.provider_type == ProviderType.ANTHROPIC
    assert out.status == ProviderStatus.CONNECTED
    assert out.logo_initials == "AN"
    assert "bg-orange" in out.logo_color_class
    assert out.model_name == "claude-3"
