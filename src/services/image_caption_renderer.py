"""Service to overlay caption text on generated meme images using AIRSTRIKE fonts."""

from pathlib import Path

from loguru import logger
from PIL import Image, ImageDraw, ImageFont

from src.config.settings import Settings


class ImageCaptionRendererError(Exception):
    """Raised when caption rendering cannot be performed."""


_PRIMARY_FONT_FILE = "AIRSTRIKEBOLD.TTF"
_CONDENSED_FONT_FILE = "AIRSTRIKECOND.TTF"

_TEXT_FILL = (255, 255, 255, 255)
_STROKE_FILL = (0, 0, 0, 255)


class ImageCaptionRenderer:
    """Draws AIRSTRIKE-styled captions at the bottom of an image."""

    def __init__(self, settings: Settings) -> None:
        """Initialize renderer and validate that primary font is available."""
        self._fonts_dir = settings.fonts_dir
        self._primary_font_path = self._fonts_dir / _PRIMARY_FONT_FILE
        self._condensed_font_path = self._fonts_dir / _CONDENSED_FONT_FILE

        if not self._primary_font_path.exists():
            raise ImageCaptionRendererError(
                f"Primary font not found at {self._primary_font_path}."
            )

    def render_caption(self, image_path: Path, caption: str) -> None:
        """Open image, overlay caption at the bottom, and save back as PNG."""
        normalized = caption.strip()
        if not normalized:
            return

        with Image.open(image_path) as base:
            canvas = base.convert("RGBA")
            self._draw_caption(canvas, normalized.upper())
            canvas.convert("RGB").save(image_path, format="PNG")

        logger.info("Caption overlaid path={} chars={}", image_path, len(normalized))

    def _draw_caption(self, image: Image.Image, caption: str) -> None:
        """Render caption centered at the bottom of the image, fill-width style."""
        width, height = image.size
        max_text_width = int(width * 0.95)
        max_total_height = int(height * 0.22)
        bottom_padding = max(12, int(height * 0.03))

        font, lines = self._fit_text(caption, max_text_width, max_total_height, height)
        line_spacing = max(2, int(font.size * 0.12))
        line_height = self._line_height(font)
        total_text_height = line_height * len(lines) + line_spacing * (len(lines) - 1)

        draw = ImageDraw.Draw(image)
        stroke_width = max(3, font.size // 12)

        y = height - bottom_padding - total_text_height
        for line in lines:
            line_width = self._text_width(font, line)
            x = (width - line_width) // 2
            draw.text(
                (x, y),
                line,
                font=font,
                fill=_TEXT_FILL,
                stroke_width=stroke_width,
                stroke_fill=_STROKE_FILL,
            )
            y += line_height + line_spacing

    def _fit_text(
        self,
        caption: str,
        max_text_width: int,
        max_total_height: int,
        image_height: int,
    ) -> tuple[ImageFont.FreeTypeFont, list[str]]:
        """Find the largest AIRSTRIKE font size that fills the available width."""
        min_size = 24
        max_size = max(min_size + 1, int(image_height * 0.18))

        candidates: list[Path] = [self._primary_font_path]
        if self._condensed_font_path.exists():
            candidates.append(self._condensed_font_path)

        for font_path in candidates:
            best_size = self._search_best_size(
                caption, font_path, max_text_width, max_total_height, min_size, max_size
            )
            if best_size is None:
                continue
            font = ImageFont.truetype(str(font_path), size=best_size)
            lines = self._wrap_text(caption, font, max_text_width)
            return font, lines

        # Last resort: smallest size with primary font; allow soft overflow.
        font = ImageFont.truetype(str(self._primary_font_path), size=min_size)
        return font, self._wrap_text(caption, font, max_text_width)

    def _search_best_size(
        self,
        caption: str,
        font_path: Path,
        max_text_width: int,
        max_total_height: int,
        min_size: int,
        max_size: int,
    ) -> int | None:
        """Binary search the largest size that fits caption within width and height."""
        lo, hi = min_size, max_size
        best: int | None = None
        while lo <= hi:
            mid = (lo + hi) // 2
            font = ImageFont.truetype(str(font_path), size=mid)
            lines = self._wrap_text(caption, font, max_text_width)
            if not all(self._text_width(font, line) <= max_text_width for line in lines):
                hi = mid - 1
                continue
            line_spacing = max(2, int(mid * 0.12))
            line_height = self._line_height(font)
            total_height = line_height * len(lines) + line_spacing * (len(lines) - 1)
            if total_height > max_total_height:
                hi = mid - 1
                continue
            best = mid
            lo = mid + 1
        return best

    @staticmethod
    def _wrap_text(
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int,
    ) -> list[str]:
        """Greedy word-wrap that keeps long single words on their own line."""
        words = text.split()
        if not words:
            return [text]

        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            tentative = f"{current} {word}"
            if ImageCaptionRenderer._text_width(font, tentative) <= max_width:
                current = tentative
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    @staticmethod
    def _text_width(font: ImageFont.FreeTypeFont, text: str) -> int:
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0]

    @staticmethod
    def _line_height(font: ImageFont.FreeTypeFont) -> int:
        # Use full vertical metrics (ascent + descent) instead of bbox height,
        # because draw.text() reserves the ascent above the baseline regardless
        # of glyph cap height. Bbox-only height under-counts and causes
        # bottom-of-image clipping for multi-line captions.
        ascent, descent = font.getmetrics()
        return ascent + descent
