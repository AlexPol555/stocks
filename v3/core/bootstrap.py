from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

try:  # pragma: no cover - optional dependency
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def setup_environment() -> Path:
    """Ensure project paths and environment variables are initialised."""
    _extend_sys_path()
    _load_env_file()
    return PROJECT_ROOT


def _extend_sys_path() -> None:
    candidates = [PROJECT_ROOT, PROJECT_ROOT / "core", PROJECT_ROOT / "services"]
    for path in candidates:
        resolved = str(path)
        if resolved not in sys.path and path.exists():
            sys.path.insert(0, resolved)


def _load_env_file() -> None:
    if load_dotenv is None:
        fallback = PROJECT_ROOT / ".env"
        if fallback.exists():
            # Minimal loader to keep parity when python-dotenv is absent
            for line in fallback.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())
        return
    load_dotenv(PROJECT_ROOT / ".env", override=False)


__all__ = ["setup_environment", "PROJECT_ROOT"]
