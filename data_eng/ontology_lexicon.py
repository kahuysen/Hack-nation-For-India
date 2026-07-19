"""
Ontology-backed lexicon for trust scoring.

Bridges ontology/*.yaml (concepts + keywords + corroboration edges) to the
planner capabilities used by trust_scoring.py. For each capability it derives
PER-FIELD keyword sets, so corroboration is measured with field-appropriate
vocabulary instead of echo-matching one keyword list everywhere:

  procedure  field <- aliases of the capability's corroborating PROCEDURE concepts
  equipment  field <- aliases of its EQUIPMENT concepts (seeds + every
                      requires_equipment edge of the seed procedures)
  specialties field <- exact ids of the linked specialty codes
  description/capability fields <- the union (free text mentions anything)

Also exposes:
  advanced_equipment_keywords(cap) -> aliases of tier == "advanced" equipment,
      so the app can show when corroboration comes from capital-intensive kit.
  NEGATION_PATTERN -> Java/Python-compatible regex for demoting negated,
      referral, or directory-listing mentions ("referred elsewhere for dialysis").

Loading is lazy and failure-tolerant: if the ontology YAMLs are not shipped
next to the code (e.g. a partial upload to a Databricks workspace),
load_lexicon() returns None and trust_scoring falls back to its hand lexicon.
"""
from functools import lru_cache
from pathlib import Path
import re

try:
    import yaml
except ImportError:                                    # pragma: no cover
    yaml = None


def word_boundary_pattern(keywords) -> str:
    """
    Java/Python regex matching any keyword at word boundaries, so 'icu' can no
    longer match 'curriculum'. Spaces inside multi-word aliases match any
    punctuation run ('x ray' hits 'x-ray'). Case-insensitive via (?i).
    """
    parts = [re.escape(k.lower()).replace(r"\ ", "[^a-z0-9]+") for k in keywords]
    return "(?i)(?<![a-z0-9])(?:" + "|".join(parts) + ")(?![a-z0-9])"

# Matches negated / deferred / referral / directory-listing context around a
# keyword hit. Fixed-width lookarounds only: valid in Python `re` AND Java
# regex (Spark rlike). Keep in sync with ontology/load_to_databricks.py.
NEGATION_PATTERN = (
    r"(?i)(?<![a-z])(no|not|without|lacks?|lacking|unavailable|discontinued"
    r"|closed|referred|referral|proposed|planned|upcoming|under construction"
    r"|listed (as|in|among|under)|no longer)(?![a-z])"
)

# Planner capability -> seed ontology concepts. Keys must match
# trust_scoring.CAPABILITY_LEXICON. Every id is validated against the YAMLs at
# load time so a typo fails fast instead of silently matching nothing.
CAPABILITY_CONCEPTS = {
    "ICU": {
        "procedures":  ["mechanical-ventilation", "emergency-resuscitation"],
        "equipment":   ["icu-beds", "ventilator", "patient-monitor",
                        "defibrillator", "oxygen-supply"],
        "specialties": ["criticalCareMedicine", "anesthesia"],
    },
    "NICU": {
        "procedures":  ["neonatal-intensive-care", "phototherapy"],
        "equipment":   ["incubator", "phototherapy-unit", "ventilator"],
        "specialties": ["neonatologyPerinatalMedicine", "pediatrics"],
    },
    "maternity": {
        "procedures":  ["antenatal-care", "normal-delivery", "cesarean-section"],
        "equipment":   ["delivery-table", "fetal-monitor", "ultrasound-machine"],
        "specialties": ["gynecologyAndObstetrics"],
    },
    "emergency": {
        "procedures":  ["emergency-resuscitation"],
        "equipment":   ["ambulance", "defibrillator", "oxygen-supply"],
        "specialties": ["emergencyMedicine"],
    },
    "oncology": {
        "procedures":  ["chemotherapy", "radiotherapy", "cancer-screening", "biopsy"],
        "equipment":   ["linear-accelerator", "brachytherapy-unit",
                        "chemotherapy-infusion-unit", "mammography-unit"],
        "specialties": ["medicalOncology", "radiationOncology"],
    },
    "trauma": {
        "procedures":  ["fracture-fixation", "emergency-resuscitation", "burn-care"],
        "equipment":   ["c-arm", "operating-theatre", "icu-beds", "blood-bank"],
        "specialties": ["criticalCareMedicine", "orthopedicSurgery", "emergencyMedicine"],
    },
    "dialysis": {
        "procedures":  ["hemodialysis", "peritoneal-dialysis", "kidney-transplant"],
        "equipment":   ["dialysis-machine", "ro-water-plant"],
        "specialties": ["nephrology", "urology"],
    },
    "cardiac": {
        "procedures":  ["angiography", "angioplasty-pci", "cabg", "valve-surgery",
                        "echocardiography", "stress-testing"],
        "equipment":   ["cath-lab", "echo-machine", "heart-lung-machine", "ecg-machine"],
        "specialties": ["cardiology", "cardiacSurgery"],
    },
}


