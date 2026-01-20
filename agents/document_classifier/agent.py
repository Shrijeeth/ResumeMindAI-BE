"""Document classification agent using Agno AI.

Uses an AI agent to analyze document content and classify it as:
- resume
- job_description
- cover_letter
- other
"""

import logging
from typing import Optional

from agno.agent import Agent
from agno.models.litellm import LiteLLM
from sqlalchemy import select

from agents.document_classifier.schemas import DocumentClassification
from configs.postgres import use_db_session
from models.document import DocumentType
from models.llm_provider import LLMProvider, ProviderStatus
from services.encryption import decrypt_api_key
from services.llm_provider import format_model_name
from services.prompts import load_prompt

logger = logging.getLogger(__name__)


async def get_user_llm_provider(user_id: str) -> Optional[LLMProvider]:
    """Fetch user's LLM provider from database.

    Prioritizes active provider, falls back to any connected provider.
    """
    async with use_db_session() as session:
        # First, try to get the active provider
        result = await session.execute(
            select(LLMProvider)
            .where(LLMProvider.user_id == user_id)
            .where(LLMProvider.status == ProviderStatus.CONNECTED.value)
            .where(LLMProvider.is_active)
            .limit(1)
        )
        provider = result.scalar_one_or_none()

        # If no active provider, fall back to any connected provider
        if not provider:
            result = await session.execute(
                select(LLMProvider)
                .where(LLMProvider.user_id == user_id)
                .where(LLMProvider.status == ProviderStatus.CONNECTED.value)
                .limit(1)
            )
            provider = result.scalar_one_or_none()

        return provider


def create_classifier_agent(
    model_id: str,
    api_key: str,
    base_url: Optional[str] = None,
) -> Agent:
    """Create an Agno agent for document classification."""
    model_kwargs = {
        "id": model_id,
        "api_key": api_key,
    }
    if base_url:
        model_kwargs["api_base"] = base_url

    agent = Agent(
        name="DocumentClassifier",
        model=LiteLLM(**model_kwargs),
        instructions=[
            "You are a document classification expert.",
            "Analyze documents and classify them accurately.",
            "Provide confidence scores based on how certain you are.",
            "Be conservative - if unsure, lower the confidence score.",
        ],
        output_schema=DocumentClassification,
        structured_outputs=True,
        markdown=False,
    )

    return agent


async def classify_document(
    text_content: str,
    filename: str,
    user_id: str,
) -> dict:
    """
    Classify a document using Agno AI agent with user's configured LLM.

    Args:
        text_content: Text content of the document (first 5000 chars)
        filename: Original filename (provides hints about content)
        user_id: User ID to fetch their configured LLM provider

    Returns:
        dict with keys:
        - document_type: str (resume, job_description, cover_letter, other)
        - confidence: float (0.0 to 1.0)
        - reasoning: str (explanation of classification)
    """
    try:
        provider = await get_user_llm_provider(user_id)
        if not provider:
            logger.error(f"No configured LLM provider found for user {user_id}")
            return {
                "document_type": DocumentType.UNKNOWN.value,
                "confidence": 0.0,
                "reasoning": "No LLM provider configured",
            }

        api_key = decrypt_api_key(provider.api_key_encrypted)
        model_name = format_model_name(provider.provider_type, provider.model_name)

        logger.info(
            f"Classifying document using provider {provider.provider_type} "
            f"with model {model_name}"
        )

        agent = create_classifier_agent(
            model_id=model_name,
            api_key=api_key,
            base_url=provider.base_url,
        )

        prompt = load_prompt("document_classifier").format(
            filename=filename,
            content=text_content[:5000],
        )

        response = await agent.arun(prompt)

        if response and response.content:
            classification = response.content

            valid_types = {dt.value for dt in DocumentType}
            doc_type = classification.document_type.lower()

            if doc_type not in valid_types:
                doc_type = DocumentType.OTHER.value

            logger.info(
                f"Document classified: {doc_type} "
                f"(confidence: {classification.confidence:.2f}) - "
                f"{classification.reasoning[:100]}"
            )

            return {
                "document_type": doc_type,
                "confidence": classification.confidence,
                "reasoning": classification.reasoning,
            }

        logger.warning("No classification response from agent")
        return {
            "document_type": DocumentType.UNKNOWN.value,
            "confidence": 0.0,
            "reasoning": "Classification failed - no response from AI",
        }

    except Exception as e:
        logger.error(f"Error classifying document: {e}")
        return {
            "document_type": DocumentType.UNKNOWN.value,
            "confidence": 0.0,
            "reasoning": f"Classification error: {str(e)[:100]}",
        }
