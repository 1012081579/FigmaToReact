#!/usr/bin/env python3
"""Scaffold a small stateless TypeScript React component for a greenfield prototype."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PASCAL_CASE = re.compile(r"^[A-Z][A-Za-z0-9]*$")
HOST_ELEMENTS = (
    "div",
    "section",
    "article",
    "button",
    "nav",
    "header",
    "footer",
    "main",
    "aside",
    "form",
    "ul",
    "li",
)


def to_kebab_case(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def render_component(name: str, element: str) -> str:
    default_type = "\n  type = \"button\"," if element == "button" else ""
    type_attribute = "\n      type={type}" if element == "button" else ""
    return f'''import type {{ ComponentPropsWithoutRef }} from "react";

export type {name}Props = ComponentPropsWithoutRef<"{element}">;

export function {name}({{{default_type}
  className,
  ...props
}}: {name}Props) {{
  return (
    <{element}{type_attribute}
      className={{className}}
      data-component="{to_kebab_case(name)}"
      {{...props}}
    />
  );
}}
'''


def render_index(name: str) -> str:
    return f'''export {{ {name} }} from "./{name}";
export type {{ {name}Props }} from "./{name}";
'''


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a stateless host-element React component in a matching named "
            "file. Use only when the target repository has no conflicting "
            "generator or file convention."
        )
    )
    parser.add_argument("name", help="PascalCase component name")
    parser.add_argument("--dir", required=True, type=Path, help="Parent output directory")
    parser.add_argument("--element", choices=HOST_ELEMENTS, default="div")
    parser.add_argument("--flat", action="store_true", help="Write directly into --dir")
    parser.add_argument("--index", action="store_true", help="Create an index.ts export")
    parser.add_argument("--dry-run", action="store_true", help="Print output paths only")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not PASCAL_CASE.fullmatch(args.name):
        raise SystemExit("Component name must be PascalCase, for example ProductCard")

    output_dir = args.dir if args.flat else args.dir / args.name
    files = {output_dir / f"{args.name}.tsx": render_component(args.name, args.element)}
    if args.index:
        files[output_dir / "index.ts"] = render_index(args.name)

    conflicts = [path for path in files if path.exists()]
    if conflicts:
        joined = "\n".join(str(path) for path in conflicts)
        raise SystemExit(f"Refusing to overwrite existing files:\n{joined}")

    if args.dry_run:
        for path in files:
            print(path)
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    for path, content in files.items():
        path.write_text(content, encoding="utf-8")
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
