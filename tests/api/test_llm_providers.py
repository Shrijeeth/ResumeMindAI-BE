import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from api import llm_providers
from app import app
from configs import get_settings, supabase
from configs.postgres import get_db
from middlewares.auth import get_current_user
from models import LLMProvider, ProviderStatus, ProviderType
from services import encryption


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = "test-user-123"
    return user


@pytest.fixture(autouse=True)
def stub_supabase_client(monkeypatch):
    class DummyAuth:
        def get_user(self, token):
            user = MagicMock()
            user.user = MagicMock()
            user.user.id = "dummy"
            return user

    dummy_client = MagicMock()
    dummy_client.auth = DummyAuth()

    supabase.supabase_client = dummy_client

    async def get_client():
        return dummy_client

    monkeypatch.setattr(supabase, "get_supabase_client", get_client)
    yield
    supabase.supabase_client = None


@pytest.fixture(autouse=True)
def ensure_app_secret(monkeypatch):
    monkeypatch.setenv("APP_SECRET", "test-secret-key-32chars-123456")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def ensure_provider_out_defaults(monkeypatch):
    def _from_orm_model(provider):
        now = datetime.utcnow()
        created = getattr(provider, "created_at", None) or now
        updated = getattr(provider, "updated_at", None) or now
        status = getattr(provider, "status", None) or ProviderStatus.INACTIVE
        latency = getattr(provider, "latency_ms", None)
        error_message = getattr(provider, "error_message", None)

        provider.created_at = created
        provider.updated_at = updated
        provider.status = status

        return llm_providers.ProviderOut(
            id=provider.id,
            provider_type=provider.provider_type,
            model_name=provider.model_name,
            base_url=provider.base_url,
            status=status,
            latency_ms=latency,
            error_message=error_message,
            logo_initials=llm_providers.PROVIDER_INITIALS.get(
                ProviderType(provider.provider_type)
                if isinstance(provider.provider_type, str)
                else provider.provider_type,
                "??",
            ),
            logo_color_class=llm_providers.PROVIDER_COLOR_CLASSES.get(
                ProviderType(provider.provider_type)
                if isinstance(provider.provider_type, str)
                else provider.provider_type,
                "",
            ),
            created_at=created,
            updated_at=updated,
        )

    monkeypatch.setattr(
        llm_providers.ProviderOut, "from_orm_model", staticmethod(_from_orm_model)
    )


