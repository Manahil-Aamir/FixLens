#!/usr/bin/env python
"""Black-box check of a running FixLens API.

Usage (start the server first):
    python api_check.py                          protocol and validation checks only
    python api_check.py D:\\FixLens\\kettle.jpg    plus full diagnosis flows on that photo
    python api_check.py D:\\FixLens\\photos        every photo in a folder
Options:
    --base http://localhost:8000    --timeout 120    --strategies first,last
"""
import argparse
import io
import json
import mimetypes
import re
import sys
import time
from pathlib import Path

import httpx

STATUSES = {"needs_answers", "complete", "unsupported"}
RISKS = {"low", "medium", "high", "stop"}
LABELS = {"most_likely", "possible"}
EXPECTED_OBJECTS = {
    "blender", "coffee_maker", "electric_kettle", "hair_dryer", "iron",
    "microwave", "stand_mixer", "toaster", "vacuum_cleaner", "washing_machine",
}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_UPLOAD = 10 * 1024 * 1024
MAX_ROUNDS = 8
FORBIDDEN = re.compile(
    r"\bunscrew\w*|\bopen\w* (up )?the (casing|housing|body)|\bback panel"
    r"|\bbypass\w*|\bwhile (it is |it's )?plugged in",
    re.IGNORECASE,
)
PROHIBITION = re.compile(r"\b(without|do not|don't|never|avoid|not)\b[^.;]{0,40}$", re.IGNORECASE)


def forbidden_instruction(text: str) -> bool:
    """True for 'unscrew the cover', False for 'without unscrewing anything'."""
    for m in FORBIDDEN.finditer(text):
        if not PROHIBITION.search(text[max(0, m.start() - 60):m.start()]):
            return True
    return False


def has_key(obj, key: str) -> bool:
    if isinstance(obj, dict):
        return key in obj or any(has_key(v, key) for v in obj.values())
    if isinstance(obj, list):
        return any(has_key(v, key) for v in obj)
    return False

HAZARD_TERMS = [
    "burn mark", "scorch", "melted", "burning smell", "sparks", "smoke",
    "exposed wire", "bare wire", "frayed",
]


class Report:
    def __init__(self):
        self.passed = 0
        self.failures: list[str] = []
        self.warnings: list[str] = []

    def section(self, title: str) -> None:
        print(f"\n== {title} ==")

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        if ok:
            self.passed += 1
            print(f"  PASS  {name}")
        else:
            self.failures.append(name)
            print(f"  FAIL  {name}" + (f"\n          -> {detail}" if detail else ""))
        return ok

    def warn(self, name: str, detail: str = "") -> None:
        self.warnings.append(name)
        print(f"  WARN  {name}" + (f"\n          -> {detail}" if detail else ""))

    def note(self, text: str) -> None:
        print(f"  info  {text}")


class Api:
    def __init__(self, base: str, timeout: float):
        self.base = base.rstrip("/")
        self.http = httpx.Client(timeout=timeout)
        self.timings: dict[str, list[float]] = {"create": [], "answer": []}

    def request(self, method: str, path: str, **kw) -> httpx.Response:
        return self.http.request(method, self.base + path, **kw)

    def create(self, name: str, data: bytes, mime: str) -> httpx.Response:
        t = time.perf_counter()
        r = self.request("POST", "/diagnoses", files={"image": (name, data, mime)})
        self.timings["create"].append(time.perf_counter() - t)
        return r

    def answer(self, diagnosis_id: str, answers: list[dict]) -> httpx.Response:
        t = time.perf_counter()
        r = self.request("POST", f"/diagnoses/{diagnosis_id}/answers", json={"answers": answers})
        self.timings["answer"].append(time.perf_counter() - t)
        return r


def safe_json(r: httpx.Response):
    try:
        return r.json()
    except ValueError:
        return None


# ---------------------------------------------------------------- response validation

