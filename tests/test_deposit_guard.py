"""Regression test for the Zenodo deposit tool's publish guard.

`deposit_to_zenodo.py` previously advertised a ``--dry-run`` flag that it never
implemented: the argument was referenced only *after* the deposition had been created,
the 24 MB archive uploaded, and the metadata written. A rehearsal therefore performed a
real deposit, and the resulting draft sat on Zenodo with a pre-reserved DOI.

The rewrite inverts the default - staging is the default action, and publishing needs an
explicit ``--publish`` - and verifies the staged checksum before the irreversible call.
These tests hold that behaviour in place: a dry run must send no write request at all,
staging must not publish, and a mismatched checksum must abort before the publish POST.
"""
import hashlib
import importlib.util
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "submission" / "release" / "deposit_to_zenodo.py"

# The submission tooling is deliberately not redistributed - neither in the public
# repository nor in the Zenodo archive - so this module skips where it is absent rather
# than erroring on import. In the project itself the script is always present and every
# test below runs.
if not SCRIPT.exists():
    raise unittest.SkipTest(f"{SCRIPT.name} is not redistributed in this tree")


def load_module():
    spec = importlib.util.spec_from_file_location("deposit_to_zenodo", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def local_md5(module) -> str:
    h = hashlib.md5()
    with module.ARCHIVE.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class FakeResponse:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError(f"unexpected HTTP {self.status_code}")


class FakeHTTP:
    """Records every request so a test can assert on what was *not* sent."""

    def __init__(self, staged_md5=None, staged=True, submitted=False):
        self.calls = []
        self.staged_md5 = staged_md5
        self.staged = staged
        self.submitted = submitted
        self.deposition = {
            "id": 42,
            "submitted": submitted,
            "doi": "10.5281/zenodo.42" if submitted else None,
            "links": {"bucket": "https://example.invalid/api/files/bucket-id",
                      "html": "https://example.invalid/deposit/42"},
            "files": ([{"filename": "aic_weather_decision_release.zip",
                        "filesize": 1,
                        "checksum": f"md5:{staged_md5}"}] if staged else []),
        }

    def post(self, url, **kwargs):
        self.calls.append(("POST", url))
        if url.endswith("/actions/publish"):
            return FakeResponse(200, {"doi": "10.5281/zenodo.42"})
        return FakeResponse(201, self.deposition)

    def put(self, url, **kwargs):
        self.calls.append(("PUT", url))
        return FakeResponse(200, {})

    def get(self, url, **kwargs):
        self.calls.append(("GET", url))
        return FakeResponse(200, self.deposition)

    def writes(self):
        return [c for c in self.calls if c[0] in ("POST", "PUT")]

    def published(self):
        return [c for c in self.calls if c[1].endswith("/actions/publish")]


class DryRunSendsNothing(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.env = mock.patch.dict("os.environ", {"ZENODO_TOKEN": "a" * 60})

    def test_dry_run_makes_no_write_request(self):
        fake = FakeHTTP()
        self.env.start()
        self.addCleanup(self.env.stop)
        with mock.patch.object(self.module, "requests", fake):
            rc = self.module.main(["--dry-run"])
        self.assertEqual(rc, 0)
        self.assertEqual(fake.writes(), [], "a dry run must not create or upload")
        self.assertEqual(fake.published(), [])

    def test_dry_run_on_existing_deposition_still_writes_nothing(self):
        fake = FakeHTTP(staged=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        with mock.patch.object(self.module, "requests", fake):
            rc = self.module.main(["--dry-run", "--deposition-id", "42", "--publish"])
        self.assertEqual(rc, 0)
        self.assertEqual(fake.writes(), [])
        self.assertEqual(fake.calls, [], "a dry run should not even read")

    def test_missing_token_stops_before_any_request(self):
        fake = FakeHTTP()
        with mock.patch.dict("os.environ", {}, clear=True), \
                mock.patch.object(self.module, "requests", fake):
            rc = self.module.main(["--deposition-id", "42", "--publish"])
        self.assertEqual(rc, 2)
        self.assertEqual(fake.calls, [])


class StagingDoesNotPublish(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.env = mock.patch.dict("os.environ", {"ZENODO_TOKEN": "a" * 60})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_new_deposition_is_staged_not_published(self):
        fake = FakeHTTP()
        with mock.patch.object(self.module, "requests", fake):
            rc = self.module.main([])
        self.assertEqual(rc, 0)
        self.assertEqual(fake.published(), [], "staging must not publish by default")
        self.assertIn(("POST", f"{self.module.api_base()}/depositions"), fake.calls)

    def test_existing_staged_file_is_not_re_uploaded(self):
        fake = FakeHTTP(staged_md5="0" * 32, staged=True)
        with mock.patch.object(self.module, "requests", fake):
            rc = self.module.main(["--deposition-id", "42"])
        self.assertEqual(rc, 0)
        self.assertEqual([c for c in fake.calls if c[0] == "PUT" and "bucket" in c[1]],
                         [], "the archive was already staged")


class PublishGuard(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.env = mock.patch.dict("os.environ", {"ZENODO_TOKEN": "a" * 60})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_checksum_mismatch_refuses_to_publish(self):
        fake = FakeHTTP(staged_md5="deadbeef" + "0" * 24, staged=True)
        with mock.patch.object(self.module, "requests", fake):
            rc = self.module.main(["--deposition-id", "42", "--publish"])
        self.assertEqual(rc, 2)
        self.assertEqual(fake.published(), [], "a stale upload must not become a DOI")

    def test_missing_staged_file_refuses_to_publish(self):
        fake = FakeHTTP(staged=False)
        with mock.patch.object(self.module, "requests", fake):
            rc = self.module.main(["--deposition-id", "42", "--publish"])
        self.assertEqual(rc, 2)
        self.assertEqual(fake.published(), [])

    def test_matching_checksum_publishes(self):
        fake = FakeHTTP(staged_md5=local_md5(self.module), staged=True)
        with mock.patch.object(self.module, "requests", fake):
            rc = self.module.main(["--deposition-id", "42", "--publish"])
        self.assertEqual(rc, 0)
        self.assertEqual(len(fake.published()), 1)

    def test_already_published_record_is_not_touched(self):
        fake = FakeHTTP(staged_md5=local_md5(self.module), staged=True, submitted=True)
        with mock.patch.object(self.module, "requests", fake):
            rc = self.module.main(["--deposition-id", "42", "--publish"])
        self.assertEqual(rc, 2)
        self.assertEqual(fake.published(), [])


if __name__ == "__main__":
    unittest.main()
