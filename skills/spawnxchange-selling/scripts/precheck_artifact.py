#!/usr/bin/env python3
"""Look over an artifact archive before you publish it.

Standard library only. No network access, no credentials, nothing extracted:
this reads one archive and tells you what is in it that you may not want to sell.

It is advisory. It is not the marketplace's safety scan, it does not predict
that scan's verdict, and passing here is not approval — it is one careful look
before you spend a fee and hand your bytes to buyers, who receive them exactly
as you upload them.

Two severities:

  STOP  Something that does not belong in a listing at all: a compiled program,
        an archive nested inside this one, a vendored dependency tree, or an
        archive whose own structure is unsafe.
  LOOK  Something worth a human decision. For each one you are deciding between
        three things: it is a fair part of what you are selling, it is a leak
        you want to remove, or it is something that should not be published.
        Only you can tell those apart.
"""

import argparse
import re
import stat
import struct
import sys
import tarfile
import zipfile
from pathlib import Path

# The API's own upload limit, checked here so a doomed upload fails for free.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

# Directories that carry somebody else's code, your version control history, or a
# build cache. None of it is what a buyer is paying for, all of it bloats the
# archive, and a dependency tree is a common way for something unreviewed to end
# up inside a listing.
VENDORED_DIRS = {
    "node_modules", ".venv", "venv", "vendor", ".git", ".hg", ".svn",
    "__pycache__", ".tox", ".mypy_cache", ".pytest_cache", ".gradle", ".terraform",
    "bower_components", "site-packages",
}
# Build output is sometimes deliberate, so it is raised rather than refused.
BUILD_DIRS = {"dist", "build", "target", "out", ".next", ".nuxt", ".output"}

# How much of any one file is examined. A pre-flight check must not be the thing
# that runs out of memory, and source files are small: a text file larger than
# this is itself worth remarking on, which is what the "too large to be source"
# finding does.
SCAN_BYTES_PER_ENTRY = 128 * 1024
SNIFF_BYTES = 8192

CONTROL_CHAR_CODEPOINTS = frozenset(range(0x20)) | {0x7F}
NUL_BYTE = bytes([0])
WINDOWS_DRIVE_PATTERN = re.compile(r"^[a-zA-Z]:[\\/]")

# What `file` looks for. Executable code is a different finding from binary
# data: a compiled program is dead weight a buyer cannot read or review, while a
# database, an image or a PDF may be exactly what is being sold.
# Android bytecode. The version digits move between platform releases, so each
# is listed rather than matching a bare "dex\n" prefix that a text file could
# begin with.
DEX_SIGNATURES = tuple(
    (bytes.fromhex("6465780a") + version + bytes([0]),
     "an Android DEX executable")
    for version in (b"035", b"037", b"038", b"039", b"040")
)

ELF_MAGIC = bytes.fromhex("7f454c46")
# Mach-O stores its magic in the file's own byte order, so the byte sequence
# gives both the width and the endianness. An iOS or macOS binary is one of
# these; an .ipa or .apk is a zip and is caught as a nested archive.
MACHO_MAGICS = {
    bytes.fromhex("cefaedfe"): ("little", "32-bit"),
    bytes.fromhex("cffaedfe"): ("little", "64-bit"),
    bytes.fromhex("feedface"): ("big", "32-bit"),
    bytes.fromhex("feedfacf"): ("big", "64-bit"),
}
# A COFF object file has no magic number, only a machine type. Recognising one
# needs the header's shape as well: see _coff_object_description.
COFF_MACHINES = {
    0x014C: "x86", 0x8664: "x86-64", 0xAA64: "ARM64", 0x01C0: "ARM",
    0x01C4: "ARM Thumb-2", 0x0200: "Itanium", 0x0166: "MIPS",
    0x01F0: "PowerPC", 0x5032: "RISC-V 32", 0x5064: "RISC-V 64",
}

