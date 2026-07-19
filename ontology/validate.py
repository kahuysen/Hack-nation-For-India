"""Referential-integrity check for the ontology YAML files.

Verifies that ids are unique within each file and that every cross-file
reference (corroborating_*, performed_by, requires_equipment, enables)
resolves to an existing id. Exits non-zero on any failure.
"""

import pathlib
import sys

import yaml

BASE = pathlib.Path(__file__).parent


def load(name: str, key: str) -> dict:
    entries = yaml.safe_load((BASE / name).read_text())[key]
    ids = [e["id"] for e in entries]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        sys.exit(f"{name}: duplicate ids {sorted(dupes)}")
    return {e["id"]: e for e in entries}


def check_refs(source: str, entries: dict, field: str, target_name: str, target: dict, errors: list):
    for eid, entry in entries.items():
        for ref in entry.get(field) or []:
            if ref not in target:
                errors.append(f"{source}:{eid}.{field} -> '{ref}' not found in {target_name}")


def main() -> None:
    specialties = load("specialties.yaml", "specialties")
    procedures = load("procedures.yaml", "procedures")
    equipment = load("equipment.yaml", "equipment")

    errors: list[str] = []
    check_refs("specialties", specialties, "corroborating_procedures", "procedures", procedures, errors)
    check_refs("specialties", specialties, "corroborating_equipment", "equipment", equipment, errors)
    check_refs("procedures", procedures, "performed_by", "specialties", specialties, errors)
    check_refs("procedures", procedures, "requires_equipment", "equipment", equipment, errors)
    check_refs("equipment", equipment, "enables", "procedures", procedures, errors)

    if errors:
        print("\n".join(errors))
        sys.exit(f"{len(errors)} broken reference(s)")

    print(
        f"OK: {len(specialties)} specialties, {len(procedures)} procedures, "
        f"{len(equipment)} equipment — all cross-references resolve."
    )


if __name__ == "__main__":
    main()
