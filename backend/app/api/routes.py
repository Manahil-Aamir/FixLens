from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.api.schemas import AnswersIn, DiagnosisOut, to_response
from app.domain.entities import Answer
from app.domain.errors import DiagnosisNotFound

router = APIRouter()
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_VIDEO_BYTES = 120 * 1024 * 1024
MAX_NOTE_CHARS = 500


def _c(request: Request):
    return request.app.state.container


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/objects")
def list_objects(request: Request):
    kb = _c(request).kb
    return [{"id": oid, "name": kb.get(oid).name} for oid in kb.list_object_ids()]


@router.post("/diagnoses", response_model=DiagnosisOut)
def create_diagnosis(
    request: Request,
    image: UploadFile | None = File(None),
    video: UploadFile | None = File(None),
    note: str | None = Form(None),
):
    if image is None and video is None:
        raise HTTPException(422, "Send an 'image' or a 'video' file.")
    note = (note or "").strip() or None
    if note and len(note) > MAX_NOTE_CHARS:
        raise HTTPException(422, f"The description is too long (max {MAX_NOTE_CHARS} characters).")

    is_video = image is None
    upload = video if is_video else image
    limit = MAX_VIDEO_BYTES if is_video else MAX_IMAGE_BYTES

    data = upload.file.read(limit + 1)
    if not data:
        raise HTTPException(400, "Empty upload.")
    if len(data) > limit:
        raise HTTPException(413, f"File is larger than {limit // (1024 * 1024)} MB.")

    mime = "video/mp4" if is_video else (upload.content_type or "image/jpeg")
    c = _c(request)
    diagnosis = c.start_diagnosis.execute(data, mime, note)
    return to_response(diagnosis, c.kb)


@router.post("/diagnoses/{diagnosis_id}/answers", response_model=DiagnosisOut)
def answer(diagnosis_id: str, body: AnswersIn, request: Request):
    c = _c(request)
    answers = [Answer(question_id=a.question_id, value=a.value) for a in body.answers]
    return to_response(c.answer_questions.execute(diagnosis_id, answers), c.kb)


@router.get("/diagnoses/{diagnosis_id}", response_model=DiagnosisOut)
def get_diagnosis(diagnosis_id: str, request: Request):
    c = _c(request)
    diagnosis = c.repo.get(diagnosis_id)
    if diagnosis is None:
        raise DiagnosisNotFound("Diagnosis not found.")
    return to_response(diagnosis, c.kb)