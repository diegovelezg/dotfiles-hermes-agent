"""Helpers for loading Hermes .env files consistently across entrypoints."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def _load_dotenv_with_fallback(path: Path, *, override: bool) -> None:
    try:
        load_dotenv(dotenv_path=path, override=override, encoding="utf-8")
    except UnicodeDecodeError:
        load_dotenv(dotenv_path=path, override=override, encoding="latin-1")


def load_hermes_dotenv(
    *,
    hermes_home: str | os.PathLike | None = None,
    project_env: str | os.PathLike | None = None,
) -> Dict[str, str]:
    """Load Hermes environment files with user config taking precedence.

    Behavior:
    - `~/.hermes/.env` overrides stale shell-exported values when present.
    - project `.env` acts as a dev fallback and only fills missing values when
      the user env exists.
    - if no user env exists, the project `.env` also overrides stale shell vars.

    Returns:
        Dict of all variables loaded from .env files (also exported to os.environ).
    """
    loaded: list[Path] = []
    all_vars: Dict[str, str] = {}

    home_path = Path(hermes_home or os.getenv("HERMES_HOME", Path.home() / ".hermes"))
    user_env = home_path / ".env"
    project_env_path = Path(project_env) if project_env else None

    # Capture vars added by load_dotenv (before vs after diff)
    keys_before = set(os.environ.keys())

    if user_env.exists():
        _load_dotenv_with_fallback(user_env, override=True)
        loaded.append(user_env)

    if project_env_path and project_env_path.exists():
        _load_dotenv_with_fallback(project_env_path, override=not loaded)
        loaded.append(project_env_path)

    new_keys = set(os.environ.keys()) - keys_before

    # Export everything to os.environ so subprocesses and subagents inherit it
    for key in new_keys:
        all_vars[key] = os.environ[key]

    return all_vars
