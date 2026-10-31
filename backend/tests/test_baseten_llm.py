import io
from types import SimpleNamespace as NS

import pytest
from PIL import Image

from app.application.hypothesis_ranker import rank
from app.domain.entities import Observation
from app.domain.errors import InvalidImage
from app.infrastructure.baseten_llm import BasetenVisionLLM, LLMOutputError
from app.infrastructure.yaml_kb import YamlKnowledgeBase

KB = YamlKnowledgeBase("kb")
IDS = KB.list_object_ids()


def _jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), "white").save(buf, "JPEG")
    return buf.getvalue()


class FakeClient:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, **kw):
        self.calls.append(kw)
        content = self.replies.pop(0)
        return NS(choices=[NS(finish_reason="stop", message=NS(content=content))])


def _llm(replies):
    client = FakeClient(replies)
    return BasetenVisionLLM("k", "http://x", "m", client=client), client


def test_identify_parses_fenced_json():
    llm, _ = _llm(['```json\n{"object_id": "Electric Kettle", "components": ["lid"], '
                   '"visible_issues": ["white deposit"], "confidence": 0.9}\n```'])
    obs = llm.identify(_jpeg(), "image/jpeg", IDS)
    assert obs.object_id == "electric_kettle"
    assert obs.visible_issues == ["white deposit"]


def test_unknown_object_is_clamped():
    llm, _ = _llm(['{"object_id": "dishwasher", "confidence": 0.95}'])
    obs = llm.identify(_jpeg(), "image/jpeg", IDS)
    assert obs.object_id == "unknown" and obs.confidence <= 0.3


def test_retries_on_bad_json():
    llm, client = _llm(["Sure! Here you go", '{"object_id": "toaster"}'])
    assert llm.identify(_jpeg(), "image/jpeg", IDS).object_id == "toaster"
    assert len(client.calls) == 2


def test_empty_reply_doubles_token_budget():
    llm, client = _llm(["", '{"object_id": "toaster"}'])
    llm.identify(_jpeg(), "image/jpeg", IDS)
    assert client.calls[1]["max_tokens"] == 2 * client.calls[0]["max_tokens"]


def test_gives_up_after_attempts():
    llm, _ = _llm(["nope", "still nope", "no"])
    with pytest.raises(LLMOutputError):
        llm.identify(_jpeg(), "image/jpeg", IDS)


def test_write_plan_orders_steps():
    kettle = KB.get("electric_kettle")
    obs = Observation(object_id="electric_kettle", visible_issues=["white deposit"])
    hyps = rank(obs, [], kettle)
    llm, _ = _llm(['{"summary": "Likely limescale.", "escalate": false, "steps": ['
                   '{"instruction": "Unplug the kettle.", "risk": "low"},'
                   '{"instruction": "Descale with vinegar.", "risk": "medium", "stop_if": "cracks"}]}'])
    plan = llm.write_plan(obs, hyps, [], kettle)
    assert [s.order for s in plan.steps] == [1, 2]
    assert plan.steps[1].stop_if == "cracks"
    
def test_bad_image_raises_invalid_image():
    llm, _ = _llm([])
    with pytest.raises(InvalidImage):
        llm.identify(b"not an image", "image/jpeg", IDS)