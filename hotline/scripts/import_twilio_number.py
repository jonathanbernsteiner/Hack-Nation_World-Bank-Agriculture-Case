"""Import the Twilio number into ElevenLabs and assign the hotline agent (#56).

Default is --dry-run: read-only, prints what --apply would do. --apply first backs up the
number's current Twilio voice config to hotline/.cache/twilio_number_backup.json, then
imports the number into ElevenLabs and assigns ELEVENLABS_AGENT_ID. Idempotent: if the number
is already imported, only the agent assignment is ensured. --restore deletes the ElevenLabs
number and puts the backed-up VoiceUrl/VoiceMethod back on Twilio.

Run from hotline/:  uv run python scripts/import_twilio_number.py [--dry-run | --apply | --restore]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

import httpx

HOTLINE_DIR = Path(__file__).resolve().parents[1]
BACKUP_PATH = HOTLINE_DIR / ".cache" / "twilio_number_backup.json"
ELEVENLABS_API = "https://api.elevenlabs.io"
TWILIO_API = "https://api.twilio.com/2010-04-01"
NUMBER_LABEL = "Simu ya Kahawa"
HTTP_TIMEOUT_SECS = 30.0
REQUIRED_ENV = (
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_PHONE_NUMBER",
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_AGENT_ID",
)


class ImportError_(Exception):
    """An operator-fixable problem; main() prints it (no secrets) and exits non-zero."""


def redact_url(url: str | None) -> str:
    """Host and path only: never query strings or credentials."""
    if not url:
        return "(none)"
    parts = urlsplit(url)
    return f"{parts.hostname or ''}{parts.path}"


def _check(resp: httpx.Response, what: str) -> dict:
    if resp.status_code >= 400:
        raise ImportError_(f"{what} failed: HTTP {resp.status_code}")
    if not resp.content:
        return {}
    try:
        return resp.json()
    except ValueError as exc:
        raise ImportError_(f"{what} failed: response was not JSON") from exc


class Importer:
    def __init__(self, env: dict, twilio: httpx.Client, eleven: httpx.Client, backup_path: Path = BACKUP_PATH):
        self.env = env
        self.twilio = twilio
        self.eleven = eleven
        self.backup_path = backup_path
        self.number = env["TWILIO_PHONE_NUMBER"]
        self.account = env["TWILIO_ACCOUNT_SID"]

    # --- Twilio ---
    def twilio_number(self) -> dict:
        resp = self.twilio.get(
            f"{TWILIO_API}/Accounts/{self.account}/IncomingPhoneNumbers.json", params={"PhoneNumber": self.number}
        )
        items = _check(resp, "Twilio number lookup").get("incoming_phone_numbers", [])
        if not items:
            raise ImportError_(f"Twilio has no incoming number {self.number}")
        return items[0]

    def write_backup(self, tw: dict, imported: dict | None = None) -> bool:
        """Back up the Twilio config; never overwrite a good backup once ElevenLabs owns the number."""
        already_elevenlabs = "elevenlabs" in (tw.get("voice_url") or "")
        if (already_elevenlabs or imported) and self.backup_path.exists():
            return False
        if already_elevenlabs:
            print("warning: number already points at ElevenLabs and no backup exists; restore will not know the old URL")
        data = {k: tw.get(k) for k in ("sid", "voice_url", "voice_method", "status_callback")}
        self.backup_path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_path.write_text(json.dumps(data, indent=2))
        return True

    # --- ElevenLabs ---
    def eleven_numbers(self) -> list[dict]:
        data = _check(self.eleven.get(f"{ELEVENLABS_API}/v1/convai/phone-numbers"), "ElevenLabs phone-number list")
        return data if isinstance(data, list) else data.get("phone_numbers", [])

    def find_imported(self) -> dict | None:
        return next((n for n in self.eleven_numbers() if n.get("phone_number") == self.number), None)

    def assign_agent(self, phone_id: str) -> None:
        body = {"agent_id": self.env["ELEVENLABS_AGENT_ID"]}
        _check(self.eleven.patch(f"{ELEVENLABS_API}/v1/convai/phone-numbers/{phone_id}", json=body), "agent assignment")

    # --- commands ---
    def run(self, apply: bool) -> list[str]:
        log: list[str] = []
        tw = self.twilio_number()
        log.append(f"twilio: sid={tw['sid']} voice_url={redact_url(tw.get('voice_url'))} method={tw.get('voice_method')}")
        imported = self.find_imported()
        agent = self.env["ELEVENLABS_AGENT_ID"]
        if not apply:
            log.append(f"would back up to {self.backup_path}")
            if imported:
                log.append(f"would ensure agent {agent} on existing number {imported['phone_number_id']}")
            else:
                log.append(f"would import {self.number} as '{NUMBER_LABEL}' and assign agent {agent}")
            log.append("dry run: nothing written (use --apply)")
            return log
        wrote = self.write_backup(tw, imported)  # always before any ElevenLabs write
        log.append(f"backup {'written' if wrote else 'kept (already imported)'}: {self.backup_path}")
        if imported:
            phone_id = imported["phone_number_id"]
            log.append(f"already imported ({phone_id})")
        else:
            body = {
                "phone_number": self.number,
                "label": NUMBER_LABEL,
                "sid": self.account,
                "token": self.env["TWILIO_AUTH_TOKEN"],
                "provider": "twilio",
            }
            created = _check(self.eleven.post(f"{ELEVENLABS_API}/v1/convai/phone-numbers", json=body), "import")
            phone_id = created.get("phone_number_id")
            if not phone_id:
                raise ImportError_("import response has no phone_number_id; check GET /v1/convai/phone-numbers")
            log.append(f"imported ({phone_id})")
        current_agent = (imported or {}).get("assigned_agent") or {}
        if imported and current_agent.get("agent_id") == agent:
            log.append("agent already assigned")
        else:
            self.assign_agent(phone_id)
            log.append(f"agent {agent} assigned")
        return log

    def restore(self) -> list[str]:
        if not self.backup_path.exists():
            raise ImportError_(f"no backup at {self.backup_path}")
        backup = json.loads(self.backup_path.read_text())
        log: list[str] = []
        imported = self.find_imported()
        if imported:
            resp = self.eleven.delete(f"{ELEVENLABS_API}/v1/convai/phone-numbers/{imported['phone_number_id']}")
            _check(resp, "ElevenLabs delete")
            log.append("deleted number from ElevenLabs")
        else:
            log.append("number not in ElevenLabs; nothing to delete")
        form = {"VoiceUrl": backup.get("voice_url") or "", "VoiceMethod": backup.get("voice_method") or "POST"}
        if backup.get("status_callback"):
            form["StatusCallback"] = backup["status_callback"]
        resp = self.twilio.post(f"{TWILIO_API}/Accounts/{self.account}/IncomingPhoneNumbers/{backup['sid']}.json", data=form)
        _check(resp, "Twilio restore")
        log.append(f"twilio voice_url restored to {redact_url(backup.get('voice_url'))} ({form['VoiceMethod']})")
        return log


def build_clients(env: dict) -> tuple[httpx.Client, httpx.Client]:
    twilio = httpx.Client(auth=(env["TWILIO_ACCOUNT_SID"], env["TWILIO_AUTH_TOKEN"]), timeout=HTTP_TIMEOUT_SECS)
    eleven = httpx.Client(headers={"xi-api-key": env["ELEVENLABS_API_KEY"]}, timeout=HTTP_TIMEOUT_SECS)
    return twilio, eleven


def main(argv: list[str] | None = None, env: dict | None = None, clients=None, backup_path: Path = BACKUP_PATH) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="read-only plan (default)")
    mode.add_argument("--apply", action="store_true", help="back up, import and assign the agent")
    mode.add_argument("--restore", action="store_true", help="delete from ElevenLabs and restore the Twilio VoiceUrl")
    args = parser.parse_args(argv)
    env = dict(os.environ) if env is None else env
    missing = [k for k in REQUIRED_ENV if not env.get(k)]
    if missing:
        print(f"missing env: {', '.join(missing)}", file=sys.stderr)
        return 2
    twilio, eleven = clients or build_clients(env)
    importer = Importer(env, twilio, eleven, backup_path)
    try:
        lines = importer.restore() if args.restore else importer.run(apply=args.apply)
    except ImportError_ as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except httpx.HTTPError as exc:
        print(f"error: network failure ({type(exc).__name__})", file=sys.stderr)
        return 1
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
