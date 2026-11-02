from app.domain.entities import Answer, Hypothesis, ObjectKnowledge, Observation, Question

CUE_BOOST = 1.0
SUPPORT_BOOST = 4.0
RULE_OUT_FACTOR = 0.05


def rank(observation: Observation, answers: list[Answer], kb: ObjectKnowledge) -> list[Hypothesis]:
    text = " ".join([*observation.visible_issues, observation.note]).lower()
    scores: dict[str, float] = {}
    reasons: dict[str, list[str]] = {f.id: [] for f in kb.faults}

    for f in kb.faults:
        hits = [c for c in f.visual_cues if c.lower() in text]
        scores[f.id] = 1.0 + CUE_BOOST * len(hits)
        if hits:
            reasons[f.id].append("photo shows: " + ", ".join(hits))

    questions = {q.id: q for q in kb.questions}
    for a in answers:
        q = questions.get(a.question_id)
        opt = next((o for o in q.options if o.label == a.value), None) if q else None
        if not opt:
            continue
        for fid in opt.supports:
            if fid in scores:
                scores[fid] *= SUPPORT_BOOST
                reasons[fid].append(f"you said: {opt.label}")
        for fid in opt.rules_out:
            if fid in scores:
                scores[fid] *= RULE_OUT_FACTOR

    total = sum(scores.values()) or 1.0
    hyps = [
        Hypothesis(fault_id=fid, likelihood=round(s / total, 3), reason="; ".join(reasons[fid]))
        for fid, s in scores.items()
    ]
    return sorted(hyps, key=lambda h: -h.likelihood)


def needs_more_info(hyps: list[Hypothesis], threshold: float) -> bool:
    """Abstain from concluding while the leading hypothesis is not confident enough."""
    return not hyps or hyps[0].likelihood < threshold


def select_questions(
    hyps: list[Hypothesis], answers: list[Answer], kb: ObjectKnowledge, limit: int = 2
) -> list[Question]:
    asked = {a.question_id for a in answers}
    top = {h.fault_id for h in hyps[:3]}
    candidates = [q for q in kb.questions if q.id not in asked and top & set(q.distinguishes)]
    candidates.sort(key=lambda q: -len(top & set(q.distinguishes)))
    return [
        Question(id=q.id, text=q.text, options=[o.label for o in q.options])
        for q in candidates[:limit]
    ]
    
def is_inconclusive(hyps: list[Hypothesis], margin: float = 0.1) -> bool:
    """Top two hypotheses too close to call after questions are exhausted."""
    return len(hyps) > 1 and hyps[0].likelihood - hyps[1].likelihood < margin