"""Twilio voice webhook for the farm record demo call (issues #14, #15).

When someone dials our Twilio number, Twilio posts to these routes. We greet the
caller, collect their PIN on the keypad and record a spoken recap of their day.
When the recording is ready, `forwarder` sends it with the PIN to `POST /calls` (#11).
"""

import logging
import os
import re
import threading

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import VoiceResponse

from twilio_line.forwarder import forward_recording

PIN_PATTERN = re.compile(r"\d{4,8}")
MAX_PIN_ATTEMPTS = 2
PIN_TIMEOUT_SECONDS = 10
RECORDING_MAX_SECONDS = 120
TWIML_MEDIA_TYPE = "application/xml"

GREETING = "Welcome to the farm record line."
PIN_PROMPT = "Please enter your PIN, then press the hash key."
PIN_RETRY = "Sorry, that PIN was not valid."
PIN_FAILED = "Sorry, we could not read your PIN. Please call again. Goodbye."
RECAP_PROMPT = (
    "Thank you. Tell me what happened on your farm today. "
    "Start after the beep, and press the hash key when you are done."
)
GOODBYE = "Thank you. We received your report. Goodbye."

logger = logging.getLogger(__name__)
app = FastAPI(title="Farm record Twilio line")


class PinStore:
    """PINs entered on live calls, keyed by Twilio's CallSid, so PINs never travel in URLs."""

    def __init__(self) -> None:
        self._pins: dict[str, str] = {}
        self._lock = threading.Lock()

    def save(self, call_sid: str, pin: str) -> None:
        with self._lock:
            self._pins[call_sid] = pin

    def get(self, call_sid: str) -> str | None:
        with self._lock:
            return self._pins.get(call_sid)


pins = PinStore()


def pin_for_call(call_sid: str) -> str | None:
    """The PIN the caller entered on this call, if any. Used by the recording forwarder (#15)."""
    return pins.get(call_sid)


def _signed_url(request: Request) -> str:
    """The URL Twilio signed: the public ngrok URL when set, otherwise the URL as received."""
    base_url = os.environ.get("PUBLIC_BASE_URL")
    if not base_url:
        return str(request.url)
    query = f"?{request.url.query}" if request.url.query else ""
    return f"{base_url.rstrip('/')}{request.url.path}{query}"


async def _verified_form(request: Request) -> dict[str, str]:
    """Twilio's form fields, after checking the request really came from Twilio."""
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not auth_token:
        logger.error("TWILIO_AUTH_TOKEN is not set; rejecting %s", request.url.path)
        raise HTTPException(status_code=500, detail="Server is missing its Twilio configuration")
    form = {key: str(value) for key, value in (await request.form()).items()}
    signature = request.headers.get("X-Twilio-Signature", "")
    if not RequestValidator(auth_token).validate(_signed_url(request), form, signature):
        logger.warning("Rejected %s: missing or invalid Twilio signature", request.url.path)
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    return form


def _twiml(response: VoiceResponse) -> Response:
    return Response(content=str(response), media_type=TWIML_MEDIA_TYPE)


def _ask_for_pin(response: VoiceResponse, attempt: int) -> None:
    action = f"/twilio/pin?attempt={attempt}"
    gather = response.gather(
        input="dtmf", finish_on_key="#", timeout=PIN_TIMEOUT_SECONDS, action=action, method="POST"
    )
    gather.say(PIN_PROMPT)
    # Reached only when no key was pressed before the timeout: treat it as an empty PIN.
    response.redirect(action, method="POST")


def _record_recap(response: VoiceResponse) -> None:
    response.say(RECAP_PROMPT)
    response.record(
        max_length=RECORDING_MAX_SECONDS,
        play_beep=True,
        finish_on_key="#",
        action="/twilio/recorded",
        method="POST",
        recording_status_callback="/twilio/recording",
        recording_status_callback_event="completed",
        recording_status_callback_method="POST",
    )


@app.post("/twilio/voice")
async def incoming_call(request: Request) -> Response:
    await _verified_form(request)
    response = VoiceResponse()
    response.say(GREETING)
    _ask_for_pin(response, attempt=1)
    return _twiml(response)


@app.post("/twilio/pin")
async def pin_entered(request: Request, attempt: int = 1) -> Response:
    form = await _verified_form(request)
    digits = form.get("Digits", "")
    call_sid = form.get("CallSid", "")
    response = VoiceResponse()
    if PIN_PATTERN.fullmatch(digits) and call_sid:
        pins.save(call_sid, digits)
        _record_recap(response)
    elif attempt < MAX_PIN_ATTEMPTS:
        response.say(PIN_RETRY)
        _ask_for_pin(response, attempt=attempt + 1)
    else:
        logger.info("Call %s ended after %d invalid PIN attempts", call_sid, attempt)
        response.say(PIN_FAILED)
        response.hangup()
    return _twiml(response)


@app.post("/twilio/recorded")
async def recap_recorded(request: Request) -> Response:
    await _verified_form(request)
    response = VoiceResponse()
    response.say(GOODBYE)
    response.hangup()
    return _twiml(response)


@app.post("/twilio/recording", status_code=204)
async def recording_ready(request: Request, background_tasks: BackgroundTasks) -> Response:
    """Twilio says the recording file is ready. Answer at once; forwarding to /calls runs afterwards."""
    form = await _verified_form(request)
    call_sid = form.get("CallSid", "")
    status = form.get("RecordingStatus", "")
    pin = pin_for_call(call_sid)
    if status != "completed":
        logger.info("Call %s: ignoring recording status %r", call_sid, status)
    elif pin is None:
        logger.error("Call %s: recording ready but no PIN was entered; nothing sent", call_sid)
    else:
        background_tasks.add_task(forward_recording, call_sid, form.get("RecordingUrl", ""), pin)
    return Response(status_code=204)
