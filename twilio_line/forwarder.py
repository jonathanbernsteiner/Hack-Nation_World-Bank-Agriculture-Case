"""Forward finished Twilio recordings to the laptop's `POST /calls` (issue #15).

Twilio tells us a recap recording is ready. We download the WAV, keep a copy on disk
and send it with the caller's PIN to `POST /calls` (#11), which turns it into ledger rows.
Every failure is logged with the CallSid and leaves the audio on disk for a re-send.
"""

import logging
import os
import re
from pathlib import Path

import httpx

CALL_SID_PATTERN = re.compile(r"CA[0-9a-f]{32}")
TWILIO_MEDIA_PREFIX = "https://api.twilio.com/"
DEFAULT_RECORDINGS_DIR = "recordings"
DOWNLOAD_TIMEOUT_SECONDS = 30
CALLS_TIMEOUT_SECONDS = 300  # /calls runs speech-to-text, translation and extraction
AUDIO_FIELD = "audio"
PIN_FIELD = "pin"
AUDIO_CONTENT_TYPE = "audio/wav"

logger = logging.getLogger(__name__)


def http_client() -> httpx.Client:
    """The HTTP client for Twilio and /calls. Tests replace it with a mock transport."""
    return httpx.Client()


def download_recording(client: httpx.Client, recording_url: str, account_sid: str, auth_token: str) -> bytes:
    if not recording_url.startswith(TWILIO_MEDIA_PREFIX):
        raise ValueError(f"not a Twilio media URL: {recording_url!r}")
    response = client.get(
        f"{recording_url}.wav",
        auth=(account_sid, auth_token),
        timeout=DOWNLOAD_TIMEOUT_SECONDS,
        follow_redirects=True,
    )
    response.raise_for_status()
    return response.content


def save_recording(audio: bytes, call_sid: str, recordings_dir: Path) -> Path:
    recordings_dir.mkdir(parents=True, exist_ok=True)
    path = recordings_dir / f"{call_sid}.wav"
    path.write_bytes(audio)
    return path


def send_to_calls_api(client: httpx.Client, calls_api_url: str, audio_path: Path, pin: str) -> httpx.Response:
    with audio_path.open("rb") as audio_file:
        response = client.post(
            calls_api_url,
            files={AUDIO_FIELD: (audio_path.name, audio_file, AUDIO_CONTENT_TYPE)},
            data={PIN_FIELD: pin},
            timeout=CALLS_TIMEOUT_SECONDS,
        )
    response.raise_for_status()
    return response


def forward_recording(call_sid: str, recording_url: str, pin: str) -> None:
    """Download the recording, keep it on disk and send it to POST /calls. Logs failures, never raises."""
    if not CALL_SID_PATTERN.fullmatch(call_sid):
        logger.error("Ignoring recording with an invalid CallSid %r", call_sid)
        return
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    calls_api_url = os.environ.get("CALLS_API_URL", "")
    recordings_dir = Path(os.environ.get("RECORDINGS_DIR", DEFAULT_RECORDINGS_DIR))

    with http_client() as client:
        try:
            audio_path = save_recording(
                download_recording(client, recording_url, account_sid, auth_token), call_sid, recordings_dir
            )
        except (httpx.HTTPError, ValueError, OSError) as error:
            logger.error("Call %s: could not download and save the recording: %s", call_sid, error)
            return
        if not calls_api_url:
            logger.error("Call %s: CALLS_API_URL is not set; recording kept at %s", call_sid, audio_path)
            return
        try:
            response = send_to_calls_api(client, calls_api_url, audio_path, pin)
        except httpx.HTTPStatusError as error:
            logger.error(
                "Call %s: POST /calls returned %s; recording kept at %s",
                call_sid, error.response.status_code, audio_path,
            )
            return
        except httpx.HTTPError as error:
            logger.error("Call %s: POST /calls failed (%s); recording kept at %s", call_sid, error, audio_path)
            return
    logger.info("Call %s: recording sent to /calls (HTTP %s)", call_sid, response.status_code)
