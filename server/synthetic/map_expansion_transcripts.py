"""SYNTHETIC transcripts for the map-expansion calls (conversation_id 'synmap-%'). Pure and deterministic.

Each transcript is built from the call's own entries: the sale (kg, form, price, buyer), the problem
symptom, or a plain price question when the call has no entries. Seeded by the conversation id.
"""

import random
import zlib

SEED = 20261006
FORM_SW = {"kiboko": "kiboko", "faq": "FAQ", "parchment": "parchment"}
BUYER_SW = {"middleman": "dalali", "cooperative": "chama cha ushirika", "other": "mnunuzi mwingine"}
BUYER_EN = {"middleman": "a middleman", "cooperative": "the cooperative", "other": "another buyer"}
GREETINGS = (
    ("Habari, karibu kwenye simu ya kahawa. Unaweza kuniambia nini leo?", "Hello, welcome to the coffee line. What can you tell me today?"),
    ("Karibu. Nikusaidie vipi kuhusu kahawa yako?", "Welcome. How can I help with your coffee?"),
)
GOODBYES = (
    ("Asante kwa kupiga simu. Kwaheri!", "Thank you for calling. Goodbye!"),
    ("Asante sana, kwaheri na uwe na siku njema.", "Thank you very much, goodbye and have a good day."),
)
ADVICE = {
    "coffee_wilt_disease": ("Ng'oa miti iliyonyauka na uichome, usiache mizizi shambani.", "Uproot the wilted trees and burn them; do not leave roots in the field."),
    "coffee_leaf_rust": ("Ondoa majani yaliyoathirika na upulizie dawa ya shaba.", "Remove the affected leaves and spray a copper fungicide."),
    "coffee_berry_disease": ("Pogoa matawi na upulizie dawa ya shaba kabla ya mvua.", "Prune the branches and spray copper before the rains."),
    "black_coffee_twig_borer": ("Kata matawi yenye vitundu na uyachome.", "Cut the branches with holes and burn them."),
}
DEFAULT_ADVICE = ("Tunza shamba lako na uwasiliane na afisa wa kilimo.", "Look after your field and contact the agriculture officer.")


def _ugx(value: float) -> str:
    return f"{round(value):,}"


def _farmer_report(entries: tuple[dict, ...], fallback: tuple[str, str]) -> tuple[str, str]:
    sw, en = [], []
    for e in entries:
        if e.get("kind") == "sale":
            kg, total = int(e["amount_kg"]), int(e["price_total"])
            form, buyer = e.get("coffee_form") or "kiboko", e.get("buyer_type") or "other"
            sw.append(f"Niliuza kilo {kg} za kahawa ya {FORM_SW.get(form, form)} kwa {BUYER_SW.get(buyer, buyer)}, "
                      f"shilingi {_ugx(total)} (shilingi {_ugx(total / kg)} kwa kilo).")
            en.append(f"I sold {kg} kilos of {form} coffee to {BUYER_EN.get(buyer, buyer)} for {_ugx(total)} shillings "
                      f"({_ugx(total / kg)} per kilo).")
        elif e.get("kind") == "observation" and e.get("evidence_quote"):
            disease = e.get("likely_disease")
            sw.append(DISEASE_SW.get(disease, "Nina tatizo kwenye miti ya kahawa."))
            en.append(e["evidence_quote"])
    return (" ".join(sw), " ".join(en)) if sw else fallback


DISEASE_SW = {
    "coffee_wilt_disease": "Miti ya kahawa inanyauka na majani yanakauka.",
    "coffee_leaf_rust": "Majani yana vumbi la rangi ya machungwa upande wa chini.",
    "coffee_berry_disease": "Matunda ya kahawa yana madoa meusi.",
    "black_coffee_twig_borer": "Matawi yanakauka na kuna vitundu vidogo.",
}
PRICE_QUESTION = ("Bei ya kahawa kijijini ni shilingi ngapi kwa kilo?", "What is the coffee price in the village per kilo?")


def _agent_reply(entries: tuple[dict, ...], village: str, median_per_kg: float | None) -> tuple[str, str]:
    price = (f"Bei ya kawaida ya kahawa hapa {village} ni shilingi {_ugx(median_per_kg)} kwa kilo.",
             f"The usual coffee price in {village} is {_ugx(median_per_kg)} shillings per kilo.") if median_per_kg else None
    for e in entries:
        if e.get("kind") == "observation":
            advice = ADVICE.get(e.get("likely_disease"), DEFAULT_ADVICE)
            return advice
    if price:
        return price
    return ("Nimeandika ujumbe wako.", "I have noted your message.")


def build_transcript(conversation_id: str, entries: tuple[dict, ...], village: str,
                     median_per_kg: float | None) -> dict:
    """Returns {'lines': [{i, role, sw, en, t}], 'sw': str, 'en': str}. Same inputs, same output."""
    rng = random.Random(zlib.crc32(f"{SEED}:{conversation_id}".encode()))
    greeting, goodbye = rng.choice(GREETINGS), rng.choice(GOODBYES)
    report = _farmer_report(entries, PRICE_QUESTION)
    reply = _agent_reply(entries, village, median_per_kg)
    turns = [("agent", greeting), ("farmer", report), ("agent", reply), ("farmer", ("Asante.", "Thank you.")), ("agent", goodbye)]
    lines = [{"i": i, "role": role, "sw": sw, "en": en, "t": i * 12} for i, (role, (sw, en)) in enumerate(turns)]
    label = {"agent": "Agent", "farmer": "Farmer"}
    return {
        "lines": lines,
        "sw": "\n".join(f"{label[r]}: {sw}" for r, (sw, _) in turns),
        "en": "\n".join(f"{label[r]}: {en}" for r, (_, en) in turns),
    }
