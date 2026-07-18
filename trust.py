"""Trust scoring for facility capability claims.

Heuristic corroboration layer: for each facility x capability, check whether
the claim in `capability` is echoed by `procedure`, `equipment`, or the
free-text `description`. This is the placeholder for the LLM extraction
pipeline — swap `score_facility` for model-generated evidence later without
touching the app.
"""

from dataclasses import dataclass, field

CAPABILITIES = ["ICU", "NICU", "Emergency care", "Maternity", "Oncology", "Trauma center"]

# Keywords whose presence in another field corroborates the claim.
CORROBORATION_KEYWORDS = {
    "ICU": ["icu", "intensive care", "ventilator", "critical care"],
    "NICU": ["nicu", "neonatal", "incubator", "newborn", "warmer"],
    "Emergency care": ["emergency", "trauma", "ambulance", "24/7", "casualty", "first aid"],
    "Maternity": ["maternity", "labor", "labour", "delivery", "deliveries", "cesarean", "obstetric", "fetal"],
    "Oncology": ["oncology", "cancer", "chemotherapy", "radiation", "linear accelerator", "pet-ct"],
    "Trauma center": ["trauma", "emergency surgery", "level i", "level ii"],
}

TIER_CORROBORATED = "Corroborated"
TIER_CLAIMED_ONLY = "Claimed only"
TIER_NOT_CLAIMED = "Not claimed"

# Trust weight each tier contributes to regional coverage.
TIER_WEIGHTS = {TIER_CORROBORATED: 1.0, TIER_CLAIMED_ONLY: 0.3, TIER_NOT_CLAIMED: 0.0}


@dataclass
class ClaimAssessment:
    capability: str
    claimed: bool
    tier: str
    weight: float
    evidence: list = field(default_factory=list)  # (source_field, matching text)


def _matches(text, keywords):
    text = (text or "").lower()
    return [kw for kw in keywords if kw in text]


def score_facility(row, capability):
    """Assess one capability claim for one facility row (dict-like)."""
    claimed = capability.lower() in (row.get("capability") or "").lower()
    if not claimed:
        return ClaimAssessment(capability, False, TIER_NOT_CLAIMED, 0.0)

    keywords = CORROBORATION_KEYWORDS[capability]
    evidence = []
    for source in ("procedure", "equipment", "description"):
        hits = _matches(row.get(source), keywords)
        if hits:
            evidence.append((source, ", ".join(hits)))

    tier = TIER_CORROBORATED if len(evidence) >= 1 else TIER_CLAIMED_ONLY
    return ClaimAssessment(capability, True, tier, TIER_WEIGHTS[tier], evidence)


def knowledge_score(row):
    """How much do we actually know about this facility? 0..1 based on field completeness."""
    fields = ["description", "capability", "procedure", "equipment", "capacity", "numberDoctors"]
    filled = sum(1 for f in fields if str(row.get(f) or "").strip() not in ("", "nan"))
    return filled / len(fields)


def classify_region(coverage, knowledge, coverage_threshold=0.5, knowledge_threshold=0.45):
    """The 2x2 that separates medical deserts from data deserts."""
    if knowledge < knowledge_threshold:
        return "🟡 Data desert" if coverage < coverage_threshold else "🟠 Claimed, unverified"
    return "🔴 Medical desert" if coverage < coverage_threshold else "🟢 Served"
