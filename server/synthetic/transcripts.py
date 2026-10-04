"""Short Kiswahili and English call transcripts for the SYNTHETIC season.

Written by the agent, not by a native speaker: they need a check by a Ugandan Kiswahili
speaker before they appear in a demo. Farmer lines are what an extraction would read;
the PIN is shown as [PIN], like a real redacted transcript. `evidence_quote` values are
exact substrings of one English farmer line and never the whole line.
"""

from dataclasses import dataclass

from farm_ledger import BuyerType, PaidHow
from farm_ledger.enums import CoffeeForm

SECONDS_PER_TURN = 9
Turn = tuple[str, str, str]  # role ("agent" or "farmer"), Kiswahili, English

OPENING: tuple[Turn, ...] = (
    ("agent",
     ("Habari, mimi ni kompyuta ya Simu ya Kahawa. Simu hii inarekodiwa ili kutunza kumbukumbu"
      " ya shamba lako. Unakubali?"),
     ("Hello, I am a computer, the Coffee Phone. This call is recorded to keep a record of your farm."
      " Do you agree?")),
    ("farmer", "Ndiyo, nakubali.", "Yes, I agree."),
    ("agent", "Tafadhali bonyeza nambari yako ya siri ya tarakimu nne.",
     "Please press your four-digit PIN."),
    ("farmer", "[PIN]", "[PIN]"),
)
CLOSING: tuple[Turn, ...] = (("agent", "Asante kwa kupiga simu. Kwaheri.", "Thank you for calling. Goodbye."),)
CONFIRM: Turn = ("farmer", "Ndiyo, sawa.", "Yes, that is right.")

FORM_WORDS = {
    CoffeeForm.KIBOKO: ("kiboko", "kiboko"),
    CoffeeForm.FAQ: ("kahawa iliyokobolewa (FAQ)", "FAQ"),
    CoffeeForm.PARCHMENT: ("parchment", "parchment"),
}
BUYER_WORDS = {
    BuyerType.MIDDLEMAN: ("kwa dalali {name}", "to a middleman, {name}"),
    BuyerType.COOPERATIVE: ("kwa chama cha ushirika", "to the cooperative"),
    BuyerType.OTHER: ("kwa mfanyabiashara wa kituo cha biashara", "to a trader at the trading centre"),
}
PAID_WORDS = {
    PaidHow.CASH: ("pesa taslimu", "in cash"),
    PaidHow.MOBILE_MONEY: ("kwa mobile money", "by mobile money"),
}
DISTRESS_SW = " Nilihitaji pesa za ada ya shule, kwa hiyo niliuza mapema kwa bei ndogo."
DISTRESS_EN = " I needed school fees, so I sold early at a low price."

ASK_SALE: Turn = ("agent", "Uliuza kahawa mara ya mwisho lini? Niambie kiasi, aina, bei kwa kilo na mnunuzi.",
                  "When did you last sell coffee? Tell me the amount, the type, the price per kilo and the buyer.")
ASK_HARVEST: Turn = ("agent", "Umevuna kahawa kiasi gani msimu huu?", "How much coffee did you harvest this season?")
ASK_PROBLEM: Turn = ("agent", "Kuna tatizo lolote kwenye kahawa yako mwaka huu?",
                     "Any problem with your coffee this year?")


@dataclass(frozen=True)
class Observation:
    symptom: str
    likely_disease: str
    disease_confidence: float
    farmer: tuple[str, str]
    quote: str
    ask: tuple[str, str]
    answer: tuple[str, str]
    verdict: tuple[str, str]


OBSERVATIONS = {
    "twig_borer": Observation(
        "wilting", "black_coffee_twig_borer", 0.7,
        ("Matawi ya kahawa yanakauka na kuna vitundu vidogo kwenye matawi.",
         "The coffee twigs are drying and there are small holes in the branches."),
        "twigs are drying",
        ("Je, kuna vumbi la mbao karibu na vitundu?", "Is there sawdust near the holes?"),
        ("Ndiyo, kuna vumbi kidogo.", "Yes, a little."),
        ("Huenda ni kipekecha matawi cheusi cha kahawa, lakini si uhakika. Tafadhali mwone afisa ugani.",
         "It may be the black coffee twig borer, but I am not sure. Please see the extension officer."),
    ),
    "wilt": Observation(
        "wilting", "coffee_wilt_disease", 0.65,
        ("Miti ya kahawa inanyauka ghafla, majani yanakuwa ya njano, kisha mti unakauka.",
         "The coffee trees are wilting suddenly, the leaves turn yellow, then the tree dies."),
        "wilting suddenly",
        ("Je, gome limepasuka karibu na shina?", "Is the bark cracked near the base?"),
        ("Ndiyo, gome limepasuka.", "Yes, the bark is cracked."),
        ("Huenda ni ugonjwa wa kunyauka kwa kahawa. Hili ni la haraka: mwone afisa ugani mara moja.",
         "It may be coffee wilt disease. This is urgent: see the extension officer right away."),
    ),
    "leaf_rust": Observation(
        "powder_or_rust", "coffee_leaf_rust", 0.75,
        ("Majani ya kahawa yana unga wa rangi ya machungwa upande wa chini.",
         "The coffee leaves have orange powder underneath."),
        "orange powder underneath",
        ("Je, majani yanapukutika?", "Are the leaves falling?"),
        ("Ndiyo, mengi yanapukutika.", "Yes, many are falling."),
        ("Huenda ni kutu ya majani ya kahawa, lakini si uhakika. Mwone afisa ugani.",
         "It may be coffee leaf rust, but I am not sure. See the extension officer."),
    ),
    "berry_disease": Observation(
        "fruit_spots", "coffee_berry_disease", 0.7,
        ("Matunda ya kahawa yana madoa meusi yaliyozama, na mengi yanaanguka kabla ya kuiva.",
         "The coffee berries have dark sunken spots and many fall before they ripen."),
        "dark sunken spots",
        ("Je, madoa yalianza matunda yakiwa mabichi?", "Did the spots start while the berries were green?"),
        ("Ndiyo, yalikuwa mabichi.", "Yes, they were green."),
        ("Huenda ni ugonjwa wa matunda ya kahawa, na ni wa haraka. Mwone afisa ugani mara moja.",
         "It may be coffee berry disease, and it is urgent. See the extension officer right away."),
    ),
}


