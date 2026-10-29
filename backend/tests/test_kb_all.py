from app.infrastructure.yaml_kb import YamlKnowledgeBase

EXPECTED = {
    "blender", "coffee_maker", "electric_kettle", "hair_dryer", "iron",
    "microwave", "stand_mixer", "toaster", "vacuum_cleaner", "washing_machine",
}


def test_all_objects_load_and_are_usable():
    kb = YamlKnowledgeBase("kb")
    assert EXPECTED <= set(kb.list_object_ids())
    problems = []
    for oid in sorted(kb.list_object_ids()):
        obj = kb.get(oid)
        if len(obj.faults) < 3:
            problems.append(f"{oid}: only {len(obj.faults)} faults")
        if len(obj.questions) < 2:
            problems.append(f"{oid}: only {len(obj.questions)} questions")
        if not obj.safety_rules:
            problems.append(f"{oid}: no safety rules")
        covered = {fid for q in obj.questions for fid in q.distinguishes}
        uncovered = {f.id for f in obj.faults} - covered
        if uncovered:
            problems.append(f"{oid}: no question distinguishes {sorted(uncovered)}")
    assert not problems, "\n" + "\n".join(problems)