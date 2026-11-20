"""Generates a one-shot config.yml for the "Build (one-off app, manual)" workflow.

The workflow passes the app details in as environment variables (see
.github/workflows/oneoff.yaml). Everything optional the user left blank is
inherited from this repository's own config.yml `defaults:` section, so a
one-off build behaves exactly like a normal config.yml app -- it just never
touches config.yml itself and never runs on a schedule.

Usage:
    python oneoff_config.py --base config.yml --out /tmp/oneoff-config.yml
"""

from __future__ import annotations

import argparse
import copy
import os
from pathlib import Path
from typing import Mapping

import yaml

REQUIRED_INPUTS = (
    ("APP_ID", "app_id"),
    ("APP_NAME", "app_name"),
    ("PACKAGE_NAME", "package_name"),
    ("APKMIRROR_ORG", "apkmirror_org"),
    ("APKMIRROR_APP", "apkmirror_app"),
    ("PATCHES_REPO", "patches_repo"),
)

DEFAULT_MODULE_AUTHOR = "Morphe Multi-App Builder"


def _input(env: Mapping[str, str], name: str) -> str | None:
    """Return a trimmed env value, or None when unset/blank."""
    value = (env.get(name) or "").strip()
    return value or None


def _split_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def build_config(
    base_path: str | Path = "config.yml", env: Mapping[str, str] | None = None
) -> dict:
    """Build the one-off config document as a plain dict.

    Required app identity comes from the workflow inputs; anything the user
    left blank stays on this repo's config.yml defaults.
    """
    env = os.environ if env is None else env

    values: dict[str, str] = {}
    missing: list[str] = []
    for env_name, label in REQUIRED_INPUTS:
        value = _input(env, env_name)
        if value is None:
            missing.append(label)
        else:
            values[env_name] = value
    if missing:
        raise SystemExit(
            "Missing required input(s): "
            + ", ".join(missing)
            + " -- set them in the workflow's Run workflow form."
        )

    base_path = Path(base_path)
    base_raw: dict = {}
    if base_path.exists():
        with open(base_path, encoding="utf-8") as handle:
            base_raw = yaml.safe_load(handle) or {}
    if not isinstance(base_raw, dict):
        base_raw = {}

    defaults = copy.deepcopy(base_raw.get("defaults") or {})

    # --- Optional global overrides: only replace what was actually provided.
    architectures = _input(env, "ARCHITECTURES")
    if architectures:
        defaults["architectures"] = _split_list(architectures)

    dpi = _input(env, "DPI")
    if dpi:
        defaults["dpi"] = dpi

    build_mode = _input(env, "BUILD_MODE")
    if build_mode:
        defaults["build_mode"] = build_mode

    cli = dict(defaults.get("cli") or {})
    cli_repo = _input(env, "CLI_REPO")
    if cli_repo:
        cli["repo"] = cli_repo
    cli_asset_regex = _input(env, "CLI_ASSET_REGEX")
    if cli_asset_regex:
        cli["asset_regex"] = cli_asset_regex
    if cli:
        defaults["cli"] = cli

    patches_defaults = dict(defaults.get("patches") or {})
    patches_asset_regex = _input(env, "PATCHES_ASSET_REGEX")
    if patches_asset_regex:
        patches_defaults["asset_regex"] = patches_asset_regex
    if patches_defaults:
        defaults["patches"] = patches_defaults

    # --- The single app this run builds.
    app: dict = {
        "id": values["APP_ID"],
        "enabled": True,
        "name": values["APP_NAME"],
        "package_name": values["PACKAGE_NAME"],
        "apkmirror": {
            "org": values["APKMIRROR_ORG"],
            "app": values["APKMIRROR_APP"],
        },
        "patches": {"repo": values["PATCHES_REPO"]},
        "include_patches": [],
        "exclude_patches": [],
    }

    release_prefix = _input(env, "APKMIRROR_RELEASE_PREFIX")
    if release_prefix:
        app["apkmirror"]["release_prefix"] = release_prefix

    version = _input(env, "VERSION")
    if version:
        app["version"] = version

    module_id = _input(env, "MODULE_ID")
    if module_id:
        app["module"] = {
            "id": module_id,
            "author": _input(env, "MODULE_AUTHOR") or DEFAULT_MODULE_AUTHOR,
        }

    return {"defaults": defaults, "apps": [app]}


def dump_config(config: dict, out_path: str | Path) -> Path:
    """Write the generated config as valid YAML."""
    out_path = Path(out_path)
    text = yaml.safe_dump(config, sort_keys=False, allow_unicode=True)
    out_path.write_text(text, encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a one-off config.yml from workflow inputs"
    )
    parser.add_argument(
        "--base", default="config.yml", help="config.yml whose defaults are reused"
    )
    parser.add_argument(
        "--out", default="oneoff-config.yml", help="Where to write the generated config"
    )
    args = parser.parse_args(argv)

    out_path = dump_config(build_config(args.base), args.out)
    print(f"--- Generated {out_path} ---")
    print(out_path.read_text(encoding="utf-8"))
    print("--- End config ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
