"""Service for mascot-preserving image-to-image generation using HuggingFace."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from huggingface_hub import InferenceClient
from loguru import logger
from PIL.Image import Image

from src.config.settings import Settings
from src.utils.prompt_loader import load_prompt_file


class ImageGenerationError(Exception):
    """Raised when image generation fails."""


class ImageGenerationService:
    """Generates meme images with mascot identity constraints."""

    def __init__(self, settings: Settings) -> None:
        """Initialize image generation service and prompt templates."""
        self._settings = settings
        self._client = InferenceClient(
            provider=settings.hf_inference_provider,
            api_key=settings.huggingface_token,
            timeout=settings.generation_timeout_seconds,
        )

        prompts_root = settings.prompts_root
        self._base_character_prompt = load_prompt_file(prompts_root / "image" / "base_character.md")
        self._negative_prompt = load_prompt_file(prompts_root / "image" / "negative_prompt.md")
        self._meme_style_prompt = load_prompt_file(prompts_root / "image" / "meme_style.md")

    async def generate_image_path(self, optimized_prompt: str, model: str | None = None) -> Path:
        """Generate an image with mascot reference and return saved file path."""
        mascot_path = self._settings.mascot_image_path
        if not mascot_path.exists():
            raise ImageGenerationError(f"Mascot image not found at {mascot_path}.")
        if not optimized_prompt or not optimized_prompt.strip():
            raise ImageGenerationError("Optimized prompt cannot be empty.")

        composed_prompt = self._compose_prompt(optimized_prompt)
        selected_model = self._resolve_model(model)
        source_bytes = mascot_path.read_bytes()

        logger.info(
            "Generating image with model={} provider={} retries={}",
            selected_model,
            self._settings.hf_inference_provider,
            self._settings.generation_retries,
        )
        image = await self._generate_with_retries(
            model=selected_model,
            prompt=composed_prompt,
            source_bytes=source_bytes,
        )

        output_path = self._build_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path, format="PNG")
        logger.info("Image generated successfully path={}", output_path)
        return output_path

    def _compose_prompt(self, optimized_prompt: str) -> str:
        """Compose reusable prompt blocks for cinematic mascot memes."""
        blocks = [
            f"Scene request:\n{optimized_prompt.strip()}",
            self._base_character_prompt,
        ]
        style_prompt = self._meme_style_prompt.strip()
        if style_prompt:
            blocks.append(style_prompt)
        return "\n\n".join(blocks)

    async def _generate_with_retries(self, model: str, prompt: str, source_bytes: bytes) -> Image:
        """Call HF API with retry and timeout safeguards."""
        last_error: Exception | None = None
        retries = max(self._settings.generation_retries, 1)

        for attempt in range(1, retries + 1):
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(
                        self._call_image_to_image,
                        model=model,
                        prompt=prompt,
                        source_bytes=source_bytes,
                        source_path=self._settings.mascot_image_path,
                    ),
                    timeout=self._settings.generation_timeout_seconds,
                )
            except asyncio.TimeoutError as exc:
                last_error = exc
                logger.warning("Generation timeout attempt={}/{}", attempt, retries)
            except Exception as exc:
                if self._is_image_to_image_unsupported(exc):
                    logger.warning(
                        "Model/provider does not support image-to-image. Falling back to text-to-image model={}",
                        model,
                    )
                    return await asyncio.wait_for(
                        asyncio.to_thread(
                            self._call_text_to_image,
                            model=model,
                            prompt=prompt,
                        ),
                        timeout=self._settings.generation_timeout_seconds,
                    )
                last_error = exc
                logger.warning(
                    "Generation request failed attempt={}/{} error={}",
                    attempt,
                    retries,
                    exc,
                )

            if attempt < retries:
                backoff_seconds = self._settings.generation_retry_base_delay_seconds * attempt
                await asyncio.sleep(backoff_seconds)

        logger.error("Image generation exhausted retries model={}", model)
        raise ImageGenerationError("Image generation failed in HuggingFace Inference API.") from last_error

    def _call_image_to_image(
        self,
        model: str,
        prompt: str,
        source_bytes: bytes,
        source_path: Path,
    ) -> Image:
        """Perform blocking HF image-to-image request."""
        width, height = self._parse_size(self._settings.generation_size)
        if self._is_flux_kontext_model(model):
            return self._client.image_to_image(
                image=source_path,
                prompt=prompt,
                model=model,
                width=width,
                height=height,
                guidance_scale=self._settings.generation_guidance_scale,
                num_inference_steps=self._settings.generation_num_inference_steps,
                strength=self._settings.generation_strength,
            )
        return self._client.image_to_image(
            image=source_bytes,
            prompt=prompt,
            negative_prompt=self._negative_prompt,
            model=model,
            width=width,
            height=height,
            guidance_scale=self._settings.generation_guidance_scale,
            num_inference_steps=self._settings.generation_num_inference_steps,
            strength=self._settings.generation_strength,
            adapter_id=self._settings.hf_ip_adapter_model,
            ip_adapter_image=source_bytes,
        )

    def _is_flux_kontext_model(self, model: str) -> bool:
        """Detect FLUX Kontext models that require image path payloads."""
        return "flux.1-kontext" in model.lower()

    def _call_text_to_image(self, model: str, prompt: str) -> Image:
        """Fallback blocking HF text-to-image request for unsupported providers/models."""
        width, height = self._parse_size(self._settings.generation_size)
        return self._client.text_to_image(
            prompt=prompt,
            negative_prompt=self._negative_prompt,
            model=model,
            width=width,
            height=height,
            guidance_scale=self._settings.generation_guidance_scale,
            num_inference_steps=self._settings.generation_num_inference_steps,
        )

    def _is_image_to_image_unsupported(self, error: Exception) -> bool:
        """Detect provider/model combinations that reject image-to-image task."""
        message = str(error).lower()
        return "not supported for task image-to-image" in message

    def _parse_size(self, generation_size: str) -> tuple[int, int]:
        """Parse WxH size with strict validation."""
        try:
            width_raw, height_raw = generation_size.lower().split("x", maxsplit=1)
            width = int(width_raw.strip())
            height = int(height_raw.strip())
        except (AttributeError, ValueError) as exc:
            raise ImageGenerationError(
                f"Invalid generation_size '{generation_size}'. Expected format WIDTHxHEIGHT."
            ) from exc

        if width <= 0 or height <= 0:
            raise ImageGenerationError("generation_size dimensions must be positive integers.")

        return width, height

    def _resolve_model(self, model: str | None) -> str:
        """Resolve model aliases while keeping direct override support."""
        if model is None:
            return self._settings.hf_image_model

        normalized = model.strip().lower()
        if normalized in {"sdxl", "stable-diffusion-xl"}:
            return self._settings.hf_sdxl_image_model
        return model.strip()

    def _build_output_path(self) -> Path:
        """Create deterministic output path under configured outputs directory."""
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"meme_{timestamp}_{uuid4().hex[:8]}.png"
        return self._settings.outputs_dir / filename
