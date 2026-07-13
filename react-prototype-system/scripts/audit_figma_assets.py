#!/usr/bin/env python3
"""Audit Figma image assets by content and safely fix mismatched suffixes."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Optional


@dataclass(frozen=True)
class AssetFormat:
    name: str
    canonical_suffix: str
    accepted_suffixes: tuple[str, ...]
    mime_type: str


@dataclass
class Finding:
    severity: str
    code: str
    path: str
    message: str
    target: Optional[str] = None


@dataclass(frozen=True)
class RenameRecord:
    source: str
    target: str


FORMATS = {
    "svg": AssetFormat("svg", ".svg", (".svg",), "image/svg+xml"),
    "png": AssetFormat("png", ".png", (".png",), "image/png"),
    "jpeg": AssetFormat(
        "jpeg", ".jpg", (".jpg", ".jpeg", ".jpe", ".jfif"), "image/jpeg"
    ),
    "gif": AssetFormat("gif", ".gif", (".gif",), "image/gif"),
    "webp": AssetFormat("webp", ".webp", (".webp",), "image/webp"),
    "avif": AssetFormat("avif", ".avif", (".avif",), "image/avif"),
    "heif": AssetFormat(
        "heif", ".heic", (".heic", ".heif"), "image/heif"
    ),
    "bmp": AssetFormat("bmp", ".bmp", (".bmp",), "image/bmp"),
    "tiff": AssetFormat("tiff", ".tiff", (".tif", ".tiff"), "image/tiff"),
    "ico": AssetFormat("ico", ".ico", (".ico",), "image/x-icon"),
    "pdf": AssetFormat("pdf", ".pdf", (".pdf",), "application/pdf"),
}

KNOWN_SUFFIXES = frozenset(
    suffix for asset_format in FORMATS.values() for suffix in asset_format.accepted_suffixes
)
SKIP_DIRECTORIES = frozenset(
    {".git", ".next", "build", "dist", "node_modules", "out", "coverage"}
)
SVG_ROOT_PATTERN = re.compile(r"<(?:[A-Za-z_][\w.-]*:)?svg(?:\s|>)", re.IGNORECASE)
SVG_DOCUMENT_PATTERN = re.compile(
    r"\A\s*(?:<\?[^?]*\?>\s*)*(?:<!--.*?-->\s*)*"
    r"<(?:[A-Za-z_][\w.-]*:)?svg(?:\s|>)",
    re.IGNORECASE | re.DOTALL,
)
CSS_URL_PATTERN = re.compile(r"url\(\s*([^)]*?)\s*\)", re.IGNORECASE | re.DOTALL)
CSS_IMPORT_PATTERN = re.compile(r"@import\b", re.IGNORECASE)
CSS_COMMENT_PATTERN = re.compile(r"/\*.*?\*/", re.DOTALL)
SAFE_RASTER_DATA_PATTERN = re.compile(
    r"^data:image/(?:png|jpe?g|gif|webp|avif)(?:;|,)", re.IGNORECASE
)
XML_COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
XML_STYLESHEET_PATTERN = re.compile(r"<\?xml-stylesheet\b", re.IGNORECASE)
XML_ENCODING_PATTERN = re.compile(
    br"<\?xml[^>]*\bencoding\s*=\s*['\"]([^'\"]+)['\"]", re.IGNORECASE
)
DANGEROUS_DECLARATION_PATTERN = re.compile(
    r"<!ENTITY|<!DOCTYPE[^>]*(?:SYSTEM|PUBLIC)", re.IGNORECASE | re.DOTALL
)
TEXT_REFERENCE_SUFFIXES = frozenset(
    {
        ".css",
        ".html",
        ".js",
        ".json",
        ".jsx",
        ".less",
        ".md",
        ".mdx",
        ".mjs",
        ".cjs",
        ".scss",
        ".sass",
        ".ts",
        ".tsx",
        ".toml",
        ".yaml",
        ".yml",
    }
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Detect Figma asset formats from file content, report suffix mismatches, "
            "and audit SVG integrity. The default mode is read-only."
        )
    )
    parser.add_argument("paths", nargs="+", type=Path, help="Asset files or directories")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Rename mismatched files without overwriting existing targets",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit one JSON report instead of human-readable findings",
    )
    parser.add_argument(
        "--references-root",
        action="append",
        default=[],
        type=Path,
        help=(
            "Scan this file or directory for stale references after a rename; "
            "repeat for multiple roots"
        ),
    )
    parser.add_argument(
        "--reference-change",
        action="append",
        default=[],
        metavar="OLD=NEW",
        help=(
            "Recheck a previous rename when no rename occurs in this run; "
            "repeat for multiple changes"
        ),
    )
    return parser.parse_args()


def iter_candidate_files(paths: Iterable[Path]) -> Iterable[Path]:
    seen: set[Path] = set()
    for raw_path in paths:
        path = raw_path.expanduser()
        if not path.exists():
            raise FileNotFoundError(path)

        explicit_file = path.is_file()
        candidates = [path] if explicit_file else path.rglob("*")
        for candidate in candidates:
            if not candidate.is_file() or candidate.is_symlink():
                continue
            if not explicit_file and any(
                part in SKIP_DIRECTORIES for part in candidate.parts
            ):
                continue
            if (
                not explicit_file
                and candidate.suffix.lower() not in KNOWN_SUFFIXES
                and not has_detectable_asset_content(candidate)
            ):
                continue
            identity = candidate.resolve()
            if identity not in seen:
                seen.add(identity)
                yield candidate


def decode_svg_text(data: bytes) -> Optional[str]:
    encodings: list[str] = []
    if data.startswith((b"\x00\x00\xfe\xff", b"\xff\xfe\x00\x00")):
        encodings.append("utf-32")
    elif data.startswith((b"\xfe\xff", b"\xff\xfe")):
        encodings.append("utf-16")
    elif data.startswith(b"\x00\x00\x00<"):
        encodings.append("utf-32-be")
    elif data.startswith(b"<\x00\x00\x00"):
        encodings.append("utf-32-le")
    elif data.startswith(b"\x00<\x00"):
        encodings.append("utf-16-be")
    elif data.startswith(b"<\x00"):
        encodings.append("utf-16-le")
    else:
        declaration = XML_ENCODING_PATTERN.search(data[:1024])
        if declaration:
            try:
                encodings.append(declaration.group(1).decode("ascii"))
            except UnicodeDecodeError:
                pass
    encodings.append("utf-8-sig")

    for encoding in dict.fromkeys(encodings):
        try:
            text = data.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
        prefix = text[:8192]
        if SVG_DOCUMENT_PATTERN.search(prefix) or (
            DANGEROUS_DECLARATION_PATTERN.search(prefix)
            and SVG_ROOT_PATTERN.search(prefix)
        ):
            return text
    return None


def iso_bmff_brands(data: bytes) -> set[bytes]:
    if len(data) < 16 or data[4:8] != b"ftyp":
        return set()
    box_size = int.from_bytes(data[:4], "big")
    if box_size < 16 or box_size > len(data):
        box_size = len(data)
    brands = {data[8:12]}
    brands.update(data[index : index + 4] for index in range(16, box_size - 3, 4))
    return brands


def detect_format(data: bytes) -> tuple[Optional[AssetFormat], Optional[str]]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return FORMATS["png"], None
    if data.startswith(b"\xff\xd8\xff"):
        return FORMATS["jpeg"], None
    if data.startswith((b"GIF87a", b"GIF89a")):
        return FORMATS["gif"], None
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return FORMATS["webp"], None
    if data.startswith(b"%PDF-"):
        return FORMATS["pdf"], None
    if data.startswith(b"BM"):
        return FORMATS["bmp"], None
    if data.startswith((b"II*\x00", b"MM\x00*")):
        return FORMATS["tiff"], None
    if data.startswith(b"\x00\x00\x01\x00"):
        return FORMATS["ico"], None

    brands = iso_bmff_brands(data)
    if brands:
        if brands.intersection({b"avif", b"avis"}):
            return FORMATS["avif"], None
        if brands.intersection(
            {b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"}
        ):
            return FORMATS["heif"], None

    svg_text = decode_svg_text(data)
    if svg_text is not None:
        return FORMATS["svg"], svg_text
    return None, None


def has_detectable_asset_content(path: Path) -> bool:
    try:
        with path.open("rb") as asset_file:
            data = asset_file.read(65536)
    except OSError:
        return False
    asset_format, _ = detect_format(data)
    return asset_format is not None


def local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1].split(":", 1)[-1]


def css_reference_values(value: str) -> Iterable[str]:
    for match in CSS_URL_PATTERN.finditer(value):
        yield match.group(1).strip().strip("'\"").strip()


def is_local_or_safe_embedded_reference(value: str) -> bool:
    return value.startswith("#") or bool(SAFE_RASTER_DATA_PATTERN.match(value))


def audit_svg(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    path_text = str(path)
    declaration_text = XML_COMMENT_PATTERN.sub("", text)

    if XML_STYLESHEET_PATTERN.search(declaration_text):
        findings.append(
            Finding(
                "error",
                "svg-xml-stylesheet",
                path_text,
                "SVG contains an XML stylesheet processing instruction",
            )
        )

    if DANGEROUS_DECLARATION_PATTERN.search(declaration_text):
        findings.append(
            Finding(
                "error",
                "svg-dangerous-declaration",
                path_text,
                "SVG contains an external doctype or entity declaration",
            )
        )
        return findings

    try:
        root = ET.fromstring(text)
    except (ET.ParseError, ValueError) as error:
        findings.append(
            Finding(
                "error",
                "svg-parse-error",
                path_text,
                f"SVG XML cannot be parsed: {error}",
            )
        )
        return findings

    if local_name(root.tag) != "svg":
        findings.append(
            Finding(
                "error",
                "svg-invalid-root",
                path_text,
                "Detected SVG text does not have an <svg> root element",
            )
        )
        return findings

    if not root.tag.startswith("{http://www.w3.org/2000/svg}"):
        findings.append(
            Finding(
                "warning",
                "svg-missing-namespace",
                path_text,
                "SVG root has no standard xmlns declaration; standalone loading may fail",
            )
        )

    viewbox = next(
        (
            value
            for attribute, value in root.attrib.items()
            if local_name(attribute) == "viewBox"
        ),
        None,
    )
    if viewbox is None:
        findings.append(
            Finding(
                "warning",
                "svg-missing-viewbox",
                path_text,
                "SVG has no viewBox; responsive scaling may be incorrect",
            )
        )
    else:
        try:
            values = [float(value) for value in re.split(r"[\s,]+", viewbox.strip())]
        except ValueError:
            values = []
        if (
            len(values) != 4
            or not all(math.isfinite(value) for value in values)
            or values[2] <= 0
            or values[3] <= 0
        ):
            findings.append(
                Finding(
                    "error",
                    "svg-invalid-viewbox",
                    path_text,
                    "SVG viewBox must contain four finite numbers with positive width and height",
                )
            )

    reported: set[tuple[str, str]] = set()
    defined_ids: set[str] = set()
    referenced_ids: set[str] = set()
    for element in root.iter():
        tag = local_name(element.tag)
        tag_lower = tag.lower()
        if tag_lower in {"script", "foreignobject"}:
            key = ("svg-active-content", tag)
            if key not in reported:
                reported.add(key)
                findings.append(
                    Finding(
                        "error",
                        "svg-active-content",
                        path_text,
                        f"SVG contains active <{tag}> content",
                    )
                )

        if tag == "style" and element.text:
            style_text = CSS_COMMENT_PATTERN.sub("", element.text)
            if CSS_IMPORT_PATTERN.search(style_text):
                key = ("svg-external-css-url", "@import")
                if key not in reported:
                    reported.add(key)
                    findings.append(
                        Finding(
                            "error",
                            "svg-external-css-url",
                            path_text,
                            "SVG <style> content contains an external @import",
                        )
                    )
            for reference in css_reference_values(style_text):
                if reference.startswith("#") and len(reference) > 1:
                    referenced_ids.add(reference[1:])
                elif reference and not is_local_or_safe_embedded_reference(reference):
                    key = ("svg-external-css-url", reference)
                    if key not in reported:
                        reported.add(key)
                        findings.append(
                            Finding(
                                "error",
                                "svg-external-css-url",
                                path_text,
                                f"SVG <style> content references external URL: {reference}",
                            )
                        )

        for raw_name, value in element.attrib.items():
            attribute = local_name(raw_name)
            normalized_value = value.strip()
            if attribute == "id" and normalized_value:
                if normalized_value in defined_ids:
                    key = ("svg-duplicate-id", normalized_value)
                    if key not in reported:
                        reported.add(key)
                        findings.append(
                            Finding(
                                "error",
                                "svg-duplicate-id",
                                path_text,
                                f"SVG defines duplicate id #{normalized_value}",
                            )
                        )
                defined_ids.add(normalized_value)
            if attribute in {"href", "src"}:
                if normalized_value.startswith("#") and len(normalized_value) > 1:
                    referenced_ids.add(normalized_value[1:])
                elif normalized_value and not is_local_or_safe_embedded_reference(
                    normalized_value
                ):
                    key = ("svg-external-reference", normalized_value)
                    if key not in reported:
                        reported.add(key)
                        findings.append(
                            Finding(
                                "error",
                                "svg-external-reference",
                                path_text,
                                (
                                    "SVG references external or active content: "
                                    f"{normalized_value}"
                                ),
                            )
                        )
            if attribute.lower().startswith("on"):
                key = ("svg-event-handler", attribute)
                if key not in reported:
                    reported.add(key)
                    findings.append(
                        Finding(
                            "error",
                            "svg-event-handler",
                            path_text,
                            f"SVG contains event-handler attribute {attribute}",
                        )
                    )
            for reference in css_reference_values(normalized_value):
                if reference.startswith("#") and len(reference) > 1:
                    referenced_ids.add(reference[1:])
                elif reference and not is_local_or_safe_embedded_reference(reference):
                    key = ("svg-external-css-url", reference)
                    if key not in reported:
                        reported.add(key)
                        findings.append(
                            Finding(
                                "error",
                                "svg-external-css-url",
                                path_text,
                                f"SVG style references external URL: {reference}",
                            )
                        )

    for reference in sorted(referenced_ids - defined_ids):
        findings.append(
            Finding(
                "error",
                "svg-missing-id-reference",
                path_text,
                f"SVG references missing internal id #{reference}",
            )
        )
    return findings


def png_integrity_problem(data: bytes) -> Optional[str]:
    if len(data) < 33 or data[12:16] != b"IHDR":
        return "PNG is missing a complete IHDR header"

    offset = 8
    chunk_index = 0
    saw_idat = False
    allowed_depths = {
        0: {1, 2, 4, 8, 16},
        2: {8, 16},
        3: {1, 2, 4, 8},
        4: {8, 16},
        6: {8, 16},
    }
    while offset + 12 <= len(data):
        length = int.from_bytes(data[offset : offset + 4], "big")
        chunk_end = offset + 12 + length
        if chunk_end > len(data):
            return "PNG contains a truncated chunk"

        chunk_type = data[offset + 4 : offset + 8]
        chunk_data = data[offset + 8 : offset + 8 + length]
        expected_crc = int.from_bytes(data[offset + 8 + length : chunk_end], "big")
        actual_crc = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            return f"PNG chunk {chunk_type.decode('ascii', errors='replace')} has an invalid CRC"
        if chunk_index == 0 and (chunk_type != b"IHDR" or length != 13):
            return "PNG does not begin with a valid IHDR chunk"
        if chunk_type == b"IHDR":
            if chunk_index != 0:
                return "PNG contains more than one IHDR chunk"
            width = int.from_bytes(chunk_data[:4], "big")
            height = int.from_bytes(chunk_data[4:8], "big")
            bit_depth = chunk_data[8]
            color_type = chunk_data[9]
            if width == 0 or height == 0:
                return "PNG IHDR has zero width or height"
            if bit_depth not in allowed_depths.get(color_type, set()):
                return "PNG IHDR has an invalid bit-depth and color-type combination"
            if chunk_data[10] != 0 or chunk_data[11] != 0 or chunk_data[12] not in {0, 1}:
                return "PNG IHDR uses unsupported compression, filter, or interlace values"
        elif chunk_type == b"IDAT":
            saw_idat = True
        if chunk_type == b"IEND":
            if length != 0:
                return "PNG has an invalid IEND chunk"
            if not saw_idat:
                return "PNG contains no image-data chunk"
            return None

        chunk_index += 1
        offset = chunk_end

    return "PNG has no complete IEND chunk"


def jpeg_integrity_problem(data: bytes) -> Optional[str]:
    if len(data) < 4 or not data.startswith(b"\xff\xd8"):
        return "JPEG is missing its SOI marker"

    sof_markers = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
    offset = 2
    saw_sof = False
    while offset < len(data):
        if data[offset] != 0xFF:
            return "JPEG contains data before its scan header"
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset >= len(data):
            return "JPEG ends inside a marker"

        marker = data[offset]
        offset += 1
        if marker == 0xD9:
            return "JPEG reaches EOI before defining image data"
        if marker == 0x00 or 0xD0 <= marker <= 0xD8 or marker == 0x01:
            continue
        if offset + 2 > len(data):
            return "JPEG contains a truncated segment length"

        segment_length = int.from_bytes(data[offset : offset + 2], "big")
        if segment_length < 2:
            return "JPEG contains an invalid segment length"
        segment_end = offset + segment_length
        if segment_end > len(data):
            return "JPEG contains a truncated segment"
        payload = data[offset + 2 : segment_end]

        if marker in sof_markers:
            if len(payload) < 6:
                return "JPEG contains a truncated frame header"
            height = int.from_bytes(payload[1:3], "big")
            width = int.from_bytes(payload[3:5], "big")
            if width == 0 or height == 0:
                return "JPEG frame has zero width or height"
            saw_sof = True
        if marker == 0xDA:
            if not saw_sof:
                return "JPEG scan appears before a frame header"
            if len(payload) < 4:
                return "JPEG contains a truncated scan header"
            scan_offset = segment_end
            while scan_offset + 1 < len(data):
                marker_offset = data.find(b"\xff", scan_offset)
                if marker_offset < 0 or marker_offset + 1 >= len(data):
                    break
                next_byte = data[marker_offset + 1]
                if next_byte == 0x00 or 0xD0 <= next_byte <= 0xD7:
                    scan_offset = marker_offset + 2
                    continue
                if next_byte == 0xD9:
                    return None
                scan_offset = marker_offset + 2
            return "JPEG has no final EOI marker"

        offset = segment_end

    return "JPEG contains no scan data"


def skip_gif_sub_blocks(data: bytes, offset: int) -> tuple[int, Optional[str]]:
    while True:
        if offset >= len(data):
            return offset, "GIF ends inside a data sub-block"
        block_size = data[offset]
        offset += 1
        if block_size == 0:
            return offset, None
        if offset + block_size > len(data):
            return offset, "GIF contains a truncated data sub-block"
        offset += block_size


def gif_integrity_problem(data: bytes) -> Optional[str]:
    if len(data) < 13:
        return "GIF is shorter than its logical screen header"
    width = int.from_bytes(data[6:8], "little")
    height = int.from_bytes(data[8:10], "little")
    if width == 0 or height == 0:
        return "GIF logical screen has zero width or height"

    offset = 13
    packed = data[10]
    if packed & 0x80:
        offset += 3 * (2 ** ((packed & 0x07) + 1))
    if offset > len(data):
        return "GIF contains a truncated global color table"

    saw_image = False
    while offset < len(data):
        introducer = data[offset]
        if introducer == 0x3B:
            return None if saw_image else "GIF contains no image descriptor"
        if introducer == 0x21:
            if offset + 2 > len(data):
                return "GIF contains a truncated extension"
            offset, problem = skip_gif_sub_blocks(data, offset + 2)
            if problem:
                return problem
            continue
        if introducer == 0x2C:
            if offset + 10 > len(data):
                return "GIF contains a truncated image descriptor"
            image_width = int.from_bytes(data[offset + 5 : offset + 7], "little")
            image_height = int.from_bytes(data[offset + 7 : offset + 9], "little")
            if image_width == 0 or image_height == 0:
                return "GIF image descriptor has zero width or height"
            image_packed = data[offset + 9]
            offset += 10
            if image_packed & 0x80:
                offset += 3 * (2 ** ((image_packed & 0x07) + 1))
            if offset >= len(data):
                return "GIF is missing image LZW data"
            lzw_code_size = data[offset]
            if not 2 <= lzw_code_size <= 8:
                return "GIF has an invalid LZW minimum code size"
            offset, problem = skip_gif_sub_blocks(data, offset + 1)
            if problem:
                return problem
            saw_image = True
            continue
        return f"GIF contains unknown block introducer 0x{introducer:02x}"

    return "GIF has no trailer"


def webp_integrity_problem(data: bytes) -> Optional[str]:
    if len(data) < 20:
        return "WebP is shorter than its required container header"
    container_end = int.from_bytes(data[4:8], "little") + 8
    if container_end > len(data):
        return "WebP RIFF container is truncated"
    if container_end < 20:
        return "WebP RIFF container has an invalid size"

    offset = 12
    saw_image_payload = False
    while offset < container_end:
        if offset + 8 > container_end:
            return "WebP contains a truncated chunk header"
        chunk_type = data[offset : offset + 4]
        chunk_size = int.from_bytes(data[offset + 4 : offset + 8], "little")
        chunk_end = offset + 8 + chunk_size
        if chunk_end > container_end:
            return "WebP contains a truncated chunk"
        chunk_data = data[offset + 8 : chunk_end]
        if chunk_type == b"VP8 ":
            if len(chunk_data) < 10 or chunk_data[3:6] != b"\x9d\x01\x2a":
                return "WebP contains an invalid VP8 frame header"
            width = int.from_bytes(chunk_data[6:8], "little") & 0x3FFF
            height = int.from_bytes(chunk_data[8:10], "little") & 0x3FFF
            if width == 0 or height == 0:
                return "WebP VP8 frame has zero width or height"
            saw_image_payload = True
        elif chunk_type == b"VP8L":
            if len(chunk_data) < 5 or chunk_data[0] != 0x2F:
                return "WebP contains an invalid VP8L frame header"
            if int.from_bytes(chunk_data[1:5], "little") >> 29:
                return "WebP VP8L frame uses an unsupported version"
            saw_image_payload = True
        elif chunk_type == b"ANMF":
            if len(chunk_data) < 24 or chunk_data[16:20] not in {b"VP8 ", b"VP8L"}:
                return "WebP contains an invalid animated frame"
            saw_image_payload = True
        offset = chunk_end + (chunk_size % 2)
    if offset != container_end:
        return "WebP chunk padding exceeds its RIFF container"
    if not saw_image_payload:
        return "WebP contains no image payload"
    return None


def iso_bmff_integrity_problem(data: bytes) -> Optional[str]:
    offset = 0
    box_types: set[bytes] = set()
    while offset < len(data):
        if offset + 8 > len(data):
            return "ISO-BMFF image contains a truncated box header"
        box_size = int.from_bytes(data[offset : offset + 4], "big")
        box_type = data[offset + 4 : offset + 8]
        header_size = 8
        if box_size == 1:
            if offset + 16 > len(data):
                return "ISO-BMFF image contains a truncated extended box size"
            box_size = int.from_bytes(data[offset + 8 : offset + 16], "big")
            header_size = 16
        elif box_size == 0:
            box_size = len(data) - offset
        if box_size < header_size or offset + box_size > len(data):
            return "ISO-BMFF image contains an invalid or truncated box"
        if offset == 0 and (box_type != b"ftyp" or box_size < 16):
            return "ISO-BMFF image does not begin with a valid ftyp box"
        box_types.add(box_type)
        offset += box_size
    if not box_types.intersection({b"meta", b"moov"}):
        return "ISO-BMFF image contains no metadata or movie box"
    return None


def bmp_integrity_problem(data: bytes) -> Optional[str]:
    if len(data) < 26:
        return "BMP is shorter than its file and DIB headers"
    declared_size = int.from_bytes(data[2:6], "little")
    pixel_offset = int.from_bytes(data[10:14], "little")
    dib_size = int.from_bytes(data[14:18], "little")
    if declared_size and declared_size > len(data):
        return "BMP file data is truncated"
    if dib_size < 12 or 14 + dib_size > len(data):
        return "BMP contains an invalid or truncated DIB header"
    if pixel_offset < 14 + dib_size or pixel_offset >= len(data):
        return "BMP has an invalid pixel-data offset"
    return None


def tiff_integrity_problem(data: bytes) -> Optional[str]:
    if len(data) < 10:
        return "TIFF is shorter than its first image directory"
    byteorder = "little" if data.startswith(b"II*\x00") else "big"
    ifd_offset = int.from_bytes(data[4:8], byteorder)
    if ifd_offset < 8 or ifd_offset + 2 > len(data):
        return "TIFF has an invalid first image-directory offset"
    entry_count = int.from_bytes(data[ifd_offset : ifd_offset + 2], byteorder)
    if ifd_offset + 2 + entry_count * 12 + 4 > len(data):
        return "TIFF contains a truncated first image directory"
    return None


def ico_integrity_problem(data: bytes) -> Optional[str]:
    if len(data) < 22:
        return "ICO is shorter than its header and first directory entry"
    image_count = int.from_bytes(data[4:6], "little")
    directory_end = 6 + image_count * 16
    if image_count == 0 or directory_end > len(data):
        return "ICO has an invalid or truncated image directory"
    for offset in range(6, directory_end, 16):
        image_size = int.from_bytes(data[offset + 8 : offset + 12], "little")
        image_offset = int.from_bytes(data[offset + 12 : offset + 16], "little")
        if (
            image_size == 0
            or image_offset < directory_end
            or image_offset + image_size > len(data)
        ):
            return "ICO contains an invalid or truncated image entry"
    return None


def audit_binary_integrity(
    path: Path, data: bytes, asset_format: AssetFormat
) -> list[Finding]:
    problem: Optional[str] = None
    if asset_format.name == "png":
        problem = png_integrity_problem(data)
    elif asset_format.name == "jpeg":
        problem = jpeg_integrity_problem(data)
    elif asset_format.name == "gif":
        problem = gif_integrity_problem(data)
    elif asset_format.name == "webp":
        problem = webp_integrity_problem(data)
    elif asset_format.name == "bmp":
        problem = bmp_integrity_problem(data)
    elif asset_format.name == "tiff":
        problem = tiff_integrity_problem(data)
    elif asset_format.name == "ico":
        problem = ico_integrity_problem(data)
    elif asset_format.name in {"avif", "heif"}:
        problem = iso_bmff_integrity_problem(data)
    elif asset_format.name == "pdf" and not data.rstrip().endswith(b"%%EOF"):
        problem = "PDF has no final EOF marker and may be truncated"

    if problem is None:
        return []
    return [
        Finding(
            "error",
            f"{asset_format.name}-integrity",
            str(path),
            problem,
        )
    ]


def normalized_target(path: Path, asset_format: AssetFormat) -> Path:
    base = path
    while base.suffix.lower() in KNOWN_SUFFIXES:
        base = base.with_suffix("")
    return base.with_suffix(asset_format.canonical_suffix)


def rename_without_overwrite(source: Path, target: Path) -> None:
    os.link(source, target, follow_symlinks=False)
    try:
        source.unlink()
    except OSError:
        try:
            if os.path.samestat(source.stat(), target.stat()):
                target.unlink()
        except OSError:
            pass
        raise


def parse_reference_changes(values: Iterable[str]) -> list[RenameRecord]:
    records: list[RenameRecord] = []
    for value in values:
        source, separator, target = value.partition("=")
        source = source.strip()
        target = target.strip()
        if not separator or not source or not target or source == target:
            raise ValueError(
                f"Invalid reference change {value!r}; expected distinct OLD=NEW paths"
            )
        records.append(RenameRecord(source, target))
    return records


def iter_reference_files(paths: Iterable[Path]) -> Iterable[Path]:
    seen: set[Path] = set()
    for raw_path in paths:
        path = raw_path.expanduser()
        if not path.exists():
            raise FileNotFoundError(path)

        explicit_file = path.is_file()
        candidates = [path] if explicit_file else path.rglob("*")
        for candidate in candidates:
            if not candidate.is_file() or candidate.is_symlink():
                continue
            if not explicit_file and any(
                part in SKIP_DIRECTORIES for part in candidate.parts
            ):
                continue
            if candidate.suffix.lower() not in TEXT_REFERENCE_SUFFIXES:
                continue
            identity = candidate.resolve()
            if identity not in seen:
                seen.add(identity)
                yield candidate


def reference_needles(record: RenameRecord, root: Path) -> list[str]:
    source = Path(record.source).expanduser()
    root_dir = root if root.is_dir() else root.parent
    needles = {source.as_posix(), source.name}

    try:
        relative = source.resolve().relative_to(root_dir.resolve()).as_posix()
    except (OSError, ValueError):
        relative = source.as_posix().lstrip("./")
    if relative:
        needles.update({relative, f"./{relative}", f"/{relative}"})
    return sorted((value for value in needles if value), key=len, reverse=True)


def basename_is_ambiguous(root: Path, record: RenameRecord) -> bool:
    root_dir = root if root.is_dir() else root.parent
    source = Path(record.source).expanduser()
    try:
        source_identity = source.resolve()
    except OSError:
        source_identity = source
    for candidate in root_dir.rglob(source.name):
        try:
            if candidate.resolve() != source_identity:
                return True
        except OSError:
            continue
    return False


def audit_stale_references(
    roots: Iterable[Path], records: Iterable[RenameRecord]
) -> tuple[list[Finding], int]:
    root_list = list(roots)
    record_list = list(dict.fromkeys(records))
    files = sorted(iter_reference_files(root_list))
    findings: list[Finding] = []

    for candidate in files:
        try:
            text = candidate.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for record in record_list:
            matching_roots = [
                root
                for root in root_list
                if (root if root.is_dir() else root.parent) in candidate.parents
                or candidate == root
            ]
            root = matching_roots[0] if matching_roots else root_list[0]
            needles = reference_needles(record, root)
            ambiguous_basename = basename_is_ambiguous(root, record)
            for line_number, line in enumerate(text.splitlines(), start=1):
                matched = next((needle for needle in needles if needle in line), None)
                if matched is None:
                    continue
                basename_only = matched == Path(record.source).name
                severity = "warning" if basename_only and ambiguous_basename else "error"
                code = (
                    "possible-stale-asset-reference"
                    if severity == "warning"
                    else "stale-asset-reference"
                )
                findings.append(
                    Finding(
                        severity,
                        code,
                        str(candidate),
                        (
                            f"Line {line_number} references renamed asset "
                            f"{record.source}"
                        ),
                        record.target,
                    )
                )
    return findings, len(files)


def inspect_file(
    path: Path, fix: bool
) -> tuple[list[Finding], Optional[RenameRecord]]:
    findings: list[Finding] = []
    rename_record: Optional[RenameRecord] = None

    try:
        data = path.read_bytes()
    except OSError as error:
        return (
            [Finding("error", "read-error", str(path), f"Cannot read file: {error}")],
            rename_record,
        )

    asset_format, svg_text = detect_format(data)
    suffix = path.suffix.lower()
    if asset_format is None:
        findings.append(
            Finding(
                "error",
                "unknown-or-corrupt-format",
                str(path),
                "Selected asset content is unsupported or corrupt",
            )
        )
        return findings, rename_record

    if asset_format.name == "svg" and svg_text is not None:
        content_findings = audit_svg(path, svg_text)
    else:
        content_findings = audit_binary_integrity(path, data, asset_format)

    if suffix not in asset_format.accepted_suffixes:
        target = normalized_target(path, asset_format)
        if not fix:
            findings.append(
                Finding(
                    "error",
                    "suffix-mismatch",
                    str(path),
                    (
                        f"Suffix {suffix or '<none>'} does not match detected "
                        f"{asset_format.name} content ({asset_format.mime_type})"
                    ),
                    str(target),
                )
            )
        elif any(item.severity == "error" for item in content_findings):
            findings.append(
                Finding(
                    "error",
                    "fix-skipped-content-errors",
                    str(path),
                    "Cannot fix suffix until content-integrity errors are resolved",
                    str(target),
                )
            )
        else:
            try:
                rename_without_overwrite(path, target)
            except FileExistsError:
                findings.append(
                    Finding(
                        "error",
                        "rename-conflict",
                        str(path),
                        "Cannot fix suffix because the target path already exists",
                        str(target),
                    )
                )
            except OSError as error:
                findings.append(
                    Finding(
                        "error",
                        "rename-error",
                        str(path),
                        f"Cannot rename file: {error}",
                        str(target),
                    )
                )
            else:
                rename_record = RenameRecord(str(path), str(target))
                for item in content_findings:
                    item.path = str(target)
                findings.append(
                    Finding(
                        "info",
                        "renamed",
                        str(path),
                        (
                            f"Renamed to match detected {asset_format.name} content "
                            f"({asset_format.mime_type})"
                        ),
                        str(target),
                    )
                )

    findings.extend(content_findings)
    return findings, rename_record


def render_human(
    findings: list[Finding], checked: int, renamed: int, references_checked: int
) -> None:
    for finding in findings:
        target = f" -> {finding.target}" if finding.target else ""
        print(
            f"{finding.severity.upper()} {finding.code}: "
            f"{finding.path}{target}: {finding.message}"
        )
    errors = sum(finding.severity == "error" for finding in findings)
    warnings = sum(finding.severity == "warning" for finding in findings)
    print(
        f"Checked {checked} asset(s); renamed {renamed}; "
        f"reference files {references_checked}; errors {errors}; warnings {warnings}"
    )


def main() -> int:
    args = parse_args()
    try:
        rename_records = parse_reference_changes(args.reference_change)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    if rename_records and not args.references_root:
        print("--reference-change requires --references-root", file=sys.stderr)
        return 2

    try:
        files = sorted(iter_candidate_files(args.paths))
    except FileNotFoundError as error:
        print(f"Path not found: {error}", file=sys.stderr)
        return 2

    findings: list[Finding] = []
    renamed = 0
    for path in files:
        file_findings, rename_record = inspect_file(path, args.fix)
        findings.extend(file_findings)
        if rename_record is not None:
            rename_records.append(rename_record)
            renamed += 1

    references_checked = 0
    if args.references_root:
        if not rename_records:
            findings.append(
                Finding(
                    "error",
                    "reference-scan-no-renames",
                    ", ".join(str(path) for path in args.references_root),
                    (
                        "Reference scanning requires a rename from --fix or an "
                        "explicit --reference-change OLD=NEW"
                    ),
                )
            )
        else:
            try:
                reference_findings, references_checked = audit_stale_references(
                    args.references_root, rename_records
                )
            except FileNotFoundError as error:
                print(f"Reference root not found: {error}", file=sys.stderr)
                return 2
            findings.extend(reference_findings)

    if args.json:
        print(
            json.dumps(
                {
                    "checked": len(files),
                    "renamed": renamed,
                    "referencesChecked": references_checked,
                    "renameRecords": [asdict(record) for record in rename_records],
                    "errors": sum(item.severity == "error" for item in findings),
                    "warnings": sum(item.severity == "warning" for item in findings),
                    "findings": [asdict(item) for item in findings],
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        render_human(findings, len(files), renamed, references_checked)

    return 1 if any(item.severity == "error" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
