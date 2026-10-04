"""Tests for hotline.pipeline.transcript (issue #57)."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from hotline.pipeline.transcript import (
    call_meta,
    collect_pins,
    redact_pins,
    render,
    scrub_tool_results,
    to_lines,
)

FIXTURE = Path(__file__).parent / "fixtures" / "post_call_transcription.json"
FAKE_NUMBER = "+256000000000"  # obviously synthetic sentinel for the leak scan
START_2230_UTC = int(datetime(2026, 10, 3, 22, 30, tzinfo=timezone.utc).timestamp())


def _turn(role, message, t=0, **extra):
    return {"role": role, "message": message, "time_in_call_secs": t, **extra}


def _lines(*texts):
    return [{"i": i, "role": "farmer", "sw": s, "t": None} for i, s in enumerate(texts)]


def _payload(turns, start=START_2230_UTC):
    return {
        "conversation_id": "conv_synthetic",
        "transcript": turns,
        "metadata": {
            "start_time_unix_secs": start,
            "call_duration_secs": 61,
            "phone_call": {"external_number": FAKE_NUMBER, "agent_number": FAKE_NUMBER},
        },
        "conversation_initiation_client_data": {
            "dynamic_variables": {"system__caller_id": FAKE_NUMBER}
        },
    }


def _tool_payload():
    return _payload(
        [
            _turn("agent", "Habari. Sema PIN yako."),
            _turn("user", "tisa sifuri sifuri moja", 3),
            _turn(
                "agent",
                "Sawa.",
                5,
                tool_calls=[
                    {
                        "request_id": "r1",
                        "tool_name": "identify_farmer",
                        "params_as_json": json.dumps({"pin": "9001", "call_sid": "CAfake"}),
                    }
                ],
                tool_results=[
                    {
                        "request_id": "r1",
                        "tool_name": "identify_farmer",
                        "result_value": json.dumps({"ok": True, "median": 5900}),
                        "is_error": False,
                    }
                ],
            ),
            _turn("user", "Nimeuza kwa shilingi 5,900 kwa kilo.", 9),
            _turn(
                "agent",
                "PIN yako mpya ni nne, nane, tatu, moja. Nirudie: nne nane tatu moja.",
                12,
                tool_calls=[
                    {"request_id": "r2", "tool_name": "register_farmer", "params_as_json": "{}"}
                ],
                tool_results=[
                    {
                        "request_id": "r2",
                        "tool_name": "register_farmer",
                        "result_value": json.dumps({"pin": "4831", "farmer": "ok"}),
                        "is_error": False,
                    }
                ],
            ),
        ]
    )


def test_fixture_line_count_matches_non_empty_agent_user_turns():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))["data"]
    expected = [t for t in data["transcript"] if t["role"] in ("agent", "user") and t["message"]]
    lines = to_lines(data)
    assert len(lines) == len(expected) > 0
    assert [ln["i"] for ln in lines] == list(range(len(lines)))
    assert [ln["sw"] for ln in lines] == [t["message"].strip() for t in expected]
    assert [ln["role"] for ln in lines] == ["agent" if t["role"] == "agent" else "farmer" for t in expected]
    assert all(ln["t"] is not None for ln in lines)


@pytest.mark.parametrize(
    "text",
    [
        "PIN ni 9001 asante",
        "PIN ni 9 0 0 1 asante",
        "PIN ni tisa sifuri sifuri moja asante",
        "PIN ni tisa, sifuri, sifuri, moja asante",
        "PIN ni Tisa na sifuri na sifuri na moja asante",
        "PIN ni 9-0-0-1 asante",
        "PIN ni tisa sufuri sufuri moja asante",
    ],
)
def test_each_pin_form_is_redacted(text):
    (out,) = redact_pins(_lines(text), {"9001"})
    assert out["sw"] == "PIN ni [PIN] asante"


def test_redaction_does_not_mutate_input():
    lines = _lines("9001")
    redact_pins(lines, {"9001"})
    assert lines[0]["sw"] == "9001"


def test_price_and_unrelated_numbers_stay_intact():
    text = "Nimeuza kwa shilingi 5,900 kwa kilo moja, na gunia mbili."
    assert redact_pins(_lines(text), {"9001"})[0]["sw"] == text
    assert redact_pins(_lines(text), set())[0]["sw"] == text
    assert redact_pins(_lines("5,900"), {"5900"})[0]["sw"] == "[PIN]"


def test_register_farmer_result_and_agent_readback_redacted():
    data = _tool_payload()
    scrubbed = scrub_tool_results(data)
    register = next(s for s in scrubbed if s["tool_name"] == "register_farmer")
    assert register["result"] == {"pin": "[PIN]", "farmer": "ok"}
    lines = to_lines(data)
    assert lines[4]["sw"] == "PIN yako mpya ni [PIN]. Nirudie: [PIN]."


def test_tool_params_stripped_and_results_kept():
    scrubbed = scrub_tool_results(_tool_payload())
    identify = next(s for s in scrubbed if s["tool_name"] == "identify_farmer")
    assert identify["result"] == {"ok": True, "median": 5900}
    assert identify["is_error"] is False
    blob = json.dumps(scrubbed)
    assert "params" not in blob and "9001" not in blob and "CAfake" not in blob and "4831" not in blob


def test_pin_in_tool_params_redacts_spoken_pin():
    lines = to_lines(_tool_payload())
    assert lines[1]["sw"] == "[PIN]"


def test_dtmf_only_digit_turn_and_spoken_pin_both_redacted():
    data = _payload([_turn("user", "9001"), _turn("agent", "Umesema tisa sifuri sifuri moja."), _turn("user", "9 0 0 1")])
    assert [ln["sw"] for ln in to_lines(data)] == ["[PIN]", "Umesema [PIN].", "[PIN]"]


def test_redacted_keypad_turn_is_kept_as_is():
    data = _payload([_turn("user", "<REDACTED>", source_medium="dtmf")])
    assert [ln["sw"] for ln in to_lines(data)] == ["<REDACTED>"]


def test_partial_spoken_pin_run_is_redacted_when_pin_known():
    data = _tool_payload()
    data["transcript"].append(_turn("user", "tisa sifuri sifuri tu", 20))
    assert to_lines(data)[-1]["sw"] == "[PIN] tu"


def test_no_pin_payload_is_unchanged():
    data = _payload([_turn("agent", "Habari"), _turn("user", "Bei ni elfu nne kwa kilo moja")])
    assert collect_pins(data) == set()
    assert [ln["sw"] for ln in to_lines(data)] == ["Habari", "Bei ni elfu nne kwa kilo moja"]


def test_empty_turns_dropped_and_other_roles_ignored_and_index_contiguous():
    data = _payload(
        [
            _turn("agent", "Habari"),
            _turn("agent", ""),
            _turn("user", "   "),
            _turn("user", None),
            {"role": "system", "message": "x"},
            _turn("user", "Ndiyo", None),
        ]
    )
    lines = to_lines(data)
    assert [(ln["i"], ln["role"], ln["sw"], ln["t"]) for ln in lines] == [
        (0, "agent", "Habari", 0.0),
        (1, "farmer", "Ndiyo", None),
    ]


def test_null_and_empty_tool_lists_are_equal():
    for tools in (None, []):
        data = _payload([_turn("agent", "Hi", tool_calls=tools, tool_results=tools)])
        assert scrub_tool_results(data) == []
        assert to_lines(data)[0]["sw"] == "Hi"
    assert to_lines({}) == [] and scrub_tool_results({}) == []


def test_render():
    lines = [
        {"i": 0, "role": "agent", "sw": "Habari", "t": None},
        {"i": 1, "role": "farmer", "sw": "Nzuri", "t": None},
    ]
    assert render(lines) == "Agent: Habari\nFarmer: Nzuri"
    assert render([{**ln, "en": "Hello"} for ln in lines[:1]], "en") == "Agent: Hello"


def test_call_date_rolls_over_at_2230_utc():
    meta = call_meta(_payload([], START_2230_UTC))
    assert meta["call_date_kampala"] == "2026-10-04"
    assert meta["received_at"] == datetime(2026, 10, 3, 22, 30, tzinfo=timezone.utc)
    assert meta["duration_secs"] == 61 and meta["conversation_id"] == "conv_synthetic"
    before = int(datetime(2026, 10, 3, 20, 59, tzinfo=timezone.utc).timestamp())
    assert call_meta(_payload([], before))["call_date_kampala"] == "2026-10-03"


def test_call_meta_missing_start_time():
    meta = call_meta({"conversation_id": "c"})
    assert meta["received_at"] is None and meta["call_date_kampala"] is None


def test_external_number_never_in_any_output():
    for data in (_tool_payload(), json.loads(FIXTURE.read_text(encoding="utf-8"))["data"]):
        outputs = [to_lines(data), scrub_tool_results(data), call_meta(data)]
        assert FAKE_NUMBER not in repr(outputs) and "256000000000" not in repr(outputs)
    data = _tool_payload()
    data["transcript"][4]["tool_results"][0]["result_value"] = json.dumps(
        {"caller_id": FAKE_NUMBER, "note": f"call {FAKE_NUMBER}"}
    )
    assert FAKE_NUMBER not in repr(scrub_tool_results(data))
