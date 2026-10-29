import logging
import sys

from app.application import hypothesis_ranker as hr
from app.application import safety_policy as sp
from app.config import get_settings
from app.domain.entities import Answer
from app.infrastructure.baseten_llm import BasetenVisionLLM
from app.infrastructure.yaml_kb import YamlKnowledgeBase


def main(path: str) -> None:
    s = get_settings()
    kb = YamlKnowledgeBase(s.kb_dir)
    llm = BasetenVisionLLM(s.baseten_api_key, s.baseten_base_url, s.baseten_model,
                           s.max_tokens, s.max_image_px)

    obs = llm.identify(open(path, "rb").read(), "image/jpeg", kb.list_object_ids())
    print("\nOBSERVATION\n", obs.model_dump_json(indent=2))
    obj = kb.get(obs.object_id)
    if obj is None:
        print("\nNot a supported appliance, stopping.")
        return

    answers: list[Answer] = []
    while True:
        hyps = hr.rank(obs, answers, obj)
        print("\nTOP HYPOTHESES:", [(h.fault_id, h.likelihood) for h in hyps[:3]])
        if not hr.needs_more_info(hyps, s.ask_threshold):
            break
        qs = hr.select_questions(hyps, answers, obj, s.max_questions)
        if not qs:
            break
        for q in qs:
            print("\n" + q.text)
            for i, o in enumerate(q.options, 1):
                print(f"  {i}. {o}")
            choice = int(input("> "))
            answers.append(Answer(question_id=q.id, value=q.options[choice - 1]))

    plan = llm.write_plan(obs, hyps, answers, obj)
    plan = sp.apply(plan, sp.evaluate(obs, answers, obj))
    print("\nPLAN:", plan.summary, "| escalate:", plan.escalate)
    for st in plan.steps:
        extra = f"  (stop if: {st.stop_if})" if st.stop_if else ""
        print(f"{st.order}. [{st.risk.value}] {st.instruction}{extra}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main(sys.argv[1])