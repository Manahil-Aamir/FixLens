from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent  # the backend folder


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    baseten_api_key: str
    baseten_base_url: str
    baseten_model: str
    max_tokens: int = 3000
    max_image_px: int = 1024
    kb_dir: str = str(BASE_DIR / "kb")
    db_path: str = str(BASE_DIR / "fixlens.db")
    ask_threshold: float = 0.6   
    max_questions: int = 2


def get_settings() -> Settings:
    return Settings()