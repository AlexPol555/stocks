from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from core.settings import get_settings


class BatchMode(str, Enum):
    ONLY_UNPROCESSED = "only_unprocessed"
    RECHECK_ALL = "recheck_all"
    RECHECK_SELECTED_RANGE = "recheck_selected_range"


@dataclass(frozen=True)
class PipelineConfig:
    batch_size: int = 100
    chunk_size: int = 100
    auto_apply_threshold: float = 0.85
    review_lower_threshold: float = 0.60
    fuzzy_threshold: int = 65
    cos_candidate_threshold: float = 0.60
    cos_auto_threshold: float = 0.80
    max_retries: int = 2
    retry_backoff_seconds: float = 2.0
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    use_faiss: bool = False
    dry_run: bool = False
    version: str = "v1"
    progress_refresh_interval: float = 0.5
    auto_apply_confirm: bool = True
    history_keep_max: int = 10
    cache_embeddings: bool = True
    allow_confirmed_overwrite: bool = False

    extra: Dict[str, Any] = field(default_factory=dict)

    def with_overrides(self, **kwargs: Any) -> "PipelineConfig":
        data = self.as_dict()
        data.update(kwargs)
        return PipelineConfig(**data)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "batch_size": self.batch_size,
            "chunk_size": self.chunk_size,
            "auto_apply_threshold": self.auto_apply_threshold,
            "review_lower_threshold": self.review_lower_threshold,
            "fuzzy_threshold": self.fuzzy_threshold,
            "cos_candidate_threshold": self.cos_candidate_threshold,
            "cos_auto_threshold": self.cos_auto_threshold,
            "max_retries": self.max_retries,
            "retry_backoff_seconds": self.retry_backoff_seconds,
            "embedding_model": self.embedding_model,
            "use_faiss": self.use_faiss,
            "dry_run": self.dry_run,
            "version": self.version,
            "progress_refresh_interval": self.progress_refresh_interval,
            "auto_apply_confirm": self.auto_apply_confirm,
            "history_keep_max": self.history_keep_max,
            "cache_embeddings": self.cache_embeddings,
            "allow_confirmed_overwrite": self.allow_confirmed_overwrite,
            "extra": dict(self.extra),
        }


def _default_config_path() -> Path:
    settings = get_settings()
    default = settings.config_dir / "news_pipeline.yml"
    return default


def load_pipeline_config(
    path: Optional[str | Path] = None,
    *,
    overrides: Optional[Dict[str, Any]] = None,
) -> PipelineConfig:
    config_path: Optional[Path] = None
    if path:
        config_path = Path(path).expanduser().resolve()
    else:
        env_value = os.getenv("NEWS_PIPELINE_CONFIG")
        if env_value:
            config_path = Path(env_value).expanduser().resolve()
        else:
            candidate = _default_config_path()
            if candidate.exists():
                config_path = candidate

    data: Dict[str, Any] = {}
    if config_path and config_path.exists():
        with config_path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
            if not isinstance(loaded, dict):
                raise ValueError("news pipeline config must be a mapping")
            data.update(loaded)

    if overrides:
        data.update(overrides)

    def _pop_bool(key: str, default: bool) -> bool:
        value = data.pop(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        if isinstance(value, (int, float)):
            return bool(value)
        return default

    return PipelineConfig(
        batch_size=int(data.pop("batch_size", PipelineConfig.batch_size)),
        chunk_size=int(data.pop("chunk_size", PipelineConfig.chunk_size)),
        auto_apply_threshold=float(data.pop("auto_apply_threshold", PipelineConfig.auto_apply_threshold)),
        review_lower_threshold=float(data.pop("review_lower_threshold", PipelineConfig.review_lower_threshold)),
        fuzzy_threshold=int(data.pop("fuzzy_threshold", PipelineConfig.fuzzy_threshold)),
        cos_candidate_threshold=float(data.pop("cos_candidate_threshold", PipelineConfig.cos_candidate_threshold)),
        cos_auto_threshold=float(data.pop("cos_auto_threshold", PipelineConfig.cos_auto_threshold)),
        max_retries=int(data.pop("max_retries", PipelineConfig.max_retries)),
        retry_backoff_seconds=float(data.pop("retry_backoff_seconds", PipelineConfig.retry_backoff_seconds)),
        embedding_model=str(data.pop("embedding_model", PipelineConfig.embedding_model)),
        use_faiss=_pop_bool("use_faiss", PipelineConfig.use_faiss),
        dry_run=_pop_bool("dry_run", PipelineConfig.dry_run),
        version=str(data.pop("version", PipelineConfig.version)),
        progress_refresh_interval=float(data.pop("progress_refresh_interval", PipelineConfig.progress_refresh_interval)),
        auto_apply_confirm=_pop_bool("auto_apply_confirm", PipelineConfig.auto_apply_confirm),
        history_keep_max=int(data.pop("history_keep_max", PipelineConfig.history_keep_max)),
        cache_embeddings=_pop_bool("cache_embeddings", PipelineConfig.cache_embeddings),
        allow_confirmed_overwrite=_pop_bool("allow_confirmed_overwrite", PipelineConfig.allow_confirmed_overwrite),
        extra=data,
    )


__all__ = ["BatchMode", "PipelineConfig", "load_pipeline_config"]
