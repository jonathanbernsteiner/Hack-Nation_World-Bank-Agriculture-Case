"""Tests for the Twilio voice webhook (#14), using properly signed Twilio-style form posts."""

import xml.etree.ElementTree as ET

import pytest
from twilio.request_validator import RequestValidator

from twilio_line import app as line
from twilio_line.tests.signing import AUTH_TOKEN, PUBLIC_BASE_URL, post_signed

CALL_SID = "CA" + "0" * 32


def twiml(response):
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    return ET.fromstring(response.text)


def test_incoming_call_greets_and_asks_for_pin(client):
    root = twiml(post_signed(client, "/twilio/voice", {"CallSid": CALL_SID}))

    assert root[0].tag == "Say"
    gather = root.find("Gather")
    assert gather.get("input") == "dtmf"
    assert gather.get("finishOnKey") == "#"
    assert gather.get("action") == "/twilio/pin?attempt=1"
    assert gather.find("Say").text == line.PIN_PROMPT
    assert root.find("Redirect").text == "/twilio/pin?attempt=1"


def test_valid_pin_starts_recording_and_remembers_pin(client):
    call_sid = "CA" + "1" * 32
    response = post_signed(client, "/twilio/pin?attempt=1", {"CallSid": call_sid, "Digits": "4821"})
    root = twiml(response)

    record = root.find("Record")
    assert record.get("maxLength") == str(line.RECORDING_MAX_SECONDS)
    assert record.get("playBeep") == "true"
    assert record.get("action") == "/twilio/recorded"
    assert record.get("recordingStatusCallback") == "/twilio/recording"
    assert line.pin_for_call(call_sid) == "4821"
    assert "4821" not in response.text  # the PIN never goes into a URL


@pytest.mark.parametrize("digits", ["", "12", "12*4", "123456789"])
def test_invalid_pin_gets_one_retry(client, digits):
    root = twiml(post_signed(client, "/twilio/pin?attempt=1", {"CallSid": CALL_SID, "Digits": digits}))

    assert root[0].text == line.PIN_RETRY
    assert root.find("Gather").get("action") == "/twilio/pin?attempt=2"
    assert root.find("Record") is None


def test_second_invalid_pin_ends_the_call(client):
    root = twiml(post_signed(client, "/twilio/pin?attempt=2", {"CallSid": CALL_SID, "Digits": ""}))

    assert root[0].text == line.PIN_FAILED
    assert root.find("Hangup") is not None
    assert root.find("Gather") is None


def test_finished_recording_says_goodbye_and_hangs_up(client):
    root = twiml(post_signed(client, "/twilio/recorded", {"CallSid": CALL_SID}))

    assert root[0].text == line.GOODBYE
    assert root.find("Hangup") is not None


@pytest.mark.parametrize(
    "path", ["/twilio/voice", "/twilio/pin?attempt=1", "/twilio/recorded", "/twilio/recording"]
)
def test_rejects_missing_or_wrong_signature(client, path):
    form = {"CallSid": CALL_SID, "Digits": "4821"}

    assert client.post(path, data=form).status_code == 403
    assert client.post(path, data=form, headers={"X-Twilio-Signature": "forged"}).status_code == 403


def test_tampered_form_fails_signature_check(client):
    signature = RequestValidator(AUTH_TOKEN).compute_signature(
        PUBLIC_BASE_URL + "/twilio/pin?attempt=1", {"CallSid": CALL_SID, "Digits": "1111"}
    )
    response = client.post(
        "/twilio/pin?attempt=1",
        data={"CallSid": CALL_SID, "Digits": "9999"},
        headers={"X-Twilio-Signature": signature},
    )

    assert response.status_code == 403


def test_signature_uses_received_url_without_public_base_url(client, monkeypatch):
    monkeypatch.delenv("PUBLIC_BASE_URL")

    response = post_signed(client, "/twilio/voice", {"CallSid": CALL_SID}, base_url="http://testserver")

    assert response.status_code == 200


def test_missing_auth_token_is_a_server_error(client, monkeypatch):
    monkeypatch.delenv("TWILIO_AUTH_TOKEN")

    assert client.post("/twilio/voice", data={"CallSid": CALL_SID}).status_code == 500
