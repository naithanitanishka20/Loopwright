import hashlib
import importlib

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
