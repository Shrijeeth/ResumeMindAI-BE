import shutil
from pathlib import Path

import pytest

from services import prompts


@pytest.fixture
def prompts_dir(tmp_path, monkeypatch):
    repo_prompts = Path(__file__).resolve().parent.parent.parent / "prompts"
    original_exists = repo_prompts.exists()
    if not original_exists:
        repo_prompts.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(prompts, "Path", Path)
    yield repo_prompts
    # clean up only if we created it
    if not original_exists:
        shutil.rmtree(repo_prompts, ignore_errors=True)


def test_load_prompt_returns_content(prompts_dir):
    prompt_file = prompts_dir / "sample.txt"
    prompt_file.write_text("Hello prompt")

    content = prompts.load_prompt("sample")

    assert content == "Hello prompt"


def test_load_prompt_raises_when_missing(prompts_dir):
    missing = prompts_dir / "does_not_exist.txt"
    if missing.exists():
        missing.unlink()

    with pytest.raises(FileNotFoundError):
        prompts.load_prompt("does_not_exist")
