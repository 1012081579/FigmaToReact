from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import audit_design_tokens as auditor  # noqa: E402


def valid_manifest() -> dict:
    return {
        "schemaVersion": 1,
        "source": {
            "kind": "figma",
            "identifier": "file-key node 1:2",
            "access": "complete",
            "notes": "",
        },
        "theme": {
            "mechanism": "css-variables",
            "defaultMode": "light",
            "modes": ["light", "dark"],
        },
        "tokens": [
            {
                "sourceName": "Color/Surface/Primary",
                "category": "color",
                "semanticName": "surface-primary",
                "cssVariable": "--color-surface-primary",
                "utilities": ["bg-surface-primary"],
                "values": {"light": "#fff", "dark": "#111"},
                "consumers": [
                    {
                        "file": "src/ProductCard.tsx",
                        "property": "background",
                        "usage": "bg-surface-primary",
                    }
                ],
            }
        ],
        "exceptions": [
            {
                "file": "src/ProductCard.tsx",
                "property": "width",
                "literal": "w-[37px]",
                "sourceEvidence": "Figma node 1:2 width 37px, unbound",
                "reason": "One-off composition width",
            }
        ],
    }


class DesignTokenAuditTests(unittest.TestCase):
    def make_project(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        source = root / "src"
        source.mkdir()
        (source / "ProductCard.tsx").write_text(
            '<article className="bg-surface-primary w-[37px]" />\n',
            encoding="utf-8",
        )
        return temporary, root

    def test_valid_manifest_proves_consumers_and_exceptions(self) -> None:
        temporary, root = self.make_project()
        self.addCleanup(temporary.cleanup)

        findings, counts = auditor.audit_manifest(valid_manifest(), root.resolve())

        self.assertEqual(findings, [])
        self.assertEqual(counts.tokens, 1)
        self.assertEqual(counts.consumers, 1)
        self.assertEqual(counts.exceptions, 1)

    def test_partial_access_warns_without_inventing_an_error(self) -> None:
        temporary, root = self.make_project()
        self.addCleanup(temporary.cleanup)
        manifest = valid_manifest()
        manifest["source"]["access"] = "partial"

        findings, _ = auditor.audit_manifest(manifest, root.resolve())

        self.assertEqual(
            [item.code for item in findings], ["partial-source-access"]
        )

    def test_screenshot_only_source_cannot_claim_tokens(self) -> None:
        temporary, root = self.make_project()
        self.addCleanup(temporary.cleanup)
        manifest = valid_manifest()
        manifest["source"]["access"] = "screenshot-only"

        findings, _ = auditor.audit_manifest(manifest, root.resolve())

        self.assertIn("insufficient-token-source", {item.code for item in findings})

    def test_arbitrary_utility_is_not_semantic_token_evidence(self) -> None:
        temporary, root = self.make_project()
        self.addCleanup(temporary.cleanup)
        manifest = valid_manifest()
        token = manifest["tokens"][0]
        token["utilities"] = ["bg-[#fff]"]
        token["consumers"][0]["usage"] = "bg-[#fff]"

        findings, _ = auditor.audit_manifest(manifest, root.resolve())

        codes = {item.code for item in findings}
        self.assertIn("arbitrary-token-utility", codes)
        self.assertIn("arbitrary-consumer-usage", codes)

    def test_raw_palette_usage_in_a_consumer_is_a_bypass(self) -> None:
        temporary, root = self.make_project()
        self.addCleanup(temporary.cleanup)
        component = root / "src" / "ProductCard.tsx"
        component.write_text(
            '<article className="bg-surface-primary text-gray-500 w-[37px]" />\n',
            encoding="utf-8",
        )

        findings, _ = auditor.audit_manifest(valid_manifest(), root.resolve())

        bypasses = [
            item for item in findings if item.code == "hardcoded-token-bypass"
        ]
        self.assertEqual(len(bypasses), 1)
        self.assertIn("text-gray-500", bypasses[0].message)

    def test_missing_usage_and_duplicate_identity_fail(self) -> None:
        temporary, root = self.make_project()
        self.addCleanup(temporary.cleanup)
        manifest = valid_manifest()
        duplicate = copy.deepcopy(manifest["tokens"][0])
        duplicate["consumers"][0]["usage"] = "text-surface-primary"
        duplicate["utilities"] = ["text-surface-primary"]
        manifest["tokens"].append(duplicate)

        findings, _ = auditor.audit_manifest(manifest, root.resolve())

        codes = {item.code for item in findings}
        self.assertIn("consumer-usage-not-found", codes)
        self.assertIn("duplicate-source-name", codes)
        self.assertIn("duplicate-semantic-name", codes)
        self.assertIn("duplicate-css-variable", codes)

    def test_consumer_cannot_escape_project_root(self) -> None:
        temporary, root = self.make_project()
        self.addCleanup(temporary.cleanup)
        manifest = valid_manifest()
        manifest["tokens"][0]["consumers"][0]["file"] = "../outside.tsx"

        findings, _ = auditor.audit_manifest(manifest, root.resolve())

        self.assertIn("consumer-outside-root", {item.code for item in findings})

    def test_cli_emits_a_successful_json_report(self) -> None:
        temporary, root = self.make_project()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "design-token-map.json"
        manifest_path.write_text(json.dumps(valid_manifest()), encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "audit_design_tokens.py"),
                str(manifest_path),
                "--root",
                str(root),
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["errors"], 0)
        self.assertEqual(report["tokens"], 1)


if __name__ == "__main__":
    unittest.main()
