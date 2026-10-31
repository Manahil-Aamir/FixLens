import re

from app.domain.entities import (
    Answer, ObjectKnowledge, Observation, Plan, Question, Risk, SafetyRule, Step,
)

_RANK = {Risk.LOW: 0, Risk.MEDIUM: 1, Risk.HIGH: 2, Risk.STOP: 3}

CONFIRM_QUESTION_ID = "q_safety_check"
CONFIRM_YES = "Yes, I notice one of these"
CONFIRM_NO = "No, none of these"

# Words a vision model often uses for normal wear (an iron's soleplate, a toaster's browning,
# a stained kettle base). Seen in a photo alone they justify a question, not a STOP.
PHOTO_NEEDS_CONFIRMATION = ("burn mark", "scorch", "melted")

# Apply to every appliance, on top of each KB file's own rules.
GLOBAL_RULES = [
    SafetyRule(
        id="g_fire",
        triggers=["burning smell", "smell of burning", "smoke", "sparks", "sparking", "melted", "scorch", "burn mark", "on fire"],
        risk=Risk.STOP,
        message="Stop using the appliance. Unplug it only if you can reach the plug safely, keep it away from flammable things, and do not try to repair it.",
    ),
    SafetyRule(
        id="g_exposed_wiring",
        triggers=["exposed wire", "bare wire", "frayed", "damaged cord", "damaged plug"],
        risk=Risk.STOP,
        message="Do not use it. A damaged cord, plug or exposed wiring is a fire and shock risk.",
    ),
    SafetyRule(
        id="g_gas",
        triggers=["smell of gas", "gas smell", "gas leak"],
        risk=Risk.STOP,
        message="Leave the area, avoid switches and flames, and contact your gas provider or emergency services.",
    ),
    SafetyRule(
        id="g_swollen_battery",
        triggers=["swollen battery", "bulging battery"],
        risk=Risk.STOP,
        message="Stop using it and keep it away from heat. Swollen batteries can catch fire.",
    ),
    SafetyRule(
        id="g_water_electrics",
        triggers=["water in the base", "water got into the base", "water near the socket", "wet plug", "wet socket"],
        risk=Risk.STOP,
        message="Do not plug it in or touch it while wet. Water and electrics are a shock hazard.",
    ),
]

# Steps matching these are removed, unless the step is telling the user NOT to do it.
FORBIDDEN_INSTRUCTIONS = [
    r"\bopen(s|ed|ing)? (up )?the (casing|housing|body|unit|cabinet)\b",
    r"\bremov(e|es|ed|ing) (the )?(back|rear|side|cover|panel|casing|housing)\b",
    r"\bunscrew(s|ed|ing)?\b",
    r"\bwhile (it is |it's )?plugged in\b",
    r"\bbypass(es|ed|ing)?\b",
    r"\bjump(er)?\b|\bshort[- ]?(circuit|out)\b",
    r"\bcapacitor\b",
    r"\bsolder(s|ed|ing)?\b",
]
_FORBIDDEN = re.compile("|".join(FORBIDDEN_INSTRUCTIONS), re.IGNORECASE)
_PROHIBITION = re.compile(r"\b(without|do not|don't|never|avoid|not)\b[^.;]{0,40}$", re.IGNORECASE)

# "no burning smell" should not trigger "burning smell".
_NEGATION = re.compile(r"\b(no|not|without|free of|none|isn't|doesn't)\b[^.;,]{0,20}$")


def _present(trigger: str, text: str, check_negation: bool) -> bool:
    start = 0
    while (i := text.find(trigger, start)) != -1:
        if not check_negation or not _NEGATION.search(text[max(0, i - 30):i]):
            return True
        start = i + len(trigger)
    return False


def _ambiguous(trigger: str) -> bool:
    return any(p in trigger for p in PHOTO_NEEDS_CONFIRMATION)