def body_problems(body: dict) -> list[str]:
    """Everything a mobile client relies on, checked on every diagnosis response."""
    need = {"id", "status", "appliance", "observation", "questions", "hypotheses", "plan", "notice"}
    missing = need - set(body)
    if missing:
        return [f"missing keys {sorted(missing)}"]

    p: list[str] = []
    if "likelihood" in json.dumps(body):
        p.append("raw likelihood numbers leaked into the response")
    status = body["status"]
    if status not in STATUSES:
        return p + [f"unknown status {status!r}"]

    for k in ("object_id", "components", "visible_issues"):
        if k not in body["observation"]:
            p.append(f"observation missing {k}")

    if status == "needs_answers":
        if not body["questions"]:
            p.append("needs_answers but no questions")
        for q in body["questions"]:
            if not {"id", "text", "options"} <= set(q) or len(q.get("options", [])) < 2:
                p.append(f"malformed question {q.get('id')}")
        if body["plan"] is not None:
            p.append("plan present while questions are still open")
        if body["hypotheses"]:
            p.append("hypotheses exposed before the diagnosis is complete")
    else:
        if body["questions"]:
            p.append("questions present on a closed diagnosis")

    if status == "unsupported":
        if body["plan"] is not None:
            p.append("unsupported diagnosis has a plan")
        if not body["notice"]:
            p.append("unsupported diagnosis has no notice")

    if status == "complete":
        plan = body["plan"]
        if not plan or not plan.get("steps"):
            p.append("complete but no plan steps")
        else:
            steps = plan["steps"]
            orders = [s["order"] for s in steps]
            if orders != list(range(1, len(orders) + 1)):
                p.append(f"step orders are {orders}")
            for s in steps:
                if s["risk"] not in RISKS:
                    p.append(f"bad risk {s['risk']!r}")
                if not s["instruction"].strip():
                    p.append("empty step instruction")
                if forbidden_instruction(s["instruction"]):
                    p.append(f"forbidden DIY instruction: {s['instruction'][:80]!r}")
            if any(s["risk"] == "stop" for s in steps) and not plan["escalate"]:
                p.append("stop step without escalate=true")
        hyps = body["hypotheses"]
        if len(hyps) > 3:
            p.append("more than 3 hypotheses")
        for h in hyps:
            if h.get("label") not in LABELS or not h.get("name"):
                p.append(f"bad hypothesis {h}")
        if any(h.get("label") == "most_likely" for h in hyps[1:]):
            p.append("most_likely is not the first hypothesis")
    return p


# ---------------------------------------------------------------- static checks

def static_checks(api: Api, rep: Report) -> None:
    rep.section("Basics")
    r = api.request("GET", "/health")
    rep.check("GET /health -> 200 {'status': 'ok'}",
              r.status_code == 200 and safe_json(r) == {"status": "ok"}, f"{r.status_code} {r.text[:100]}")

    r = api.request("GET", "/objects")
    objs = safe_json(r)
    ok = r.status_code == 200 and isinstance(objs, list) and objs and all(
        isinstance(o, dict) and o.get("id") and o.get("name") for o in objs)
    rep.check("GET /objects -> non-empty list of {id, name}", bool(ok), f"{r.status_code} {r.text[:150]}")
    if ok:
        ids = {o["id"] for o in objs}
        rep.note(f"{len(ids)} appliances: {', '.join(sorted(ids))}")
        if EXPECTED_OBJECTS - ids:
            rep.warn("some expected appliances are not loaded", str(sorted(EXPECTED_OBJECTS - ids)))

    r = api.request("GET", "/openapi.json")
    paths = (safe_json(r) or {}).get("paths", {})
    rep.check("GET /openapi.json lists the diagnosis routes",
              "/diagnoses" in paths and "/diagnoses/{diagnosis_id}/answers" in paths, f"{r.status_code}")
    rep.check("GET /docs -> 200", api.request("GET", "/docs").status_code == 200)

    r = api.request("OPTIONS", "/diagnoses", headers={
        "Origin": "http://example.com", "Access-Control-Request-Method": "POST"})
    rep.check("CORS preflight is allowed",
              r.status_code in (200, 204) and "access-control-allow-origin" in r.headers, f"{r.status_code}")

    rep.section("Input validation (no model calls)")
    r = api.request("GET", "/diagnoses/does-not-exist")
    rep.check("GET unknown diagnosis -> 404 with detail",
              r.status_code == 404 and "detail" in (safe_json(r) or {}), f"{r.status_code} {r.text[:100]}")

    r = api.answer("does-not-exist", [{"question_id": "a", "value": "b"}])
    rep.check("POST answers to unknown diagnosis -> 404", r.status_code == 404, f"{r.status_code}")

    r = api.request("POST", "/diagnoses/does-not-exist/answers", json={"answers": []})
    rep.check("POST empty answers list -> 422", r.status_code == 422, f"{r.status_code}")

    r = api.request("POST", "/diagnoses")
    rep.check("POST /diagnoses without a file -> 422", r.status_code == 422, f"{r.status_code}")

    r = api.create("empty.jpg", b"", "image/jpeg")
    rep.check("POST /diagnoses with an empty file is rejected (400/422)",
              r.status_code in (400, 422), f"{r.status_code} {r.text[:100]}")

    r = api.create("fake.jpg", b"this is definitely not an image", "image/jpeg")
    rep.check("POST /diagnoses with non-image bytes -> 400",
              r.status_code == 400, f"{r.status_code} {r.text[:150]}")

    r = api.request("PUT", "/diagnoses")
    rep.check("PUT /diagnoses -> 405", r.status_code == 405, f"{r.status_code}")


