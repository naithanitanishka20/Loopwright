# Testing

Install the development dependencies and run the unit suite:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

Run browser coverage separately:

```bash
python -m pip install -e ".[dev,e2e]"
python -m playwright install chromium
python -m pytest -m e2e -q
```

The tests cover configuration types, malformed schema-v2 output, geometry repair, zone search, routing, restricted pickle loading, downloader integrity, CLI solve/validate, and SVG rendering. Dataset tests are marked `dataset` and skip if `data/ResPlan.zip` is missing.

When adding a fix, add the failing public-seam test first. Keep network tests deterministic by injecting the downloader opener. Check crafted pickle, JSON, geometry, output paths, and non-finite numbers.
