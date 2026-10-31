from __future__ import annotations

from typing import Protocol

from app.domain.entities import (
    Answer, Diagnosis, Hypothesis, ObjectKnowledge, Observation, Plan,
)


class VisionLLM(Protocol):
    """Everything model-related lives behind this. Swap or fake it freely."""

    def identify(
        self,
        image: bytes,
        mime: str,
        known_objects: list[str],
        cue_hints: list[str] | None = None,
    ) -> Observation: ...

    def write_plan(
        self,
        observation: Observation,
        hypotheses: list[Hypothesis],
        answers: list[Answer],
        kb: ObjectKnowledge,
    ) -> Plan: ...


class KnowledgeBase(Protocol):
    def list_object_ids(self) -> list[str]: ...
    def get(self, object_id: str) -> ObjectKnowledge | None: ...
    def all_visual_cues(self) -> list[str]: ...


class SessionRepo(Protocol):
    def save(self, diagnosis: Diagnosis) -> None: ...
    def get(self, diagnosis_id: str) -> Diagnosis | None: ...