from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class Risk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    STOP = "stop"  # do not continue, call a professional


class DiagnosisStatus(str, Enum):
    NEEDS_ANSWERS = "needs_answers"
    COMPLETE = "complete"


# ---------- Knowledge base (loaded from YAML) ----------

class SafetyRule(BaseModel):
    id: str
    triggers: list[str]  # keywords matched against observations and answers
    risk: Risk
    message: str


class Fault(BaseModel):
    id: str
    name: str
    description: str
    visual_cues: list[str] = []   # words that may appear in the photo analysis
    checks: list[str] = []        # safe things the user can try


class QuestionOption(BaseModel):
    label: str
    supports: list[str] = []      # fault ids this answer makes more likely
    rules_out: list[str] = []     # fault ids this answer excludes


class KBQuestion(BaseModel):
    id: str
    text: str
    distinguishes: list[str]      # fault ids this question helps separate
    options: list[QuestionOption] = Field(min_length=2, max_length=5)


class ObjectKnowledge(BaseModel):
    id: str
    name: str
    components: list[str]
    faults: list[Fault]
    questions: list[KBQuestion] = []
    safety_rules: list[SafetyRule] = []


# ---------- Diagnosis flow ----------

class Observation(BaseModel):
    object_id: str  # a KB id, or "unknown"
    components: list[str] = []
    visible_issues: list[str] = []
    confidence: float = Field(ge=0, le=1, default=0.5)


class Question(BaseModel):
    id: str
    text: str
    options: list[str] = Field(min_length=2, max_length=5)


class Answer(BaseModel):
    question_id: str
    value: str


class Hypothesis(BaseModel):
    fault_id: str
    likelihood: float = Field(ge=0, le=1)
    reason: str = ""


class Step(BaseModel):
    order: int
    instruction: str
    risk: Risk = Risk.LOW
    stop_if: str | None = None 


class Plan(BaseModel):
    summary: str
    steps: list[Step]


class Diagnosis(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    status: DiagnosisStatus = DiagnosisStatus.NEEDS_ANSWERS
    observation: Observation
    questions: list[Question] = []
    answers: list[Answer] = []
    hypotheses: list[Hypothesis] = []
    plan: Plan | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))