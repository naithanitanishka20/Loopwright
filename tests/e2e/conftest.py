"""Browser fixture for the e2e tests.

Uses Playwright's own Chromium if it was installed with
`python -m playwright install chromium`, else the system's Edge or Chrome, so no
browser download is needed on most machines. Skips when none is available.
"""
import pytest


@pytest.fixture(scope="module")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api", reason="install the e2e extra")
    with sync_api.sync_playwright() as p:
        launched = None
        for kwargs in ({}, {"channel": "msedge"}, {"channel": "chrome"}):
            try:
                launched = p.chromium.launch(**kwargs)
                break
            except Exception:
                continue
        if launched is None:
            pytest.skip("no Chromium, Edge or Chrome available to Playwright")
        yield launched
        launched.close()
