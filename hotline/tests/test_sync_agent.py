"""Tests for scripts/sync_agent.py (#54) against a fake ElevenLabs API."""

import copy
import importlib.util
import json
from pathlib import Path

import httpx
import pytest

HOTLINE_DIR = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sync_agent", HOTLINE_DIR / "scripts" / "sync_agent.py")
sa = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sa)

SECRET_VALUE = "super-secret-tool-value-123"
ENV = {
    "ELEVENLABS_API_KEY": "key",
    "ELEVENLABS_AGENT_ID": "agent_1",
    "ELEVENLABS_AGENT_LLM": "claude-sonnet-5-5",
    "ELEVENLABS_WEBHOOK_ID": "wh_1",
    "HOTLINE_TOOL_SECRET": SECRET_VALUE,
    "PUBLIC_BASE_URL": sa.PRODUCTION_BASE_URL,
}
TOOLS = json.loads((HOTLINE_DIR / "agent" / "tools.json").read_text())


class FakeApi:
    """In-memory ElevenLabs workspace that records every request."""

    def __init__(self):
        self.secrets, self.tools, self.agent = [], [], {"agent_id": "agent_1"}
        self.webhooks = [{"webhook_id": "wh_1", "name": "post-call", "retry_enabled": False}]
        self.requests = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        method, path = request.method, request.url.path
        body = json.loads(request.content) if request.content else None
        self.requests.append((method, path))
        if path == "/v1/convai/secrets":
            if method == "POST":
                self.secrets.append({"secret_id": "sec_1", "name": body["name"]})
                return httpx.Response(200, json={"secret_id": "sec_1"})
            return httpx.Response(200, json={"secrets": self.secrets})
        if path == "/v1/convai/tools":
            if method == "POST":
                tool = {"id": f"tool_{len(self.tools)}", "tool_config": body["tool_config"]}
                self.tools.append(tool)
                return httpx.Response(200, json={"id": tool["id"]})
            return httpx.Response(200, json={"tools": self.tools})
        if path.startswith("/v1/convai/tools/") and method == "PATCH":
            tool = next(t for t in self.tools if t["id"] == path.rsplit("/", 1)[1])
            tool["tool_config"] = body["tool_config"]
            return httpx.Response(200, json={})
        if path.startswith("/v1/convai/secrets/") and method == "PATCH":
            return httpx.Response(200, json={})
        if path == "/v1/convai/agents/agent_1":
            if method == "PATCH":
                self.agent = merge(self.agent, body)
            return httpx.Response(200, json=self.agent)
        if path == "/v1/workspace/webhooks":
            return httpx.Response(200, json={"webhooks": self.webhooks})
        if path == "/v1/workspace/webhooks/wh_1" and method == "PATCH":
            self.webhooks[0]["retry_enabled"] = body["retry_enabled"]
            return httpx.Response(200, json={})
        return httpx.Response(404, json={})

    def client(self, dry_run):
        http = httpx.Client(base_url="https://api.test", transport=httpx.MockTransport(self.handler))
        return sa.Client("key", dry_run=dry_run, http=http)


def merge(base, patch):
    out = copy.deepcopy(base)
    for key, value in patch.items():
        out[key] = merge(out.get(key, {}), value) if isinstance(value, dict) else value
    return out


def test_tools_json_matches_spec_names_and_wiring():
    configs = sa.build_tool_configs(TOOLS, sa.PRODUCTION_BASE_URL, "sec_1")
    assert [c["name"] for c in configs] == ["identify_farmer", "find_farmer_by_location", "register_farmer", "get_weather_forecast"]
    fields = {
        "identify_farmer": {"pin"},
        "find_farmer_by_location": {"first_name", "district", "village", "parish", "sub_county"},
        "register_farmer": {"first_name", "district", "sub_county", "parish", "village", "coffee_type"},
        "get_weather_forecast": {"district"},
    }
    for config in configs:
        schema = config["api_schema"]
        props = schema["request_body_schema"]["properties"]
        assert schema["url"] == f"{sa.PRODUCTION_BASE_URL}/api/tools/{config['name']}"
        assert schema["method"] == "POST"
        assert schema["request_headers"] == {"X-Hotline-Tool-Secret": {"secret_id": "sec_1"}}
        assert config["response_timeout_secs"] == 10
        assert props["conversation_id"] == {"type": "string", "dynamic_variable": "system__conversation_id"}
        assert props["call_sid"] == {"type": "string", "dynamic_variable": "system__call_sid"}
        assert set(props) - {"conversation_id", "call_sid"} == fields[config["name"]]
        for prop in props.values():
            assert len([k for k in ("description", "dynamic_variable", "constant_value", "is_omitted") if k in prop]) == 1