EXECUTABLE_SIGNATURES = (
    (b"MZ", "a Windows executable or DLL"),
    (bytes.fromhex("cafebabe"), "a Java class or a universal Mach-O binary"),
    (bytes.fromhex("cafebabf"), "a 64-bit universal Mach-O binary"),
    (bytes.fromhex("0061736d"), "a WebAssembly module"),
    (b"!<arch>", "a static library: an archive of object files"),
    (bytes.fromhex("4243c0de"), "LLVM bitcode: compiled, but not yet linked"),
    (bytes.fromhex("edabeedb"), "an RPM package"),
) + DEX_SIGNATURES
# An archive inside an archive: neither you nor the marketplace can see what is
# in it without unpacking it, so it is not something to ship unexamined.
NESTED_ARCHIVE_SIGNATURES = (
    (bytes.fromhex("504b0304"), "a nested zip archive"),
    (bytes.fromhex("1f8b"), "a nested gzip archive"),
    (b"BZh", "a nested bzip2 archive"),
    (bytes.fromhex("fd377a585a"), "a nested xz archive"),
    (bytes.fromhex("377abcaf271c"), "a nested 7-zip archive"),
    (b"Rar!", "a nested RAR archive"),
)
DATA_SIGNATURES = (
    (b"SQLite format 3", "a SQLite database, which may hold rows you did not "
                         "mean to publish"),
    (bytes.fromhex("89504e47"), "a PNG image"),
    (bytes.fromhex("ffd8ff"), "a JPEG image"),
    (b"GIF8", "a GIF image"),
    (b"%PDF", "a PDF"),
    (b"OggS", "an Ogg media file"),
    (bytes.fromhex("1a45dfa3"), "a Matroska or WebM media file"),
    (bytes.fromhex("00010000"), "a TrueType font"),
    (b"OTTO", "an OpenType font"),
    (b"wOF", "a web font"),
)

