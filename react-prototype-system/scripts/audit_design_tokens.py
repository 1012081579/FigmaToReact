#!/usr/bin/env python3
"""Audit a project-local Figma-to-Tailwind design-token evidence manifest."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional


ACCESS_LEVELS = {"complete", "partial", "screenshot-only", "unavailable"}
SEMANTIC_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CSS_VARIABLE_PATTERN = re.compile(r"^--[a-z0-9]+(?:-[a-z0-9]+)*$")
ARBITRARY_VISUAL_UTILITY_PATTERN = re.compile(
    r"(?<![\w-])(?:[\w-]+:)*(?:"
    r"bg|text|border(?:-[trblxy])?|fill|stroke|shadow|rounded(?:-[trbl])?|"
    r"ring|outline|divide|accent|caret|decoration|font|leading|tracking|"
    r"p[trblxy]?|m[trblxy]?|gap[xy]?|space-[xy]|w|min-w|max-w|h|min-h|max-h|size"
    r")-\[[^\]\r\n]+\]"
)
RAW_PALETTE_UTILITY_PATTERN = re.compile(
    r"(?<![\w-])(?:[\w-]+:)*(?:bg|text|border|fill|stroke|ring|outline|"
    r"divide|accent|caret|decoration)-(?:slate|gray|zinc|neutral|stone|red|"
    r"orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|"
    r"violet|purple|fuchsia|pink|rose)-(?:950|900|800|700|600|500|400|300|"
    r"200|100|50)(?!\d)(?:/\d+)?"
)
RAW_COLOR_LITERAL_PATTERN = re.compile(
    r"(?<![\w-])#[0-9a-fA-F]{3,8}\b|"
    r"\b(?:rgb|rgba|hsl|hsla|oklch|oklab|lab|lch|color)\([^\r\n)]*\)"
)


@dataclass
class Finding:
    severity: str
    code: str
    location: str
    message: str


@dataclass(frozen=True)
class AuditCounts:
    tokens: int = 0
    consumers: int = 0
    exceptions: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a Figma design-token manifest and prove that declared "
            "semantic usages exist in project consumer files."
        )
    )
    parser.add_argument("manifest", type=Path, help="Path to the JSON token manifest")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Project root used to resolve consumer files (default: current directory)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit one JSON report instead of human-readable findings",
    )
    return parser.parse_args()


def add(
    findings: list[Finding], severity: str, code: str, location: str, message: str
) -> None:
    findings.append(Finding(severity, code, location, message))


def require_object(
    value: Any, findings: list[Finding], location: str
) -> Optional[dict[str, Any]]:
    if not isinstance(value, dict):
        add(findings, "error", "expected-object", location, "Must be a JSON object")
        return None
    return value


def require_list(
    value: Any, findings: list[Finding], location: str
) -> Optional[list[Any]]:
    if not isinstance(value, list):
        add(findings, "error", "expected-list", location, "Must be a JSON array")
        return None
    return value


def require_string(
    owner: dict[str, Any], key: str, findings: list[Finding], location: str
) -> Optional[str]:
    value = owner.get(key)
    field_location = f"{location}.{key}"
    if not isinstance(value, str) or not value.strip():
        add(
            findings,
            "error",
            "expected-string",
            field_location,
            "Must be a non-empty string",
        )
        return None
    return value.strip()


def resolve_consumer(
    root: Path, raw_path: str, findings: list[Finding], location: str
) -> Optional[Path]:
    relative = Path(raw_path)
    if relative.is_absolute():
        add(
            findings,
            "error",
            "absolute-consumer-path",
            location,
            "Consumer paths must be relative to --root",
        )
        return None

    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        add(
            findings,
            "error",
            "consumer-outside-root",
            location,
            "Consumer path resolves outside --root",
        )
        return None
    return candidate


def read_consumer(
    path: Path,
    cache: dict[Path, Optional[str]],
    findings: list[Finding],
    location: str,
) -> Optional[str]:
    if path in cache:
        return cache[path]
    if not path.is_file():
        add(
            findings,
            "error",
            "missing-consumer-file",
            location,
            f"Consumer file does not exist: {path}",
        )
        cache[path] = None
        return None
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        add(
            findings,
            "error",
            "consumer-read-error",
            location,
            f"Cannot read consumer file: {error}",
        )
        cache[path] = None
        return None
    cache[path] = content
    return content


def audit_token(
    token: Any,
    index: int,
    modes: list[str],
    root: Path,
    cache: dict[Path, Optional[str]],
    consumer_paths: set[Path],
    findings: list[Finding],
) -> tuple[Optional[str], Optional[str], Optional[str], int]:
    location = f"tokens[{index}]"
    item = require_object(token, findings, location)
    if item is None:
        return None, None, None, 0

    source_name = require_string(item, "sourceName", findings, location)
    require_string(item, "category", findings, location)
    semantic_name = require_string(item, "semanticName", findings, location)
    css_variable = require_string(item, "cssVariable", findings, location)

    if semantic_name and not SEMANTIC_NAME_PATTERN.fullmatch(semantic_name):
        add(
            findings,
            "error",
            "invalid-semantic-name",
            f"{location}.semanticName",
            "Use lowercase semantic kebab-case",
        )
    if css_variable and not CSS_VARIABLE_PATTERN.fullmatch(css_variable):
        add(
            findings,
            "error",
            "invalid-css-variable",
            f"{location}.cssVariable",
            "Use a lowercase CSS custom property such as --color-surface-primary",
        )

    utilities_value = require_list(item.get("utilities"), findings, f"{location}.utilities")
    utilities: list[str] = []
    if utilities_value is not None:
        for utility_index, utility in enumerate(utilities_value):
            utility_location = f"{location}.utilities[{utility_index}]"
            if not isinstance(utility, str) or not utility.strip():
                add(
                    findings,
                    "error",
                    "invalid-utility",
                    utility_location,
                    "Utility must be a non-empty string",
                )
                continue
            utility = utility.strip()
            if any(character.isspace() for character in utility):
                add(
                    findings,
                    "error",
                    "invalid-utility",
                    utility_location,
                    "Declare one utility per entry",
                )
            if "[" in utility or "]" in utility:
                add(
                    findings,
                    "error",
                    "arbitrary-token-utility",
                    utility_location,
                    "Arbitrary-value utilities are not semantic-token evidence",
                )
            utilities.append(utility)
        if not utilities:
            add(
                findings,
                "error",
                "missing-token-utilities",
                f"{location}.utilities",
                "Declare at least one semantic utility",
            )
        if len(utilities) != len(set(utilities)):
            add(
                findings,
                "error",
                "duplicate-token-utility",
                f"{location}.utilities",
                "Utilities must be unique within a token",
            )

    values = require_object(item.get("values"), findings, f"{location}.values")
    if values is not None:
        for mode in modes:
            if mode not in values or values[mode] is None:
                add(
                    findings,
                    "error",
                    "missing-mode-value",
                    f"{location}.values",
                    f"Missing value for declared mode {mode!r}",
                )
        for extra_mode in sorted(set(values) - set(modes)):
            add(
                findings,
                "warning",
                "undeclared-value-mode",
                f"{location}.values.{extra_mode}",
                "Value uses a mode not declared in theme.modes",
            )

    consumers_value = require_list(
        item.get("consumers"), findings, f"{location}.consumers"
    )
    consumer_count = 0
    if consumers_value is not None:
        if not consumers_value:
            add(
                findings,
                "error",
                "missing-token-consumer",
                f"{location}.consumers",
                "Declare at least one exact consumer",
            )
        for consumer_index, consumer in enumerate(consumers_value):
            consumer_location = f"{location}.consumers[{consumer_index}]"
            consumer_item = require_object(consumer, findings, consumer_location)
            if consumer_item is None:
                continue
            file_name = require_string(
                consumer_item, "file", findings, consumer_location
            )
            require_string(consumer_item, "property", findings, consumer_location)
            usage = require_string(consumer_item, "usage", findings, consumer_location)
            consumer_count += 1

            if usage:
                if "[" in usage or "]" in usage:
                    add(
                        findings,
                        "error",
                        "arbitrary-consumer-usage",
                        f"{consumer_location}.usage",
                        "Arbitrary values require an exception, not token-consumer evidence",
                    )
                allowed_usage = usage in utilities or bool(
                    css_variable and css_variable in usage
                )
                if not allowed_usage:
                    add(
                        findings,
                        "error",
                        "undeclared-consumer-usage",
                        f"{consumer_location}.usage",
                        "Usage must be a declared utility or reference the token CSS variable",
                    )

            if not file_name:
                continue
            path = resolve_consumer(
                root, file_name, findings, f"{consumer_location}.file"
            )
            if path is None:
                continue
            consumer_paths.add(path)
            content = read_consumer(path, cache, findings, consumer_location)
            if content is not None and usage and usage not in content:
                add(
                    findings,
                    "error",
                    "consumer-usage-not-found",
                    consumer_location,
                    f"Declared usage {usage!r} is absent from {file_name}",
                )

    return source_name, semantic_name, css_variable, consumer_count


def audit_exception(
    exception: Any,
    index: int,
    root: Path,
    cache: dict[Path, Optional[str]],
    findings: list[Finding],
) -> Optional[tuple[Path, str]]:
    location = f"exceptions[{index}]"
    item = require_object(exception, findings, location)
    if item is None:
        return None

    file_name = require_string(item, "file", findings, location)
    require_string(item, "property", findings, location)
    literal = require_string(item, "literal", findings, location)
    require_string(item, "sourceEvidence", findings, location)
    require_string(item, "reason", findings, location)

    if not file_name:
        return None
    path = resolve_consumer(root, file_name, findings, f"{location}.file")
    if path is None:
        return None
    content = read_consumer(path, cache, findings, location)
    if content is not None and literal and literal not in content:
        add(
            findings,
            "error",
            "exception-literal-not-found",
            location,
            f"Declared literal {literal!r} is absent from {file_name}",
        )
        return None
    if content is not None and literal:
        return path, literal
    return None


def audit_hardcoded_bypasses(
    consumer_paths: set[Path],
    cache: dict[Path, Optional[str]],
    exception_literals: dict[Path, set[str]],
) -> list[Finding]:
    findings: list[Finding] = []
    patterns = (
        ARBITRARY_VISUAL_UTILITY_PATTERN,
        RAW_PALETTE_UTILITY_PATTERN,
        RAW_COLOR_LITERAL_PATTERN,
    )
    for path in sorted(consumer_paths):
        content = cache.get(path)
        if content is None:
            continue
        allowed = exception_literals.get(path, set())
        reported: set[tuple[int, str]] = set()
        reported_spans: list[tuple[int, int]] = []
        for pattern in patterns:
            for match in pattern.finditer(content):
                literal = match.group(0)
                if any(
                    match.start() >= start and match.end() <= end
                    for start, end in reported_spans
                ):
                    continue
                if any(
                    literal == exception
                    or literal in exception
                    or exception in literal
                    for exception in allowed
                ):
                    continue
                line_number = content.count("\n", 0, match.start()) + 1
                key = (line_number, literal)
                if key in reported:
                    continue
                reported.add(key)
                reported_spans.append((match.start(), match.end()))
                findings.append(
                    Finding(
                        "error",
                        "hardcoded-token-bypass",
                        f"{path}:{line_number}",
                        (
                            f"Consumer contains raw or arbitrary visual value {literal!r}; "
                            "use a mapped semantic token or record an exact exception"
                        ),
                    )
                )
    return findings


def audit_manifest(data: Any, root: Path) -> tuple[list[Finding], AuditCounts]:
    findings: list[Finding] = []
    manifest = require_object(data, findings, "manifest")
    if manifest is None:
        return findings, AuditCounts()

    if manifest.get("schemaVersion") != 1:
        add(
            findings,
            "error",
            "unsupported-schema-version",
            "schemaVersion",
            "schemaVersion must be 1",
        )

    source = require_object(manifest.get("source"), findings, "source")
    access: Optional[str] = None
    if source is not None:
        kind = require_string(source, "kind", findings, "source")
        require_string(source, "identifier", findings, "source")
        access = require_string(source, "access", findings, "source")
        if kind and kind != "figma":
            add(
                findings,
                "error",
                "unsupported-source-kind",
                "source.kind",
                "Source-backed token manifests currently require kind 'figma'",
            )
        if access and access not in ACCESS_LEVELS:
            add(
                findings,
                "error",
                "invalid-source-access",
                "source.access",
                f"Use one of: {', '.join(sorted(ACCESS_LEVELS))}",
            )
        elif access == "partial":
            add(
                findings,
                "warning",
                "partial-source-access",
                "source.access",
                "Do not claim complete source-token coverage",
            )
        elif access in {"screenshot-only", "unavailable"}:
            add(
                findings,
                "error",
                "insufficient-token-source",
                "source.access",
                "Do not create a Figma token manifest without authoritative token metadata",
            )

    modes: list[str] = []
    theme = require_object(manifest.get("theme"), findings, "theme")
    if theme is not None:
        require_string(theme, "mechanism", findings, "theme")
        mode_values = require_list(theme.get("modes"), findings, "theme.modes")
        if mode_values is not None:
            for index, mode in enumerate(mode_values):
                if not isinstance(mode, str) or not mode.strip():
                    add(
                        findings,
                        "error",
                        "invalid-theme-mode",
                        f"theme.modes[{index}]",
                        "Mode must be a non-empty string",
                    )
                    continue
                modes.append(mode.strip())
            if not modes:
                add(
                    findings,
                    "error",
                    "missing-theme-mode",
                    "theme.modes",
                    "Declare at least one mode",
                )
            if len(modes) != len(set(modes)):
                add(
                    findings,
                    "error",
                    "duplicate-theme-mode",
                    "theme.modes",
                    "Theme modes must be unique",
                )
        default_mode = require_string(theme, "defaultMode", findings, "theme")
        if default_mode and default_mode not in modes:
            add(
                findings,
                "error",
                "invalid-default-mode",
                "theme.defaultMode",
                "Default mode must be present in theme.modes",
            )

    tokens_value = require_list(manifest.get("tokens"), findings, "tokens")
    source_names: set[str] = set()
    semantic_names: set[str] = set()
    css_variables: set[str] = set()
    cache: dict[Path, Optional[str]] = {}
    consumer_paths: set[Path] = set()
    consumer_count = 0
    token_count = len(tokens_value) if tokens_value is not None else 0
    if tokens_value is not None:
        if not tokens_value:
            add(
                findings,
                "error",
                "missing-tokens",
                "tokens",
                "A design-token manifest must declare at least one scoped token",
            )
        for index, token in enumerate(tokens_value):
            source_name, semantic_name, css_variable, consumers = audit_token(
                token, index, modes, root, cache, consumer_paths, findings
            )
            consumer_count += consumers
            for value, seen, code, field in (
                (source_name, source_names, "duplicate-source-name", "sourceName"),
                (
                    semantic_name,
                    semantic_names,
                    "duplicate-semantic-name",
                    "semanticName",
                ),
                (
                    css_variable,
                    css_variables,
                    "duplicate-css-variable",
                    "cssVariable",
                ),
            ):
                if value is None:
                    continue
                if value in seen:
                    add(
                        findings,
                        "error",
                        code,
                        f"tokens[{index}].{field}",
                        f"Duplicate identity {value!r}",
                    )
                seen.add(value)

    exceptions_value = manifest.get("exceptions", [])
    exceptions = require_list(exceptions_value, findings, "exceptions")
    exception_count = len(exceptions) if exceptions is not None else 0
    exception_literals: dict[Path, set[str]] = {}
    if exceptions is not None:
        for index, exception in enumerate(exceptions):
            allowed = audit_exception(exception, index, root, cache, findings)
            if allowed is not None:
                path, literal = allowed
                exception_literals.setdefault(path, set()).add(literal)

    findings.extend(
        audit_hardcoded_bypasses(consumer_paths, cache, exception_literals)
    )

    return findings, AuditCounts(token_count, consumer_count, exception_count)


def render_human(findings: list[Finding], counts: AuditCounts) -> None:
    for finding in findings:
        print(
            f"{finding.severity.upper()} {finding.code}: "
            f"{finding.location}: {finding.message}"
        )
    errors = sum(item.severity == "error" for item in findings)
    warnings = sum(item.severity == "warning" for item in findings)
    print(
        f"Checked {counts.tokens} token(s), {counts.consumers} consumer(s), "
        f"and {counts.exceptions} exception(s); errors {errors}; warnings {warnings}"
    )


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest.expanduser()
    root = args.root.expanduser().resolve()
    if not manifest_path.is_file():
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        return 2
    if not root.is_dir():
        print(f"Project root not found: {root}", file=sys.stderr)
        return 2

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        print(f"Cannot read manifest: {error}", file=sys.stderr)
        return 2

    findings, counts = audit_manifest(data, root)
    if args.json:
        print(
            json.dumps(
                {
                    "tokens": counts.tokens,
                    "consumers": counts.consumers,
                    "exceptions": counts.exceptions,
                    "errors": sum(item.severity == "error" for item in findings),
                    "warnings": sum(
                        item.severity == "warning" for item in findings
                    ),
                    "findings": [asdict(item) for item in findings],
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        render_human(findings, counts)
    return 1 if any(item.severity == "error" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
