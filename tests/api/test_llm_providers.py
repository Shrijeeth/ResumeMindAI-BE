import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from api import llm_providers
from app import app
from models import LLMProvider, ProviderStatus, ProviderType
from services import encryption


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = "test-user-123"
    return user


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    session.delete = MagicMock()
    return session


@pytest.fixture
def sample_provider():
    return LLMProvider(
        id=uuid.uuid4(),
        user_id="test-user-123",
        provider_type=ProviderType.OPENAI,
        model_name="gpt-4",
        base_url="https://api.openai.com",
        api_key_encrypted=b"encrypted_key",
        status=ProviderStatus.INACTIVE,
        latency_ms=None,
        error_message=None,
    )


def test_list_providers_empty(monkeypatch, mock_user, mock_db_session):
    async def mock_get_current_user():
        return mock_user

    async def mock_get_db():
        yield mock_db_session

    result_mock = MagicMock()
    result_mock.scalars().all.return_value = []
    mock_db_session.execute.return_value = result_mock

    monkeypatch.setattr(llm_providers, "get_current_user", mock_get_current_user)
    monkeypatch.setattr(llm_providers, "get_db", mock_get_db)

    client = TestClient(app)
    response = client.get(
        "/api/settings/llm-providers/",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_providers_with_data(
    monkeypatch, mock_user, mock_db_session, sample_provider
):
    async def mock_get_current_user():
        return mock_user

    async def mock_get_db():
        yield mock_db_session

    result_mock = MagicMock()
    result_mock.scalars().all.return_value = [sample_provider]
    mock_db_session.execute.return_value = result_mock

    monkeypatch.setattr(llm_providers, "get_current_user", mock_get_current_user)
    monkeypatch.setattr(llm_providers, "get_db", mock_get_db)

    client = TestClient(app)
    response = client.get(
        "/api/settings/llm-providers/",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["provider_type"] == "openai"
    assert data[0]["model_name"] == "gpt-4"
    assert data[0]["status"] == "inactive"
    assert data[0]["logo_initials"] == "OA"
    assert "bg-emerald-500" in data[0]["logo_color_class"]
    assert "api_key" not in data[0]


def test_create_provider_success(monkeypatch, mock_user, mock_db_session):
    async def mock_get_current_user():
        return mock_user

    async def mock_get_db():
        yield mock_db_session

    def mock_encrypt(api_key: str) -> bytes:
        return b"encrypted_" + api_key.encode()

    created_provider = None

    def capture_add(provider):
        nonlocal created_provider
        created_provider = provider
        provider.id = uuid.uuid4()

    mock_db_session.add.side_effect = capture_add

    async def mock_refresh(provider):
        pass

    mock_db_session.refresh.side_effect = mock_refresh

    monkeypatch.setattr(llm_providers, "get_current_user", mock_get_current_user)
    monkeypatch.setattr(llm_providers, "get_db", mock_get_db)
    monkeypatch.setattr(encryption, "encrypt_api_key", mock_encrypt)

    client = TestClient(app)
    response = client.post(
        "/api/settings/llm-providers/",
        headers={"Authorization": "Bearer fake-token"},
        json={
            "provider_type": "anthropic",
            "model_name": "claude-3-opus",
            "base_url": "https://api.anthropic.com",
            "api_key": "sk-ant-test123",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["provider_type"] == "anthropic"
    assert data["model_name"] == "claude-3-opus"
    assert data["status"] == "inactive"
    assert data["logo_initials"] == "AN"
    assert "api_key" not in data
    assert created_provider is not None
    assert created_provider.user_id == "test-user-123"


def test_update_provider_success(
    monkeypatch, mock_user, mock_db_session, sample_provider
):
    async def mock_get_current_user():
        return mock_user

    async def mock_get_db():
        yield mock_db_session

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = sample_provider
    mock_db_session.execute.return_value = result_mock

    monkeypatch.setattr(llm_providers, "get_current_user", mock_get_current_user)
    monkeypatch.setattr(llm_providers, "get_db", mock_get_db)

    client = TestClient(app)
    response = client.patch(
        f"/api/settings/llm-providers/{sample_provider.id}",
        headers={"Authorization": "Bearer fake-token"},
        json={
            "model_name": "gpt-4-turbo",
            "status": "connected",
            "latency_ms": 150,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["model_name"] == "gpt-4-turbo"
    assert data["status"] == "connected"
    assert data["latency_ms"] == 150


def test_update_provider_not_found(monkeypatch, mock_user, mock_db_session):
    async def mock_get_current_user():
        return mock_user

    async def mock_get_db():
        yield mock_db_session

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = result_mock

    monkeypatch.setattr(llm_providers, "get_current_user", mock_get_current_user)
    monkeypatch.setattr(llm_providers, "get_db", mock_get_db)

    client = TestClient(app)
    response = client.patch(
        f"/api/settings/llm-providers/{uuid.uuid4()}",
        headers={"Authorization": "Bearer fake-token"},
        json={"model_name": "gpt-4-turbo"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_provider_success(
    monkeypatch, mock_user, mock_db_session, sample_provider
):
    async def mock_get_current_user():
        return mock_user

    async def mock_get_db():
        yield mock_db_session

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = sample_provider
    mock_db_session.execute.return_value = result_mock

    monkeypatch.setattr(llm_providers, "get_current_user", mock_get_current_user)
    monkeypatch.setattr(llm_providers, "get_db", mock_get_db)

    client = TestClient(app)
    response = client.delete(
        f"/api/settings/llm-providers/{sample_provider.id}",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_db_session.delete.assert_called_once()


def test_delete_provider_not_found(monkeypatch, mock_user, mock_db_session):
    async def mock_get_current_user():
        return mock_user

    async def mock_get_db():
        yield mock_db_session

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = result_mock

    monkeypatch.setattr(llm_providers, "get_current_user", mock_get_current_user)
    monkeypatch.setattr(llm_providers, "get_db", mock_get_db)

    client = TestClient(app)
    response = client.delete(
        f"/api/settings/llm-providers/{uuid.uuid4()}",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_test_connection_success(
    monkeypatch, mock_user, mock_db_session, sample_provider
):
    async def mock_get_current_user():
        return mock_user

    async def mock_get_db():
        yield mock_db_session

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = sample_provider
    mock_db_session.execute.return_value = result_mock

    async def mock_test_connection(provider, **kwargs):
        return ProviderStatus.CONNECTED, 120, None

    monkeypatch.setattr(llm_providers, "get_current_user", mock_get_current_user)
    monkeypatch.setattr(llm_providers, "get_db", mock_get_db)
    monkeypatch.setattr(llm_providers, "test_provider_connection", mock_test_connection)

    client = TestClient(app)
    response = client.post(
        f"/api/settings/llm-providers/{sample_provider.id}/test-connection",
        headers={"Authorization": "Bearer fake-token"},
        json={},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "connected"
    assert data["latency_ms"] == 120
    assert data["error_message"] is None
    assert "provider" in data
    assert data["provider"]["status"] == "connected"


def test_test_connection_with_override(
    monkeypatch, mock_user, mock_db_session, sample_provider
):
    async def mock_get_current_user():
        return mock_user

    async def mock_get_db():
        yield mock_db_session

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = sample_provider
    mock_db_session.execute.return_value = result_mock

    test_args = {}

    async def mock_test_connection(provider, **kwargs):
        test_args.update(kwargs)
        return ProviderStatus.CONNECTED, 100, None

    monkeypatch.setattr(llm_providers, "get_current_user", mock_get_current_user)
    monkeypatch.setattr(llm_providers, "get_db", mock_get_db)
    monkeypatch.setattr(llm_providers, "test_provider_connection", mock_test_connection)

    client = TestClient(app)
    response = client.post(
        f"/api/settings/llm-providers/{sample_provider.id}/test-connection",
        headers={"Authorization": "Bearer fake-token"},
        json={
            "api_key": "sk-override-key",
            "base_url": "https://custom.api.com",
            "model_name": "gpt-4-turbo",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert test_args["override_api_key"] == "sk-override-key"
    assert test_args["override_base_url"] == "https://custom.api.com"
    assert test_args["override_model_name"] == "gpt-4-turbo"


def test_test_connection_failure(
    monkeypatch, mock_user, mock_db_session, sample_provider
):
    async def mock_get_current_user():
        return mock_user

    async def mock_get_db():
        yield mock_db_session

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = sample_provider
    mock_db_session.execute.return_value = result_mock

    async def mock_test_connection(provider, **kwargs):
        return ProviderStatus.ERROR, 50, "Invalid API key"

    monkeypatch.setattr(llm_providers, "get_current_user", mock_get_current_user)
    monkeypatch.setattr(llm_providers, "get_db", mock_get_db)
    monkeypatch.setattr(llm_providers, "test_provider_connection", mock_test_connection)

    client = TestClient(app)
    response = client.post(
        f"/api/settings/llm-providers/{sample_provider.id}/test-connection",
        headers={"Authorization": "Bearer fake-token"},
        json={},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "error"
    assert data["latency_ms"] == 50
    assert data["error_message"] == "Invalid API key"
    assert data["provider"]["status"] == "error"


def test_encryption_masks_api_key_in_response(monkeypatch, mock_user, mock_db_session):
    async def mock_get_current_user():
        return mock_user

    async def mock_get_db():
        yield mock_db_session

    def mock_encrypt(api_key: str) -> bytes:
        return b"encrypted_secret"

    created_provider = None

    def capture_add(provider):
        nonlocal created_provider
        created_provider = provider
        provider.id = uuid.uuid4()

    mock_db_session.add.side_effect = capture_add

    monkeypatch.setattr(llm_providers, "get_current_user", mock_get_current_user)
    monkeypatch.setattr(llm_providers, "get_db", mock_get_db)
    monkeypatch.setattr(encryption, "encrypt_api_key", mock_encrypt)

    client = TestClient(app)
    response = client.post(
        "/api/settings/llm-providers/",
        headers={"Authorization": "Bearer fake-token"},
        json={
            "provider_type": "openai",
            "model_name": "gpt-4",
            "api_key": "sk-super-secret-key-12345",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.json()
    assert "api_key" not in response_data
    assert "sk-super-secret-key-12345" not in str(response_data)
    assert created_provider.api_key_encrypted == b"encrypted_secret"