def _find_ontology_dir() -> Path | None:
    """Walk upward from this file (then cwd) looking for ontology/specialties.yaml."""
    candidates = [Path(__file__).resolve().parent, Path.cwd().resolve()]
    for start in candidates:
        for base in (start, *start.parents):
            d = base / "ontology"
            if (d / "specialties.yaml").is_file():
                return d
    return None


class OntologyLexicon:
    """Per-capability, per-field keyword sets derived from the ontology graph."""

    def __init__(self, base_dir: Path):
        load = lambda name, key: {
            c["id"]: c for c in yaml.safe_load((base_dir / name).read_text())[key]
        }
        self.specialties = load("specialties.yaml", "specialties")
        self.procedures = load("procedures.yaml", "procedures")
        self.equipment = load("equipment.yaml", "equipment")
        self._validate()

    def _validate(self):
        for cap, seeds in CAPABILITY_CONCEPTS.items():
            for pid in seeds["procedures"]:
                assert pid in self.procedures, f"{cap}: unknown procedure id {pid!r}"
            for eid in seeds["equipment"]:
                assert eid in self.equipment, f"{cap}: unknown equipment id {eid!r}"
            for sid in seeds["specialties"]:
                assert sid in self.specialties, f"{cap}: unknown specialty id {sid!r}"

    def _equipment_ids(self, capability: str) -> list[str]:
        """Seed equipment + every requires_equipment edge of the seed procedures."""
        seeds = CAPABILITY_CONCEPTS[capability]
        ids = dict.fromkeys(seeds["equipment"])                  # ordered de-dupe
        for pid in seeds["procedures"]:
            for eid in self.procedures[pid].get("requires_equipment", []):
                ids.setdefault(eid)
        return list(ids)

    @staticmethod
    def _keywords(concepts: dict, ids) -> list[str]:
        out = dict.fromkeys(
            k.lower() for cid in ids for k in concepts[cid].get("keywords", [])
        )
        return list(out)

    def procedure_keywords(self, capability: str) -> list[str]:
        return self._keywords(self.procedures, CAPABILITY_CONCEPTS[capability]["procedures"])

    def equipment_keywords(self, capability: str) -> list[str]:
        return self._keywords(self.equipment, self._equipment_ids(capability))

    def advanced_equipment_keywords(self, capability: str) -> list[str]:
        ids = [e for e in self._equipment_ids(capability)
               if self.equipment[e].get("tier") == "advanced"]
        return self._keywords(self.equipment, ids)

    def specialty_ids(self, capability: str) -> list[str]:
        """Exact camelCase codes (lowercased) for the closed specialties field."""
        return [s.lower() for s in CAPABILITY_CONCEPTS[capability]["specialties"]]


@lru_cache(maxsize=1)
def load_lexicon() -> OntologyLexicon | None:
    """Singleton loader; None when PyYAML or the YAML files are unavailable."""
    if yaml is None:
        return None
    base = _find_ontology_dir()
    return OntologyLexicon(base) if base else None
