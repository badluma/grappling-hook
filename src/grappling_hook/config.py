"""User config, stored as TOML in the platform's config dir."""

import os
import sys
import tomllib
from dataclasses import asdict, dataclass, fields
from pathlib import Path


def _config_path() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "grappling-hook" / "config.toml"


@dataclass
class Config:
    debug: bool = False
    use_external_client: bool = False
    custom_aniworld_path: str = ""
    download_dir: str = ""

    @classmethod
    def load(cls) -> "Config":
        try:
            data = tomllib.loads(_config_path().read_text())
        except (OSError, tomllib.TOMLDecodeError):
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self) -> None:
        path = _config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        for key, value in asdict(self).items():
            toml_value = f"'{value}'" if isinstance(value, str) else str(value).lower()
            lines.append(f"{key} = {toml_value}")
        path.write_text("\n".join(lines) + "\n")
