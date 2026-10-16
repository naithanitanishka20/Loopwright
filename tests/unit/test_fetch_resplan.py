import hashlib
import importlib
import math
import pathlib

import pytest


fetcher = importlib.import_module("scripts.fetch_resplan")


class FakeResponse:
    def __init__(self, body, final_url=None):
        self.body = body
        self.final_url = final_url or fetcher.URL

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def geturl(self):
        return self.final_url

    def read(self, size=-1):
        if not self.body:
            return b""
        chunk, self.body = self.body[:size], self.body[size:]
        return chunk


def test_download_uses_timeout_and_commits_only_after_checksum(tmp_path):
    payload = b"resplan fixture"
    seen = {}

    def opener(request, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        return FakeResponse(payload)

    target = tmp_path / "ResPlan.zip"
    digest = hashlib.sha256(payload).hexdigest()

    result = fetcher.download(target, digest, opener=opener, timeout=3)

    assert result == target
    assert target.read_bytes() == payload
    assert seen == {"url": fetcher.URL, "timeout": 3}
    assert not list(tmp_path.glob("*.part"))


def test_checksum_mismatch_preserves_existing_file(tmp_path):
    target = tmp_path / "ResPlan.zip"
    target.write_bytes(b"trusted old file")

    def opener(request, timeout):
        return FakeResponse(b"untrusted content")

    with pytest.raises(ValueError, match="checksum"):
        fetcher.download(target, "0" * 64, opener=opener)

    assert target.read_bytes() == b"trusted old file"
    assert not list(tmp_path.glob("*.part"))


def test_download_checksum_mismatch_does_not_commit_partial_file(tmp_path):
    target = tmp_path / "ResPlan.zip"

    def opener(request, timeout):
        return FakeResponse(b"untrusted content")

    with pytest.raises(ValueError, match="checksum"):
        fetcher.download(target, "0" * 64, opener=opener)

    assert not target.exists()
    assert not list(tmp_path.glob("*.part"))


def test_download_rejects_unpinned_host(tmp_path):
    def opener(request, timeout):
        return FakeResponse(b"payload", final_url="https://example.com/file")

    with pytest.raises(ValueError, match="host"):
        fetcher.download(tmp_path / "ResPlan.zip", "0" * 64, opener=opener)


def test_download_fetches_the_url_it_is_given(tmp_path):
    payload = b"split fixture"
    seen = {}

    def opener(request, timeout):
        seen["url"] = request.full_url
        return FakeResponse(payload, final_url=request.full_url)

    target = tmp_path / "split.json"
    fetcher.download(target, hashlib.sha256(payload).hexdigest(), url=fetcher.SPLIT_URL, opener=opener)

    assert seen["url"] == "https://raw.githubusercontent.com/m-agour/ResPlan/main/split.json"
    assert target.read_bytes() == payload


def test_download_refuses_a_given_url_on_another_host(tmp_path):
    def opener(request, timeout):
        raise AssertionError("connected to a host that should have been refused")

    with pytest.raises(ValueError, match="host"):
        fetcher.download(tmp_path / "split.json", "0" * 64, url="https://example.com/split.json", opener=opener)


def _record(calls):
    def fake_download(destination, sha256, *, url, timeout):
        calls[pathlib.Path(destination).name] = (url, sha256)
        return destination

    return fake_download


def test_main_fetches_the_archive_and_the_split_each_with_its_own_digest(monkeypatch):
    calls = {}
    monkeypatch.delenv("LOOPWRIGHT_RESPLAN_SHA256", raising=False)
    monkeypatch.setattr(fetcher, "download", _record(calls))

    fetcher.main([])

    assert calls == {
        "ResPlan.zip": (fetcher.URL, fetcher.PINNED_SHA256),
        "split.json": (fetcher.SPLIT_URL, fetcher.SPLIT_PINNED_SHA256),
    }


def test_main_applies_the_environment_digest_to_the_archive_only(monkeypatch):
    calls = {}
    monkeypatch.setenv("LOOPWRIGHT_RESPLAN_SHA256", "a" * 64)
    monkeypatch.setattr(fetcher, "download", _record(calls))

    fetcher.main([])

    assert calls["ResPlan.zip"][1] == "a" * 64
    assert calls["split.json"][1] == fetcher.SPLIT_PINNED_SHA256


@pytest.mark.dataset
@pytest.mark.parametrize(("name", "pin"), [("ResPlan.zip", "PINNED_SHA256"), ("split.json", "SPLIT_PINNED_SHA256")])
def test_pinned_digests_accept_the_real_files(name, pin):
    from tests.conftest import DATA

    real = DATA.with_name(name)
    if not real.exists():
        pytest.skip(f"{real} not downloaded")

    def opener(request, timeout):
        raise AssertionError("a matching local file must not trigger a download")

    assert fetcher.download(real, getattr(fetcher, pin), opener=opener) == real


@pytest.mark.parametrize("timeout", [0, -1, math.nan, math.inf, True])
def test_download_rejects_invalid_timeout(tmp_path, timeout):
    with pytest.raises(ValueError, match="timeout"):
        fetcher.download(tmp_path / "ResPlan.zip", "0" * 64, timeout=timeout)


def test_download_removes_a_partial_file_when_size_limit_is_exceeded(tmp_path, monkeypatch):
    target = tmp_path / "ResPlan.zip"
    monkeypatch.setattr(fetcher, "MAX_BYTES", 3)

    def opener(request, timeout):
        return FakeResponse(b"too large")

    with pytest.raises(ValueError, match="maximum"):
        fetcher.download(target, "0" * 64, opener=opener)

    assert not target.exists()
    assert not list(tmp_path.glob("*.part"))
