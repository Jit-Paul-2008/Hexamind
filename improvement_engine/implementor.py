"""Apply suggested improvements to pipeline config."""

from __future__ import annotations

from pathlib import Path


class ConfigImplementor:
    def __init__(self, env_file_path: Path | None = None) -> None:
        self.env_file_path = env_file_path or Path.home() / "Desktop" / "Hexamind" / ".env.autonomous"

    async def apply(self, config_changes: dict) -> bool:
        if not config_changes:
            return True
        lines = []
        if self.env_file_path.exists():
            lines = self.env_file_path.read_text(encoding="utf-8").splitlines()
        data = {line.split("=", 1)[0]: line.split("=", 1)[1] for line in lines if "=" in line and not line.strip().startswith("#")}
        data.update({key: str(value) for key, value in config_changes.items()})
        rendered = [f"{key}={value}" for key, value in sorted(data.items())]
        self.env_file_path.write_text("\n".join(rendered) + "\n", encoding="utf-8")
        return True

    async def rollback(self, previous_config: dict) -> bool:
        return True