# Things worth a second look. Deliberately broad: this is a prompt for a human
# decision, not a detector, and a false positive costs you five seconds.
LOOK_PATTERNS = (
    ("private key material (a PEM block)", re.compile(
        r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")),
    ("a 64-character hex value (a key, or a hash)", re.compile(
        r"\b0x[a-fA-F0-9]{64}\b")),
    ("a cloud metadata endpoint", re.compile(
        r"169\.254\.169\.254|metadata\.google\.internal", re.IGNORECASE)),
    ("a cloud access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    # A name that sounds like a credential, assigned a literal that looks like
    # one. The value must be a quoted string or a bare env-file value: that is
    # what keeps `token = rest[index];` from reading as a leak.
    ("an assigned secret, key or token", re.compile(
        r"""(?i)[A-Z0-9_.-]*(?:api[_-]?key|secret|passwd|password|token|"""
        r"""credential)[A-Z0-9_.-]*\s*[:=]\s*"""
        r"""(?:["'][A-Za-z0-9_.\-/+=:]{12,}["']|[A-Za-z0-9_.\-/+=]{12,}\s*$)""",
        re.MULTILINE)),
    ("an email address", re.compile(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("a blockchain address", re.compile(
        r"\b0x[a-fA-F0-9]{40}\b|\bbc1[a-z0-9]{25,59}\b")),
    ("a street address", re.compile(
        r"\b\d+\s+[A-Za-z0-9\s,.-]{3,40}\s+"
        r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|"
        r"Place|Pl|Court|Ct|Parkway|Pkwy|Highway|Hwy)\b", re.IGNORECASE)),
)

# Files whose whole purpose is to hold configuration you did not mean to ship.
SENSITIVE_NAMES = re.compile(
    r"(?:^|/)(?:\.env(?:\..+)?|\.npmrc|\.pypirc|\.netrc|id_rsa|id_ed25519|"
    r"\.aws/credentials|credentials\.json|service-account.*\.json)$",
    re.IGNORECASE,
)


class PrecheckError(Exception):
    """Raised for an archive that cannot be read at all."""


def _elf_description(data):
    """Name an ELF file by its e_type, which separates an object from a program."""
    if len(data) < 18:
        return "an ELF binary"
    order = "little" if data[5] == 1 else "big"
    return {
        1: "an ELF object file, before linking",
        2: "an ELF executable",
        3: "an ELF shared library or position-independent executable",
        4: "an ELF core dump",
    }.get(int.from_bytes(data[16:18], order), "an ELF binary")


def _macho_description(data, order, width):
    """Name a Mach-O file by its filetype field, at a fixed offset of 12."""
    kind = "binary"
    if len(data) >= 16:
        kind = {
            1: "object file, before linking",
            2: "executable",
            6: "dynamic library",
            8: "loadable bundle",
        }.get(int.from_bytes(data[12:16], order), "binary")
    return f"a {width} Mach-O {kind} (macOS or iOS)"


def _coff_object_description(data):
    """Recognise an unlinked Windows object file, which carries no magic number.

    The machine type must be one we know, and the optional-header size must be
    zero: an object file has no optional header, an executable image does. Both
    conditions together are what keeps this from matching arbitrary bytes.
    """
    if len(data) < 20:
        return None
    machine = int.from_bytes(data[0:2], "little")
    if machine not in COFF_MACHINES:
        return None
    if int.from_bytes(data[16:18], "little") != 0:
        return None
    return ("a Windows COFF object file, before linking "
            f"({COFF_MACHINES[machine]})")


def looks_binary(data):
    """Classify a file by content, the way `file` does.

    Returns (description, kind) where kind is "executable", "nested archive" or
    "data", or (None, None) for text. Signatures come first so the message can
    name the thing; otherwise a NUL byte or a high share of non-text bytes is
    what separates a compiled artifact from source. This reads content, not the
    file extension, so renaming does not change the answer.
    """
    if not data:
        return None, None

    if data.startswith(ELF_MAGIC):
        return _elf_description(data), "executable"
    for magic, (order, width) in MACHO_MAGICS.items():
        if data.startswith(magic):
            return _macho_description(data, order, width), "executable"
    for signature, description in EXECUTABLE_SIGNATURES:
        if data.startswith(signature):
            return description, "executable"
    for signature, description in NESTED_ARCHIVE_SIGNATURES:
        if data.startswith(signature):
            return description, "nested archive"
    for signature, description in DATA_SIGNATURES:
        if data.startswith(signature):
            return description, "data"

    coff = _coff_object_description(data)
    if coff:
        return coff, "executable"

    head = data[:SNIFF_BYTES]
    if NUL_BYTE in head:
        return "binary (contains null bytes)", "data"
    printable = sum(
        1 for byte in head
        if byte in (9, 10, 13) or 0x20 <= byte < 0x7F or byte >= 0x80
    )
    if head and printable / len(head) < 0.85:
        return "binary (mostly non-text bytes)", "data"
    return None, None


def normalize_entry_name(raw_name):
    """Return (normalized, problem) for one archive member name."""
    if not raw_name:
        return None, "the archive contains an entry with no name"
    if any(ord(character) in CONTROL_CHAR_CODEPOINTS for character in raw_name):
        return None, f"an entry name contains control characters: {raw_name!r}"
    normalized = raw_name.replace("\\", "/")
    if (normalized.startswith("/") or raw_name.startswith("\\")
            or WINDOWS_DRIVE_PATTERN.match(raw_name)):
        return None, f"an entry is an absolute path: {raw_name}"
    segments = [s for s in normalized.split("/") if s]
    if not segments:
        return None, f"an entry resolves to an empty path: {raw_name}"
    if any(s in (".", "..") for s in segments):
        return None, f"an entry points outside the archive: {raw_name}"
    return "/".join(segments), None


class Entry:
    """One archive member, read in memory. Nothing is ever extracted to disk."""

    def __init__(self, name, size, data):
        self.name = name
        self.size = size
        self.data = data


def _has_embedded_null(raw_archive_bytes, info):
    """Python truncates decoded ZIP names at the first NUL; check raw bytes."""
    try:
        offset = info.header_offset
        if offset + 30 > len(raw_archive_bytes):
            return False
        name_length = struct.unpack_from("<H", raw_archive_bytes, offset + 26)[0]
        if offset + 30 + name_length > len(raw_archive_bytes):
            return False
        raw_name = raw_archive_bytes[offset + 30: offset + 30 + name_length]
    except Exception:
        return False
    return NUL_BYTE in raw_name.rstrip(NUL_BYTE)


def _read_zip(path):
    problems, entries, seen = [], [], set()
    raw = path.read_bytes()
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if _has_embedded_null(raw, info):
                problems.append(f"an entry name contains a null byte: {info.filename}")
                continue
            name, problem = normalize_entry_name(info.filename)
            if problem:
                problems.append(problem)
                continue
            if info.flag_bits & 0x1:
                problems.append(f"an entry is encrypted and cannot be reviewed: {name}")
                continue
            if info.is_dir():
                continue
            mode = (info.external_attr >> 16) & 0xFFFF
            if mode and stat.S_ISLNK(mode):
                problems.append(f"an entry is a symbolic link: {name}")
                continue
            if name in seen:
                problems.append(f"the archive contains the same path twice: {name}")
                continue
            seen.add(name)
            with archive.open(info) as handle:
                entries.append(Entry(name, int(info.file_size or 0),
                                     handle.read(SCAN_BYTES_PER_ENTRY)))
    return problems, entries


def _read_tar(path):
    problems, entries, seen = [], [], set()
    with tarfile.open(path) as archive:
        for member in archive.getmembers():
            name, problem = normalize_entry_name(member.name)
            if problem:
                problems.append(problem)
                continue
            if member.issym() or member.islnk():
                problems.append(f"an entry is a link: {name}")
                continue
            if not member.isfile():
                continue
            if name in seen:
                problems.append(f"the archive contains the same path twice: {name}")
                continue
            seen.add(name)
            handle = archive.extractfile(member)
            entries.append(Entry(name, int(member.size or 0),
                                 handle.read(SCAN_BYTES_PER_ENTRY) if handle else b""))
    return problems, entries


def plural(count):
    return f"{count} file" if count == 1 else f"{count} files"


def directory_of(name, groups):
    """The first path segment of `name` that names one of `groups`."""
    for part in name.split("/")[:-1]:
        if part in groups:
            return part
    return None


def precheck_archive(archive_path):
    """Read the archive and describe what is in it. Returns a plain dict."""
    path = Path(archive_path)
    if not path.is_file():
        raise PrecheckError(f"archive not found: {path}")

    name = path.name.lower()
    try:
        if name.endswith(".zip"):
            problems, entries = _read_zip(path)
        elif name.endswith((".tar.gz", ".tgz")):
            problems, entries = _read_tar(path)
        else:
            raise PrecheckError(
                f"unsupported archive type: {path.name} (use .zip or .tar.gz)")
    except (zipfile.BadZipFile, tarfile.TarError, OSError) as exc:
        raise PrecheckError(f"the archive could not be read: {exc}") from exc

    stop = [("archive structure", problem) for problem in problems]
    look = []

    upload_bytes = path.stat().st_size
    if upload_bytes > MAX_UPLOAD_BYTES:
        stop.append(("too large",
                     f"the archive is {upload_bytes} bytes; the limit is {MAX_UPLOAD_BYTES}"))

    vendored, build = {}, {}
    for entry in entries:
        found = directory_of(entry.name, VENDORED_DIRS)
        if found:
            vendored[found] = vendored.get(found, 0) + 1
            continue
        found = directory_of(entry.name, BUILD_DIRS)
        if found:
            build[found] = build.get(found, 0) + 1
            continue

        description, kind = looks_binary(entry.data)
        if kind in ("executable", "nested archive"):
            stop.append((kind, f"{entry.name} is {description}. A buyer cannot "
                               "read it and nobody can review it."))
            continue
        if kind == "data":
            look.append(("binary file", entry.name, description))
            continue

        # Text, but bigger than source files run. Either it is not really source
        # — a dump, an export, a log, a vendored bundle — or it is, and only its
        # first part was examined. Say so rather than let the truncation pass
        # silently.
        if entry.size > SCAN_BYTES_PER_ENTRY:
            look.append(("a file too large to be source", entry.name,
                         f"{entry.size} bytes; only the first "
                         f"{SCAN_BYTES_PER_ENTRY} were examined"))

        if SENSITIVE_NAMES.search(entry.name):
            look.append(("a file that usually holds credentials", entry.name,
                         "check whether it belongs in a listing at all"))

        text = entry.data.decode("utf-8", errors="ignore")
        for label, pattern in LOOK_PATTERNS:
            match = pattern.search(text)
            if match:
                look.append((label, entry.name, match.group(0)[:80]))

    for directory, count in sorted(vendored.items()):
        stop.append(("vendored code",
                     f"{directory}/ is in the archive ({plural(count)}). Buyers are "
                     "not paying for this, and it hides code nobody reviewed."))
    for directory, count in sorted(build.items()):
        look.append(("build output", f"{directory}/",
                     f"{plural(count)}. Ship it only if a buyer needs it."))

    return {
        "archive": str(path),
        "upload_bytes": upload_bytes,
        "entries": len(entries),
        "stop": stop,
        "look": look,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Look over an artifact archive before publishing it.")
    parser.add_argument("--archive", required=True, help=".zip or .tar.gz to inspect")
    parser.add_argument("--max-examples", type=int, default=5,
                        help="examples to print per category (default 5)")
    args = parser.parse_args()

    try:
        result = precheck_archive(args.archive)
    except PrecheckError as error:
        parser.exit(1, f"error: {error}\n")

    print(f"archive   {result['archive']}")
    print(f"contents  {result['entries']} files, {result['upload_bytes']} bytes")
    print()

    if result["stop"]:
        print(f"STOP  {len(result['stop'])} thing(s) that do not belong in a listing:")
        for label, detail in result["stop"][:args.max_examples * 2]:
            print(f"  [{label}] {detail}")
        print()

    if result["look"]:
        grouped = {}
        for label, where, value in result["look"]:
            grouped.setdefault(label, []).append((where, value))
        print(f"LOOK  {len(result['look'])} thing(s) worth deciding about. For each,")
        print("      is it a fair part of what you are selling, a leak you want to")
        print("      remove, or something that should not be published at all?")
        for label, hits in grouped.items():
            print(f"  {label} ({len(hits)}):")
            for where, value in hits[:args.max_examples]:
                print(f"    {where}: {value}")
            if len(hits) > args.max_examples:
                print(f"    ... and {len(hits) - args.max_examples} more")
        print()

    if not result["stop"] and not result["look"]:
        print("Nothing stood out.")
        print()

    print("This is one careful look, not the marketplace's safety review, and it")
    print("does not predict that review's outcome. Buyers receive this archive")
    print("exactly as you upload it.")

    return 2 if result["stop"] else 0


if __name__ == "__main__":
    sys.exit(main())
