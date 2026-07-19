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
#
# Curation policy: seeds were audited against derive_capability_concepts()
# (bottom-up graph walk from anchor specialties — see compare_derived()) and
# extended with its defensible finds. Deliberately NOT adopted, because a
# specialty is broader than a planner capability:
#   - maternity: ivf / hysteroscopy / hysterectomy / cancer-screening /
#     laparoscopic-surgery (gynecology, not obstetric care)
#   - trauma: joint-replacement / arthroscopy (elective orthopedics) and
#     stroke-thrombolysis (stroke pathway, not injury)
#   - dialysis: icu-beds (reached only via kidney-transplant; too generic)
#   - anywhere: operating-theatre unless explicitly modeled (19 procedures
#     require it — it corroborates everything, i.e. nothing)
CAPABILITY_CONCEPTS = {
    "ICU": {
        "procedures":  ["mechanical-ventilation", "emergency-resuscitation",
                        "burn-care"],
        "equipment":   ["icu-beds", "ventilator", "patient-monitor",
                        "defibrillator", "oxygen-supply", "isolation-ward"],
        "specialties": ["criticalCareMedicine", "anesthesia"],
    },
    "NICU": {
        "procedures":  ["neonatal-intensive-care", "phototherapy"],
        "equipment":   ["incubator", "phototherapy-unit", "ventilator",
                        "patient-monitor"],
        "specialties": ["neonatologyPerinatalMedicine", "pediatrics"],
    },
    "maternity": {
        "procedures":  ["antenatal-care", "normal-delivery", "cesarean-section"],
        "equipment":   ["delivery-table", "fetal-monitor", "ultrasound-machine"],
        "specialties": ["gynecologyAndObstetrics"],
    },
    "emergency": {
        "procedures":  ["emergency-resuscitation", "minor-wound-care",
                        "fracture-fixation", "stroke-thrombolysis"],
        "equipment":   ["ambulance", "defibrillator", "oxygen-supply",
                        "xray-machine", "c-arm", "ct-scanner",
                        "patient-monitor", "ventilator", "icu-beds"],
        "specialties": ["emergencyMedicine"],
    },
    "oncology": {
        "procedures":  ["chemotherapy", "radiotherapy", "cancer-screening", "biopsy"],
        "equipment":   ["linear-accelerator", "brachytherapy-unit",
                        "chemotherapy-infusion-unit", "mammography-unit",
                        "laboratory-analyzer", "microscope"],
        "specialties": ["medicalOncology", "radiationOncology"],
    },
    "trauma": {
        "procedures":  ["fracture-fixation", "emergency-resuscitation", "burn-care",
                        "mechanical-ventilation", "minor-wound-care", "spine-surgery"],
        "equipment":   ["c-arm", "operating-theatre", "icu-beds", "blood-bank",
                        "ambulance", "ct-scanner", "defibrillator", "oxygen-supply",
                        "patient-monitor", "ventilator", "xray-machine"],
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
        "equipment":   ["cath-lab", "echo-machine", "heart-lung-machine",
                        "ecg-machine", "icu-beds", "patient-monitor"],
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


# --------------------------------------------------------------------------- #
# Bottom-up derivation of capability concept sets from the graph itself.
#
# Instead of hand-listing every seed concept, anchor each planner capability on
# its specialties and walk the edges:
#   anchor specialty --corroborating_procedures-->  procedures
#   anchor specialty <--performed_by--              procedures   (reverse edge)
#   anchor specialty --corroborating_equipment-->   equipment
#   derived procedure --requires_equipment-->       equipment
#
# Hub guard: equipment reached ONLY via the requires_equipment hop is dropped
# when many procedures across the whole graph require it (operating-theatre is
# required by 19 — it corroborates everything, i.e. nothing). Explicitly
# modeled corroborating_equipment survives regardless of degree.
#
# Derivation is deliberately an AUDIT/SUGGESTION tool, not the runtime source:
# anchors are specialty-shaped, and a specialty is broader than a planner
# capability (gynecologyAndObstetrics covers IVF and hysteroscopy, which are
# not "maternity"). CAPABILITY_CONCEPTS stays the curated contract; run
# compare_derived() to see what the graph thinks curation missed.
# --------------------------------------------------------------------------- #
ANCHOR_SPECIALTIES = {
    "ICU":       ["criticalCareMedicine"],
    "NICU":      ["neonatologyPerinatalMedicine"],
    "maternity": ["gynecologyAndObstetrics"],
    "emergency": ["emergencyMedicine"],
    "oncology":  ["medicalOncology", "radiationOncology"],
    "trauma":    ["criticalCareMedicine", "emergencyMedicine", "orthopedicSurgery"],
    "dialysis":  ["nephrology"],
    "cardiac":   ["cardiology", "cardiacSurgery"],
}

MAX_EQUIPMENT_DEGREE = 6   # requires_equipment in-degree above this = hub


def derive_capability_concepts(lex: "OntologyLexicon",
                               anchors: dict = None,
                               max_equipment_degree: int = MAX_EQUIPMENT_DEGREE) -> dict:
    """Walk the graph from anchor specialties; returns the same shape as
    CAPABILITY_CONCEPTS. Pure function of the YAMLs — nothing hand-listed
    except the anchors."""
    anchors = anchors or ANCHOR_SPECIALTIES
    degree = {}
    for p in lex.procedures.values():
        for eid in p.get("requires_equipment", []):
            degree[eid] = degree.get(eid, 0) + 1

    derived = {}
    for cap, anchor_ids in anchors.items():
        for sid in anchor_ids:
            assert sid in lex.specialties, f"{cap}: unknown anchor specialty {sid!r}"
        procs = dict.fromkeys(
            pid
            for sid in anchor_ids
            for pid in lex.specialties[sid].get("corroborating_procedures", []))
        for pid, p in lex.procedures.items():                 # reverse performed_by
            if any(sid in p.get("performed_by", []) for sid in anchor_ids):
                procs.setdefault(pid)
        explicit_eq = dict.fromkeys(
            eid
            for sid in anchor_ids
            for eid in lex.specialties[sid].get("corroborating_equipment", []))
        equipment = dict(explicit_eq)
        for pid in procs:                                     # one hop, hub-guarded
            for eid in lex.procedures[pid].get("requires_equipment", []):
                if eid in explicit_eq or degree.get(eid, 0) <= max_equipment_degree:
                    equipment.setdefault(eid)
        derived[cap] = {"procedures": list(procs),
                        "equipment": list(equipment),
                        "specialties": list(anchor_ids)}
    return derived


def compare_derived(lex: "OntologyLexicon") -> dict:
    """Per capability: what bottom-up derivation adds to / misses from the
    curated CAPABILITY_CONCEPTS. Feed to a test or eyeball in a notebook."""
    derived = derive_capability_concepts(lex)
    report = {}
    for cap, hand in CAPABILITY_CONCEPTS.items():
        d = derived[cap]
        report[cap] = {
            kind: {"derived_adds": sorted(set(d[kind]) - set(hand[kind])),
                   "hand_only": sorted(set(hand[kind]) - set(d[kind]))}
            for kind in ("procedures", "equipment", "specialties")
        }
    return report


@lru_cache(maxsize=1)
def load_lexicon() -> OntologyLexicon | None:
    """Singleton loader; None when PyYAML or the YAML files are unavailable."""
    if yaml is None:
        return None
    base = _find_ontology_dir()
    return OntologyLexicon(base) if base else None
