from typing import Literal

from pydantic import BaseModel, Field

from app.application import hypothesis_ranker as hr
from app.domain.entities import Diagnosis, DiagnosisStatus, Risk
from app.domain.ports import KnowledgeBase


class AnswerIn(BaseModel):
    question_id: str
    value: str


class AnswersIn(BaseModel):
    answers: list[AnswerIn] = Field(min_length=1)


class QuestionOut(BaseModel):
    id: str
    text: str
    options: list[str]


class StepOut(BaseModel):
    order: int
    instruction: str
    risk: Risk
    stop_if: str | None = None


class PlanOut(BaseModel):
    summary: str
    escalate: bool
    steps: list[StepOut]


class HypothesisOut(BaseModel):
    fault_id: str
    name: str
    label: Literal["most_likely", "possible"]


class ObservationOut(BaseModel):
    object_id: str
    components: list[str]
    visible_issues: list[str]


class DiagnosisOut(BaseModel):
    id: str
    status: DiagnosisStatus
    appliance: str | None
    observation: ObservationOut
    questions: list[QuestionOut]
    hypotheses: list[HypothesisOut]
    plan: PlanOut | None
    notice: str | None


def to_response(d: Diagnosis, kb: KnowledgeBase) -> DiagnosisOut:
    obj = kb.get(d.observation.object_id)
    fault_names = {f.id: f.name for f in obj.faults} if obj else {}

    hypotheses: list[HypothesisOut] = []
    if d.status == DiagnosisStatus.COMPLETE:
        clear_winner = not hr.is_inconclusive(d.hypotheses)
        for i, h in enumerate(d.hypotheses[:3]):
            hypotheses.append(HypothesisOut(
                fault_id=h.fault_id,
                name=fault_names.get(h.fault_id, h.fault_id),
                label="most_likely" if (i == 0 and clear_winner) else "possible",
            ))

    return DiagnosisOut(
        id=d.id,
        status=d.status,
        appliance=obj.name if obj else None,
        observation=ObservationOut(
            object_id=d.observation.object_id,
            components=d.observation.components,
            visible_issues=d.observation.visible_issues,
        ),
        questions=[QuestionOut(id=q.id, text=q.text, options=q.options) for q in d.questions],
        hypotheses=hypotheses,
        plan=PlanOut(
            summary=d.plan.summary,
            escalate=d.plan.escalate,
            steps=[StepOut(**s.model_dump(include={"order", "instruction", "risk", "stop_if"}))
                   for s in d.plan.steps],
        ) if d.plan else None,
        notice=d.notice,
    )