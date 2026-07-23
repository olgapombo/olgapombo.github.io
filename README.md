# Olga Pombo's Website (Hugo)

[Hugo](https://gohugo.io/) static site generator now powers this repository.

The website content is located in the `content/` directory.

To edit the home page, please go to:
### ➡️ [content/_index.md](content/_index.md)

---

## Local Development
To preview the site locally, install Hugo and run:
```bash
hugo server -D
```

---

The site is built and deployed using [GitHub Actions](https://github.com/features/actions) workflow.
The workflow is defined in the [hugo.yml](.github/workflows/hugo.yml) file.

## Image optimization

The repository includes a Python command-line tool that scans `static/`, converts
JPEG, PNG, GIF, BMP, JFIF, and TIFF images to WebP, and updates local references
in Markdown, HTML, CSS, JSON, YAML, TOML, JavaScript, and other text files. It
preserves animated GIFs and does not rewrite external URLs.

[Install uv](https://docs.astral.sh/uv/getting-started/installation/), then preview
the proposed conversions without changing files:

```bash
uv sync
uv run site-image-optimize
```

Apply the conversion while retaining the original images:

```bash
uv run site-image-optimize --apply
```

Apply it and remove originals only after every conversion and reference update
succeeds:

```bash
uv run site-image-optimize --apply --delete-originals
```

Useful options include `--quality 82`, `--static-dir static`, `--overwrite`, and
`--check`. The latter exits with status 1 when convertible images remain, making
it suitable for CI checks. Run the test suite with:

```bash
uv run pytest
```

The manually triggered [Optimize static images](.github/workflows/optimize-images.yml)
GitHub Actions workflow runs the optimizer, tests and builds the Hugo site, then
opens a pull request containing the generated changes.
