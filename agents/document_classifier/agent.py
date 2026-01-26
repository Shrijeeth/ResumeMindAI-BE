"""Document classification agent using Agno AI.

Uses an AI agent to analyze document content and classify it as:
- resume
- job_description
- cover_letter
- other
"""

import html
import logging
import re
from typing import Optional

from agno.agent import Agent
from agno.models.litellm import LiteLLM

from agents.document_classifier.schemas import DocumentClassification
from configs.postgres import use_db_session
from models.document import DocumentType
from services.encryption import decrypt_api_key
from services.llm_provider import (
    format_model_name,
)
from services.llm_provider import (
    get_user_llm_provider as _get_user_llm_provider,
)
from services.prompts import load_prompt

logger = logging.getLogger(__name__)


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


def _sanitize_user_text(value: str, max_length: int) -> str:
    """Best-effort neutralization of user-provided text for prompts."""

    cleaned = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]", "", value or "")
    cleaned = cleaned[:max_length].strip()
    return html.escape(cleaned, quote=False)


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

        safe_filename = _sanitize_user_text(filename, max_length=256)
        safe_content = _sanitize_user_text(text_content[:5000], max_length=5000)

        prompt = load_prompt("document_classifier").format(
            filename=safe_filename,
            content=f"<user_content>\n{safe_content}\n</user_content>",
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


async def get_user_llm_provider(user_id: str, allow_fallback_connected: bool = True):
    """Helper to fetch user's LLM provider with its own DB session."""

    async with use_db_session() as session:
        return await _get_user_llm_provider(
            session, user_id, allow_fallback_connected=allow_fallback_connected
        )
