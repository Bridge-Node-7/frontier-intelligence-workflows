from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    file = ROOT / path
    text = file.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"expected text not found in {path}: {old!r}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


# Validation-only dependencies are pinned so structured-document assurance is reproducible.
(ROOT / "requirements-validation.txt").write_text(
    "jsonschema==4.25.1\nPyYAML==6.0.3\n",
    encoding="utf-8",
    newline="\n",
)

# Promote the accumulated hardening work to the bounded maintenance release.
(ROOT / "VERSION").write_text("0.6.1\n", encoding="utf-8", newline="\n")
replace_once("scripts/release_common.py", 'EXPECTED_VERSION = "0.6.0"', 'EXPECTED_VERSION = "0.6.1"')
replace_once("README.md", "**v0.6.0 — Decision-Ready Intelligence**", "**v0.6.1 — Decision-Ready Intelligence**")
replace_once("LIMITATIONS.md", "Current release: `0.6.0`.", "Current release: `0.6.1`.")
replace_once("docs/assurance/TESTING.md", "# Validation — v0.6.0", "# Validation — v0.6.1")

# Close the Unreleased hardening set as 0.6.1 while retaining a clean Unreleased section.
changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
old_unreleased = """## [Unreleased]\n\n- Add repository-wide offline JSON Schema document validation to the existing syntax preflight, including parser and structural negative regressions.\n- Emit machine-generated expected integrity metadata to hosted validation evidence without mutating the reviewed repository tree.\n- Keep hostile-filesystem policy failures fail-closed while allowing independent website, link, secret, local-path, personal-contact, and source-safety scans to complete; classify prohibited directories as tracked violations or removable untracked local artifacts.\n\n## [0.6.0] - 2026-09-11\n"""
new_unreleased = """## [Unreleased]\n\n_No unreleased changes._\n\n## [0.6.1] - 2026-09-13\n\nCurrent public release.\n\n- Validate every policy-approved JSON, YAML, and TOML artifact for syntax before a repository PASS can be reported.\n- Validate every `*.schema.json` document against its declared JSON Schema metaschema in addition to FIW's offline structural checks.\n- Keep repository diagnostics independent: a hostile-filesystem finding remains blocking without suppressing unrelated public-boundary controls.\n- Keep machine-readable validation output optional while surfacing every blocking control directly in terminal output.\n- Pin validation-only dependencies and install them in hosted validation/release workflows.\n- Preserve Perception Integrity and Radiant Guardian truth boundaries, human decision authority, and the aggressive public file-policy threat model.\n\n## [0.6.0] - 2026-09-11\n"""
if old_unreleased not in changelog:
    raise SystemExit("unexpected CHANGELOG Unreleased section")
(ROOT / "CHANGELOG.md").write_text(changelog.replace(old_unreleased, new_unreleased, 1), encoding="utf-8", newline="\n")

# Make clean local verification self-contained and explicit.
readme = (ROOT / "README.md").read_text(encoding="utf-8")
needle = """Run the complete repository gate:\n\n```bash\nmkdir -p ../fiw-validation ../fiw-release\n"""
replacement = """Run the complete repository gate from an isolated Python environment. The validation-only dependencies are pinned and are not runtime dependencies of FIW's public methods.\n\n```bash\npython -m venv ../fiw-validation-venv\nsource ../fiw-validation-venv/bin/activate  # Windows PowerShell: ..\\fiw-validation-venv\\Scripts\\Activate.ps1\npython -m pip install -r requirements-validation.txt\nmkdir -p ../fiw-validation ../fiw-release\n"""
if needle not in readme:
    raise SystemExit("README complete-gate block not found")
(ROOT / "README.md").write_text(readme.replace(needle, replacement, 1), encoding="utf-8", newline="\n")

# The testing guide uses the same isolated validation dependency boundary.
testing = (ROOT / "docs/assurance/TESTING.md").read_text(encoding="utf-8")
needle = """```bash\nmkdir -p ../fiw-validation ../fiw-release\n"""
replacement = """```bash\npython -m venv ../fiw-validation-venv\nsource ../fiw-validation-venv/bin/activate  # Windows PowerShell: ..\\fiw-validation-venv\\Scripts\\Activate.ps1\npython -m pip install -r requirements-validation.txt\nmkdir -p ../fiw-validation ../fiw-release\n"""
if needle not in testing:
    raise SystemExit("TESTING complete-gate block not found")
(ROOT / "docs/assurance/TESTING.md").write_text(testing.replace(needle, replacement, 1), encoding="utf-8", newline="\n")

