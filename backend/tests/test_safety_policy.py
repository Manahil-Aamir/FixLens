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
    

def test_overlapping_rules_are_deduplicated():
    obs = Observation(object_id="electric_kettle")
    answers = [Answer(question_id="q_smell", value="Yes, burning smell or sparks")]
    ids = [r.id for r in sp.evaluate(obs, answers, kb)]
    assert "sr_burning" in ids
    assert "g_fire" not in ids
    
def test_prohibitions_are_not_mistaken_for_instructions():
    assert not sp.violates_policy("Without unscrewing or opening the casing, look under the nozzle.")
    assert not sp.violates_policy("Do not remove the back panel.")
    assert sp.violates_policy("Remove the back panel and check the wiring.")
    assert sp.violates_policy("Unscrewing the cover is the next step.")


def test_photo_burn_words_alone_do_not_stop_but_ask():
    obs = Observation(object_id="electric_kettle", visible_issues=["scorch", "burn mark"])
    assert sp.evaluate(obs, [], kb) == []
    assert sp.needs_heat_confirmation(obs, [])


def test_confirmed_heat_damage_stops_and_denial_does_not():
    obs = Observation(object_id="electric_kettle", visible_issues=["burn mark"])
    yes = [Answer(question_id=sp.CONFIRM_QUESTION_ID, value=sp.CONFIRM_YES)]
    no = [Answer(question_id=sp.CONFIRM_QUESTION_ID, value=sp.CONFIRM_NO)]
    assert any(r.risk == Risk.STOP for r in sp.evaluate(obs, yes, kb))
    assert sp.evaluate(obs, no, kb) == []
    assert not sp.needs_heat_confirmation(obs, no)