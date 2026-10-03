"""Translation: Swahili text in, English text out, on CPU.

Uses NLLB-200 (distilled 600M) through Hugging Face transformers, swh_Latn -> eng_Latn.
Long text is split into sentences (after . ! ? or a newline), and any sentence longer
than MAX_WORDS is cut into word chunks, so nothing is truncated by the model's input
limit. Chunks are translated in small batches and joined with spaces.

Config (function arg wins over env var):
  TRANSLATE_MODEL  model name or path; default facebook/nllb-200-distilled-600M

The model downloads (about 2.4 GB) on first use and is then cached in memory.
NLLB-200 is licensed CC-BY-NC (non-commercial use only).
"""

import os
import re
from functools import lru_cache

SRC_LANG = "swh_Latn"
TGT_LANG = "eng_Latn"
MAX_WORDS = 60  # keeps a chunk well under the 512-token limit
MAX_TOKENS = 256
BATCH = 8

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|\n+")


def split_sentences(text: str) -> list[str]:
    """Split on sentence-ending punctuation or newlines; cut very long sentences by words."""
    chunks = []
    for sentence in _SENTENCE_END.split(text):
        words = sentence.split()
        for i in range(0, len(words), MAX_WORDS):
            chunks.append(" ".join(words[i:i + MAX_WORDS]))
    return chunks


@lru_cache(maxsize=None)
def _get_model(name: str):
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer  # heavy import; keep it lazy

    tokenizer = AutoTokenizer.from_pretrained(name, src_lang=SRC_LANG)
    return tokenizer, AutoModelForSeq2SeqLM.from_pretrained(name).eval()


def translate(text: str, *, model: str | None = None) -> str:
    """Return the English translation of Swahili text ("" for empty or blank input)."""
    chunks = split_sentences(text)
    if not chunks:
        return ""
    import torch

    tokenizer, nllb = _get_model(model or os.environ.get("TRANSLATE_MODEL", "facebook/nllb-200-distilled-600M"))
    eng = tokenizer.convert_tokens_to_ids(TGT_LANG)
    out = []
    for i in range(0, len(chunks), BATCH):
        inputs = tokenizer(chunks[i:i + BATCH], return_tensors="pt", padding=True)
        with torch.inference_mode():
            ids = nllb.generate(**inputs, forced_bos_token_id=eng, max_length=MAX_TOKENS)
        out += tokenizer.batch_decode(ids, skip_special_tokens=True)
    return " ".join(s.strip() for s in out).strip()
