"""Tests for forwarding finished recordings to POST /calls (#15). Twilio and /calls are mocked."""

import logging
from uuid import uuid4

import httpx
import pytest

from twilio_line import app as line
from twilio_line import forwarder
from twilio_line.tests.signing import post_signed

ACCOUNT_SID = "ACtest-account"
CALLS_API_URL = "http://box.local:8000/calls"
RECORDING_URL = "https://api.twilio.com/2010-04-01/Accounts/ACtest/Recordings/RE123"
WAV_BYTES = b"RIFF\x00\x00\x00\x00WAVEfmt fake-audio"
PIN = "4821"


class FakeServers:
    """Mock transport standing in for Twilio's media URL and the laptop's /calls."""

    def __init__(self):
        self.download_status = 200
        self.calls_status = 200
        self.calls_unreachable = False
        self.requests = []

    def handle(self, request):
        request.read()
        self.requests.append(request)
        if request.url.host == "api.twilio.com":
            return httpx.Response(self.download_status, content=WAV_BYTES)
        if self.calls_unreachable:
            raise httpx.ConnectError("connection refused", request=request)
        return httpx.Response(self.calls_status, json={"saved": self.calls_status < 400})

    def posts_to_calls(self):
        return [request for request in self.requests if request.method == "POST"]


@pytest.fixture
def servers(monkeypatch, tmp_path):
    fake = FakeServers()
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", ACCOUNT_SID)
    monkeypatch.setenv("CALLS_API_URL", CALLS_API_URL)
    monkeypatch.setenv("RECORDINGS_DIR", str(tmp_path))
    monkeypatch.setattr(forwarder, "http_client", lambda: httpx.Client(transport=httpx.MockTransport(fake.handle)))
    return fake


def new_call(pin=PIN):
    call_sid = "CA" + uuid4().hex
    if pin:
        line.pins.save(call_sid, pin)
    return call_sid


def recording_ready(client, call_sid, status="completed", url=RECORDING_URL):
    form = {"CallSid": call_sid, "RecordingSid": "RE123", "RecordingStatus": status, "RecordingUrl": url}
    return post_signed(client, "/twilio/recording", form)


def test_finished_recording_is_saved_and_sent_with_pin(client, servers, tmp_path):
    call_sid = new_call()

    response = recording_ready(client, call_sid)

    assert response.status_code == 204
    download, upload = servers.requests
    assert str(download.url) == RECORDING_URL + ".wav"
    assert download.headers["authorization"].startswith("Basic ")
    assert str(upload.url) == CALLS_API_URL
    assert b'name="pin"' in upload.content and PIN.encode() in upload.content
    assert b'name="audio"' in upload.content and WAV_BYTES in upload.content
    assert (tmp_path / f"{call_sid}.wav").read_bytes() == WAV_BYTES


@pytest.mark.parametrize("status", [404, 500])
def test_calls_api_error_is_logged_and_audio_kept(client, servers, tmp_path, caplog, status):
    servers.calls_status = status
    call_sid = new_call()

    with caplog.at_level(logging.ERROR):
        recording_ready(client, call_sid)

    assert f"Call {call_sid}: POST /calls returned {status}" in caplog.text
    assert (tmp_path / f"{call_sid}.wav").exists()


def test_unreachable_calls_api_is_logged_and_audio_kept(client, servers, tmp_path, caplog):
    servers.calls_unreachable = True
    call_sid = new_call()

    with caplog.at_level(logging.ERROR):
        recording_ready(client, call_sid)

    assert f"Call {call_sid}: POST /calls failed" in caplog.text
    assert (tmp_path / f"{call_sid}.wav").exists()


def test_missing_calls_api_url_keeps_audio_and_sends_nothing(client, servers, tmp_path, caplog, monkeypatch):
    monkeypatch.delenv("CALLS_API_URL")
    call_sid = new_call()

    with caplog.at_level(logging.ERROR):
        recording_ready(client, call_sid)

    assert servers.posts_to_calls() == []
    assert "CALLS_API_URL is not set" in caplog.text
    assert (tmp_path / f"{call_sid}.wav").exists()


def test_failed_download_sends_nothing(client, servers, tmp_path, caplog):
    servers.download_status = 500
    call_sid = new_call()

    with caplog.at_level(logging.ERROR):
        recording_ready(client, call_sid)

    assert servers.posts_to_calls() == []
    assert f"Call {call_sid}: could not download" in caplog.text
    assert not (tmp_path / f"{call_sid}.wav").exists()


def test_recording_without_pin_sends_nothing(client, servers, caplog):
    call_sid = new_call(pin=None)

    with caplog.at_level(logging.ERROR):
        response = recording_ready(client, call_sid)

    assert response.status_code == 204
    assert servers.requests == []
    assert f"Call {call_sid}: recording ready but no PIN" in caplog.text


def test_non_twilio_recording_url_is_refused(client, servers, caplog):
    call_sid = new_call()

    with caplog.at_level(logging.ERROR):
        recording_ready(client, call_sid, url="https://attacker.example/recording")

    assert servers.requests == []
    assert "not a Twilio media URL" in caplog.text


def test_unfinished_recording_status_is_ignored(client, servers):
    call_sid = new_call()

    response = recording_ready(client, call_sid, status="absent")

    assert response.status_code == 204
    assert servers.requests == []
