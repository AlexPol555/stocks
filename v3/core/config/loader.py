from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

try:  # pragma: no cover - optional dependency
    import yaml
except ImportError as exc:  # pragma: no cover - runtime warning
    yaml = None  # type: ignore
    YAML_IMPORT_ERROR = exc
else:
    YAML_IMPORT_ERROR = None


class ConfigLoadError(RuntimeError):
    """Raised when configuration cannot be loaded."""


def load_yaml_config(path: Path) -> Dict[str, Any]:
    """Load YAML configuration from the given path."""
    if yaml is None:
        raise ConfigLoadError(
            "PyYAML is required to load analytics configuration. Install it via 'pip install pyyaml'."
        ) from YAML_IMPORT_ERROR

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except FileNotFoundError as exc:
        raise ConfigLoadError(f"Configuration file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigLoadError(f"Invalid YAML in configuration file: {path}") from exc
    if not isinstance(data, dict):
        raise ConfigLoadError(f"Configuration root must be a mapping, got {type(data)!r}")
    return data
