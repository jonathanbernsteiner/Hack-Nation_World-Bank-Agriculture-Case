"""Tests for scripts/import_twilio_number.py (#56) against fake Twilio + ElevenLabs APIs."""

import importlib.util
import json
from pathlib import Path
from urllib.parse import parse_qs

import httpx

HOTLINE_DIR = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("import_twilio_number", HOTLINE_DIR / "scripts" / "import_twilio_number.py")
itn = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(itn)

TOKEN = "twilio-token-SECRET"
KEY = "eleven-key-SECRET"
ENV = {
    "TWILIO_ACCOUNT_SID": "AC123",
    "TWILIO_AUTH_TOKEN": TOKEN,
    "TWILIO_PHONE_NUMBER": "+16282729173",
    "ELEVENLABS_API_KEY": KEY,
    "ELEVENLABS_AGENT_ID": "agent_1",
}
OLD_URL = "https://old.ngrok.app/voice?x=secretq"


class Fake:
    def __init__(self, imported=None):
        self.requests = []  # (method, host, path, body)
        self.imported = imported
        self.twilio_voice_url = OLD_URL

    def handler(self, request: httpx.Request) -> httpx.Response:
        host, path, method = request.url.host, request.url.path, request.method
        raw = request.content.decode() if request.content else ""
        body = json.loads(raw) if raw.startswith("{") else {k: v[0] for k, v in parse_qs(raw).items()}
        self.requests.append((method, host, path, body))
        if host == "api.twilio.com":
            if method == "GET":
                return httpx.Response(200, json={"incoming_phone_numbers": [
                    {"sid": "PN1", "voice_url": self.twilio_voice_url, "voice_method": "POST", "status_callback": ""}]})
            self.twilio_voice_url = body["VoiceUrl"]
            return httpx.Response(200, json={})
        if method == "GET":
            return httpx.Response(200, json=[self.imported] if self.imported else [])
        if method == "POST":
            self.imported = {"phone_number_id": "ph_1", "phone_number": ENV["TWILIO_PHONE_NUMBER"]}
            return httpx.Response(200, json={"phone_number_id": "ph_1"})
        if method == "PATCH":
            self.imported = {**self.imported, "assigned_agent": {"agent_id": body["agent_id"]}}
            return httpx.Response(200, json={})
        if method == "DELETE":
            self.imported = None
            return httpx.Response(200, json={})
        return httpx.Response(404)

    def clients(self):
        t = httpx.Client(transport=httpx.MockTransport(self.handler), auth=("a", "b"))
        e = httpx.Client(transport=httpx.MockTransport(self.handler))
        return t, e

    def writes(self):
        return [r for r in self.requests if r[0] != "GET" and r[1] != "api.twilio.com"]


def run(fake, tmp_path, *flags):
    return itn.main(list(flags), env=ENV, clients=fake.clients(), backup_path=tmp_path / "backup.json")


def test_dry_run_is_read_only(tmp_path, capsys):
    fake = Fake()
    assert run(fake, tmp_path) == 0
    assert all(r[0] == "GET" for r in fake.requests)
    assert not (tmp_path / "backup.json").exists()
    assert "would import" in capsys.readouterr().out


def test_apply_backs_up_before_import_and_assigns(tmp_path):
    fake = Fake()
    assert run(fake, tmp_path, "--apply") == 0
    backup = json.loads((tmp_path / "backup.json").read_text())
    assert backup["voice_url"] == OLD_URL and backup["sid"] == "PN1"
    methods = [r[0] for r in fake.requests if r[1] != "api.twilio.com"]
    assert methods == ["GET", "POST", "PATCH"]
    post = next(r for r in fake.requests if r[0] == "POST")
    assert post[3] == {"phone_number": ENV["TWILIO_PHONE_NUMBER"], "label": "Simu ya Kahawa",
                       "sid": "AC123", "token": TOKEN, "provider": "twilio"}
    patch = next(r for r in fake.requests if r[0] == "PATCH")
    assert patch[2].endswith("/ph_1") and patch[3] == {"agent_id": "agent_1"}


def test_backup_file_exists_when_first_elevenlabs_write_happens(tmp_path):
    fake = Fake()
    seen = []
    orig = fake.handler

    def spy(request):
        if request.method == "POST" and request.url.host != "api.twilio.com":
            seen.append((tmp_path / "backup.json").exists())
        return orig(request)

    fake.handler = spy
    run(fake, tmp_path, "--apply")
    assert seen == [True]


def test_second_run_makes_no_write(tmp_path):
    fake = Fake()
    run(fake, tmp_path, "--apply")
    before = len(fake.requests)
    assert run(fake, tmp_path, "--apply") == 0
    assert [r for r in fake.requests[before:] if r[0] in ("POST", "PATCH", "DELETE") and r[1] != "api.twilio.com"] == []


def test_already_imported_without_agent_only_assigns(tmp_path):
    fake = Fake(imported={"phone_number_id": "ph_9", "phone_number": ENV["TWILIO_PHONE_NUMBER"]})
    run(fake, tmp_path, "--apply")
    assert [r[0] for r in fake.writes()] == ["PATCH"]


def test_restore_deletes_and_resets_voice_url(tmp_path):
    fake = Fake()
    run(fake, tmp_path, "--apply")
    fake.twilio_voice_url = "https://api.elevenlabs.io/twilio/inbound_call"
    assert run(fake, tmp_path, "--restore") == 0
    assert fake.imported is None
    post = [r for r in fake.requests if r[1] == "api.twilio.com" and r[0] == "POST"][-1]
    assert post[2].endswith("/IncomingPhoneNumbers/PN1.json")
    assert post[3]["VoiceUrl"] == OLD_URL and post[3]["VoiceMethod"] == "POST"


def test_apply_after_import_keeps_original_backup(tmp_path):
    fake = Fake()
    run(fake, tmp_path, "--apply")
    fake.twilio_voice_url = "https://api.elevenlabs.io/twilio/inbound_call"
    run(fake, tmp_path, "--apply")
    assert json.loads((tmp_path / "backup.json").read_text())["voice_url"] == OLD_URL


def test_restore_without_backup_fails(tmp_path, capsys):
    assert run(Fake(), tmp_path, "--restore") == 1
    assert "no backup" in capsys.readouterr().err


def test_no_secret_in_output(tmp_path, capsys):
    for flags in ((), ("--apply",), ("--restore",)):
        run(Fake(), tmp_path, *flags)
    out = capsys.readouterr()
    assert TOKEN not in out.out + out.err and KEY not in out.out + out.err
    assert "secretq" not in out.out + out.err  # query string redacted


def test_missing_env_exits_2():
    assert itn.main([], env={}) == 2
