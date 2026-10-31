from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.api.schemas import AnswersIn, DiagnosisOut, to_response
from app.domain.entities import Answer
from app.domain.errors import DiagnosisNotFound

router = APIRouter()
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


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
def create_diagnosis(request: Request, image: UploadFile = File(...)):
    data = image.file.read(MAX_UPLOAD_BYTES + 1)
    if not data:
        raise HTTPException(400, "Empty upload.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Image is larger than 10 MB.")
    c = _c(request)
    diagnosis = c.start_diagnosis.execute(data, image.content_type or "image/jpeg")
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