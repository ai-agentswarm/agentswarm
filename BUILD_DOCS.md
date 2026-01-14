# Building Documentation

This project uses [MkDocs](https://www.mkdocs.org/) with the [Material theme](https://squidfunk.github.io/mkdocs-material/) to generate the static site from the markdown files in the `docs` folder.

## Prerequisites

Ensure you have the documentation dependencies installed. You can install them using the `docs` extra:

```bash
pip install -e ".[docs]"
```

## Building the Site

To build the static site into the `site` folder, run:

```bash
mkdocs build
```

This will create (or update) the `site` directory with the compiled HTML and assets.

## Local Development

To preview the documentation locally with live reloading, use the built-in server:

```bash
mkdocs serve
```

By default, the site will be available at `http://127.0.0.1:8000/`.

## Configuration

The documentation structure and plugins are configured in [mkdocs.yml](mkdocs.yml).
The Python API documentation is automatically generated using [mkdocstrings](https://mkdocstrings.github.io/).
