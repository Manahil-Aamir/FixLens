from dataclasses import dataclass

from app.application.answer_questions import AnswerQuestions
from app.application.start_diagnosis import StartDiagnosis
from app.config import Settings
from app.domain.ports import KnowledgeBase, SessionRepo, VisionLLM
from app.infrastructure.baseten_llm import BasetenVisionLLM
from app.infrastructure.session_repo import SqliteSessionRepo
from app.infrastructure.yaml_kb import YamlKnowledgeBase


@dataclass(frozen=True)
class Container:
    kb: KnowledgeBase
    repo: SessionRepo
    start_diagnosis: StartDiagnosis
    answer_questions: AnswerQuestions


def make_container(
    kb: KnowledgeBase,
    llm: VisionLLM,
    repo: SessionRepo,
    ask_threshold: float,
    max_questions: int,
) -> Container:
    return Container(
        kb=kb,
        repo=repo,
        start_diagnosis=StartDiagnosis(llm, kb, repo, ask_threshold, max_questions),
        answer_questions=AnswerQuestions(llm, kb, repo, ask_threshold, max_questions),
    )


def build_container(s: Settings) -> Container:
    llm = BasetenVisionLLM(
        s.baseten_api_key, s.baseten_base_url, s.baseten_model, s.max_tokens, s.max_image_px
    )
    return make_container(
        YamlKnowledgeBase(s.kb_dir), llm, SqliteSessionRepo(s.db_path),
        s.ask_threshold, s.max_questions,
    )