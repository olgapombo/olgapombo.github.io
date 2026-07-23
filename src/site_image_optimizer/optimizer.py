from __future__ import annotations

import os
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageOps

IMAGE_SUFFIXES = frozenset({".bmp", ".gif", ".jfif", ".jpeg", ".jpg", ".png", ".tif", ".tiff"})
TEXT_SUFFIXES = frozenset(
    {
        ".css",
        ".htm",
        ".html",
        ".js",
        ".json",
        ".jsx",
        ".md",
        ".markdown",
        ".sass",
        ".scss",
        ".toml",
        ".ts",
        ".tsx",
        ".txt",
        ".xml",
        ".yaml",
        ".yml",
    }
)
EXCLUDED_DIRS = frozenset({".git", ".venv", "node_modules", "public", "resources"})
REFERENCE_DELIMITERS = " \t\r\n\"'()<>[]{}="


class OptimizationError(RuntimeError):
    """Raised when the requested conversion cannot be performed safely."""


@dataclass(frozen=True)
class Conversion:
    source: Path
    destination: Path


@dataclass
class OptimizationReport:
    conversions: list[Conversion] = field(default_factory=list)
    changed_files: list[Path] = field(default_factory=list)
    original_bytes: int = 0
    webp_bytes: int = 0

    @property
    def bytes_saved(self) -> int:
        return self.original_bytes - self.webp_bytes


def discover_images(static_dir: Path) -> list[Path]:
    if not static_dir.is_dir():
        raise OptimizationError(f"Static directory does not exist: {static_dir}")
    return sorted(
        path
        for path in static_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def plan_conversions(static_dir: Path, *, overwrite: bool = False) -> list[Conversion]:
    sources = discover_images(static_dir)
    default_destinations = Counter(source.with_suffix(".webp") for source in sources)
    conversions: list[Conversion] = []
    for source in sources:
        destination = source.with_suffix(".webp")
        if default_destinations[destination] > 1:
            source_type = source.suffix.lower().lstrip(".")
            destination = source.with_name(f"{source.stem}-{source_type}.webp")
        conversions.append(Conversion(source, destination))

    existing = [item.destination for item in conversions if item.destination.exists() and not overwrite]
    if existing:
        raise OptimizationError(
            "WebP destinations already exist; use --overwrite to replace them:\n  "
            + "\n  ".join(str(path) for path in existing)
        )
    return conversions


def _webp_frame(frame: Image.Image) -> Image.Image:
    if frame.mode in {"RGBA", "LA"} or "transparency" in frame.info:
        return frame.convert("RGBA")
    return frame.convert("RGB")


def convert_image(conversion: Conversion, *, quality: int) -> int:
    destination = conversion.destination
    temporary = destination.with_name(f".{destination.name}.tmp")
    destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        with Image.open(conversion.source) as image:
            if getattr(image, "is_animated", False):
                frames: list[Image.Image] = []
                durations: list[int] = []
                for frame_number in range(image.n_frames):
                    image.seek(frame_number)
                    frames.append(_webp_frame(image.copy()))
                    durations.append(int(image.info.get("duration", 100)))
                frames[0].save(
                    temporary,
                    format="WEBP",
                    save_all=True,
                    append_images=frames[1:],
                    duration=durations,
                    loop=int(image.info.get("loop", 0)),
                    quality=quality,
                    method=6,
                )
            else:
                normalized = _webp_frame(ImageOps.exif_transpose(image))
                normalized.save(temporary, format="WEBP", quality=quality, method=6)
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return destination.stat().st_size


def _iter_text_files(root: Path, static_dir: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative_parts = path.relative_to(root).parts
        if any(part in EXCLUDED_DIRS for part in relative_parts):
            continue
        # The static tree contains legacy HTML whose image links also need updating.
        yield path


def _reference_variants(conversion: Conversion, static_dir: Path, basename_unique: bool) -> list[tuple[str, str]]:
    old_relative = conversion.source.relative_to(static_dir).as_posix()
    new_relative = conversion.destination.relative_to(static_dir).as_posix()
    variants = [
        (f"static/{old_relative}", f"static/{new_relative}"),
        (f"/{old_relative}", f"/{new_relative}"),
        (old_relative, new_relative),
    ]
    if basename_unique:
        variants.append((conversion.source.name, conversion.destination.name))
    # Longest first avoids replacing the tail of a more specific path.
    return sorted(set(variants), key=lambda item: len(item[0]), reverse=True)


def _is_external_reference(text: str, position: int) -> bool:
    token_start = position
    while token_start > 0 and text[token_start - 1] not in REFERENCE_DELIMITERS:
        token_start -= 1
    return "://" in text[token_start:position]


def rewrite_references(root: Path, static_dir: Path, conversions: list[Conversion]) -> list[Path]:
    name_counts = Counter(item.source.name for item in conversions)
    replacements: list[tuple[re.Pattern[str], str]] = []
    for conversion in conversions:
        for old, new in _reference_variants(conversion, static_dir, name_counts[conversion.source.name] == 1):
            replacements.append(
                (re.compile(rf"(?<![A-Za-z0-9_.-]){re.escape(old)}(?![A-Za-z0-9_.-])"), new)
            )
    replacements.sort(key=lambda item: len(item[0].pattern), reverse=True)

    changed_files: list[Path] = []
    for path in _iter_text_files(root, static_dir):
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
            encoding = "latin-1"

        updated = text
        for pattern, replacement in replacements:
            updated = pattern.sub(
                lambda match: match.group(0) if _is_external_reference(updated, match.start()) else replacement,
                updated,
            )
        if updated != text:
            path.write_bytes(updated.encode(encoding))
            changed_files.append(path)
    return changed_files


def optimize(
    root: Path,
    *,
    static_name: str = "static",
    quality: int = 82,
    delete_originals: bool = False,
    overwrite: bool = False,
) -> OptimizationReport:
    if not 1 <= quality <= 100:
        raise OptimizationError("Quality must be between 1 and 100")

    root = root.resolve()
    static_dir = (root / static_name).resolve()
    try:
        static_dir.relative_to(root)
    except ValueError as error:
        raise OptimizationError("Static directory must be inside the site root") from error

    conversions = plan_conversions(static_dir, overwrite=overwrite)
    report = OptimizationReport(conversions=conversions)
    report.original_bytes = sum(item.source.stat().st_size for item in conversions)

    for conversion in conversions:
        report.webp_bytes += convert_image(conversion, quality=quality)
    report.changed_files = rewrite_references(root, static_dir, conversions)

    if delete_originals:
        for conversion in conversions:
            conversion.source.unlink()
    return report
