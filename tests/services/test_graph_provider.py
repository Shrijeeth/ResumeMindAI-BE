import types

import pytest

from models import ProviderType
from services import graph_provider


@pytest.fixture
def provider_base():
    return types.SimpleNamespace(
        provider_type=ProviderType.OPENAI,
        model_name="gpt-4",
        base_url="https://api.test",
        api_key_encrypted=b"encrypted",
    )


def test_create_lite_model_for_graphrag_builds_params(monkeypatch, provider_base):
    captured = {}

    def fake_decrypt(value):
        captured["decrypt_arg"] = value
        return "sk-test"

    class DummyLiteModel:
        def __init__(self, model_name, additional_params=None):
            captured["model_name"] = model_name
            captured["additional_params"] = additional_params

    monkeypatch.setattr(graph_provider, "decrypt_api_key", fake_decrypt)
    monkeypatch.setattr(graph_provider, "LiteModel", DummyLiteModel)

    result = graph_provider.create_lite_model_for_graphrag(provider_base)

    assert isinstance(result, DummyLiteModel)
    assert captured["decrypt_arg"] == provider_base.api_key_encrypted
    assert captured["model_name"] == "openai/gpt-4"
    assert captured["additional_params"] == {
        "api_key": "sk-test",
        "api_base": provider_base.base_url,
    }


def test_create_lite_model_for_graphrag_without_base_url(monkeypatch, provider_base):
    provider_base.base_url = None

    monkeypatch.setattr(graph_provider, "decrypt_api_key", lambda _: "sk-test")

    class DummyLiteModel:
        def __init__(self, model_name, additional_params=None):
            self.model_name = model_name
            self.additional_params = additional_params

    monkeypatch.setattr(graph_provider, "LiteModel", DummyLiteModel)

    model = graph_provider.create_lite_model_for_graphrag(provider_base)

    assert model.additional_params == {"api_key": "sk-test"}


def test_create_kg_model_config_uses_extraction_model(monkeypatch):
    extraction_model = object()
    created_config = object()

    monkeypatch.setattr(
        graph_provider,
        "create_lite_model_for_graphrag",
        lambda provider, temperature=0.0: extraction_model,
    )
    monkeypatch.setattr(
        graph_provider.KnowledgeGraphModelConfig,
        "with_model",
        classmethod(lambda cls, model: created_config),
    )

    provider = types.SimpleNamespace(
        provider_type=ProviderType.OPENAI,
        model_name="gpt-4",
        base_url=None,
        api_key_encrypted=b"encrypted",
    )

    config = graph_provider.create_kg_model_config(provider)

    assert config is created_config


@pytest.mark.parametrize(
    "provider, expected",
    [
        (
            types.SimpleNamespace(
                api_key_encrypted=None,
                model_name="gpt",
                provider_type=ProviderType.OPENAI,
            ),
            (False, "LLM provider has no API key configured"),
        ),
        (
            types.SimpleNamespace(
                api_key_encrypted=b"enc",
                model_name=None,
                provider_type=ProviderType.OPENAI,
            ),
            (False, "LLM provider has no model name configured"),
        ),
        (
            types.SimpleNamespace(
                api_key_encrypted=b"enc",
                model_name="gpt",
                provider_type=ProviderType.OPENAI,
            ),
            (True, None),
        ),
    ],
)
def test_validate_provider_for_graphrag(provider, expected):
    assert graph_provider.validate_provider_for_graphrag(provider) == expected
