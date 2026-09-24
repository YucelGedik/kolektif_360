"""Pydantic models for the OPC UA / PLC configuration.

Node mapping is entirely config-driven (integration brief section 10 & 26):
no hard-coded `ns=2;s=Brode.*` style NodeIds and no assumption that the
namespace index stays `ns=4` forever. Everything the client needs to resolve
a tag comes from `config/opcua.json`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class OpcUaConfig(BaseModel):
    endpoint: str = ""
    security_policy: str = "None"
    security_mode: str = "None"
    read_interval_ms: int = Field(default=100, gt=0)
    reconnect_backoff_ms: int = Field(default=1000, gt=0)
    reconnect_backoff_max_ms: int = Field(default=5000, gt=0)
    command_pulse_ms: int = Field(default=150, gt=0)
    stale_timeout_ms: int = Field(default=1000, gt=0)
    # Geçici mühendislik Vision veri simülatörü (PLC-HMI-20260917-02).
    # Varsayılan FALSE: normal müşteri dağıtımında bu özellik ve sayfası
    # görünmez/aktif olmaz. Gerçek kamera devreye alındığında kapatılıp
    # kaldırılabilir olması gerektiğinden ayrı bir mimari parça, tek bayrak.
    vision_simulator_enabled: bool = False
    # Ayri surec karari (KARARLAR.md #1): "KAMERA EKRANI" artik sayfa
    # degistirmiyor, VisionCut'in kendi exe'sini one aliyor/baslatiyor.
    # Bos birakilirsa buton yalnizca calisan pencereyi one alabilir.
    vision_exe: str = ""
    nodes: dict[str, str] = Field(default_factory=dict)

    @property
    def is_configured(self) -> bool:
        """No endpoint means: run in Demo mode instead of attempting a connection."""
        return bool(self.endpoint.strip())

    def node_id(self, name: str) -> str | None:
        return self.nodes.get(name)
