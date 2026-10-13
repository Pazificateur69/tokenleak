"""Packaging checks for the PyPI release (stdlib only, no build)."""
import io
import os
import re
import sys
import unittest
from unittest import mock

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "skills", "tokenleak", "scripts"))
import tokenleak as T  # noqa: E402


def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()


class Packaging(unittest.TestCase):
    def test_version_is_dynamic_from_module(self):
        py = read("pyproject.toml")
        project = py.split("[project]", 1)[1].split("\n[", 1)[0]
        self.assertIn('dynamic = ["version"]', project)
        self.assertIsNone(re.search(r"^version\s*=", project, re.M))  # a static one would drift from __version__
        self.assertIn('version = { attr = "tokenleak.__version__" }', py)
        self.assertIn('tokenleak = "tokenleak:main"', py)

    def test_cli_only_rules_link_is_pinned_to_the_installed_tag(self):
        out = io.StringIO()
        with mock.patch("tokenleak.open", side_effect=OSError, create=True):  # no SKILL.md next to the module
            T.print_rules(out)
        self.assertIn("/blob/v%s/skills/tokenleak/SKILL.md" % T.__version__, out.getvalue())

    @unittest.skipUnless(all(os.path.exists(os.path.join(ROOT, *p)) for p in (
        ("README.md",), ("README.fr.md",), ("docs", "index.html"), ("skills", "tokenleak", "scripts", "tokenleak.py"))),
        "not in the sdist")
    def test_readme_pins_this_release_and_its_hash(self):
        import hashlib
        readme = read("README.md") + read("README.fr.md") + read("docs", "index.html")
        with open(os.path.join(ROOT, "skills", "tokenleak", "scripts", "tokenleak.py"), "rb") as f:
            digest = hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()  # Windows checkouts get CRLF; the release is LF
        pins = re.findall(r"tokenleak/(v[0-9.]+|main)/skills/tokenleak/(?:scripts/tokenleak\.py|SKILL\.md)", readme)
        self.assertTrue(pins)
        self.assertEqual(set(pins), {"v" + T.__version__})  # bump the README pin with every release
        self.assertIn(digest, readme)

    @unittest.skipUnless(os.path.exists(os.path.join(ROOT, ".github")), "not in the sdist")
    def test_publish_uses_trusted_publishing(self):
        wf = read(".github", "workflows", "publish.yml")
        for s in ("types: [published]", "id-token: write", "name: pypi", "pypa/gh-action-pypi-publish"):
            self.assertIn(s, wf)
        self.assertNotIn("secrets.", wf)


if __name__ == "__main__":
    unittest.main()
