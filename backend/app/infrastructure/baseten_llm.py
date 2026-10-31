import base64
import json
import logging
import re
import time
from typing import TypeVar

from openai import OpenAI, OpenAIError
from app.domain.errors import InvalidImage, LLMError, LLMUnavailable
from pydantic import BaseModel, Field, ValidationError

from app.domain.entities import (
    Answer, Hypothesis, ObjectKnowledge, Observation, Plan, Risk, Step,
)
from app.infrastructure.image_utils import prepare_image

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

IDENTIFY_SYSTEM = (
    "You are a careful visual inspector for household appliances. Describe only what is "
    "visibly present in the photo; never guess at hidden or internal parts. "
    "Reply with ONE JSON object and nothing else: no prose, no markdown."
)

IDENTIFY_USER = """Known appliance ids: {objects}
Pick the id that matches the appliance in the photo, or "unknown" if it matches none or you are not sure.

JSON schema:
{{"object_id": string, "components": [string], "visible_issues": [string], "confidence": number between 0 and 1}}

Rules:
- components: parts you can actually see, short names.
- visible_issues: short plain phrases for visible damage or abnormal conditions, e.g. "white deposit inside", "frayed cord", "water stain", "cracked lid", "burn mark". If nothing looks wrong, return an empty list. Never write phrases like "no damage".
- Where one of these phrases fits what you see, use it exactly; otherwise use your own short phrase: {cues}
- confidence: how sure you are about object_id."""

PLAN_SYSTEM = (
    "You write safe, practical troubleshooting plans for household appliances for non-experts. "
    "Reply with ONE JSON object and nothing else: no prose, no markdown."
)

PLAN_RULES = """Rules:
- Base the steps on the candidate faults and their listed checks. Do not invent other repairs.
- Order steps from simplest and safest to more involved. Use 3 to 6 steps.
- The first step must be to unplug the appliance (or switch it off) when that is relevant.
- NEVER tell the user to open the casing, remove panels, unscrew anything, touch internal electrical parts, or bypass any safety device.
- risk is one of: "low", "medium", "high", "stop".
- stop_if: an optional short warning sign that means the user should stop and call a professional.
- Set escalate to true if a professional is probably needed.
- Never mention percentages, probabilities or scores.

JSON schema:
{"summary": string, "escalate": boolean, "steps": [{"instruction": string, "risk": string, "stop_if": string or null}]}"""


class LLMOutputError(LLMError):
    """The model did not return usable output after retries."""


class _IdentifyOut(BaseModel):
    object_id: str
    components: list[str] = []
    visible_issues: list[str] = []
    confidence: float = Field(default=0.5, ge=0, le=1)


class _StepOut(BaseModel):
    instruction: str
    risk: Risk = Risk.LOW
    stop_if: str | None = None


class _PlanOut(BaseModel):
    summary: str
    steps: list[_StepOut] = Field(min_length=1)
    escalate: bool = False


def _extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found in reply")
    return json.loads(text[start : end + 1])


