import os
import subprocess
import wave

import pytest

from pipeline import AudioDecodeError, AudioFileNotFound, convert_to_wav16k, stt


def make_tone(path, rate=8000, seconds=1):
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
         f"sine=frequency=440:duration={seconds}", "-ar", str(rate), str(path)],
        check=True,
    )
    return path


@pytest.mark.parametrize("ext", ["wav", "mp3"])
def test_converts_8khz_to_16khz_mono(tmp_path, ext):
    src = make_tone(tmp_path / f"in.{ext}", rate=8000)
    dst = tmp_path / "out.wav"
    convert_to_wav16k(src, dst)
    with wave.open(str(dst)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2)
        assert w.getnframes() > 0


def test_missing_file_raises(tmp_path):
    with pytest.raises(AudioFileNotFound, match="nope.wav"):
        convert_to_wav16k(tmp_path / "nope.wav", tmp_path / "out.wav")


def test_non_audio_file_raises(tmp_path):
    bad = tmp_path / "notes.wav"
    bad.write_text("this is not audio")
    with pytest.raises(AudioDecodeError, match="notes.wav"):
        convert_to_wav16k(bad, tmp_path / "out.wav")


def test_transcribe_joins_segments_and_uses_config(tmp_path, monkeypatch):
    class Seg:
        def __init__(self, text):
            self.text = text

    class FakeModel:
        def transcribe(self, wav, language):
            self.seen = (wav, language)
            return [Seg(" habari "), Seg("yako")], None

    fake = FakeModel()
    seen = {}

    def fake_get(name, device, compute):
        seen["cfg"] = (name, device, compute)
        return fake

    monkeypatch.setattr(stt, "_get_model", fake_get)
    monkeypatch.setenv("STT_LANGUAGE", "sw")
    src = make_tone(tmp_path / "in.wav")
    assert stt.transcribe(src, model="tiny") == "habari yako"
    assert seen["cfg"] == ("tiny", "cpu", "int8")
    assert fake.seen[1] == "sw"
    assert not os.path.exists(fake.seen[0])  # temp wav cleaned up


@pytest.mark.slow
@pytest.mark.skipif(not os.environ.get("RUN_SLOW"), reason="set RUN_SLOW=1 (downloads the real model)")
@pytest.mark.parametrize("ext", ["wav", "mp3"])
def test_real_model_transcribes_wav_and_mp3(tmp_path, ext):
    src = make_tone(tmp_path / f"in.{ext}", rate=16000, seconds=2)
    assert isinstance(stt.transcribe(src), str)
