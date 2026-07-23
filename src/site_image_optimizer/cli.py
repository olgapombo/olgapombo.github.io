from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .optimizer import OptimizationError, optimize, plan_conversions


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="site-image-optimize",
        description="Convert images under a static directory to WebP and rewrite local references.",
    )
    parser.add_argument("root", nargs="?", default=".", type=Path, help="site root (default: current directory)")
    parser.add_argument("--static-dir", default="static", help="static directory relative to the root")
    parser.add_argument("--quality", type=int, default=82, help="WebP quality from 1 to 100 (default: 82)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="write WebP files and update references")
    mode.add_argument("--check", action="store_true", help="exit 1 when convertible images remain")
    parser.add_argument(
        "--delete-originals",
        action="store_true",
        help="delete source images after successful conversion (requires --apply)",
    )
    parser.add_argument("--overwrite", action="store_true", help="replace existing same-name WebP files")
    return parser


def _human_size(size: int) -> str:
    value = float(abs(size))
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            prefix = "-" if size < 0 else ""
            return f"{prefix}{value:.1f} {unit}"
        value /= 1024
    raise AssertionError("unreachable")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.delete_originals and not args.apply:
        print("error: --delete-originals requires --apply", file=sys.stderr)
        return 2

    root = args.root.resolve()
    static_dir = root / args.static_dir
    try:
        conversions = plan_conversions(static_dir, overwrite=args.overwrite)
        if not args.apply:
            label = "check" if args.check else "dry run"
            print(f"{label}: {len(conversions)} image(s) can be converted")
            for conversion in conversions:
                print(f"  {conversion.source.relative_to(root)} -> {conversion.destination.relative_to(root)}")
            if not conversions:
                print("No convertible images found.")
            return 1 if args.check and conversions else 0

        report = optimize(
            root,
            static_name=args.static_dir,
            quality=args.quality,
            delete_originals=args.delete_originals,
            overwrite=args.overwrite,
        )
    except (OptimizationError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print(f"Converted {len(report.conversions)} image(s) and updated {len(report.changed_files)} file(s).")
    print(
        f"Image data: {_human_size(report.original_bytes)} -> {_human_size(report.webp_bytes)} "
        f"(saved {_human_size(report.bytes_saved)})."
    )
    if args.delete_originals:
        print("Original images deleted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