class BasetenVisionLLM:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        max_tokens: int = 3000,
        max_image_px: int = 1024,
        token_cap: int = 6000,
        attempts: int = 3,
        timeout: float = 30.0,
        client: OpenAI | None = None,
    ):
        self._client = client or OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        self._model = model
        self._max_tokens = max_tokens
        self._max_px = max_image_px
        self._token_cap = token_cap
        self._attempts = attempts

    # ---------- core call ----------

    def _complete_json(self, messages: list[dict], model_cls: type[T]) -> T:
        max_tokens = self._max_tokens
        last_error = "unknown"
        for attempt in range(1, self._attempts + 1):
            started = time.perf_counter()
            try:
                resp = self._client.chat.completions.create(
                    model=self._model, messages=messages, max_tokens=max_tokens
                )
            except OpenAIError as e:
                log.warning("model call failed after %.1fs: %s", time.perf_counter() - started, e)
                raise LLMUnavailable(f"Model service error: {e}") from e

            usage = getattr(resp, "usage", None)
            details = getattr(usage, "completion_tokens_details", None)
            log.info(
                "model call %.1fs completion_tokens=%s reasoning_tokens=%s",
                time.perf_counter() - started,
                getattr(usage, "completion_tokens", "?"),
                getattr(details, "reasoning_tokens", "?"),
            )

            choice = resp.choices[0]
            content = (choice.message.content or "").strip()

            if not content:
                # Reasoning models can spend the whole budget thinking. Give them more room.
                last_error = f"empty reply (finish_reason={choice.finish_reason})"
                max_tokens = min(max_tokens * 2, self._token_cap)
                continue
            try:
                return model_cls.model_validate(_extract_json(content))
            except (ValueError, ValidationError) as e:
                last_error = str(e)[:300]
                messages = messages + [
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": (
                        "That reply was not valid. Reply again with ONLY the JSON object "
                        f"matching the schema. Problem: {last_error}"
                    )},
                ]
        raise LLMOutputError(f"No valid JSON after {self._attempts} attempts: {last_error}")

    # ---------- VisionLLM port ----------

    def identify(
        self,
        image: bytes,
        mime: str,
        known_objects: list[str],
        cue_hints: list[str] | None = None,
    ) -> Observation:
        try:
            jpeg, out_mime = prepare_image(image, self._max_px)
        except ValueError as e:
            raise InvalidImage(str(e)) from e
        b64 = base64.b64encode(jpeg).decode()

        prompt = IDENTIFY_USER.format(
            objects=", ".join(known_objects),
            cues=", ".join(cue_hints or []) or "n/a",
        )
        messages = [
            {"role": "system", "content": IDENTIFY_SYSTEM},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{out_mime};base64,{b64}"}},
            ]},
        ]
        out = self._complete_json(messages, _IdentifyOut)

        object_id = out.object_id.strip().lower().replace(" ", "_").replace("-", "_")
        confidence = out.confidence
        if object_id not in known_objects:
            object_id, confidence = "unknown", min(confidence, 0.3)
        return Observation(
            object_id=object_id,
            components=[c.strip() for c in out.components if c.strip()],
            visible_issues=[v.strip() for v in out.visible_issues if v.strip()],
            confidence=confidence,
        )

    def write_plan(
        self,
        observation: Observation,
        hypotheses: list[Hypothesis],
        answers: list[Answer],
        kb: ObjectKnowledge,
    ) -> Plan:
        faults = {f.id: f for f in kb.faults}
        questions = {q.id: q for q in kb.questions}

        lines = [f"Appliance: {kb.name}"]
        lines.append("Visible in photo: " + (", ".join(observation.components) or "n/a"))
        lines.append("Visible issues: " + (", ".join(observation.visible_issues) or "none noted"))
        if answers:
            lines.append("User answers:")
            for a in answers:
                q = questions.get(a.question_id)
                lines.append(f"- {q.text if q else a.question_id} -> {a.value}")
        lines.append("Candidate faults, most likely first:")
        for i, h in enumerate(hypotheses[:3]):
            f = faults.get(h.fault_id)
            if not f:
                continue
            tag = "most likely" if i == 0 else "also possible"
            lines.append(f"- {f.name} ({tag}): {f.description}")
            for c in f.checks:
                lines.append(f"    safe check: {c}")

        messages = [
            {"role": "system", "content": PLAN_SYSTEM},
            {"role": "user", "content": "\n".join(lines) + "\n\n" + PLAN_RULES},
        ]
        out = self._complete_json(messages, _PlanOut)
        return Plan(
            summary=out.summary,
            steps=[
                Step(order=i, instruction=s.instruction, risk=s.risk, stop_if=s.stop_if)
                for i, s in enumerate(out.steps, start=1)
            ],
            escalate=out.escalate,
        )