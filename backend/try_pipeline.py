import logging
import sys

from app.application import hypothesis_ranker as hr
from app.application import safety_policy as sp
from app.config import get_settings
from app.domain.entities import Answer
from app.infrastructure.baseten_llm import BasetenVisionLLM
from app.infrastructure.yaml_kb import YamlKnowledgeBase


def ask_choice(options: list[str]) -> str:
    """Keep asking until the user types a valid option number."""
    for i, o in enumerate(options, 1):
        print(f"  {i}. {o}")
    while True:
        raw = input("> ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print(f"Please enter a number from 1 to {len(options)}")


def main(path: str) -> None:
    s = get_settings()
    kb = YamlKnowledgeBase(s.kb_dir)
    llm = BasetenVisionLLM(
        s.baseten_api_key, s.baseten_base_url, s.baseten_model,
        s.max_tokens, s.max_image_px,
    )

    with open(path, "rb") as f:
        image = f.read()

    # 1. Look at the photo
    obs = llm.identify(
        image, "image/jpeg", kb.list_object_ids(), cue_hints=kb.all_visual_cues()
    )
    print("\nOBSERVATION\n", obs.model_dump_json(indent=2))

    obj = kb.get(obs.object_id)
    if obj is None:
        print("\nNot a supported appliance, stopping.")
        return

    # 2. Rank faults, and ask questions only while unsure
    answers: list[Answer] = []
    while True:
        hyps = hr.rank(obs, answers, obj)
        print("\nTOP HYPOTHESES:", [(h.fault_id, h.likelihood) for h in hyps[:3]])

        if not hr.needs_more_info(hyps, s.ask_threshold):
            break
        questions = hr.select_questions(hyps, answers, obj, s.max_questions)
        if not questions:
            break
        for q in questions:
            print("\n" + q.text)
            answers.append(Answer(question_id=q.id, value=ask_choice(q.options)))

    inconclusive = hr.is_inconclusive(hyps)
    if inconclusive:
        print("\nThe answers do not point to one clear cause.")

    # 3. Write the plan, then let the safety rules override it
    plan = llm.write_plan(obs, hyps, answers, obj)
    plan = sp.apply(plan, sp.evaluate(obs, answers, obj))
    if inconclusive:
        plan.escalate = True

    print("\nPLAN:", plan.summary, "| escalate:", plan.escalate)
    for st in plan.steps:
        extra = f"  (stop if: {st.stop_if})" if st.stop_if else ""
        print(f"{st.order}. [{st.risk.value}] {st.instruction}{extra}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) != 2:
        sys.exit("Usage: python try_pipeline.py path\\to\\photo.jpg")
    main(sys.argv[1])