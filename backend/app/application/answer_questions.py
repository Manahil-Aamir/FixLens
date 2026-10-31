from app.application.diagnosis_flow import advance
from app.domain.entities import Answer, Diagnosis, DiagnosisStatus
from app.domain.errors import DiagnosisClosed, DiagnosisNotFound, InvalidAnswer
from app.domain.ports import KnowledgeBase, SessionRepo, VisionLLM


class AnswerQuestions:
    def __init__(
        self,
        llm: VisionLLM,
        kb: KnowledgeBase,
        repo: SessionRepo,
        ask_threshold: float,
        max_questions: int,
    ):
        self._llm, self._kb, self._repo = llm, kb, repo
        self._ask_threshold, self._max_questions = ask_threshold, max_questions

    def execute(self, diagnosis_id: str, answers: list[Answer]) -> Diagnosis:
        diagnosis = self._repo.get(diagnosis_id)
        if diagnosis is None:
            raise DiagnosisNotFound("Diagnosis not found.")
        if diagnosis.status != DiagnosisStatus.NEEDS_ANSWERS:
            raise DiagnosisClosed("This diagnosis has no open questions.")

        open_questions = {q.id: q for q in diagnosis.questions}
        given_ids = [a.question_id for a in answers]
        if len(set(given_ids)) != len(given_ids) or set(given_ids) != set(open_questions):
            raise InvalidAnswer(
                "Answer every open question exactly once: " + ", ".join(open_questions)
            )
        for a in answers:
            if a.value not in open_questions[a.question_id].options:
                raise InvalidAnswer(f"'{a.value}' is not an option for {a.question_id}.")

        obj = self._kb.get(diagnosis.observation.object_id)
        if obj is None:  # the KB changed since this diagnosis was stored
            raise DiagnosisClosed("This appliance is no longer supported.")

        diagnosis.answers.extend(answers)
        advance(diagnosis, obj, self._llm, self._ask_threshold, self._max_questions)
        self._repo.save(diagnosis)
        return diagnosis