# Extend the hardened validator with generic structured-artifact semantic checks.
validator = ROOT / "scripts" / "validate_repo.py"
text = validator.read_text(encoding="utf-8")
text = text.replace(
    "import re\nimport subprocess\nimport sys\n",
    "import json\nimport re\nimport subprocess\nimport sys\nimport tomllib\n\nimport yaml\nfrom jsonschema.exceptions import SchemaError\nfrom jsonschema.validators import validator_for\n",
    1,
)
insert_before = "\ndef validate(root: Path, check_manifest: bool = True):\n"
structured_function = r'''

def _structured_semantic_findings(root: Path) -> list[str]:
    """Parse every approved structured artifact and validate schema documents.

    This is deliberately independent from byte-integrity: updating a manifest hash
    cannot convert malformed JSON/YAML/TOML or an invalid JSON Schema into PASS.
    """

    records, _policy_findings = scan_repository(root, include_manifests=True)
    findings: list[str] = []
    for record in records:
        path = record.path
        relative = record.relative
        suffix = path.suffix.lower()
        try:
            source = path.read_text(encoding="utf-8")
            if suffix == ".json":
                document = json.loads(source)
                if relative.endswith(".schema.json"):
                    if not isinstance(document, (dict, bool)):
                        raise ValueError("JSON Schema root must be an object or boolean")
                    validator_class = validator_for(document)
                    validator_class.check_schema(document)
            elif suffix in {".yml", ".yaml"}:
                document = yaml.safe_load(source)
                if document is None:
                    raise ValueError("YAML document is empty")
            elif suffix == ".toml":
                tomllib.loads(source)
        except (OSError, UnicodeError, json.JSONDecodeError, yaml.YAMLError, tomllib.TOMLDecodeError, SchemaError, ValueError) as exc:
            findings.append(f"{relative}: {type(exc).__name__}: {exc}")
    return findings
'''
if "def _structured_semantic_findings" not in text:
    if insert_before not in text:
        raise SystemExit("validate() insertion point not found")
    text = text.replace(insert_before, structured_function + insert_before, 1)

needle = """    _fold_core_security_scans(report, root)\n\n    file_policy = next(\n"""
replacement = """    _fold_core_security_scans(report, root)\n\n    semantic_findings = _structured_semantic_findings(root)\n    report[\"checks\"].append({\n        \"name\": \"structured_artifact_semantics\",\n        \"status\": \"PASS\" if not semantic_findings else \"FAIL\",\n        \"passed\": not semantic_findings,\n        \"detail\": (\n            \"Every policy-approved JSON, YAML, and TOML artifact parses; every JSON Schema validates against its declared metaschema.\"\n            if not semantic_findings\n            else \"; \".join(semantic_findings)\n        ),\n    })\n\n    file_policy = next(\n"""
if needle not in text:
    raise SystemExit("validate semantic check insertion point not found")
text = text.replace(needle, replacement, 1)
validator.write_text(text, encoding="utf-8", newline="\n")

# Add regressions to the existing approved release-tooling test surface.
test_path = ROOT / "tests" / "test_release_tooling.py"
tests = test_path.read_text(encoding="utf-8")
insert = r'''

    def test_structured_semantics_baseline_passes(self):
        item = self.check("structured_artifact_semantics", check_manifest=False)
        self.assertEqual(item["status"], "PASS", item)

    def test_malformed_governed_json_fails_semantic_control(self):
        path = self.repo / "data" / "synthetic" / "frontier-claim-experience.json"
        path.write_text("{not-json\n", encoding="utf-8", newline="\n")
        item = self.check("structured_artifact_semantics", check_manifest=False)
        self.assertEqual(item["status"], "FAIL", item)
        self.assertIn("frontier-claim-experience.json", item["detail"])

    def test_schema_invalid_against_metaschema_fails_even_when_json_parses(self):
        path = self.repo / "profiles" / "perception-integrity" / "schema" / "perception-integrity-assessment.schema.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        schema["type"] = 7
        path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8", newline="\n")
        item = self.check("structured_artifact_semantics", check_manifest=False)
        self.assertEqual(item["status"], "FAIL", item)
        self.assertIn("perception-integrity-assessment.schema.json", item["detail"])

    def test_malformed_governed_yaml_fails_semantic_control(self):
        path = self.repo / ".github" / "dependabot.yml"
        path.write_text("updates: [\n", encoding="utf-8", newline="\n")
        item = self.check("structured_artifact_semantics", check_manifest=False)
        self.assertEqual(item["status"], "FAIL", item)
        self.assertIn("dependabot.yml", item["detail"])
'''
marker = "\n\nif __name__ == \"__main__\":\n"
if "test_structured_semantics_baseline_passes" not in tests:
    if marker not in tests:
        raise SystemExit("test file insertion point not found")
    tests = tests.replace(marker, insert + marker, 1)
test_path.write_text(tests, encoding="utf-8", newline="\n")

# Add validation dependencies to both hosted gates.
for relative in (".github/workflows/validate.yml", ".github/workflows/release.yml"):
    path = ROOT / relative
    workflow = path.read_text(encoding="utf-8")
    needle = '      - name: Create external evidence directories\n'
    install = '      - name: Install validation dependencies\n        run: python -m pip install --disable-pip-version-check -r requirements-validation.txt\n\n'
    if install not in workflow:
        if needle not in workflow:
            raise SystemExit(f"workflow insertion point missing: {relative}")
        workflow = workflow.replace(needle, install + needle, 1)
    path.write_text(workflow, encoding="utf-8", newline="\n")

# Align file policy with the new validation-only root file and release.
policy_path = ROOT / "REPO_FILE_POLICY.json"
policy = json.loads(policy_path.read_text(encoding="utf-8"))
for key in ("allowed_path_globs", "allowed_root_files"):
    values = list(policy[key])
    if "requirements-validation.txt" not in values:
        values.append("requirements-validation.txt")
    policy[key] = sorted(values)
policy["release_version"] = "0.6.1"
for name in ("validate.yml", "release.yml"):
    digest = hashlib.sha256((ROOT / ".github" / "workflows" / name).read_bytes()).hexdigest()
    policy["approved_workflow_sha256"][name] = digest
policy_path.write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
