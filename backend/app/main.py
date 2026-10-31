import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import get_settings
from app.container import Container, build_container
from app.domain.errors import (
    DiagnosisClosed, DiagnosisNotFound, InvalidAnswer, InvalidImage, LLMError,
)

log = logging.getLogger("fixlens")

# exception class -> (HTTP status, fixed message or None to pass the original through)
_ERRORS = {
    DiagnosisNotFound: (404, None),
    DiagnosisClosed: (409, None),
    InvalidAnswer: (422, None),
    InvalidImage: (400, None),
    LLMError: (502, "The AI service is unavailable right now. Please try again."),
}


def _handler(status: int, message: str | None):
    async def handle(request: Request, exc: Exception):
        if status >= 500:
            log.exception("upstream failure: %s", exc)
        return JSONResponse(status_code=status, content={"detail": message or str(exc)})
    return handle


def create_app(container: Container | None = None) -> FastAPI:
    app = FastAPI(title="FixLens API")
    app.state.container = container or build_container(get_settings())
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )
    for exc_class, (status, message) in _ERRORS.items():
        app.add_exception_handler(exc_class, _handler(status, message))
    app.include_router(router)
    return app