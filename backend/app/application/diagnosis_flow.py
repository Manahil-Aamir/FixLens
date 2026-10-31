from app.application import hypothesis_ranker as hr
from app.application import safety_policy as sp
from app.domain.entities import Diagnosis, DiagnosisStatus, ObjectKnowledge, Plan, Risk
from app.domain.ports import VisionLLM


def advance(
    d: Diagnosis,
    obj: ObjectKnowledge,
    llm: VisionLLM,
    ask_threshold: float,
    max_questions: int,
) -> Diagnosis:
    d.hypotheses = hr.rank(d.observation, d.answers, obj)
    triggered = sp.evaluate(d.observation, d.answers, obj)
    must_stop = any(r.risk == Risk.STOP for r in triggered)

    if not must_stop:
        # Burn-like words in the photo alone are not enough to stop: confirm with the user first.
        if sp.needs_heat_confirmation(d.observation, d.answers):
            d.questions, d.plan = [sp.heat_confirmation_question()], None
            d.status = DiagnosisStatus.NEEDS_ANSWERS
            return d

        # Ask more only while unsure.
        if hr.needs_more_info(d.hypotheses, ask_threshold):
            questions = hr.select_questions(d.hypotheses, d.answers, obj, max_questions)
            if questions:
                d.questions, d.plan = questions, None
                d.status = DiagnosisStatus.NEEDS_ANSWERS
                return d

    d.questions = []
    base = Plan(summary="", steps=[]) if must_stop else llm.write_plan(
        d.observation, d.hypotheses, d.answers, obj
    )
    plan = sp.apply(base, triggered)
    if not must_stop and hr.is_inconclusive(d.hypotheses):
        plan.escalate = True
        d.notice = (
            "The answers don't point to one clear cause, so consider a professional opinion."
        )
    d.plan = plan
    d.status = DiagnosisStatus.COMPLETE
    return d