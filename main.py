#!/usr/bin/env python3
"""Deliver the news-image-20261125 entry image to the grader output dir.

The competition entry itself is a finished front-page image, ``entry.png``,
which ships in this repository next to this script.  At grading time there
is nothing to render: the job of this program is to place a byte-exact copy
of that image where the grader looks for it, and to prove -- before it
reports success -- that the copy really is the intended file.

Concretely, a run does four things:

1. Locate the bundled ``entry.png`` (see :func:`find_source`).
2. Sanity-check it: PNG magic bytes first, then a full SHA-256 digest
   compared against the digest recorded when the entry was finalised.
3. Copy it into the output directory under the name ``entry.png``,
   writing to a temporary sibling first so a half-written file can never
   be mistaken for the deliverable.
4. Read the copy back and compare it byte for byte with the source.

Only the Python standard library is used, because the grader runs this
file with a stock ``python:3.13-slim`` interpreter.  Every failure path
prints one clear line to stderr and exits with a distinct non-zero code,
so a broken run is easy to tell apart from a good one in the logs.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# Facts about the entry, recorded when the image was finalised.
# --------------------------------------------------------------------------

ENTRY_FILENAME = "entry.png"

#: SHA-256 of the final entry.png.  If the bundled file ever hashes to
#: anything else, the run refuses to deliver it.
EXPECTED_SHA256 = "8ef53add1d1a2ccc3bcab31496c1bd06451acd587136a0bfb79afdc64f131f1b"

#: The first eight bytes of every PNG file (ISO/IEC 15948 signature).
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

#: Read/write block size for streaming file operations.
CHUNK_SIZE = 64 * 1024

# --------------------------------------------------------------------------
# Exit codes: one per failure mode, 0 only for a verified delivery.
# --------------------------------------------------------------------------

EXIT_OK = 0
EXIT_SOURCE_MISSING = 3
EXIT_NOT_A_PNG = 4
EXIT_DIGEST_MISMATCH = 5
EXIT_COPY_FAILED = 6
EXIT_VERIFY_FAILED = 7


def fail(code: int, message: str) -> int:
    """Print ``message`` to stderr and return ``code`` as the exit status.

    Returning the code instead of raising keeps :func:`main` flat: each
    step either succeeds and the flow continues, or the step's result is
    handed straight back to the interpreter as the process status.
    """
    print(f"error: {message}", file=sys.stderr)
    return code


def sha256_of(path: Path) -> str:
    """Return the hex SHA-256 digest of the file at ``path``.

    The file is streamed in fixed-size blocks so memory use stays flat no
    matter how large the image is.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(CHUNK_SIZE)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def has_png_signature(path: Path) -> bool:
    """Return True when the file at ``path`` starts with the PNG magic.

    This is a cheap tripwire, not a full image decode: it catches the
    classic accidents (an HTML error page saved as ``.png``, a truncated
    download, the wrong file entirely) before the more expensive digest
    comparison runs.
    """
    with path.open("rb") as handle:
        return handle.read(len(PNG_SIGNATURE)) == PNG_SIGNATURE


def find_source() -> Path | None:
    """Work out where the bundled ``entry.png`` lives.

    Two locations are tried, in order:

    * ``$MAKEFUN_BOT_DIR/entry.png`` -- the grader mounts the bot's files
      in a directory it names through this variable, which is not
      necessarily the process working directory;
    * ``entry.png`` next to this script -- the layout used everywhere
      else, including a plain checkout of the repository.

    Returns the first path that exists, or ``None`` when neither does.
    """
    candidates: list[Path] = []
    bot_dir = os.environ.get("MAKEFUN_BOT_DIR")
    if bot_dir:
        candidates.append(Path(bot_dir) / ENTRY_FILENAME)
    candidates.append(Path(__file__).resolve().parent / ENTRY_FILENAME)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def find_output_dir() -> Path:
    """Return the directory the grader expects the entry to appear in.

    ``$MAKEFUN_OUTPUT_DIR`` wins when set; otherwise the conventional
    ``/output`` mount is used.
    """
    named = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if named:
        return Path(named)
    return Path("/output")


