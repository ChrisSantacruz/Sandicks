"""Service to overlay a brand logo on the top-left corner of generated meme images."""

from pathlib import Path

from loguru import logger
from PIL import Image

from src.config.settings import Settings


class LogoOverlayError(Exception):
    """Raised when the logo overlay cannot be performed."""


class LogoOverlayRenderer:
    """Pastes a transparent brand logo on the top-left corner of an image."""

    def __init__(self, settings: Settings) -> None:
        """Initialize renderer; loads the logo into memory and validates inputs."""
        if not settings.logo_path.exists():
            raise LogoOverlayError(f"Logo image not found at {settings.logo_path}.")
        if not 0.0 < settings.logo_scale <= 1.0:
            raise LogoOverlayError(
                f"logo_scale must be in (0, 1]; got {settings.logo_scale}."
            )
        if not 0.0 <= settings.logo_padding_ratio < 0.5:
            raise LogoOverlayError(
                f"logo_padding_ratio must be in [0, 0.5); got {settings.logo_padding_ratio}."
            )

        with Image.open(settings.logo_path) as raw_logo:
            # Force RGBA so paste() honors the alpha channel even if source is RGB.
            self._logo = raw_logo.convert("RGBA")

        self._scale = settings.logo_scale
        self._padding_ratio = settings.logo_padding_ratio

    def render_logo(self, image_path: Path) -> None:
        """Open image, paste the logo on the top-left corner, and save back as PNG."""
        with Image.open(image_path) as base:
            canvas = base.convert("RGBA")
            self._paste_logo(canvas)
            canvas.convert("RGB").save(image_path, format="PNG")

        logger.info("Logo overlaid path={}", image_path)

    def _paste_logo(self, canvas: Image.Image) -> None:
        """Resize the logo proportionally to canvas width and paste with alpha."""
        canvas_width, _ = canvas.size
        target_width = max(1, int(canvas_width * self._scale))
        scale_factor = target_width / self._logo.width
        target_height = max(1, int(self._logo.height * scale_factor))

        resized_logo = self._logo.resize(
            (target_width, target_height), resample=Image.Resampling.LANCZOS
        )

        padding = max(4, int(canvas_width * self._padding_ratio))
        canvas.alpha_composite(resized_logo, dest=(padding, padding))
