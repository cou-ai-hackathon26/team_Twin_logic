from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from .assessment.types import Thresholds

BACKEND_DIR = Path(__file__).resolve().parent.parent
# published evaluation results (tracked in git, so the hosted demo shows them)
RESULTS_DIR = BACKEND_DIR / "results"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), env_prefix="PB_", extra="ignore")

    data_dir: Path = BACKEND_DIR / "data"
    database_url: str = ""  # empty -> SQLite file in data_dir
    ctc_model_id: str = "arijitx/wav2vec2-xls-r-300m-bengali"
    ctc_backend: str = "auto"  # auto | torch | onnx | onnx-int8
    whisper_size: str = "small"
    enable_whisper: bool = True
    torch_threads: int = 0  # 0 -> library default (all cores)
    preload_models: bool = False
    thresholds_file: str = "thresholds.json"
    weak_min_errors: int = 3
    weak_min_readings: int = 2
    count_unsure_as_correct: bool = True
    seed_demo: bool = True  # first start: demo teacher, one class per grade, student logins
    session_days: int = 14
    # privacy (safe by default): recordings not marked "keep" are deleted this many days after
    # upload, reviewed or not (failed ones too, after the teacher had time to retry). 0 = never.
    audio_retention_days: int = 14
    # recordings the teacher chose to keep are still deleted after this many days. 0 = never.
    kept_audio_days: int = 90
    # abuse limits per login: reading uploads and single-word checks per 10 minutes
    max_uploads_per_10min: int = 30
    max_word_checks_per_10min: int = 60
    # security: lock a login for lockout_minutes after this many wrong passwords in a row
    max_failed_logins: int = 5
    lockout_minutes: int = 10
    # "lax" for local use; "none" when the app runs inside an iframe (Hugging Face Spaces)
    cookie_samesite: str = "lax"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def db_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{(self.data_dir / 'porabondhu.db').as_posix()}"

    @property
    def onnx_dir(self) -> Path:
        return self.data_dir / "onnx"

    def resolved_ctc_backend(self) -> str:
        if self.ctc_backend != "auto":
            return self.ctc_backend
        if (self.onnx_dir / "model.int8.onnx").exists():
            return "onnx-int8"
        if (self.onnx_dir / "model.onnx").exists():
            return "onnx"
        return "torch"

    @property
    def audio_dir(self) -> Path:
        return self.data_dir / "audio"

    @property
    def reports_dir(self) -> Path:
        return self.data_dir / "reports"

    @property
    def thresholds_path(self) -> Path:
        return self.data_dir / self.thresholds_file

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.audio_dir, self.reports_dir):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s


def load_thresholds(settings: Settings | None = None) -> Thresholds:
    s = settings or get_settings()
    # local calibration first, then the published one committed in results/
    for p in (s.thresholds_path, RESULTS_DIR / "thresholds.json"):
        if p.exists():
            try:
                return Thresholds.from_dict(json.loads(p.read_text(encoding="utf-8")))
            except (ValueError, TypeError):
                pass
    return Thresholds()


def save_thresholds(th: Thresholds, meta: dict | None = None, settings: Settings | None = None) -> Path:
    s = settings or get_settings()
    data = th.to_dict()
    if meta:
        data["_meta"] = meta
    s.thresholds_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return s.thresholds_path
