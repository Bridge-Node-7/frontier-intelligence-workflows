from pathlib import Path

root = Path(__file__).resolve().parents[1]

release_test = root / "tests/test_release_semantics.py"
text = release_test.read_text(encoding="utf-8")
text = text.replace(
    'text = readme.read_text(encoding="utf-8").replace("**v0.6.0 — Decision-Ready Intelligence**", "**v10.5.01 — Decision-Ready Intelligence**")',
    'text = readme.read_text(encoding="utf-8").replace("**v0.6.1 — Decision-Ready Intelligence**", "**v10.6.11 — Decision-Ready Intelligence**")',
)
release_test.write_text(text, encoding="utf-8", newline="\n")

tooling_test = root / "tests/test_release_tooling.py"
text = tooling_test.read_text(encoding="utf-8")
text = text.replace(
    'path = self.repo / "profiles" / "perception-integrity" / "schema" / "perception-integrity-assessment.schema.json"',
    'path = self.repo / "profiles" / "radiant-guardian" / "schema" / "radiant-guardian-case.schema.json"',
)
text = text.replace(
    'self.assertIn("perception-integrity-assessment.schema.json", item["detail"])',
    'self.assertIn("radiant-guardian-case.schema.json", item["detail"])',
)
tooling_test.write_text(text, encoding="utf-8", newline="\n")
