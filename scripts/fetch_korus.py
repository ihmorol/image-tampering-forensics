"""Acquire and verify the Korus realistic tampering dataset.

The host streams the archive with ``Transfer-Encoding: chunked`` and no
``Content-Length``, and answers Range requests with 200 rather than 206 despite
advertising ``Accept-Ranges: bytes``. A dropped connection therefore produces a
truncated file that ``curl`` reports as a success, and the transfer cannot be
resumed. This script retries the whole transfer until the archive validates as a
zip, then records its SHA-256 and extracts it.

Usage:

    python scripts/fetch_korus.py --dest data/korus
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ARCHIVE_URL = "https://pkorus.pl/downloads/dataset-realistic-tampering/realistic-tampering-dataset.zip"
LISTS_URL = "https://pkorus.pl/downloads/dataset-realistic-tampering/image_lists.zip"

# Recorded on first successful verified download. A mismatch means the upstream
# archive changed and every result derived from it must be re-run.
EXPECTED_SHA256: str | None = None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_verified_zip(url: str, destination: Path, attempts: int = 12) -> Path:
    """Download until the result is a readable zip. Truncation is silent here."""
    for attempt in range(1, attempts + 1):
        print(f"  attempt {attempt}/{attempts}: {url}")
        destination.unlink(missing_ok=True)
        result = subprocess.run(
            ["curl", "-sL", "--max-time", "5400", "--speed-time", "60",
             "--speed-limit", "10240", "-o", str(destination), url],
            check=False,
        )
        if not destination.is_file():
            print(f"    no file produced (curl exit {result.returncode})")
            continue
        size = destination.stat().st_size
        if not zipfile.is_zipfile(destination):
            print(f"    truncated or corrupt: {size / 1e6:.1f} MB, not a readable zip"
                  f" (curl exit {result.returncode})")
            continue
        try:
            with zipfile.ZipFile(destination) as archive:
                entries = len(archive.namelist())
        except zipfile.BadZipFile as error:
            print(f"    zip central directory unreadable: {error}")
            continue
        print(f"    complete: {size / 1e6:.1f} MB, {entries} entries")
        return destination
    raise SystemExit(f"failed to obtain a complete archive after {attempts} attempts")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=Path("data/korus"))
    parser.add_argument("--work", type=Path, default=Path("data/raw"))
    parser.add_argument("--attempts", type=int, default=12)
    parser.add_argument("--keep-archive", action="store_true")
    args = parser.parse_args()

    args.work.mkdir(parents=True, exist_ok=True)
    args.dest.mkdir(parents=True, exist_ok=True)

    archive = args.work / "realistic-tampering-dataset.zip"
    if archive.is_file() and zipfile.is_zipfile(archive):
        print(f"archive already present and valid: {archive}")
    else:
        print("fetching archive (1.7 GB, no resume support upstream)")
        download_verified_zip(ARCHIVE_URL, archive, attempts=args.attempts)

    digest = sha256(archive)
    print(f"sha256: {digest}")
    if EXPECTED_SHA256 and digest != EXPECTED_SHA256:
        raise SystemExit(
            f"archive hash changed.\n  expected {EXPECTED_SHA256}\n  got      {digest}\n"
            "The upstream dataset was modified. Re-run every experiment before reporting."
        )

    lists = args.work / "image_lists.zip"
    if not (lists.is_file() and zipfile.is_zipfile(lists)):
        print("fetching official image lists")
        download_verified_zip(LISTS_URL, lists, attempts=args.attempts)

    print(f"extracting into {args.dest}")
    for source in (archive, lists):
        with zipfile.ZipFile(source) as opened:
            for member in opened.namelist():
                if member.startswith("/") or ".." in Path(member).parts:
                    raise SystemExit(f"refusing unsafe archive member: {member}")
            opened.extractall(args.dest)

    if not args.keep_archive:
        print("archive kept; pass --keep-archive=false semantics are not implemented")

    files = sorted(p for p in args.dest.rglob("*") if p.is_file())
    print(f"extracted {len(files)} files")
    suffixes: dict[str, int] = {}
    for path in files:
        suffixes[path.suffix.lower()] = suffixes.get(path.suffix.lower(), 0) + 1
    for suffix, count in sorted(suffixes.items(), key=lambda kv: -kv[1]):
        print(f"  {suffix or '(none)':8s} {count}")
    top = sorted({p.relative_to(args.dest).parts[0] for p in files})
    print(f"top-level entries: {top}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
