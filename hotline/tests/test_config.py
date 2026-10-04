"""Regression tests for hotline.config, .env.example names and the Vercel deploy config."""

import dataclasses
import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from hotline import config

HOTLINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = HOTLINE_DIR.parent
ENV_LINE = re.compile(r"^([A-Z][A-Z0-9_]*)=(.*)$")
NEW_HOTLINE_NAMES = (
    "ANTHROPIC_TRANSLATE_MODEL",
    "ANTHROPIC_EXTRACT_MODEL",
    "ELEVENLABS_AGENT_LLM",
    "ELEVENLABS_WEBHOOK_ID",
    "HOTLINE_TOOL_SECRET",
    "HOTLINE_ADMIN_SECRET",
    "DEMO_USER",
    "DEMO_PASSWORD",
    "LEDGER_PIN_SALT",
    "PRICE_INCLUDE_SYNTHETIC",
)
FRESH_IMPORT_SCRIPT = """
import dataclasses, json
from fastapi.testclient import TestClient
import hotline.main
from hotline import config
client = TestClient(hotline.main.app)
print(json.dumps({
    "settings": dataclasses.asdict(config.settings),
    "health": client.get("/api/health").status_code,
    "deep": client.get("/api/health?deep=1", headers={"X-Hotline-Admin-Secret": ""}).status_code,
}))
"""


def _env_example() -> dict[str, str]:
    lines = (REPO_ROOT / ".env.example").read_text().splitlines()
    return {m.group(1): m.group(2) for m in map(ENV_LINE.match, lines) if m}


def test_fresh_import_of_main_with_empty_env_is_closed():
    """Importing hotline.main in a clean process (as on a cold Vercel start with no env) must
    not raise, and deep health must stay closed while HOTLINE_ADMIN_SECRET is unset."""
    env = {"PATH": os.environ.get("PATH", ""), "VERCEL": "1"}
    result = subprocess.run(
        [sys.executable, "-c", FRESH_IMPORT_SCRIPT],
        cwd=HOTLINE_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout.strip().splitlines()[-1])
    secrets = {k: v for k, v in out["settings"].items() if k != "price_include_synthetic"}
    assert all(value is None for value in secrets.values())
    assert out["settings"]["price_include_synthetic"] is True
    assert out["health"] == 200
    assert out["deep"] == 401


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(None, True), ("", True), ("true", True), ("false", False), ("FALSE", False)],
)
def test_price_include_synthetic_defaults_true(monkeypatch, raw, expected):
    if raw is None:
        monkeypatch.delenv("PRICE_INCLUDE_SYNTHETIC", raising=False)
    else:
        monkeypatch.setenv("PRICE_INCLUDE_SYNTHETIC", raw)
    assert config.load_settings().price_include_synthetic is expected


def test_every_setting_has_a_name_in_env_example():
    names = _env_example()
    missing = [f.name.upper() for f in dataclasses.fields(config.Settings) if f.name.upper() not in names]
    assert missing == []


def test_new_hotline_names_in_env_example_have_no_values():
    names = _env_example()
    assert {name: names.get(name) for name in NEW_HOTLINE_NAMES} == dict.fromkeys(NEW_HOTLINE_NAMES, "")


def test_vercel_entrypoint_and_function_config_agree():
    """Vercel builds hotline.main:app; vercel.json must target the same file and keep the
    FastAPI framework preset (without it the build has no function and /api/* returns 404)."""
    pyproject = tomllib.loads((HOTLINE_DIR / "pyproject.toml").read_text())
    vercel = json.loads((HOTLINE_DIR / "vercel.json").read_text())
    entrypoint = pyproject["tool"]["vercel"]["entrypoint"]
    module, attr = entrypoint.split(":")
    assert entrypoint == "hotline.main:app"
    assert vercel["framework"] == "fastapi"
    function_file = module.replace(".", "/") + ".py"
    assert (HOTLINE_DIR / function_file).is_file()
    function = vercel["functions"][function_file]
    assert function["maxDuration"] == 300
    for pattern in ("evals/**", "tests/**", "agent/**", "scripts/**", ".cache/**"):
        assert pattern in function["excludeFiles"]
    assert attr == "app"


def test_no_heavy_dependencies():
    """torch/transformers/faster-whisper belong to server/, never the Vercel bundle."""
    pyproject = tomllib.loads((HOTLINE_DIR / "pyproject.toml").read_text())
    deps = " ".join(pyproject["project"]["dependencies"]).lower()
    for heavy in ("torch", "transformers", "faster-whisper", "ctranslate2", "numpy"):
        assert heavy not in deps
