"""make.fun entry: news-image-20261125 -- "The World in One Picture".

The entry image (entry.png, a front page summing up the world news of
Wednesday 25 November 2026) ships in this repository beside this
program. At run time the program copies it, byte for byte, to
entry.png inside the output directory. The image signature is checked
before the copy and the written file is read back afterwards, so a
truncated or corrupted write can never pass silently.

Standard library only; no network; deterministic across runs.
"""

import hashlib
import os
import sys
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8\xff"

SOURCE_NAME = "entry.png"
OUTPUT_NAME = "entry.png"


def image_format(data: bytes) -> str:
    """Return "PNG" or "JPEG" from the leading bytes, else raise."""
    if data.startswith(PNG_SIGNATURE):
        return "PNG"
    if data.startswith(JPEG_SIGNATURE):
        return "JPEG"
    raise ValueError("bundled entry.png is neither a PNG nor a JPEG image")


def source_path() -> Path:
    """The bundled image sits beside this file in the repository."""
    return Path(__file__).resolve().parent / SOURCE_NAME


def output_path() -> Path:
    """The grader sets MAKEFUN_OUTPUT_DIR; /output is the fallback."""
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    return out_dir / OUTPUT_NAME


def main() -> int:
    data = source_path().read_bytes()
    if not data:
        raise SystemExit("bundled entry.png is empty")
    fmt = image_format(data)

    dest = output_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)

    written = dest.read_bytes()
    if written != data:
        raise SystemExit(
            f"verification failed: wrote {len(written)} bytes, "
            f"source has {len(data)} bytes at {dest}"
        )

    digest = hashlib.sha256(written).hexdigest()
    print(f"wrote {dest} ({len(written)} bytes, {fmt}, sha256 {digest})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
