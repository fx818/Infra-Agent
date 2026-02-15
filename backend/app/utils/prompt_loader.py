"""
Utility to load prompt files from the prompts directory.
"""

from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(filename: str) -> str:
    """
    Load a prompt from the prompts directory.

    Args:
        filename: Name of the prompt file (e.g. 'intent_agent_prompt.md')

    Returns:
        The prompt content as a string.
    """
    prompt_path = _PROMPTS_DIR / filename
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")