def violates_policy(instruction: str) -> bool:
    """True for 'Unscrew the cover'; False for 'Without unscrewing anything, look inside'."""
    for m in _FORBIDDEN.finditer(instruction):
        if not _PROHIBITION.search(instruction[max(0, m.start() - 60):m.start()]):
            return True
    return False


# ---------- heat-damage confirmation ----------

def needs_heat_confirmation(observation: Observation, answers: list[Answer]) -> bool:
    """Photo shows burn-like words and the user has not been asked about them yet."""
    if any(a.question_id == CONFIRM_QUESTION_ID for a in answers):
        return False
    photo_text = " ".join(observation.visible_issues).lower()
    return any(_present(t, photo_text, True) for t in PHOTO_NEEDS_CONFIRMATION)


def heat_confirmation_question() -> Question:
    return Question(
        id=CONFIRM_QUESTION_ID,
        text=(
            "The photo shows what may be burn or heat marks. Do you notice any of these: "
            "a burning smell, sparks, smoke, melted plastic, or a damaged cord or plug?"
        ),
        options=[CONFIRM_YES, CONFIRM_NO],
    )


def evaluate(
    observation: Observation, answers: list[Answer], kb: ObjectKnowledge
) -> list[SafetyRule]:
    """Return every safety rule triggered by the photo analysis or the user's answers."""
    photo_text = " ".join(observation.visible_issues).lower()
    answer_text = " ".join(
        a.value for a in answers if a.question_id != CONFIRM_QUESTION_ID
    ).lower()
    confirmed = any(
        a.question_id == CONFIRM_QUESTION_ID and a.value == CONFIRM_YES for a in answers
    )

    triggered: list[SafetyRule] = []
    used_triggers: set[str] = set()

    # Appliance-specific rules go first because they are more precise than the global ones.
    # A rule is skipped when it shares triggers with one that already fired.
    for rule in [*kb.safety_rules, *GLOBAL_RULES]:
        triggers = {t.lower() for t in rule.triggers}
        if triggers & used_triggers:
            continue
        for t in triggers:
            # Ambiguous heat words in the photo only count once the user confirmed them.
            photo_hit = (confirmed or not _ambiguous(t)) and _present(t, photo_text, True)
            # Answers are the user's chosen labels, so match them directly.
            if photo_hit or _present(t, answer_text, False):
                triggered.append(rule)
                used_triggers |= triggers
                break

    return sorted(triggered, key=lambda r: -_RANK[r.risk])


def apply(plan: Plan, triggered: list[SafetyRule]) -> Plan:
    """Enforce safety on the model's plan. The result can only be safer than the input."""
    steps = [s for s in plan.steps if not violates_policy(s.instruction)]
    worst = triggered[0].risk if triggered else Risk.LOW

    if worst == Risk.STOP:
        stops = [r for r in triggered if r.risk == Risk.STOP]
        out = [Step(order=i + 1, instruction=r.message, risk=Risk.STOP) for i, r in enumerate(stops)]
        out.append(Step(
            order=len(out) + 1,
            instruction="Contact a qualified repair technician or the manufacturer before using or repairing this appliance.",
            risk=Risk.STOP,
        ))
        return Plan(summary="Safety first: this should not be a DIY fix.", steps=out, escalate=True)

    warnings = [
        Step(order=0, instruction=r.message, risk=r.risk)
        for r in triggered if _RANK[r.risk] >= _RANK[Risk.MEDIUM]
    ]
    if worst == Risk.HIGH:
        steps = [s for s in steps if _RANK[s.risk] < _RANK[Risk.HIGH]]

    escalate = plan.escalate or worst == Risk.HIGH
    final = warnings + steps
    if not steps:
        final.append(Step(order=0, instruction="If these checks don't help, contact a repair technician.", risk=Risk.LOW))
        escalate = True

    for i, s in enumerate(final, start=1):
        s.order = i
    return Plan(summary=plan.summary, steps=final, escalate=escalate)