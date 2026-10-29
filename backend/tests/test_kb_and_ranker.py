from app.application.hypothesis_ranker import needs_more_info, rank, select_questions
from app.domain.entities import Answer, Observation
from app.infrastructure.yaml_kb import YamlKnowledgeBase

kb = YamlKnowledgeBase("kb").get("electric_kettle")
obs = Observation(object_id="electric_kettle", visible_issues=["white deposit inside the jug"])


def test_limescale_leads_from_photo_and_answers():
    h0 = rank(obs, [], kb)
    assert h0[0].fault_id == "limescale_slow_boil"
    h1 = rank(obs, [Answer(question_id="q_boil_time", value="Yes, noticeably longer")], kb)
    assert h1[0].likelihood > h0[0].likelihood


def test_asks_only_when_unsure_and_never_repeats():
    blank = Observation(object_id="electric_kettle")
    hyps = rank(blank, [], kb)
    assert needs_more_info(hyps, 0.6)
    qs = select_questions(hyps, [], kb)
    assert 0 < len(qs) <= 2
    answered = [Answer(question_id=qs[0].id, value=qs[0].options[0])]
    assert qs[0].id not in {q.id for q in select_questions(hyps, answered, kb)}