@pytest.fixture(autouse=True)
def override_dependencies(mock_db_session, mock_user):
    async def override_get_db():
        yield mock_db_session

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[llm_providers.get_db] = override_get_db
    app.dependency_overrides[llm_providers.get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
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
        status=ProviderStatus.INACTIVE.value,
        latency_ms=None,
        error_message=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def test_list_providers_empty(monkeypatch, mock_user, mock_db_session):
    result_mock = MagicMock()
    result_mock.scalars().all.return_value = []
    mock_db_session.execute.return_value = result_mock

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
    result_mock = MagicMock()
    result_mock.scalars().all.return_value = [sample_provider]
    mock_db_session.execute.return_value = result_mock

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


def test_list_providers_uses_cache(monkeypatch, mock_user):
    now = datetime.utcnow().isoformat()
    cached_payload = [
        {
            "id": str(uuid.uuid4()),
            "provider_type": ProviderType.OPENAI.value,
            "model_name": "gpt-4",
            "base_url": "https://api.openai.com",
            "status": ProviderStatus.INACTIVE.value,
            "latency_ms": None,
            "error_message": None,
            "logo_initials": "OA",
            "logo_color_class": "bg-emerald-500/10",
            "created_at": now,
            "updated_at": now,
        }
    ]

    async def mock_get_cache(user_id):
        assert user_id == "test-user-123"
        return cached_payload

    monkeypatch.setattr(llm_providers, "get_provider_list_cache", mock_get_cache)

    client = TestClient(app)
    response = client.get(
        "/api/settings/llm-providers/",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == cached_payload


def test_create_provider_success(monkeypatch, mock_user, mock_db_session):
    def mock_encrypt(api_key: str) -> bytes:
        return b"encrypted_" + api_key.encode()

    created_provider = None

    def capture_add(obj):
        nonlocal created_provider
        if isinstance(obj, LLMProvider):
            created_provider = obj
            obj.id = uuid.uuid4()
        return None

    mock_db_session.add.side_effect = capture_add

    async def mock_refresh(provider):
        pass

    mock_db_session.refresh.side_effect = mock_refresh

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
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = sample_provider
    mock_db_session.execute.return_value = result_mock

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
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = result_mock

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
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = sample_provider
    mock_db_session.execute.return_value = result_mock

    client = TestClient(app)
    response = client.delete(
        f"/api/settings/llm-providers/{sample_provider.id}",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_db_session.delete.assert_called_once()


def test_delete_provider_not_found(monkeypatch, mock_user, mock_db_session):
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = result_mock

    client = TestClient(app)
    response = client.delete(
        f"/api/settings/llm-providers/{uuid.uuid4()}",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_test_connection_success(
    monkeypatch, mock_user, mock_db_session, sample_provider
):
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = sample_provider
    mock_db_session.execute.return_value = result_mock

    async def mock_test_connection(provider, **kwargs):
        return ProviderStatus.CONNECTED, 120, None

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
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = sample_provider
    mock_db_session.execute.return_value = result_mock

    test_args = {}

    async def mock_test_connection(provider, **kwargs):
        test_args.update(kwargs)
        return ProviderStatus.CONNECTED, 100, None

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


def test_test_connection_returns_cached(
    monkeypatch, mock_user, mock_db_session, sample_provider
):
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = sample_provider
    mock_db_session.execute.return_value = result_mock

    cached_payload = {
        "status": ProviderStatus.CONNECTED.value,
        "latency_ms": 120,
        "error_message": None,
        "provider": {
            "id": str(sample_provider.id),
            "provider_type": sample_provider.provider_type,
            "model_name": sample_provider.model_name,
            "base_url": sample_provider.base_url,
            "status": sample_provider.status,
            "latency_ms": sample_provider.latency_ms,
            "error_message": sample_provider.error_message,
            "logo_initials": "OA",
            "logo_color_class": "bg-emerald-500/10",
            "created_at": sample_provider.created_at.isoformat(),
            "updated_at": sample_provider.updated_at.isoformat(),
        },
        "cached_at": datetime.utcnow().isoformat(),
    }

    async def mock_get_cache(_):
        return cached_payload

    monkeypatch.setattr(llm_providers, "get_provider_test_cache", mock_get_cache)

    client = TestClient(app)
    response = client.post(
        f"/api/settings/llm-providers/{sample_provider.id}/test-connection",
        headers={"Authorization": "Bearer fake-token"},
        json={},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == ProviderStatus.CONNECTED.value
    assert data["latency_ms"] == 120
    assert data["error_message"] is None
    assert data.get("cached_at") is not None


def test_test_connection_failure(
    monkeypatch, mock_user, mock_db_session, sample_provider
):
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = sample_provider
    mock_db_session.execute.return_value = result_mock

    async def mock_test_connection(provider, **kwargs):
        return ProviderStatus.ERROR, 50, "Invalid API key"

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
    def mock_encrypt(api_key: str) -> bytes:
        return b"encrypted_secret"

    created_provider = None

    def capture_add(obj):
        nonlocal created_provider
        if isinstance(obj, LLMProvider):
            created_provider = obj
            obj.id = uuid.uuid4()
        return None

    mock_db_session.add.side_effect = capture_add

    monkeypatch.setattr(llm_providers, "encrypt_api_key", mock_encrypt)
    monkeypatch.setattr(encryption, "encrypt_api_key", mock_encrypt)
    monkeypatch.setattr(llm_providers, "encrypt_api_key", mock_encrypt)

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


def test_list_supported_providers(monkeypatch):
    client = TestClient(app)
    response = client.get(
        "/api/settings/llm-providers/supported",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == len(list(ProviderType))
    assert any(item["provider_type"] == "openai" for item in data)


def test_create_provider_integrity_error(monkeypatch, mock_db_session):
    mock_db_session.flush.side_effect = IntegrityError(None, None, None)

    client = TestClient(app)
    response = client.post(
        "/api/settings/llm-providers/",
        headers={"Authorization": "Bearer fake-token"},
        json={
            "provider_type": "openai",
            "model_name": "gpt-4",
            "api_key": "sk-key",
        },
    )

    assert response.status_code == status.HTTP_409_CONFLICT


def test_create_provider_generic_error(monkeypatch, mock_db_session):
    mock_db_session.flush.side_effect = Exception("boom")

    client = TestClient(app)
    response = client.post(
        "/api/settings/llm-providers/",
        headers={"Authorization": "Bearer fake-token"},
        json={
            "provider_type": "openai",
            "model_name": "gpt-4",
            "api_key": "sk-key",
        },
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_update_provider_integrity_error(monkeypatch, mock_db_session, sample_provider):
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = sample_provider
    mock_db_session.execute.return_value = result_mock
    mock_db_session.commit.side_effect = IntegrityError(None, None, None)

    client = TestClient(app)
    response = client.patch(
        f"/api/settings/llm-providers/{sample_provider.id}",
        headers={"Authorization": "Bearer fake-token"},
        json={"model_name": "gpt-4-turbo"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT


def test_update_provider_generic_error(monkeypatch, mock_db_session, sample_provider):
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = sample_provider
    mock_db_session.execute.return_value = result_mock
    mock_db_session.commit.side_effect = Exception("fail")

    client = TestClient(app)
    response = client.patch(
        f"/api/settings/llm-providers/{sample_provider.id}",
        headers={"Authorization": "Bearer fake-token"},
        json={"model_name": "gpt-4-turbo"},
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_update_provider_sets_optional_fields(
    monkeypatch, mock_db_session, sample_provider
):
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = sample_provider
    mock_db_session.execute.return_value = result_mock

    def mock_encrypt(api_key: str) -> bytes:
        return b"enc-" + api_key.encode()

    async def mock_refresh(provider):
        return None

    mock_db_session.refresh.side_effect = mock_refresh
    monkeypatch.setattr(encryption, "encrypt_api_key", mock_encrypt)

    client = TestClient(app)
    response = client.patch(
        f"/api/settings/llm-providers/{sample_provider.id}",
        headers={"Authorization": "Bearer fake-token"},
        json={
            "base_url": "https://custom.api",
            "api_key": "sk-new",
            "error_message": "oops",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert sample_provider.api_key_encrypted != b"encrypted_key"
    assert sample_provider.base_url == "https://custom.api"
    assert sample_provider.error_message == "oops"


def test_delete_provider_generic_error(monkeypatch, mock_db_session, sample_provider):
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = sample_provider
    mock_db_session.execute.return_value = result_mock
    mock_db_session.delete.side_effect = Exception("fail")

    client = TestClient(app)
    response = client.delete(
        f"/api/settings/llm-providers/{sample_provider.id}",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_test_connection_not_found(monkeypatch, mock_db_session):
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = result_mock

    client = TestClient(app)
    response = client.post(
        f"/api/settings/llm-providers/{uuid.uuid4()}/test-connection",
        headers={"Authorization": "Bearer fake-token"},
        json={},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_test_connection_commit_failure(monkeypatch, mock_db_session, sample_provider):
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = sample_provider
    mock_db_session.execute.return_value = result_mock
    mock_db_session.commit.side_effect = Exception("commit fail")

    async def mock_test_connection(provider, **kwargs):
        return ProviderStatus.CONNECTED, 10, None

    monkeypatch.setattr(llm_providers, "test_provider_connection", mock_test_connection)

    client = TestClient(app)
    response = client.post(
        f"/api/settings/llm-providers/{sample_provider.id}/test-connection",
        headers={"Authorization": "Bearer fake-token"},
        json={},
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
