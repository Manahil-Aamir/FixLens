import io

from fastapi.testclient import TestClient
from PIL import Image

from app.container import make_container
from app.domain.entities import Observation, Plan, Risk, Step
from app.infrastructure.session_repo import SqliteSessionRepo
from app.infrastructure.yaml_kb import YamlKnowledgeBase
from app.main import create_app

KB = YamlKnowledgeBase("kb")


class FakeLLM:
    def __init__(self, observation: Observation):
        self.observation = observation
        self.plan_calls = 0

    def identify(self, image, mime, known_objects, cue_hints=None):
        return self.observation

    def write_plan(self, observation, hypotheses, answers, kb):
        self.plan_calls += 1
        return Plan(summary="Try these checks.",
                    steps=[Step(order=1, instruction="Unplug the appliance.", risk=Risk.LOW)])


def _client(tmp_path, observation):
    llm = FakeLLM(observation)
    repo = SqliteSessionRepo(str(tmp_path / "test.db"))
    app = create_app(make_container(KB, llm, repo, 0.6, 2))
    return TestClient(app), llm


def _upload(client):
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), "white").save(buf, "JPEG")
    return client.post("/diagnoses", files={"image": ("k.jpg", buf.getvalue(), "image/jpeg")})


KETTLE = Observation(object_id="electric_kettle")


def test_health_and_objects(tmp_path):
    client, _ = _client(tmp_path, KETTLE)
    assert client.get("/health").json() == {"status": "ok"}
    ids = {o["id"] for o in client.get("/objects").json()}
    assert "electric_kettle" in ids


def test_question_flow_ends_with_a_plan(tmp_path):
    client, _ = _client(tmp_path, KETTLE)
    body = _upload(client).json()
    assert body["status"] == "needs_answers"
    assert 1 <= len(body["questions"]) <= 2

    for _ in range(6):
        if body["status"] != "needs_answers":
            break
        answers = [{"question_id": q["id"], "value": q["options"][-1]} for q in body["questions"]]
        resp = client.post(f"/diagnoses/{body['id']}/answers", json={"answers": answers})
        assert resp.status_code == 200
        body = resp.json()

    assert body["status"] == "complete"
    assert body["plan"]["steps"]
    assert client.get(f"/diagnoses/{body['id']}").json()["status"] == "complete"


def test_stop_from_photo_skips_questions_and_model_plan(tmp_path):
    obs = Observation(object_id="electric_kettle", visible_issues=["burn mark"])
    client, llm = _client(tmp_path, obs)
    body = _upload(client).json()
    assert body["status"] == "complete"
    assert body["questions"] == []
    assert body["plan"]["escalate"] is True
    assert all(s["risk"] == "stop" for s in body["plan"]["steps"])
    assert llm.plan_calls == 0


def test_unknown_object_is_unsupported(tmp_path):
    client, _ = _client(tmp_path, Observation(object_id="unknown", confidence=0.2))
    body = _upload(client).json()
    assert body["status"] == "unsupported"
    assert body["plan"] is None and body["notice"]


def test_error_cases(tmp_path):
    client, _ = _client(tmp_path, KETTLE)
    body = _upload(client).json()

    bad = client.post(f"/diagnoses/{body['id']}/answers",
                      json={"answers": [{"question_id": "nope", "value": "x"}]})
    assert bad.status_code == 422
    assert client.get("/diagnoses/missing").status_code == 404
    assert client.post("/diagnoses/missing/answers",
                       json={"answers": [{"question_id": "a", "value": "b"}]}).status_code == 404


def test_answering_a_finished_diagnosis_is_a_conflict(tmp_path):
    obs = Observation(object_id="electric_kettle", visible_issues=["burn mark"])
    client, _ = _client(tmp_path, obs)
    body = _upload(client).json()
    resp = client.post(f"/diagnoses/{body['id']}/answers",
                       json={"answers": [{"question_id": "q_light", "value": "x"}]})
    assert resp.status_code == 409