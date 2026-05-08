"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed runtime configuration for the application."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "telegram-ai-meme-bot"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    telegram_bot_token: str = Field(..., description="Telegram Bot API token.")
    telegram_allowed_chat_id: int = Field(
        ...,
        description="Telegram chat id where bot commands are allowed.",
    )
    huggingface_token: str = Field(..., description="HuggingFace API token.")
    groq_api_key: str = Field(..., description="Groq API key.")

    hf_image_model: str = "stabilityai/stable-diffusion-3-medium"
    hf_sdxl_image_model: str = "stabilityai/stable-diffusion-xl-base-1.0"
    hf_ip_adapter_model: str = "h94/IP-Adapter"
    hf_inference_provider: str = "fal-ai"
    groq_model: str = "llama-3.3-70b-versatile"
    groq_temperature: float = 0.7
    groq_top_p: float = 1.0
    groq_max_completion_tokens: int = 180
    prompt_output_max_words: int = 70

    mascot_image_path: Path = Path("images/personaje.jpg")
    prompts_root: Path = Path("src/prompts")
    outputs_dir: Path = Path("outputs")
    fonts_dir: Path = Path("fonts")
    logo_path: Path = Path("images/logo.png")
    logo_scale: float = 0.24
    logo_padding_ratio: float = 0.025

    generation_size: str = "1024x1024"
    generation_num_inference_steps: int = 30
    generation_guidance_scale: float = 7.0
    generation_strength: float = 0.65
    generation_timeout_seconds: float = 120.0
    generation_retries: int = 3
    generation_retry_base_delay_seconds: float = 1.5


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings object."""
    return Settings()
