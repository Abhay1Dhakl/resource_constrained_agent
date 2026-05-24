import os
from pathlib import Path


def project_root() -> Path:
    """Return the repository root directory for the project.

    Returns:
        Path: Absolute path to the repository root.
    """
    return Path(__file__).resolve().parents[2]


def load_env_file(env_path: Path | None = None) -> None:
    """Load environment variables from a local `.env` file if present.

    Args:
        env_path: Optional path to the environment file. When omitted, the
            project-level `.env` file is used.
    """
    path = env_path or project_root() / ".env"

    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value
