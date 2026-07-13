from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import audit_figma_assets as auditor  # noqa: E402


VALID_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path d="M0 0h24v24H0z"/></svg>'
)


class AssetAuditTests(unittest.TestCase):
    def test_markdown_mentioning_svg_is_not_detected_as_an_asset(self) -> None:
        markdown = b"# SVG notes\nA valid file has an <svg> root element.\n"
        asset_format, svg_text = auditor.detect_format(markdown)
        self.assertIsNone(asset_format)
        self.assertIsNone(svg_text)

    def test_svg_document_with_xml_declaration_is_detected(self) -> None:
        data = ("<?xml version=\"1.0\"?>\n" + VALID_SVG).encode()
        asset_format, svg_text = auditor.detect_format(data)
        self.assertEqual(asset_format, auditor.FORMATS["svg"])
        self.assertIsNotNone(svg_text)

    def test_fix_renames_and_reference_scan_finds_then_clears_usage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset_dir = root / "src" / "assets"
            asset_dir.mkdir(parents=True)
            source = asset_dir / "SearchIcon.png"
            source.write_text(VALID_SVG, encoding="utf-8")
            consumer = root / "src" / "SearchButton.tsx"
            consumer.write_text(
                'import icon from "./assets/SearchIcon.png";\n', encoding="utf-8"
            )

            findings, rename = auditor.inspect_file(source, fix=True)

            self.assertIsNotNone(rename)
            self.assertTrue((asset_dir / "SearchIcon.svg").is_file())
            self.assertFalse(any(item.severity == "error" for item in findings))

            stale, checked = auditor.audit_stale_references([root], [rename])
            self.assertGreaterEqual(checked, 1)
            self.assertEqual(
                [item.code for item in stale if item.severity == "error"],
                ["stale-asset-reference"],
            )

            consumer.write_text(
                'import icon from "./assets/SearchIcon.svg";\n', encoding="utf-8"
            )
            cleared, _ = auditor.audit_stale_references([root], [rename])
            self.assertEqual(cleared, [])

    def test_fix_refuses_active_svg_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "Unsafe.png"
            source.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
                "<script>alert(1)</script></svg>",
                encoding="utf-8",
            )

            findings, rename = auditor.inspect_file(source, fix=True)

            self.assertIsNone(rename)
            self.assertTrue(source.exists())
            self.assertIn("svg-active-content", {item.code for item in findings})
            self.assertIn("fix-skipped-content-errors", {item.code for item in findings})

    def test_fix_never_overwrites_existing_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "Icon.png"
            target = root / "Icon.svg"
            source.write_text(VALID_SVG, encoding="utf-8")
            target.write_text(VALID_SVG.replace("24", "16"), encoding="utf-8")

            findings, rename = auditor.inspect_file(source, fix=True)

            self.assertIsNone(rename)
            self.assertTrue(source.exists())
            self.assertIn("rename-conflict", {item.code for item in findings})

    def test_cli_rechecks_an_explicit_previous_rename(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset_dir = root / "src" / "assets"
            asset_dir.mkdir(parents=True)
            target = asset_dir / "Icon.svg"
            target.write_text(VALID_SVG, encoding="utf-8")
            consumer = root / "src" / "Button.tsx"
            consumer.write_text(
                'import icon from "./assets/Icon.png";\n', encoding="utf-8"
            )
            change = f"{asset_dir / 'Icon.png'}={target}"

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "audit_figma_assets.py"),
                    "--json",
                    "--references-root",
                    str(root),
                    "--reference-change",
                    change,
                    str(target),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(report["errors"], 1)
            self.assertEqual(report["findings"][0]["code"], "stale-asset-reference")


if __name__ == "__main__":
    unittest.main()
