from __future__ import annotations

import os
from pathlib import Path

CONFIG_DIR_ENV = "STOCKS_CONFIG_DIR"
CONFIG_FILE_ENV = "STOCKS_ANALYTICS_CONFIG"


def get_project_root() -> Path:
    """Return project root assuming this file lives in core/config."""
    return Path(__file__).resolve().parents[2]


def get_config_dir() -> Path:
    """Resolve configuration directory respecting environment overrides."""
    env_dir = os.getenv(CONFIG_DIR_ENV)
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return get_project_root() / "config"


def get_analytics_config_path() -> Path:
    """Resolve analytics configuration file location."""
    env_path = os.getenv(CONFIG_FILE_ENV)
    if env_path:
        return Path(env_path).expanduser().resolve()
    return get_config_dir() / "analytics.yml"

