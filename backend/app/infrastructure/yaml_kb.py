import re
from pathlib import Path

import yaml
from pydantic import ValidationError

from app.domain.entities import ObjectKnowledge


class _KBLoader(yaml.SafeLoader):
    """YAML 1.1 reads yes/no/on/off as booleans; for KB text we want them as strings."""


_KBLoader.yaml_implicit_resolvers = {
    key: [(tag, rx) for tag, rx in resolvers if tag != "tag:yaml.org,2002:bool"]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_KBLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|false)$", re.IGNORECASE), list("tTfF")
)


class YamlKnowledgeBase:
    def __init__(self, kb_dir: str):
        self._objects: dict[str, ObjectKnowledge] = {}
        for path in sorted(Path(kb_dir).glob("*.yaml")):
            try:
                data = yaml.load(path.read_text(encoding="utf-8"), Loader=_KBLoader)
                obj = ObjectKnowledge.model_validate(data)
            except (ValidationError, yaml.YAMLError) as e:
                raise ValueError(f"Invalid KB file {path.name}: {e}") from e
            self._validate_refs(obj, path.name)
            self._objects[obj.id] = obj

    @staticmethod
    def _validate_refs(obj: ObjectKnowledge, filename: str) -> None:
        fault_ids = {f.id for f in obj.faults}
        for q in obj.questions:
            refs = set(q.distinguishes)
            for o in q.options:
                refs |= set(o.supports) | set(o.rules_out)
            missing = refs - fault_ids
            if missing:
                raise ValueError(f"{filename}: question {q.id} references unknown faults {missing}")

    def list_object_ids(self) -> list[str]:
        return list(self._objects)

    def get(self, object_id: str) -> ObjectKnowledge | None:
        return self._objects.get(object_id)