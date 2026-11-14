"""Release-please owns versioning and packaged publication; release.yml remains evidence-only."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RP = ROOT / ".github" / "workflows" / "release-please.yml"
REL = ROOT / ".github" / "workflows" / "release.yml"


class ReleasePublicationOwnershipTests(unittest.TestCase):
    def test_release_please_skips_github_release(self) -> None:
        text = RP.read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^\s*skip-github-release:\s*true\s*$")

    def test_release_please_owns_packaged_publication(self) -> None:
        rp = RP.read_text(encoding="utf-8")
        rel = REL.read_text(encoding="utf-8")
        self.assertIn("gh release create", rp)
        self.assertIn("scripts/build_release.py", rp)
        self.assertIn("Existing release ${TAG} is incomplete", rp)
        self.assertIn("ASSET_HASHES.json", rp)
        self.assertNotIn("gh release create", rel)
        self.assertRegex(rel, r"(?m)^permissions:\n  contents: read\s*$")
        self.assertNotRegex(rel, r"(?m)^\s+contents:\s*write\s*$")
        self.assertIn("skip-github-release: true", rp)
        self.assertIn('SYNC_DIR="${RUNNER_TEMP}/fiw-release-please-sync"', rp)
        self.assertNotIn("rm -rf .repo-sync", rp)
        self.assertNotIn("COMMIT_MSG=", rp)

    def test_no_new_pat_secret_required(self) -> None:
        for path in (RP, REL):
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"secrets\.[A-Z0-9_]*(TOKEN|PAT|APP)")


    def test_artifact_name_is_filesystem_safe(self) -> None:
        rel = REL.read_text(encoding="utf-8")
        # Branch names may contain "/"; artifact names must not derive from ref_name.
        self.assertNotIn("github.ref_name", rel)
        self.assertIn(
            "frontier-intelligence-workflows-release-${{ github.run_id }}-${{ github.sha }}",
            rel,
        )

if __name__ == "__main__":
    unittest.main()