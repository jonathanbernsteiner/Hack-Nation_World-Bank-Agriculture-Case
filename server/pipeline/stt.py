"""Speech-to-text: audio file in, Swahili transcript out, on CPU.

Any file ffmpeg can read is converted to 16 kHz mono WAV, then transcribed
with faster-whisper.

Config (function args win over env vars):
  STT_MODEL         model name or path; default large-v3-turbo
  STT_DEVICE        cpu | cuda | auto; default cpu
  STT_COMPUTE_TYPE  int8 | float16 | ...; default int8
  STT_LANGUAGE      language code; default sw (Swahili)

The model downloads (about 1.6 GB) on first use and is then cached in memory.
"""

import os
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path


class SttError(Exception):
    """Base class for speech-to-text failures."""


class AudioFileNotFound(SttError):
    """The audio path does not exist or is not a file."""


class AudioDecodeError(SttError):
    """ffmpeg could not read the file as audio."""


def convert_to_wav16k(src: str | Path, dst: str | Path) -> None:
    """Write src as 16 kHz mono 16-bit WAV to dst (8 kHz phone audio is upsampled)."""
    src = Path(src)
    if not src.is_file():
        raise AudioFileNotFound(f"audio file not found: {src}")
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn",
           "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", "-f", "wav", str(dst)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError as e:
        raise SttError("ffmpeg is not installed or not on PATH") from e
    if proc.returncode != 0 or not Path(dst).exists() or Path(dst).stat().st_size <= 44:
        detail = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "no audio decoded"
        raise AudioDecodeError(f"could not read {src} as audio: {detail}")


@lru_cache(maxsize=None)
def _get_model(name: str, device: str, compute_type: str):
    from faster_whisper import WhisperModel  # heavy import; keep it lazy

    return WhisperModel(name, device=device, compute_type=compute_type)


def transcribe(
    path: str | Path,
    *,
    model: str | None = None,
    device: str | None = None,
    compute_type: str | None = None,
    language: str | None = None,
) -> str:
    """Return the transcript of an audio file (Swahili by default)."""
    whisper = _get_model(
        model or os.environ.get("STT_MODEL", "large-v3-turbo"),
        device or os.environ.get("STT_DEVICE", "cpu"),
        compute_type or os.environ.get("STT_COMPUTE_TYPE", "int8"),
    )
    lang = language or os.environ.get("STT_LANGUAGE", "sw")
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio16k.wav"
        convert_to_wav16k(path, wav)
        segments, _ = whisper.transcribe(str(wav), language=lang)
        return " ".join(s.text.strip() for s in segments).strip()
