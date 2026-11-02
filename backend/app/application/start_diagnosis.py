from app.application.diagnosis_flow import advance
from app.domain.entities import Diagnosis, DiagnosisStatus
from app.domain.ports import KnowledgeBase, SessionRepo, VisionLLM

MAX_NOTE_CHARS = 500


class StartDiagnosis:
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

    def execute(self, image: bytes, mime: str, note: str | None = None) -> Diagnosis:
        observation = self._llm.identify(
            image, mime, self._kb.list_object_ids(), cue_hints=self._kb.all_visual_cues()
        )
        # model_copy: never mutate the object the model adapter returned
        observation = observation.model_copy(
            update={"note": (note or "").strip()[:MAX_NOTE_CHARS]}
        )
        diagnosis = Diagnosis(observation=observation)
        obj = self._kb.get(observation.object_id)

        if obj is None:
            diagnosis.status = DiagnosisStatus.UNSUPPORTED
            diagnosis.notice = (
                "I could not match this to a supported appliance. "
                "Try a clearer, closer photo of one appliance."
            )
        else:
            advance(diagnosis, obj, self._llm, self._ask_threshold, self._max_questions)

        self._repo.save(diagnosis)
        return diagnosis