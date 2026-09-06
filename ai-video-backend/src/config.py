from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    planner_timeout_seconds: float = 300
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "SAz9YHcvj6GT2YYXdXww"
    elevenlabs_model: str = "eleven_turbo_v2_5"
    piper_model: str = "en_US-lessac-medium"
    piper_data_dir: Path = Path("data/piper")
    database_path: Path = Path("data/jobs.sqlite3")
    artifact_root: Path = Path("artifacts/jobs")
    worker_poll_seconds: float = 2.0
