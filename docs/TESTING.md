# Testing

Run the fast suite from the repository root:

```bash
python -m pytest -q
```

Run browser smoke coverage when the e2e extra and Chromium are installed:

```bash
python -m pytest -m e2e -q
```

Tests cover settings validation, schema boundaries, the CLI, and the dataset downloader. Dataset-specific tests should use the `dataset` marker and skip when `data/ResPlan.zip` is absent.

Every new bug should get a failing regression test at the public interface that exposed it. Keep network tests deterministic by injecting the opener and using a fixed payload.
