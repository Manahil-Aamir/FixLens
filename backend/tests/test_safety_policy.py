from app.application import safety_policy as sp
from app.domain.entities import Answer, Observation, Plan, Risk, Step
from app.infrastructure.yaml_kb import YamlKnowledgeBase

kb = YamlKnowledgeBase("kb").get("electric_kettle")


def _plan(*steps):
    return Plan(summary="s", steps=[Step(order=i + 1, instruction=t, risk=r) for i, (t, r) in enumerate(steps)])


def test_negated_photo_text_does_not_trigger():
    obs = Observation(object_id="electric_kettle", visible_issues=["no scorch marks visible"])
    assert sp.evaluate(obs, [], kb) == []


def test_burning_smell_answer_forces_stop_and_drops_diy_steps():
    obs = Observation(object_id="electric_kettle")
    answers = [Answer(question_id="q_smell", value="Yes, burning smell or sparks")]
    triggered = sp.evaluate(obs, answers, kb)
    out = sp.apply(_plan(("Descale the kettle", Risk.LOW)), triggered)
    assert out.escalate
    assert all(s.risk == Risk.STOP for s in out.steps)
    assert "Descale" not in " ".join(s.instruction for s in out.steps)


def test_forbidden_instruction_removed():
    out = sp.apply(_plan(("Remove the back panel and check the wiring", Risk.MEDIUM),
                         ("Check the plug fuse", Risk.LOW)), [])
    assert [s.instruction for s in out.steps] == ["Check the plug fuse"]