def oversize_check(api: Api, rep: Report) -> None:
    r = api.create("big.jpg", b"\0" * (MAX_UPLOAD + 1), "image/jpeg")
    rep.check("POST /diagnoses over 10 MB -> 413", r.status_code == 413, f"{r.status_code} {r.text[:100]}")


def blank_image_check(api: Api, rep: Report) -> None:
    try:
        from PIL import Image
    except ImportError:
        rep.note("Pillow not installed, skipping the synthetic image check")
        return
    buf = io.BytesIO()
    Image.new("RGB", (256, 256), (30, 120, 200)).save(buf, "JPEG")
    r = api.create("blue.jpg", buf.getvalue(), "image/jpeg")
    if rep.check("POST /diagnoses with a plain blue image -> 200", r.status_code == 200,
                 f"{r.status_code} {r.text[:200]}"):
        body = r.json()
        probs = body_problems(body)
        rep.check("blue image: response schema valid", not probs, "; ".join(probs))
        rep.note(f"blue image was classified as status={body['status']} appliance={body['appliance']}")
        if body["status"] != "unsupported":
            rep.warn("a plain blue image was not rejected as unsupported",
                     "the model matched it to an appliance; consider a stricter confidence cutoff")


# ---------------------------------------------------------------- real photo flows

class Ctx:
    errors_probed = False
    closed_probed = False


def pick(options: list[str], strategy: str) -> str:
    return options[0] if strategy == "first" else options[-1]


def probe_error_handling(api: Api, rep: Report, body: dict, label: str) -> None:
    did, qs = body["id"], body["questions"]
    q0 = qs[0]
    good = {"question_id": q0["id"], "value": q0["options"][0]}
    cases = [
        ("unknown question id", [{"question_id": "no_such_question", "value": "x"}]),
        ("option text that was not offered", [{"question_id": q0["id"], "value": "not an option"}]),
        ("same question answered twice", [good, good]),
    ]
    if len(qs) > 1:
        cases.append(("only some of the open questions answered", [good]))
    for name, answers in cases:
        r = api.answer(did, answers)
        rep.check(f"[{label}] invalid answers ({name}) -> 422", r.status_code == 422,
                  f"{r.status_code} {r.text[:150]}")
    g = api.request("GET", f"/diagnoses/{did}")
    rep.check(f"[{label}] rejected answers left the diagnosis unchanged", safe_json(g) == body)


