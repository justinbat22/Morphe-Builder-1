import tempfile
import unittest
from pathlib import Path

from config import load_config
from oneoff_config import build_config, dump_config


BASE_CONFIG = """
defaults:
  architectures: ["arm64-v8a", "universal"]
  dpi: null
  build_mode: "apk"
  cli:
    repo: "owner/cli"
    asset_regex: '^cli.*\\.jar$'
    channel: "latest"
  patches:
    asset_regex: '^patches.*\\.mpp$'
    channel: "latest"
apps:
  - id: existing
    name: "Existing"
    package_name: "com.example.existing"
    apkmirror:
      org: "example"
      app: "existing"
    patches:
      repo: "owner/patches"
"""

REQUIRED_ENV = {
    "APP_ID": "newapp",
    "APP_NAME": "New App",
    "PACKAGE_NAME": "com.example.newapp",
    "APKMIRROR_ORG": "example",
    "APKMIRROR_APP": "newapp",
    "PATCHES_REPO": "owner/newapp-patches",
}


class OneOffConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name) / "config.yml"
        self.base.write_text(BASE_CONFIG, encoding="utf-8")

    def _load(self, env: dict):
        out = Path(self.tmp.name) / "generated.yml"
        dump_config(build_config(self.base, env), out)
        return load_config(out)[0]

    def test_blank_optionals_inherit_config_defaults(self):
        app = self._load(dict(REQUIRED_ENV))
        self.assertEqual(app.architectures, ["arm64-v8a", "universal"])
        self.assertIsNone(app.dpi)
        self.assertEqual(app.build_mode, "apk")
        self.assertEqual(app.cli.repo, "owner/cli")
        self.assertEqual(app.patches.asset_regex, r"^patches.*\.mpp$")
        # release_prefix falls back to the app slug, like config.yml does.
        self.assertEqual(app.apkmirror_release_prefix, "newapp")

    def test_only_the_single_app_is_generated(self):
        out = Path(self.tmp.name) / "generated.yml"
        dump_config(build_config(self.base, dict(REQUIRED_ENV)), out)
        apps = load_config(out)
        self.assertEqual([app.id for app in apps], ["newapp"])
        self.assertTrue(apps[0].enabled)

    def test_provided_optionals_override_defaults(self):
        env = dict(
            REQUIRED_ENV,
            APKMIRROR_RELEASE_PREFIX="new-release",
            PATCHES_ASSET_REGEX=r"^custom.*\.mpp$",
            CLI_REPO="owner/custom-cli",
            CLI_ASSET_REGEX=r"^custom-cli.*\.jar$",
            VERSION="1.2.3",
            ARCHITECTURES="arm64-v8a, universal",
            DPI="480",
            BUILD_MODE="both",
            MODULE_ID="m-newapp",
            MODULE_AUTHOR="someone",
        )
        app = self._load(env)
        self.assertEqual(app.apkmirror_release_prefix, "new-release")
        self.assertEqual(app.patches.asset_regex, r"^custom.*\.mpp$")
        self.assertEqual(app.cli.repo, "owner/custom-cli")
        self.assertEqual(app.cli.asset_regex, r"^custom-cli.*\.jar$")
        self.assertEqual(app.pinned_version, "1.2.3")
        self.assertEqual(app.architectures, ["arm64-v8a", "universal"])
        self.assertEqual(app.dpi, "480")
        self.assertEqual(app.build_mode, "both")
        self.assertIsNotNone(app.module)
        self.assertEqual(app.module.id, "m-newapp")
        self.assertEqual(app.module.author, "someone")

    def test_module_author_defaults_when_blank(self):
        env = dict(REQUIRED_ENV, BUILD_MODE="module", MODULE_ID="m-newapp")
        app = self._load(env)
        self.assertEqual(app.module.author, "Morphe Multi-App Builder")

    def test_missing_required_input_fails(self):
        with self.assertRaises(SystemExit):
            build_config(self.base, {"APP_ID": "only-id"})


if __name__ == "__main__":
    unittest.main()
