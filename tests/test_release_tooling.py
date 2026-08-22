from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from build_release import build_source_archive, ensure_output_outside_root, run_validator, verify_source_archive  # noqa: E402
from release_common import (  # noqa: E402
    IntegrityError, compile_python_sources, load_policy, portable_path_error, portable_path_errors, portable_path_key,
    sha256_file, unsafe_filesystem_entry_reason, write_manifests,
)
from validate_repo import validate  # noqa: E402


class ReleaseToolingTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="fiw-tests-")
        self.repo = Path(self.temporary.name) / "repo"
        shutil.copytree(
            ROOT,
            self.repo,
            ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", "validation-report.json"),
            symlinks=True,
        )
        # v0.5 treats missing Git metadata as NOT_RUN/non-passing in strict validation.
        # Give release-tooling fixtures a real index so tracked-path coverage actually executes.
        # Intent-to-add records path membership without hashing every copied file into a
        # new object database, avoiding Windows temp/antivirus contention observed in R3.
        subprocess.run(["git", "-C", str(self.repo), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "add", "--intent-to-add", "-A"], check=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def report(self, check_manifest: bool = False):
        return validate(self.repo, check_manifest=check_manifest)

    def check(self, name: str, check_manifest: bool = False):
        report = self.report(check_manifest=check_manifest)
        return next(item for item in report["checks"] if item["name"] == name)

    def refresh(self) -> None:
        write_manifests(self.repo)

    def policy(self) -> dict:
        return json.loads((self.repo / "REPO_FILE_POLICY.json").read_text(encoding="utf-8"))

    def save_policy(self, policy: dict) -> None:
        (self.repo / "REPO_FILE_POLICY.json").write_text(
            json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def approve_workflow_change(self, name: str) -> None:
        policy = self.policy()
        policy["approved_workflow_sha256"][name] = sha256_file(self.repo / ".github" / "workflows" / name)
        self.save_policy(policy)

    def assert_check_fails(self, name: str, check_manifest: bool = False) -> None:
        item = self.check(name, check_manifest=check_manifest)
        self.assertFalse(item["passed"], item)

    def test_01_baseline_repository_passes(self):
        report = self.report(check_manifest=True)
        self.assertTrue(report["passed"], report)

    def test_02_unexpected_root_file_rejected(self):
        (self.repo / "unexpected.txt").write_text("public-looking but unapproved\n", encoding="utf-8", newline="\n")
        self.assert_check_fails("file_policy_and_filesystem")

    def test_03_prohibited_private_directory_rejected(self):
        path = self.repo / "private-client" / "engagement-notes.txt"
        path.parent.mkdir()
        path.write_text("not a secret pattern, but not public\n", encoding="utf-8", newline="\n")
        self.assert_check_fails("file_policy_and_filesystem")

    def test_04_symbolic_link_rejected(self):
        link = self.repo / "docs" / "linked-hosts.txt"
        try:
            link.symlink_to(Path("/etc/hosts"))
        except (OSError, NotImplementedError):
            self.skipTest("symbolic links unavailable")
        self.assert_check_fails("file_policy_and_filesystem")

    def test_05_symbolic_directory_rejected(self):
        link = self.repo / "docs" / "linked-directory"
        try:
            link.symlink_to(self.repo / "examples", target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symbolic links unavailable")
        self.assert_check_fails("file_policy_and_filesystem")

    def test_06_fifo_rejected(self):
        if not hasattr(os, "mkfifo"):
            self.skipTest("FIFO unavailable")
        fifo = self.repo / "docs" / "unsafe-fifo.md"
        try:
            os.mkfifo(fifo)
        except OSError:
            self.skipTest("FIFO creation unavailable")
        self.assert_check_fails("file_policy_and_filesystem")

    def test_07_control_character_path_rejected(self):
        path = self.repo / "docs" / "bad\nname.md"
        try:
            path.write_text("unsafe name\n", encoding="utf-8", newline="\n")
        except OSError:
            self.skipTest("control-character path unavailable")
        self.assert_check_fails("file_policy_and_filesystem")

    def test_08_oversized_file_rejected(self):
        policy = self.policy()
        size = int(policy["max_file_size_bytes"]) + 1
        (self.repo / "docs" / "oversized.md").write_text("x" * size, encoding="utf-8", newline="\n")
        self.assert_check_fails("file_policy_and_filesystem")

    def test_09_binary_file_rejected(self):
        path = self.repo / "docs" / "binary.md"
        path.write_bytes(b"abc\x00def")
        self.assert_check_fails("file_policy_and_filesystem")

    def test_10_nested_archive_rejected(self):
        path = self.repo / "docs" / "nested.zip"
        path.write_bytes(b"PK\x03\x04")
        self.assert_check_fails("file_policy_and_filesystem")

    def test_11_missing_manifest_rejected(self):
        (self.repo / "MANIFEST.sha256").unlink()
        self.assert_check_fails("required_files", check_manifest=True)

    def test_12_stale_manifest_rejected(self):
        (self.repo / "README.md").write_text((self.repo / "README.md").read_text(encoding="utf-8") + "\n", encoding="utf-8", newline="\n")
        self.assert_check_fails("manifest_consistency", check_manifest=True)

    def test_13_comment_spoofed_permissions_rejected(self):
        path = self.repo / ".github" / "workflows" / "validate.yml"
        text = path.read_text(encoding="utf-8")
        text = text.replace("permissions:\n  contents: read\n", "# permissions:\n#   contents: read\n")
        path.write_text(text, encoding="utf-8", newline="\n")
        self.approve_workflow_change("validate.yml")
        self.assert_check_fails("workflow_controls")

    def test_14_comment_spoofed_checkout_control_rejected(self):
        path = self.repo / ".github" / "workflows" / "validate.yml"
        text = path.read_text(encoding="utf-8").replace("          persist-credentials: false", "          # persist-credentials: false")
        path.write_text(text, encoding="utf-8", newline="\n")
        self.approve_workflow_change("validate.yml")
        self.assert_check_fails("workflow_controls")

    def test_15_mutable_action_reference_rejected(self):
        path = self.repo / ".github" / "workflows" / "validate.yml"
        text = path.read_text(encoding="utf-8").replace(
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            "actions/checkout@v7",
        )
        path.write_text(text, encoding="utf-8", newline="\n")
        self.approve_workflow_change("validate.yml")
        self.assert_check_fails("workflow_controls")

    def test_16_pages_capability_rejected(self):
        path = self.repo / ".github" / "workflows" / "release.yml"
        path.write_text(path.read_text(encoding="utf-8") + "\n# semantic change below\npermissions: write-all\n", encoding="utf-8", newline="\n")
        self.approve_workflow_change("release.yml")
        self.assert_check_fails("workflow_controls")

    def test_17_secret_fixture_rejected(self):
        path = self.repo / "docs" / "assurance" / "README.md"
        path.write_text(path.read_text(encoding="utf-8") + "\napi_key='this-is-a-realistic-secret-value'\n", encoding="utf-8", newline="\n")  # FIW_SECRET_FIXTURE
        self.refresh()
        self.assert_check_fails("secret_patterns", check_manifest=True)

    def test_18_local_user_path_rejected(self):
        path = self.repo / "docs" / "assurance" / "README.md"
        path.write_text(path.read_text(encoding="utf-8") + "\nC:/Users/ExampleUser/private.txt\n", encoding="utf-8", newline="\n")  # FIW_SECRET_FIXTURE
        self.refresh()
        self.assert_check_fails("local_user_paths", check_manifest=True)

    def test_19_broken_relative_link_rejected(self):
        path = self.repo / "docs" / "assurance" / "README.md"
        path.write_text(path.read_text(encoding="utf-8") + "\n[missing](not-present.md)\n", encoding="utf-8", newline="\n")
        self.refresh()
        self.assert_check_fails("markdown_links", check_manifest=True)

    def test_20_missing_trace_identifier_rejected(self):
        path = self.repo / "examples" / "synthetic-component-readiness" / "source-record.md"
        path.write_text(path.read_text(encoding="utf-8").replace("SRC-FIW-SYN-001", "SRC-MISSING"), encoding="utf-8", newline="\n")
        self.refresh()
        self.assert_check_fails("synthetic_example_traceability", check_manifest=True)

    def test_21_repeated_archives_are_byte_identical(self):
        first = Path(self.temporary.name) / "first.zip"
        second = Path(self.temporary.name) / "second.zip"
        build_source_archive(self.repo, first, "0.2.0")
        build_source_archive(self.repo, second, "0.2.0")
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_22_archive_membership_mismatch_rejected(self):
        archive_path = Path(self.temporary.name) / "archive.zip"
        build_source_archive(self.repo, archive_path, "0.2.0")
        tampered = Path(self.temporary.name) / "tampered-members.zip"
        with zipfile.ZipFile(archive_path, "r") as source, zipfile.ZipFile(tampered, "w") as target:
            for info in source.infolist()[:-1]:
                target.writestr(info, source.read(info.filename))
        with self.assertRaises(IntegrityError):
            verify_source_archive(tampered, self.repo, "0.2.0")

    def test_23_archive_content_mismatch_rejected(self):
        archive_path = Path(self.temporary.name) / "archive.zip"
        build_source_archive(self.repo, archive_path, "0.2.0")
        tampered = Path(self.temporary.name) / "tampered-content.zip"
        with zipfile.ZipFile(archive_path, "r") as source, zipfile.ZipFile(tampered, "w") as target:
            for index, info in enumerate(source.infolist()):
                data = source.read(info.filename)
                if index == 0:
                    data += b"tamper"
                target.writestr(info, data)
        with self.assertRaises(IntegrityError):
            verify_source_archive(tampered, self.repo, "0.2.0")

    def test_24_workflow_hash_change_requires_policy_update(self):
        path = self.repo / ".github" / "workflows" / "validate.yml"
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8", newline="\n")
        self.assert_check_fails("workflow_controls")

    def test_25_tracked_build_output_directory_rejected(self):
        path = self.repo / "dist" / "private-client-data.txt"
        path.parent.mkdir()
        path.write_text("not public\n", encoding="utf-8", newline="\n")
        self.assert_check_fails("file_policy_and_filesystem")

    def test_26_tracked_bytecode_directory_rejected(self):
        path = self.repo / "scripts" / "__pycache__" / "private-client-data.txt"
        path.parent.mkdir()
        path.write_text("not public\n", encoding="utf-8", newline="\n")
        self.assert_check_fails("file_policy_and_filesystem")

    def test_27_windows_reserved_name_rejected(self):
        self.assertIsNotNone(portable_path_error("docs/CON.md"))
        self.assertIsNotNone(portable_path_error("docs/lpt9.txt"))

    def test_28_alternate_data_stream_name_rejected(self):
        self.assertIsNotNone(portable_path_error("docs/name:stream.md"))

    def test_29_casefold_collision_detected(self):
        self.assertEqual(portable_path_key("docs/Case.md"), portable_path_key("docs/case.md"))

    def test_30_unicode_normalization_collision_detected(self):
        self.assertEqual(portable_path_key("docs/café.md"), portable_path_key("docs/café.md"))

    def test_31_in_memory_compile_leaves_tree_unchanged(self):
        before = sorted((p.relative_to(self.repo).as_posix(), p.read_bytes()) for p in self.repo.rglob("*") if p.is_file())
        compiled = compile_python_sources(self.repo)
        after = sorted((p.relative_to(self.repo).as_posix(), p.read_bytes()) for p in self.repo.rglob("*") if p.is_file())
        self.assertGreaterEqual(len(compiled), 1)
        self.assertEqual(before, after)
        self.assertFalse(any("__pycache__" in path for path, _ in after))

    def test_32_release_output_inside_root_rejected(self):
        with self.assertRaises(IntegrityError):
            ensure_output_outside_root(self.repo, self.repo / "dist")

    def test_33_release_branch_push_trigger_rejected(self):
        path = self.repo / ".github" / "workflows" / "validate.yml"
        text = path.read_text(encoding="utf-8").replace("      - main\n", "      - main\n      - \"release/**\"\n")
        path.write_text(text, encoding="utf-8", newline="\n")
        self.approve_workflow_change("validate.yml")
        self.assert_check_fails("workflow_controls")

    def test_34_builder_validator_leaves_tree_unchanged(self):
        before = sorted((p.relative_to(self.repo).as_posix(), p.read_bytes()) for p in self.repo.rglob("*") if p.is_file())
        output = Path(self.temporary.name) / "validation" / "report.json"
        run_validator(self.repo, output)
        after = sorted((p.relative_to(self.repo).as_posix(), p.read_bytes()) for p in self.repo.rglob("*") if p.is_file())
        self.assertEqual(before, after)
        self.assertFalse(any("__pycache__" in path for path, _ in after))
        self.assertTrue(output.is_file())


    def test_35_platform_independent_symlink_decision(self):
        import stat

        reason = unsafe_filesystem_entry_reason(
            relative="docs/link.md", is_symlink=True, mode=stat.S_IFREG | 0o644
        )
        self.assertIn("symbolic link or reparse point", reason or "")

    def test_36_platform_independent_special_file_decision(self):
        import stat

        reason = unsafe_filesystem_entry_reason(
            relative="docs/pipe", is_symlink=False, mode=stat.S_IFIFO | 0o600
        )
        self.assertIn("non-regular file", reason or "")

    def test_37_portable_path_policy_rejects_backslash_and_trailing_period(self):
        self.assertTrue(portable_path_errors(r"docs\bad.md"))
        self.assertTrue(portable_path_errors("docs/badname."))

    def test_38_portable_path_policy_rejects_drive_and_unc_forms(self):
        self.assertTrue(portable_path_errors("C:/docs/file.md"))
        self.assertTrue(portable_path_errors(r"\\server\share\file.md"))

    def test_39_source_archive_uses_stored_members(self):
        import tempfile

        with tempfile.TemporaryDirectory(prefix="fiw-zip-method-") as temporary:
            archive = Path(temporary) / "source.zip"
            build_source_archive(self.repo, archive, "0.2.0")
            with zipfile.ZipFile(archive, "r") as handle:
                self.assertTrue(handle.infolist())
                self.assertTrue(all(item.compress_type == zipfile.ZIP_STORED for item in handle.infolist()))

    def test_40_direct_validator_leaves_tree_unchanged_without_env(self):
        def snapshot(root: Path):
            return [
                (path.relative_to(root).as_posix(), path.read_bytes())
                for path in sorted(item for item in root.rglob("*") if item.is_file())
            ]

        before = snapshot(self.repo)
        environment = os.environ.copy()
        environment.pop("PYTHONDONTWRITEBYTECODE", None)
        completed = subprocess.run(
            [sys.executable, str(self.repo / "scripts" / "validate_repo.py"), "--root", str(self.repo)],
            cwd=self.repo,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertEqual(before, snapshot(self.repo))
        self.assertFalse(any(self.repo.rglob("*.pyc")))
        self.assertFalse(any(path.name == "__pycache__" for path in self.repo.rglob("*")))


    def test_41_stale_policy_release_version_rejected(self):
        policy = self.policy()
        policy["release_version"] = "0.1.5"
        self.save_policy(policy)
        with self.assertRaises(IntegrityError):
            load_policy(self.repo)

    def test_42_missing_policy_release_version_rejected(self):
        policy = self.policy()
        policy.pop("release_version")
        self.save_policy(policy)
        with self.assertRaises(IntegrityError):
            load_policy(self.repo)

    def test_43_unmarked_secret_inside_test_file_rejected(self):
        path = self.repo / "tests" / "test_release_tooling.py"
        secret = "api_" + "key='this-is-an-unmarked-secret-value'"
        path.write_text(
            path.read_text(encoding="utf-8") + f"\n# {secret}\n",
            encoding="utf-8",
            newline="\n",
        )
        self.refresh()
        self.assert_check_fails("secret_patterns", check_manifest=True)


if __name__ == "__main__":
    unittest.main()