def sale_turns(kg, form, price, buyer, buyer_name, paid, distress=False, unclear_price=False):
    """(turns, evidence quote) for a sale told with its weight and a price per kilo."""
    form_sw, form_en = FORM_WORDS[form]
    buyer_sw, buyer_en = (w.format(name=buyer_name) for w in BUYER_WORDS[buyer])
    paid_sw, paid_en = PAID_WORDS[paid]
    shown = "[unclear]" if unclear_price else f"{price:,}"
    sw = f"Nimeuza kilo {kg:,} za {form_sw} {buyer_sw}, shilingi {shown} kwa kilo, nimelipwa {paid_sw}."
    en = f"I sold {kg:,} kilos of {form_en} {buyer_en}, {shown} shillings a kilo, I was paid {paid_en}."
    if distress:
        sw, en = sw + DISTRESS_SW, en + DISTRESS_EN
    quote = f"I sold {kg:,} kilos" if unclear_price else f"{price:,} shillings a kilo"
    read_back = ("agent", f"Nimeelewa: kilo {kg:,} za {form_sw}, shilingi {shown} kwa kilo. Sawa?",
                 f"I understood: {kg:,} kilos of {form_en}, {shown} shillings a kilo. Is that right?")
    return (ASK_SALE, ("farmer", sw, en), read_back, CONFIRM), quote


def bag_sale_turns(form, total, buyer_name):
    """A sale told in bags with no weight: only the total paid is known."""
    form_sw, form_en = FORM_WORDS[form]
    sw = f"Nimeuza gunia moja la {form_sw} kwa dalali {buyer_name}, nimelipwa shilingi {total:,} taslimu."
    en = f"I sold one bag of {form_en} to a middleman, {buyer_name}, I was paid {total:,} shillings in cash."
    read_back = ("agent", f"Nimeelewa: gunia moja la {form_sw}, shilingi {total:,}. Sawa?",
                 f"I understood: one bag of {form_en}, {total:,} shillings. Is that right?")
    return (ASK_SALE, ("farmer", sw, en), read_back, CONFIRM), f"one bag of {form_en}"


def harvest_turns(kg, form):
    form_sw, form_en = FORM_WORDS[form]
    sw = f"Msimu huu nimevuna kilo {kg:,} za {form_sw}."
    en = f"This season I harvested {kg:,} kilos of {form_en}."
    read_back = ("agent", f"Nimeandika kilo {kg:,}. Sawa?", f"I noted {kg:,} kilos. Is that right?")
    return (ASK_HARVEST, ("farmer", sw, en), read_back, CONFIRM), f"harvested {kg:,} kilos"


def observation_turns(case: Observation):
    return (
        ASK_PROBLEM, ("farmer", *case.farmer), ("agent", *case.ask), ("farmer", *case.answer),
        ("agent", *case.verdict),
    )


def render(middle: tuple[Turn, ...]):
    """(transcript_lines, transcript_sw, transcript_en, duration_secs) for a whole call."""
    turns = (*OPENING, *middle, *CLOSING)
    lines = [
        {"i": i, "role": role, "sw": sw, "en": en, "t": i * SECONDS_PER_TURN}
        for i, (role, sw, en) in enumerate(turns)
    ]
    label = {"agent": "Agent", "farmer": "Farmer"}
    return (
        lines,
        "\n".join(f"{label[ln['role']]}: {ln['sw']}" for ln in lines),
        "\n".join(f"{label[ln['role']]}: {ln['en']}" for ln in lines),
        len(turns) * SECONDS_PER_TURN,
    )
