"""Sync the ElevenLabs agent config from the repo (#54).

Default is --dry-run: reads the workspace and prints the planned changes without
secrets. --apply upserts the workspace secret, the four webhook tools, patches the
agent (prompt with knowledge inlined, first message, language, LLM, DTMF, tools,
post-call webhook) and turns retries on for the webhook. Idempotent: a second run
makes no POSTs.

Run from hotline/:  uv run python scripts/sync_agent.py [--apply]
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
from pathlib import Path

import httpx

HOTLINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = HOTLINE_DIR.parent
AGENT_DIR = HOTLINE_DIR / "agent"
KNOWLEDGE_PATH = REPO_ROOT / "knowledge" / "coffee-problems-uganda.md"

API = "https://api.elevenlabs.io"
PRODUCTION_BASE_URL = "https://hack-nation-world-bank-agriculture.vercel.app"
KNOWLEDGE_MARKER = "<!-- KNOWLEDGE -->"
ALLOWED_DOUBLE_BRACE = re.compile(r"\{\{\s*system__[a-z_]+\s*\}\}")
HTTP_TIMEOUT_SECS = 30.0
PENDING = "<new>"
EXIT_USAGE = 2


class SyncError(Exception):
    """A config problem the operator must fix; main() turns it into a non-zero exit."""


# --- pure builders ---------------------------------------------------------


def require_production_url(base_url: str) -> str:
    cleaned = base_url.rstrip("/")
    if cleaned != PRODUCTION_BASE_URL:
        raise SyncError(f"PUBLIC_BASE_URL must be the production alias {PRODUCTION_BASE_URL} (previews are protected and would 401)")
    return cleaned


def build_prompt(prompt_md: str, knowledge_md: str) -> str:
    count = prompt_md.count(KNOWLEDGE_MARKER)
    if count != 1:
        raise SyncError(f"prompt must contain {KNOWLEDGE_MARKER} exactly once, found {count}")
    final = prompt_md.replace(KNOWLEDGE_MARKER, knowledge_md.strip())
    leftovers = [m for m in re.findall(r"\{\{.*?\}\}", final) if not ALLOWED_DOUBLE_BRACE.fullmatch(m)]
    if leftovers:
        raise SyncError(f"prompt contains unknown double-brace variables: {leftovers}")
    return final


def build_tool_configs(tools_spec: dict, base_url: str, secret_id: str) -> list[dict]:
    """Fill the tools.json templates; every tool gets the secret header and a 10 s timeout."""
    text = json.dumps(tools_spec["tools"]).replace("__BASE_URL__", base_url).replace("__SECRET_ID__", secret_id)
    return json.loads(text)


def desired_agent_patch(
    *, prompt: str, first_message: str, llm: str, tool_ids: list[str], webhook_id: str | None, agent_cfg: dict
) -> dict:
    patch = {
        "conversation_config": {
            "agent": {
                "first_message": first_message,
                "language": agent_cfg["language"],
                "prompt": {"prompt": prompt, "llm": llm, "tool_ids": tool_ids},
            },
            "conversation": {"dtmf_input_settings": agent_cfg["dtmf_input_settings"]},
        }
    }
    if "temperature" in agent_cfg:
        patch["conversation_config"]["agent"]["prompt"]["temperature"] = agent_cfg["temperature"]
    if "tts" in agent_cfg:
        patch["conversation_config"]["tts"] = agent_cfg["tts"]
    if webhook_id:
        patch["platform_settings"] = {
            "workspace_overrides": {
                "webhooks": {
                    "post_call_webhook_id": webhook_id,
                    "events": agent_cfg["webhook_events"],
                    "send_audio": agent_cfg["send_audio"],
                }
            }
        }
    return patch


def is_subset(desired, current) -> bool:
    """True when every value in desired is already present in current."""
    if isinstance(desired, dict):
        return isinstance(current, dict) and all(k in current and is_subset(v, current[k]) for k, v in desired.items())
    return desired == current


# --- API client ------------------------------------------------------------


class Client:
    """Thin ElevenLabs client. With dry_run=True any non-GET call raises."""

    def __init__(self, api_key: str, dry_run: bool, http: httpx.Client | None = None):
        self.dry_run = dry_run
        self.http = http or httpx.Client(base_url=API, headers={"xi-api-key": api_key}, timeout=HTTP_TIMEOUT_SECS)

    def call(self, method: str, path: str, body: dict | None = None) -> dict:
        if self.dry_run and method != "GET":
            raise RuntimeError(f"dry-run refused {method} {path}")
        try:
            resp = self.http.request(method, path, json=body)
        except httpx.HTTPError as exc:
            raise SyncError(f"{method} {path} failed: {type(exc).__name__}") from exc
        if resp.status_code >= 400:
            raise SyncError(f"{method} {path} returned HTTP {resp.status_code}")
        return resp.json() if resp.content else {}


# --- sync steps ------------------------------------------------------------


def plan_secret(client: Client, name: str, value: str, apply: bool, log: list[str]) -> str:
    secrets = client.call("GET", "/v1/convai/secrets").get("secrets", [])
    existing = next((s for s in secrets if s.get("name") == name), None)
    if existing:
        log.append(f"secret {name}: exists, value {'updated' if apply else 'would be updated'}")
        if apply:
            client.call("PATCH", f"/v1/convai/secrets/{existing['secret_id']}", {"type": "update", "name": name, "value": value})
        return existing["secret_id"]
    log.append(f"secret {name}: {'created' if apply else 'would be created'}")
    if not apply:
        return PENDING
    created = client.call("POST", "/v1/convai/secrets", {"type": "new", "name": name, "value": value})
    return created["secret_id"]


def plan_tools(client: Client, desired: list[dict], apply: bool, log: list[str]) -> list[str]:
    listed = client.call("GET", "/v1/convai/tools").get("tools", [])
    by_name = {t["tool_config"]["name"]: t for t in listed}
    ids = []
    for config in desired:
        name = config["name"]
        current = by_name.get(name)
        if current is None:
            log.append(f"tool {name}: {'created' if apply else 'would be created'}")
            created = client.call("POST", "/v1/convai/tools", {"tool_config": config}) if apply else {"id": PENDING}
            ids.append(created["id"])
        elif is_subset(config, current["tool_config"]):
            log.append(f"tool {name}: up to date")
            ids.append(current["id"])
        else:
            log.append(f"tool {name}: {'updated' if apply else 'would be updated'}")
            if apply:
                client.call("PATCH", f"/v1/convai/tools/{current['id']}", {"tool_config": config})
            ids.append(current["id"])
    return ids


def plan_agent(client: Client, agent_id: str, patch: dict, apply: bool, log: list[str]) -> None:
    current = client.call("GET", f"/v1/convai/agents/{agent_id}")
    if is_subset(patch, current):
        log.append("agent: up to date")
        return
    changed = sorted(_changed_paths(patch, current))
    log.append(f"agent: {'patched' if apply else 'would be patched'} ({', '.join(changed)})")
    if apply:
        client.call("PATCH", f"/v1/convai/agents/{agent_id}", patch)


def _changed_paths(desired, current, prefix="") -> list[str]:
    if isinstance(desired, dict):
        out = []
        for key, value in desired.items():
            sub = current.get(key) if isinstance(current, dict) else None
            out += _changed_paths(value, sub, f"{prefix}{key}.")
        return out
    return [] if desired == current else [prefix.rstrip(".")]


def plan_webhook_retries(client: Client, webhook_id: str, apply: bool, log: list[str]) -> None:
    hooks = client.call("GET", "/v1/workspace/webhooks").get("webhooks", [])
    hook = next((h for h in hooks if h.get("webhook_id") == webhook_id), None)
    if hook is None:
        raise SyncError("ELEVENLABS_WEBHOOK_ID is not a workspace webhook")
    if hook.get("retry_enabled"):
        log.append("webhook: retries already on")
        return
    log.append(f"webhook: retries {'enabled' if apply else 'would be enabled'}")
    if apply:
        client.call("PATCH", f"/v1/workspace/webhooks/{webhook_id}", {"name": hook["name"], "is_disabled": False, "retry_enabled": True})


def sync(client: Client, env: dict, apply: bool, attach_webhook: bool = True) -> list[str]:
    base_url = require_production_url(env.get("PUBLIC_BASE_URL") or PRODUCTION_BASE_URL)
    missing = [k for k in ("ELEVENLABS_AGENT_ID", "ELEVENLABS_AGENT_LLM", "HOTLINE_TOOL_SECRET") if not env.get(k)]
    if attach_webhook and not env.get("ELEVENLABS_WEBHOOK_ID"):
        missing.append("ELEVENLABS_WEBHOOK_ID")
    if missing:
        raise SyncError(f"missing env vars: {', '.join(missing)}")
    tools_spec = json.loads((AGENT_DIR / "tools.json").read_text(encoding="utf-8"))
    agent_cfg = json.loads((AGENT_DIR / "agent.json").read_text(encoding="utf-8"))
    prompt = build_prompt((AGENT_DIR / "prompt.md").read_text(encoding="utf-8"), KNOWLEDGE_PATH.read_text(encoding="utf-8"))
    first_message = (AGENT_DIR / "first_message_en.txt").read_text(encoding="utf-8").strip()

    log = [f"mode: {'APPLY' if apply else 'dry-run'}", f"tools base url: {base_url}", f"prompt: {len(prompt)} chars (knowledge inlined once)"]
    secret_id = plan_secret(client, tools_spec["secret_name"], env["HOTLINE_TOOL_SECRET"], apply, log)
    configs = build_tool_configs(tools_spec, base_url, secret_id)
    tool_ids = plan_tools(client, configs, apply, log)
    webhook_id = env["ELEVENLABS_WEBHOOK_ID"] if attach_webhook else None
    patch = desired_agent_patch(
        prompt=prompt, first_message=first_message, llm=env["ELEVENLABS_AGENT_LLM"],
        tool_ids=tool_ids, webhook_id=webhook_id, agent_cfg=agent_cfg,
    )
    plan_agent(client, env["ELEVENLABS_AGENT_ID"], patch, apply, log)
    if webhook_id:
        plan_webhook_retries(client, webhook_id, apply, log)
    else:
        log.append("webhook: skipped (--no-webhook)")
    return log


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="write changes (default is a dry run)")
    parser.add_argument("--dry-run", action="store_true", help="print planned changes only (default)")
    parser.add_argument("--no-webhook", action="store_true", help="do not attach the post-call webhook (attach only once #11 is live)")
    args = parser.parse_args(argv)
    if args.apply and args.dry_run:
        parser.error("--apply and --dry-run are mutually exclusive")
    env = dict(os.environ)
    if not env.get("ELEVENLABS_API_KEY"):
        print("error: ELEVENLABS_API_KEY is not set", file=sys.stderr)
        return EXIT_USAGE
    try:
        log = sync(Client(env["ELEVENLABS_API_KEY"], dry_run=not args.apply), env, args.apply, not args.no_webhook)
    except SyncError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    print("\n".join(log))
    return 0


if __name__ == "__main__":
    sys.exit(main())
