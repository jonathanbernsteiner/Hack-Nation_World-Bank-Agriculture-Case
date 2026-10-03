import importlib
import os

import pytest

from pipeline import translate as translate_fn

# pipeline.translate the function shadows the submodule, so fetch the module explicitly.
tr = importlib.import_module("pipeline.translate")


class FakeTokenizer:
    def __init__(self):
        self.batches = []

    def convert_tokens_to_ids(self, tok):
        return 7

    def __call__(self, batch, **kw):
        self.batches.append(list(batch))
        return {"batch": list(batch)}

    def batch_decode(self, ids, skip_special_tokens):
        return [f"EN({s})" for s in ids]


class FakeModel:
    def generate(self, forced_bos_token_id, max_length, **inputs):
        assert forced_bos_token_id == 7
        return inputs["batch"]


@pytest.fixture
def fake(monkeypatch):
    tok, calls = FakeTokenizer(), []

    def get(name):
        calls.append(name)
        return tok, FakeModel()

    monkeypatch.setattr(tr, "_get_model", get)
    monkeypatch.delenv("TRANSLATE_MODEL", raising=False)
    return tok, calls


@pytest.mark.parametrize("text", ["", "   ", "\n\t "])
def test_empty_input_skips_model(fake, text):
    assert tr.translate(text) == ""
    assert fake[1] == []


def test_splits_sentences_and_joins(fake):
    out = tr.translate("Habari. Leo niliuza kahawa!  Je, wewe?\nNdiyo")
    assert out == "EN(Habari.) EN(Leo niliuza kahawa!) EN(Je, wewe?) EN(Ndiyo)"


def test_long_sentence_is_chunked_and_batched(fake):
    tok, _ = fake
    words = [f"w{i}" for i in range(tr.MAX_WORDS * 2 + 5)]
    assert [len(c.split()) for c in tr.split_sentences(" ".join(words))] == [tr.MAX_WORDS, tr.MAX_WORDS, 5]
    text = " ".join(f"Sentensi {i}." for i in range(tr.BATCH + 1))
    out = tr.translate(text)
    assert [len(b) for b in tok.batches] == [tr.BATCH, 1]
    assert out.count("EN(") == tr.BATCH + 1


def test_model_config_arg_beats_env(fake, monkeypatch):
    _, calls = fake
    monkeypatch.setenv("TRANSLATE_MODEL", "from-env")
    tr.translate("Habari")
    tr.translate("Habari", model="from-arg")
    assert calls == ["from-env", "from-arg"]


def test_model_is_loaded_once(monkeypatch):
    loads = []
    tr._get_model.cache_clear()
    import transformers

    class Tok:
        def convert_tokens_to_ids(self, t):
            return 1

    monkeypatch.setattr(transformers.AutoTokenizer, "from_pretrained", lambda *a, **k: loads.append("tok") or Tok())

    class M:
        def eval(self):
            return self

    monkeypatch.setattr(transformers.AutoModelForSeq2SeqLM, "from_pretrained", lambda *a, **k: loads.append("model") or M())
    assert tr._get_model("x") is tr._get_model("x")
    assert loads == ["tok", "model"]
    tr._get_model.cache_clear()


slow = pytest.mark.skipif(not os.environ.get("RUN_SLOW"), reason="set RUN_SLOW=1 (downloads the real model)")


@pytest.mark.slow
@slow
def test_real_coffee_sale_keeps_numbers():
    out = translate_fn("Leo niliuza kilo hamsini za cherry kwa shilingi elfu nne.").lower()
    print(out)
    assert ("fifty" in out or "50" in out) and ("four thousand" in out or "4,000" in out or "4000" in out)


@pytest.mark.slow
@slow
def test_real_long_transcript_translates_in_full():
    sentence = "Leo niliuza kilo hamsini za kahawa kwa shilingi elfu nne."
    out = translate_fn(" ".join([sentence] * 40))
    assert out.lower().count("coffee") >= 38
