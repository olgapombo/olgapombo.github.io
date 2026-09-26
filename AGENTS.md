# Repository guidance for coding agents

## Project layout

- This is Olga Pombo's Hugo site. Site settings and navigation live in `hugo.toml`.
- Edit page content in `content/`; the home page is `content/_index.md`. Pages may contain inline HTML as well as Markdown.
- Edit page structure in `layouts/`, site assets and legacy documents in `static/`, and book data in `data/books.json`.
- The Python image optimizer lives in `src/site_image_optimizer/`; its tests are in `tests/`. Project dependencies and the command entry point are defined in `pyproject.toml`.
- GitHub Pages builds and deploys the site through `.github/workflows/hugo.yml`. The separate `.github/workflows/optimize-images.yml` workflow opens a pull request for image conversions.

## Working conventions

- Preserve existing page URLs, filenames, and local links when editing content, especially links to documents under `static/`.
- Keep changes focused. Do not reformat unrelated content or alter user changes already present in the working tree.
- Treat image optimization as an explicit task: preview with `uv run site-image-optimize` before using `--apply`. Use `--delete-originals` only when removal of source images is intended.

## Local checks

- Preview the site with `hugo server -D`.
- Build the site with `hugo --gc --minify` after changes to content, templates, configuration, or assets.
- For Python optimizer changes, run `uv run pytest` (after `uv sync` if dependencies are missing).
