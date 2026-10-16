<<<<<<< HEAD
"""Fetch the pinned ResPlan archive after verifying its SHA-256 digest."""

=======
"""Download ResPlan.zip (about 100 MB, CC BY 4.0) and split.json into data/, verifying each SHA-256.

Usage: python scripts/fetch_resplan.py [--sha256 DIGEST] [--timeout SECONDS]
"""

>>>>>>> e93d1bc4ec002a5c7592ba84d9672f2712ba5fd4
from __future__ import annotations

import argparse
import hashlib
<<<<<<< HEAD
=======
import math
>>>>>>> e93d1bc4ec002a5c7592ba84d9672f2712ba5fd4
import os
import pathlib
import re
import tempfile
import urllib.parse
import urllib.request


URL = "https://raw.githubusercontent.com/m-agour/ResPlan/main/ResPlan.zip"
<<<<<<< HEAD
DEST = pathlib.Path(__file__).resolve().parent.parent / "data" / "ResPlan.zip"
=======
# SHA-256 of ResPlan.zip as served at URL on 15 Oct 2026 (100,106,537 bytes).
PINNED_SHA256 = "f718de8865e51bbe93b49b584798e3c536ed6b4b8a5d32f01b56812f389aeb46"
DEST = pathlib.Path(__file__).resolve().parent.parent / "data" / "ResPlan.zip"
SPLIT_URL = "https://raw.githubusercontent.com/m-agour/ResPlan/main/split.json"
# SHA-256 of split.json as served at SPLIT_URL on 16 Oct 2026 (177,059 bytes).
SPLIT_PINNED_SHA256 = "7761df4ad4c860d7e89d1ef9c7004737cd407615b66ed9cde676d7087108c9a7"
SPLIT_DEST = DEST.with_name("split.json")
>>>>>>> e93d1bc4ec002a5c7592ba84d9672f2712ba5fd4
DEFAULT_TIMEOUT_S = 30
MAX_BYTES = 200 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
EXPECTED_HOST = "raw.githubusercontent.com"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _check_url(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != EXPECTED_HOST:
        raise ValueError("download URL must use the expected HTTPS host")


def _check_digest(digest):
    if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest.lower()):
        raise ValueError("sha256 must be a 64-character hexadecimal checksum")
    return digest.lower()


def _file_digest(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


<<<<<<< HEAD
def download(destination, sha256, *, opener=urllib.request.urlopen, timeout=DEFAULT_TIMEOUT_S):
    destination = pathlib.Path(destination)
    expected = _check_digest(sha256)
    _check_url(URL)
=======
def download(destination, sha256, *, url=URL, opener=urllib.request.urlopen, timeout=DEFAULT_TIMEOUT_S):
    destination = pathlib.Path(destination)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a finite number greater than zero")
    expected = _check_digest(sha256)
    _check_url(url)
>>>>>>> e93d1bc4ec002a5c7592ba84d9672f2712ba5fd4
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.is_symlink():
        raise ValueError(f"refusing to write through symlink: {destination}")
    if destination.exists():
        if _file_digest(destination) == expected:
            return destination
        raise ValueError(f"existing file checksum does not match: {destination}")

    temporary = None
    try:
<<<<<<< HEAD
        request = urllib.request.Request(URL, headers={"User-Agent": "loopwright-fetch/1"})
=======
        request = urllib.request.Request(url, headers={"User-Agent": "loopwright-fetch/1"})
>>>>>>> e93d1bc4ec002a5c7592ba84d9672f2712ba5fd4
        with opener(request, timeout=timeout) as response:
            final_url = response.geturl()
            _check_url(final_url)
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=destination.parent, prefix=destination.name + ".", suffix=".part", delete=False
            ) as sink:
                temporary = pathlib.Path(sink.name)
                digest = hashlib.sha256()
                size = 0
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise ValueError("download exceeds the maximum allowed size")
                    sink.write(chunk)
                    digest.update(chunk)
        if digest.hexdigest() != expected:
            raise ValueError("download checksum does not match")
        os.replace(temporary, destination)
        temporary = None
        return destination
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
<<<<<<< HEAD
    parser.add_argument("--sha256", default=os.environ.get("LOOPWRIGHT_RESPPLAN_SHA256"))
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S)
    args = parser.parse_args(argv)
    if args.sha256 is None:
        parser.error("--sha256 or LOOPWRIGHT_RESPPLAN_SHA256 is required")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    try:
        path = download(DEST, args.sha256, timeout=args.timeout)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"saved {path}")
=======
    parser.add_argument("--sha256", default=os.environ.get("LOOPWRIGHT_RESPLAN_SHA256", PINNED_SHA256))
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S)
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    for dest, url, digest in ((DEST, URL, args.sha256), (SPLIT_DEST, SPLIT_URL, SPLIT_PINNED_SHA256)):
        try:
            path = download(dest, digest, url=url, timeout=args.timeout)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        print(f"saved {path}")
>>>>>>> e93d1bc4ec002a5c7592ba84d9672f2712ba5fd4


if __name__ == "__main__":
    main()
