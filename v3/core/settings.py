from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os

from .bootstrap import PROJECT_ROOT
from .config.paths import get_analytics_config_path, get_config_dir


@dataclass(frozen=True)
class AppSettings:
    project_root: Path
    database_path: Path
    config_dir: Path
    analytics_config_path: Path
    environment: str


def _resolve_database_path() -> Path:
    db_path_env = os.getenv("STOCKS_DB_PATH")
    if db_path_env:
        return Path(db_path_env).expanduser().resolve()
    filename = os.getenv("STOCKS_DB_FILENAME", "stock_data.db")
    return (PROJECT_ROOT / filename).resolve()


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    project_root = PROJECT_ROOT
    database_path = _resolve_database_path()
    config_dir = get_config_dir()
    analytics_config_path = get_analytics_config_path()
    environment = os.getenv("STOCKS_ENV", os.getenv("ENV", "development"))
    return AppSettings(
        project_root=project_root,
        database_path=database_path,
        config_dir=config_dir,
        analytics_config_path=analytics_config_path,
        environment=environment,
    )


__all__ = ["AppSettings", "get_settings"]
