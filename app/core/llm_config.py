import os
from typing import Optional
from pydantic import BaseModel


class LLMConfig(BaseModel):
    api_key: Optional[str] = None
    model: str = "gemini-1.5-pro"  # Default model
    temperature: float = 0.3
    max_tokens: int = 500


def get_llm_config() -> LLMConfig:
    """Get LLM configuration from environment variables."""
    return LLMConfig(
        api_key=os.getenv("GEMINI_API_KEY"),
        model=os.getenv("GEMINI_MODEL", "gemini-1.5-pro"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "500"))
    )


def is_llm_configured() -> bool:
    """Check if LLM is properly configured."""
    config = get_llm_config()
    return bool(config.api_key)