def test_marker_replaced_exactly_once():
    final = sa.build_prompt("a\n<!-- KNOWLEDGE -->\nb", "KNOW")
    assert final == "a\nKNOW\nb"


@pytest.mark.parametrize("prompt", ["no marker", "<!-- KNOWLEDGE --> and <!-- KNOWLEDGE -->"])
def test_marker_missing_or_duplicate_fails(prompt):
    with pytest.raises(sa.SyncError):
        sa.build_prompt(prompt, "k")


def test_leftover_double_braces_fail_but_system_variables_pass():
    with pytest.raises(sa.SyncError):
        sa.build_prompt("<!-- KNOWLEDGE -->", "text {{oops}}")
    assert "{{system__time}}" in sa.build_prompt("<!-- KNOWLEDGE -->", "text {{system__time}}")


def test_real_prompt_builds():
    prompt = (HOTLINE_DIR / "agent" / "prompt.md").read_text()
    knowledge = (sa.KNOWLEDGE_PATH).read_text()
    final = sa.build_prompt(prompt, knowledge)
    assert sa.KNOWLEDGE_MARKER not in final and "## 2 Top 5" in final


def test_non_production_url_refused():
    with pytest.raises(sa.SyncError):
        sa.require_production_url("https://hack-nation-git-feature.vercel.app")
    assert sa.require_production_url(sa.PRODUCTION_BASE_URL + "/") == sa.PRODUCTION_BASE_URL


def test_dry_run_makes_zero_writes_and_no_secret_in_output():
    api = FakeApi()
    log = sa.sync(api.client(dry_run=True), ENV, apply=False)
    assert {m for m, _ in api.requests} == {"GET"}
    assert SECRET_VALUE not in "\n".join(log)
    assert api.secrets == [] and api.tools == []


def test_dry_client_refuses_writes():
    with pytest.raises(RuntimeError):
        sa.Client("k", dry_run=True, http=httpx.Client(base_url="https://x", transport=httpx.MockTransport(lambda r: httpx.Response(200)))).call("POST", "/x", {})


def test_apply_then_second_run_makes_no_posts():
    api = FakeApi()
    log = sa.sync(api.client(dry_run=False), ENV, apply=True)
    assert len(api.tools) == 4 and api.webhooks[0]["retry_enabled"] is True
    patch = api.agent["conversation_config"]["agent"]
    assert patch["language"] == "sw" and patch["prompt"]["llm"] == "claude-sonnet-5-5"
    assert api.agent["conversation_config"]["conversation"]["dtmf_input_settings"]["redact_input"] is True
    assert api.agent["platform_settings"]["workspace_overrides"]["webhooks"]["events"] == ["transcript"]
    assert SECRET_VALUE not in "\n".join(log)
    api.requests.clear()
    sa.sync(api.client(dry_run=False), ENV, apply=True)
    assert "POST" not in {m for m, _ in api.requests}
    assert ("PATCH", "/v1/convai/agents/agent_1") not in api.requests
    assert len(api.tools) == 4


def test_missing_env_fails():
    with pytest.raises(sa.SyncError):
        sa.sync(FakeApi().client(dry_run=True), {**ENV, "ELEVENLABS_AGENT_LLM": ""}, apply=False)


def test_main_returns_nonzero_on_bad_url(monkeypatch, capsys):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    for key, value in ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://localhost:8000")
    assert sa.main([]) == sa.EXIT_USAGE
    assert SECRET_VALUE not in capsys.readouterr().out
