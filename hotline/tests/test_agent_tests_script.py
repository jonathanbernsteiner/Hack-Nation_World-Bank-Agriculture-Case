"""Unit tests for scripts/agent_tests.py with mocked httpx (no network)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import httpx
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "agent_tests.py"
spec = importlib.util.spec_from_file_location("agent_tests_script", SCRIPT)
at = importlib.util.module_from_spec(spec)
sys.modules["agent_tests_script"] = at
spec.loader.exec_module(at)

TOOL_IDS = {"identify_farmer": "tool_abc"}


def make_api(handler) -> "at.Api":
    return at.Api("key", http=httpx.Client(transport=httpx.MockTransport(handler)))


def test_deny_list_catches_canned_bad_answer():
    assert at.find_denied("Tumia mancozeb, 50 ml kwa lita 20")
    assert at.find_denied("Spray copper oxychloride weekly")


def test_clean_answer_passes():
    clean = "Siwezi kutaja dawa wala kiasi. Tafadhali muulize afisa wa ugani."
    assert at.find_denied(clean) == []
    run = {"status": "passed", "agent_responses": [{"role": "agent", "message": clean}]}
    assert at.evaluate_run("spray", run)["passed"] is True


def test_spray_run_fails_on_deny_list_even_if_platform_passed():
    run = {"status": "passed", "agent_responses": [{"role": "agent", "message": "Tumia cypermethrin"}]}
    result = at.evaluate_run("spray", run)
    assert result["passed"] is False
    assert "deny-list" in result["reasons"][0]


def test_failed_status_is_failure_with_rationale():
    run = {"status": "failed", "condition_result": {"rationale": {"summary": "bad"}}}
    result = at.evaluate_run("forgot", run)
    assert not result["passed"] and "bad" in result["reasons"][0]


def test_report_redacts_pins(tmp_path):
    transcripts = {"t": [{"agent_responses": [{"message": "PIN yako 9001, tisa sifuri sifuri moja", "params": {"pin": "9001"}}]}]}
    path = at.write_report([{"key": "happy", "passed": True}], transcripts, out_dir=tmp_path)
    text = path.read_text(encoding="utf-8")
    assert "9001" not in text and "tisa sifuri sifuri moja" not in text
    assert at.REDACTED in text


def test_names_are_prefixed():
    assert all(t["name"].startswith("hotline-") for t in at.TESTS.values())


def test_tool_payload_references_tool_and_pin():
    body = at.build_test_payload(at.TESTS["happy"], TOOL_IDS)
    assert body["tool_call_parameters"]["referenced_tool"] == {"id": "tool_abc", "type": "webhook"}
    assert body["tool_call_parameters"]["parameters"][0]["eval"]["pattern"] == "9001"
    assert "needs_tool" not in body
    assert at.TESTS["happy"]["tool_call_parameters"].get("referenced_tool") is None  # input not mutated


def test_tool_payload_missing_tool_errors():
    with pytest.raises(at.AgentTestError):
        at.build_test_payload(at.TESTS["happy"], {})


def test_upsert_creates_when_absent_and_updates_when_present():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path, json.loads(request.content or b"{}")))
        return httpx.Response(200, json={"id": "test_new"})

    api = make_api(handler)
    body = at.build_test_payload(at.TESTS["forgot"], TOOL_IDS)
    assert api.upsert_test(body, {}) == "test_new"
    assert api.upsert_test(body, {body["name"]: "test_old"}) == "test_old"
    assert [(m, p) for m, p, _ in calls] == [
        ("POST", "/v1/convai/agent-testing/create"),
        ("PUT", "/v1/convai/agent-testing/test_old"),
    ]


def test_existing_tests_follows_pagination():
    pages = [
        {"tests": [{"name": "hotline-a", "id": "1"}], "has_more": True, "next_cursor": "c2"},
        {"tests": [{"name": "hotline-b", "id": "2"}], "has_more": False, "next_cursor": None},
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=pages[1 if request.url.params.get("cursor") else 0])

    assert make_api(handler).existing_tests() == {"hotline-a": "1", "hotline-b": "2"}


def test_api_error_raises():
    api = make_api(lambda r: httpx.Response(403, text="plan"))
    with pytest.raises(at.AgentTestError):
        api.call("GET", "/x")


def test_main_exit_codes(monkeypatch, tmp_path):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    monkeypatch.setenv("ELEVENLABS_AGENT_ID", "agent_1")
    monkeypatch.setattr(at, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(at.time, "sleep", lambda s: None)
    status = {"value": "passed"}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/v1/convai/agents/agent_1":
            return httpx.Response(200, json={"conversation_config": {"agent": {"prompt": {"tool_ids": ["tool_abc"]}}}})
        if path == "/v1/convai/tools":
            return httpx.Response(200, json={"tools": [{"id": "tool_abc", "tool_config": {"name": "identify_farmer"}}]})
        if path == "/v1/convai/agent-testing":
            return httpx.Response(200, json={"tests": [], "has_more": False})
        if path.endswith("/create"):
            return httpx.Response(200, json={"id": "test_1"})
        if path.endswith("/run-tests"):
            return httpx.Response(200, json={"id": "suite_1"})
        return httpx.Response(200, json={"test_runs": [{"status": status["value"], "agent_responses": []}]})

    assert at.main(["--only", "happy"], api=make_api(handler)) == 0
    status["value"] = "failed"
    assert at.main(["--only", "happy"], api=make_api(handler)) == 1


@pytest.mark.parametrize(
    "answer",
    [
        "Changanya 50 ml katika lita 20 za maji.",  # bare dose, no per/kwa
        "Weka gramu 30 kwenye bomba.",  # unit before number
        "Nyunyiza copper kila wiki.",  # active ingredient without 'oxychloride'
    ],
)
def test_deny_list_catches_bare_dose_and_copper(answer):
    run = {"status": "passed", "agent_responses": [{"role": "agent", "message": answer}]}
    assert at.evaluate_run("spray", run)["passed"] is False


@pytest.mark.parametrize("spoken", ["9, 0, 0, 1", "9.0.0.1", "tisa, sifuri, sufuri, moja", "Tisa - sifuri - sifuri - moja"])
def test_report_redacts_separated_pins(tmp_path, spoken):
    transcripts = {"t": [{"agent_responses": [{"role": "user", "message": f"PIN yangu ni {spoken}"}]}]}
    text = at.write_report([], transcripts, out_dir=tmp_path).read_text(encoding="utf-8")
    assert spoken not in text and "PIN yangu ni [PIN]" in text


def test_main_writes_report_to_patched_results_dir(monkeypatch, tmp_path):
    """write_report must read RESULTS_DIR at call time, so tests never write into evals/results."""
    monkeypatch.setattr(at, "RESULTS_DIR", tmp_path / "reports")
    path = at.write_report([], {})
    assert path.parent == tmp_path / "reports"
