from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from site_image_optimizer.cli import main
from site_image_optimizer.optimizer import OptimizationError, optimize, plan_conversions


def _image(path: Path, image_format: str = "JPEG") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (20, 10), (120, 30, 200)).save(path, format=image_format)


def test_converts_image_and_rewrites_local_references_only(tmp_path: Path) -> None:
    source = tmp_path / "static" / "images" / "photo.jpg"
    _image(source)
    markdown = tmp_path / "content" / "page.md"
    markdown.parent.mkdir()
    markdown.write_text(
        "![local](../static/images/photo.jpg)\n"
        "![root](/images/photo.jpg)\n"
        "![external](https://example.com/images/photo.jpg)\n",
        encoding="utf-8",
    )
    css = tmp_path / "static" / "assets" / "site.css"
    css.parent.mkdir()
    css.write_text("body { background: url('../../images/photo.jpg') }", encoding="utf-8")

    report = optimize(tmp_path, delete_originals=True)

    assert len(report.conversions) == 1
    assert not source.exists()
    assert (source.with_suffix(".webp")).exists()
    updated = markdown.read_text(encoding="utf-8")
    assert "../static/images/photo.webp" in updated
    assert "/images/photo.webp" in updated
    assert "https://example.com/images/photo.jpg" in updated
    assert "../../images/photo.webp" in css.read_text(encoding="utf-8")


def test_preserves_animated_gif(tmp_path: Path) -> None:
    source = tmp_path / "static" / "animation.gif"
    source.parent.mkdir()
    frames = [Image.new("RGB", (8, 8), color) for color in ("red", "blue")]
    frames[0].save(source, save_all=True, append_images=frames[1:], duration=[40, 60], loop=0)

    optimize(tmp_path)

    with Image.open(source.with_suffix(".webp")) as converted:
        assert converted.is_animated
        assert converted.n_frames == 2


def test_disambiguates_destination_collisions(tmp_path: Path) -> None:
    _image(tmp_path / "static" / "same.jpg")
    _image(tmp_path / "static" / "same.png", image_format="PNG")

    conversions = plan_conversions(tmp_path / "static")

    assert [item.destination.name for item in conversions] == ["same-jpg.webp", "same-png.webp"]


def test_refuses_to_replace_existing_webp_without_overwrite(tmp_path: Path) -> None:
    _image(tmp_path / "static" / "same.jpg")
    _image(tmp_path / "static" / "same.webp", image_format="WEBP")

    with pytest.raises(OptimizationError, match="already exist"):
        plan_conversions(tmp_path / "static")


def test_cli_is_dry_run_by_default_and_check_reports_work(tmp_path: Path) -> None:
    source = tmp_path / "static" / "photo.jpg"
    _image(source)

    assert main([str(tmp_path)]) == 0
    assert not source.with_suffix(".webp").exists()
    assert main([str(tmp_path), "--check"]) == 1


def test_delete_originals_requires_apply(tmp_path: Path) -> None:
    assert main([str(tmp_path), "--delete-originals"]) == 2
