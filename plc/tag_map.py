"""Loads the OPC UA config file and resolves logical tag names to NodeIds.

Keeping this in one small module means the rest of the codebase never touches
a raw NodeId string or a JSON file directly (brief section 10: NodeId mapping
must be config-based, not hard-coded).
"""

from __future__ import annotations

import json
from pathlib import Path

from app.paths import config_dir
from plc.models import OpcUaConfig

#: Resolved on each access, not at import: a test that points
#: BUFERA_CONFIG_DIR somewhere else must be able to do so after import.
def default_config_path() -> Path:
    return config_dir() / "opcua.json"


class TagMapError(RuntimeError):
    pass


def load_config(path: Path | str | None = None) -> OpcUaConfig:
    config_path = Path(path) if path is not None else default_config_path()
    if not config_path.exists():
        # ⚠️ Deliberately NOT an error. A machine that has never been
        # commissioned has no config file, and refusing to open leaves the
        # operator with a traceback instead of a screen. An empty config has
        # no endpoint, so `is_configured` is False and the HMI opens in Demo
        # mode and says so.
        #
        # A file that EXISTS but is malformed still raises: that one somebody
        # edited, and silently ignoring their mistake would be worse.
        return OpcUaConfig()
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TagMapError(f"OPC UA config is not valid JSON: {config_path} ({exc})") from exc
    return OpcUaConfig.model_validate(raw)


def save_config(config: OpcUaConfig, path: Path | str | None = None) -> None:
    config_path = Path(path) if path is not None else default_config_path()
    # Taşınabilir/paketli bir dağıtımda `config/` klasörü ilk çalıştırmada
    # hiç yoksa (config dosyası eksikti, Demo moda düşüldü) Ayarlar'dan
    # "Kaydet" tıklanınca burası olmadan write_text() FileNotFoundError
    # verirdi.
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(config.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


class TagMap:
    """Thin resolver: logical name -> NodeId string, backed by an OpcUaConfig."""

    def __init__(self, config: OpcUaConfig):
        self._config = config

    @property
    def config(self) -> OpcUaConfig:
        return self._config

    def resolve(self, name: str) -> str:
        node_id = self._config.node_id(name)
        if node_id is None:
            raise TagMapError(f"No NodeId configured for tag '{name}'")
        return node_id

    def try_resolve(self, name: str) -> str | None:
        return self._config.node_id(name)

    def known_tags(self) -> list[str]:
        return sorted(self._config.nodes.keys())