def run_flow(api: Api, rep: Report, ctx: Ctx, photo: Path, strategy: str) -> None:
    label = f"{photo.name} | {strategy}"
    mime = mimetypes.guess_type(photo.name)[0] or "image/jpeg"
    problems: list[str] = []
    seen = 0
    chosen: list[str] = []

    def see(b: dict, where: str) -> None:
        nonlocal seen
        seen += 1
        problems.extend(f"{where}: {x}" for x in body_problems(b))

    try:
        t0 = time.perf_counter()
        r = api.create(photo.name, photo.read_bytes(), mime)
        if not rep.check(f"[{label}] POST /diagnoses -> 200", r.status_code == 200,
                         f"{r.status_code} {r.text[:200]}"):
            return
        body = r.json()
        see(body, "start")
        rep.note(f"[{label}] status={body['status']} appliance={body['appliance']} "
                 f"issues={body['observation']['visible_issues']} ({time.perf_counter() - t0:.1f}s)")

        if body["status"] == "needs_answers" and not ctx.errors_probed:
            ctx.errors_probed = True
            probe_error_handling(api, rep, body, label)

        rounds = 0
        while body["status"] == "needs_answers" and rounds < MAX_ROUNDS:
            answers = [{"question_id": q["id"], "value": pick(q["options"], strategy)}
                       for q in body["questions"]]
            chosen += [a["value"] for a in answers]
            r = api.answer(body["id"], answers)
            if not rep.check(f"[{label}] POST answers round {rounds + 1} -> 200",
                             r.status_code == 200, f"{r.status_code} {r.text[:200]}"):
                return
            body = r.json()
            see(body, f"round {rounds + 1}")
            rounds += 1

        rep.check(f"[{label}] flow finishes within {MAX_ROUNDS} rounds", body["status"] != "needs_answers")
        rep.note(f"[{label}] finished as {body['status']} after {rounds} answer round(s)")

        g = api.request("GET", f"/diagnoses/{body['id']}")
        rep.check(f"[{label}] GET returns exactly the stored result",
                  g.status_code == 200 and safe_json(g) == body, f"{g.status_code}")

        if body["status"] == "complete":
            text = " ".join(body["observation"]["visible_issues"] + [c for c in chosen if not c.lower().startswith("no")]).lower()
            hazards = [t for t in HAZARD_TERMS if t in text]
            if any(c.lower().startswith("no, none") for c in chosen):  # user denied heat damage
                hazards = [t for t in hazards if t not in ("burn mark", "scorch", "melted")]
            has_stop = any(s["risk"] == "stop" for s in body["plan"]["steps"])
            if hazards and not has_stop:
                rep.warn(f"[{label}] hazard words {hazards} seen but the plan has no STOP step",
                         "check safety_policy triggers, or the wording may be negated")
            if has_stop:
                rep.note(f"[{label}] safety layer produced a STOP plan (hazards: {hazards or 'rule from answers'})")

        if not ctx.closed_probed and body["status"] != "needs_answers":
            ctx.closed_probed = True
            r = api.answer(body["id"], [{"question_id": "q", "value": "v"}])
            rep.check(f"[{label}] answering a finished diagnosis -> 409", r.status_code == 409,
                      f"{r.status_code} {r.text[:100]}")
    finally:
        if seen:
            rep.check(f"[{label}] {seen} response(s) match schema and safety invariants",
                      not problems, "; ".join(problems[:5]))


# ---------------------------------------------------------------- main

def collect_photos(paths: list[str]) -> list[Path]:
    photos: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            photos += sorted(f for f in p.iterdir() if f.suffix.lower() in IMAGE_EXTS)
        elif p.is_file():
            photos.append(p)
        else:
            print(f"warning: {raw} not found, skipped")
    return photos


def main() -> int:
    ap = argparse.ArgumentParser(description="Check a running FixLens API.")
    ap.add_argument("photos", nargs="*", help="photo files or folders for full flows")
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--strategies", default="first,last",
                    help="how to answer questions: first, last, or both (comma separated)")
    args = ap.parse_args()

    api = Api(args.base.replace("0.0.0.0", "localhost"), args.timeout)
    rep = Report()
    try:
        api.request("GET", "/health")
    except httpx.TransportError as e:
        print(f"Cannot reach {api.base}: {e}\nStart the server first:\n"
              "  uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000")
        return 2

    static_checks(api, rep)
    rep.section("Upload size limit")
    oversize_check(api, rep)
    rep.section("Image that is not an appliance")
    blank_image_check(api, rep)

    photos = collect_photos(args.photos)
    if photos:
        strategies = [s.strip() for s in args.strategies.split(",") if s.strip() in ("first", "last")]
        ctx = Ctx()
        for photo in photos:
            for strategy in strategies:
                rep.section(f"Full flow: {photo.name} (answers: {strategy} option)")
                run_flow(api, rep, ctx, photo, strategy)
        if not ctx.errors_probed:
            rep.warn("error handling on open questions was never tested",
                     "no photo produced follow-up questions; add a clean kettle photo")
        if not ctx.closed_probed:
            rep.warn("the 409 check on a finished diagnosis was never run")
    else:
        print("\n(no photos given: pass a photo or folder to test the full diagnosis flow)")

    rep.section("Latency")
    for name, vals in api.timings.items():
        if vals:
            print(f"  {name:7s} calls={len(vals):3d} avg={sum(vals) / len(vals):5.1f}s max={max(vals):5.1f}s")
            if max(vals) > 60:
                rep.warn(f"slow {name} call", f"max {max(vals):.0f}s")

    print("\n" + "=" * 60)
    print(f"passed {rep.passed}   failed {len(rep.failures)}   warnings {len(rep.warnings)}")
    for f in rep.failures:
        print(f"  FAILED: {f}")
    return 1 if rep.failures else 0


if __name__ == "__main__":
    sys.exit(main())