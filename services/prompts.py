"""Prompt loading utilities for AI agents."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_prompt(prompt_name: str) -> str:
    """
    Load a prompt template from the prompts directory.

    Args:
        prompt_name: Name of the prompt file (without .txt extension)

    Returns:
        Prompt template content as string

    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    prompts_dir = Path(__file__).resolve().parent.parent / "prompts"
    prompt_path = prompts_dir / f"{prompt_name}.txt"

    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_path}. "
            f"Expected prompt '{prompt_name}.txt' in {prompts_dir}"
        )

    logger.debug(f"Loading prompt from {prompt_path}")
    return prompt_path.read_text()
