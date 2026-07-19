"""Shared capability identifiers used by the batch pipeline and HTTP API."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Capability:
    id: str
    pipeline_key: str
    label: str


CAPABILITIES = (
    Capability("icu", "ICU", "ICU"),
    Capability("nicu", "NICU", "NICU"),
    Capability("emergency", "emergency", "Emergency care"),
    Capability("maternity", "maternity", "Maternity"),
    Capability("oncology", "oncology", "Oncology"),
    Capability("trauma", "trauma", "Trauma center"),
    Capability("dialysis", "dialysis", "Dialysis"),
    Capability("cardiac", "cardiac", "Cardiac care"),
)

BY_ID = {item.id: item for item in CAPABILITIES}
BY_PIPELINE_KEY = {item.pipeline_key: item for item in CAPABILITIES}
_ALIASES = {
    alias.casefold(): item
    for item in CAPABILITIES
    for alias in (item.id, item.pipeline_key, item.label)
}


def resolve_capability(value: str) -> Capability:
    """Resolve a stable id, pipeline key, or display label to one contract."""
    try:
        return _ALIASES[value.strip().casefold()]
    except (AttributeError, KeyError) as exc:
        allowed = ", ".join(item.id for item in CAPABILITIES)
        raise ValueError(f"Unknown capability {value!r}. Choose one of: {allowed}") from exc
