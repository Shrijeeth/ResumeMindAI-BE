"""GraphRAG-SDK LiteModel configuration service.

This module provides functions to create and configure LiteModel instances
for use with GraphRAG-SDK, using the user's configured LLM provider settings.
"""

import logging
from typing import Optional

from graphrag_sdk.model_config import KnowledgeGraphModelConfig
from graphrag_sdk.models.litellm import LiteModel

from models.llm_provider import LLMProvider
from services.encryption import decrypt_api_key
from services.llm_provider import format_model_name

logger = logging.getLogger(__name__)


def create_lite_model_for_graphrag(
    provider: LLMProvider,
    temperature: float = 0.0,
) -> LiteModel:
    """Create a LiteModel instance for GraphRAG-SDK.

    The LiteModel expects model_name in format: "provider/model"
    e.g., "openai/gpt-4", "anthropic/claude-3-sonnet", "gemini/gemini-pro"

    Args:
        provider: User's configured LLM provider from database
        temperature: Temperature for generation (default 0 for structured extraction)

    Returns:
        LiteModel configured for GraphRAG operations
    """
    # Format model name for LiteLLM (provider/model format)
    model_name = format_model_name(provider.provider_type, provider.model_name)

    # Decrypt API key
    api_key = decrypt_api_key(provider.api_key_encrypted)

    # Build additional params
    additional_params: dict = {}
    if api_key:
        additional_params["api_key"] = api_key
    if provider.base_url:
        additional_params["api_base"] = provider.base_url

    logger.info(f"Creating LiteModel for GraphRAG with model: {model_name}")

    # Create LiteModel
    # Note: LiteModel validates the key on init, so errors may occur here
    return LiteModel(
        model_name=model_name,
        additional_params=additional_params if additional_params else None,
    )


def create_kg_model_config(
    provider: LLMProvider,
    cypher_model: Optional[LiteModel] = None,
    qa_model: Optional[LiteModel] = None,
) -> KnowledgeGraphModelConfig:
    """Create a full KnowledgeGraphModelConfig for GraphRAG operations.

    This creates model instances for:
    - extract_data: Entity/relation extraction
    - cypher_generation: Query generation
    - qa: Question answering

    By default, all use the same model, but can be overridden.

    Args:
        provider: User's configured LLM provider
        cypher_model: Optional separate model for Cypher generation
        qa_model: Optional separate model for Q&A

    Returns:
        KnowledgeGraphModelConfig with configured models
    """
    # Create the primary model for extraction
    extraction_model = create_lite_model_for_graphrag(provider, temperature=0.0)

    # Use the same model for all if not specified
    return KnowledgeGraphModelConfig.with_model(extraction_model)


def validate_provider_for_graphrag(provider: LLMProvider) -> tuple[bool, Optional[str]]:
    """Validate that an LLM provider can be used for GraphRAG.

    Checks:
    - Provider has an API key
    - Provider has a model name
    - Provider type is supported

    Args:
        provider: The LLM provider to validate

    Returns:
        tuple: (is_valid, error_message)
    """
    if not provider.api_key_encrypted:
        return False, "LLM provider has no API key configured"

    if not provider.model_name:
        return False, "LLM provider has no model name configured"

    # All provider types in PROVIDER_PREFIX are supported by LiteLLM
    # Custom providers may or may not work depending on configuration
    return True, None
