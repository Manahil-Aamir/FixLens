from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    baseten_api_key: str
    baseten_base_url: str = "https://inference.baseten.co/v1"
    baseten_model: str = "meta-models/muse-spark-open-1026"
    max_tokens: int = 3000
    max_image_px: int = 1024
    kb_dir: str = "kb"
    ask_threshold: float = 0.6   # ask follow-ups only while the top hypothesis is below this
    max_questions: int = 2


def get_settings() -> Settings:
    return Settings()