def copy_atomically(source: Path, target: Path) -> None:
    """Copy ``source`` to ``target`` via a temporary sibling file.

    The bytes land in ``<target name>.tmp`` first and are flushed to disk;
    only then is the temporary file renamed over the target.  A crash or
    a full disk mid-copy therefore leaves either the old target or no
    target at all -- never a truncated file wearing the right name.

    Raises ``OSError`` on any I/O failure; the caller turns that into an
    exit code.
    """
    temporary = target.with_name(target.name + ".tmp")
    try:
        with source.open("rb") as src, temporary.open("wb") as dst:
            while True:
                block = src.read(CHUNK_SIZE)
                if not block:
                    break
                dst.write(block)
            dst.flush()
            os.fsync(dst.fileno())
        os.replace(temporary, target)
    except OSError:
        # Best effort: do not leave the partial temporary file behind.
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def files_match(first: Path, second: Path) -> bool:
    """Return True when two files hold exactly the same bytes.

    Sizes are compared first (a cheap rejection), then both files are
    streamed side by side and compared block by block, so the check costs
    one pass over the data and almost no memory.
    """
    if first.stat().st_size != second.stat().st_size:
        return False
    with first.open("rb") as fa, second.open("rb") as fb:
        while True:
            block_a = fa.read(CHUNK_SIZE)
            block_b = fb.read(CHUNK_SIZE)
            if block_a != block_b:
                return False
            if not block_a:
                return True


def validate_source(source: Path) -> int | None:
    """Check the bundled image is the intended file.

    Returns ``None`` when the source passes every check, otherwise the
    exit code describing the first failure found.  The signature tripwire
    runs before the digest so that a completely wrong file is reported as
    "not a PNG" rather than as a bare hash mismatch.
    """
    if not has_png_signature(source):
        return fail(
            EXIT_NOT_A_PNG,
            f"{source} does not start with the PNG signature; "
            "the bundled entry is damaged or is not an image at all",
        )
    actual = sha256_of(source)
    if actual != EXPECTED_SHA256:
        return fail(
            EXIT_DIGEST_MISMATCH,
            f"{source} hashes to {actual}, expected {EXPECTED_SHA256}; "
            "refusing to deliver a file that is not the finalised entry",
        )
    return None


def parse_args(argv: list[str]) -> dict[str, object]:
    """Parse the (deliberately tiny) command line.

    Supported options:

    * ``--quiet``           -- suppress the progress lines on stdout;
      errors are still reported on stderr.
    * ``--check``           -- validate the bundled entry and stop: no
      copy is made.  Handy for a smoke test of a fresh checkout.
    * ``--source PATH``     -- deliver this file instead of hunting for
      the bundled entry (used by the foreign-directory smoke tests).
    * ``--output-dir PATH`` -- copy into this directory instead of
      ``$MAKEFUN_OUTPUT_DIR`` / ``/output``.

    Anything unrecognised is ignored rather than fatal: the grader calls
    this script with no arguments, and a stray flag from a wrapper should
    never break a delivery.
    """
    options: dict[str, object] = {
        "quiet": "--quiet" in argv,
        "check_only": "--check" in argv,
        "source": None,
        "output_dir": None,
    }
    for flag, key in (("--source", "source"), ("--output-dir", "output_dir")):
        if flag in argv:
            position = argv.index(flag)
            if position + 1 < len(argv):
                options[key] = Path(argv[position + 1])
    return options


def main(argv: list[str] | None = None) -> int:
    """Run the delivery: locate, validate, copy, verify, report."""
    options = parse_args(list(sys.argv[1:] if argv is None else argv))

    def note(message: str) -> None:
        if not options["quiet"]:
            print(message)

    override = options["source"]
    if isinstance(override, Path):
        if not override.is_file():
            return fail(EXIT_SOURCE_MISSING, f"--source {override} is not a file")
        source: Path | None = override
    else:
        source = find_source()
    if source is None:
        return fail(
            EXIT_SOURCE_MISSING,
            f"could not find {ENTRY_FILENAME}: looked in $MAKEFUN_BOT_DIR "
            "and next to this script",
        )
    note(f"source: {source}")

    problem = validate_source(source)
    if problem is not None:
        return problem
    note(f"validated: PNG signature ok, sha256 {EXPECTED_SHA256[:16]}...")

    if options["check_only"]:
        note("check-only run: nothing copied")
        return EXIT_OK

    named_output = options["output_dir"]
    output_dir = named_output if isinstance(named_output, Path) else find_output_dir()
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return fail(EXIT_COPY_FAILED, f"cannot create {output_dir}: {exc}")
    target = output_dir / ENTRY_FILENAME

    try:
        copy_atomically(source, target)
    except OSError as exc:
        return fail(EXIT_COPY_FAILED, f"copy to {target} failed: {exc}")
    note(f"copied: {target} ({target.stat().st_size} bytes)")

    if not files_match(source, target):
        return fail(
            EXIT_VERIFY_FAILED,
            f"read-back check failed: {target} differs from {source}",
        )
    note("verified: delivered copy is byte-identical to the bundled entry")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
