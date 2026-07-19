# 8 · Starter materials: the prompts that made the dataset

The challenge organizers published the prompts and Pydantic models their **Foundational Data Refresh (FDR)** pipeline used to generate the dataset. Copies live in [`starter_materials/`](../starter_materials/). They matter for two reasons:

1. **They tell you exactly how noisy each field is.** Every "structured" column was produced by an LLM reading scraped web pages — these prompts are the recipe, so their weaknesses are the dataset's weaknesses.
2. **They're a style template** for our own extraction passes (trust scoring, evidence extraction) — same structured-output pattern, same conservatism rules.

The pipeline ran in stages, one file per stage:

## [`organization_extraction.py`](../starter_materials/organization_extraction.py) — stage 1: find the organizations

`OrganizationExtractionOutput { ngos[], facilities[], other_organizations[] }`

Reads scraped text and pulls out organization **names**, classifying them as healthcare facility, NGO, or other. Strict rules: only names explicitly present in the text, fullest name variant, no business suffixes, conservative when in doubt.

**Implication for us:** a "facility" row exists because an LLM decided a name on a webpage was an operating clinical site. Ghost facilities (closed, administrative-only, misclassified) are possible — good input for the Data Readiness angle and for why `source_urls` provenance matters.

## [`facility_and_ngo_fields.py`](../starter_materials/facility_and_ngo_fields.py) — stage 2: structured fields

`Facility(BaseOrganization)` — the source of most structured columns: contact info, socials, `address_*`, `facilityTypeId` (hospital/pharmacy/doctor/clinic/dentist), `operatorTypeId` (public/private), `affiliationTypeIds`, `yearEstablished`, `area`, `numberDoctors`, `capacity`, `description`.

The system prompt is evidence-strict ("include a fact only if its evidence explicitly names {organization}", "do NOT infer missing details") **except for country**: "Country extraction is MANDATORY … use contextual clues from the URL domain, phone numbers…".

**Implications for us:**
- Low coverage of `capacity` (25%) / `numberDoctors` (36%) is largely *honest absence* — the prompt forbade guessing. Missing ≠ small facility. This is the data-desert argument in one line.
- Address fields were parsed by LLM from free text — expect city/district/state inconsistencies (matches the Marketplace listing's warning).
- Country is the one *inferred* field — fine for India-only data, but a reminder that not all fields carry equal evidentiary weight.

## [`free_form.py`](../starter_materials/free_form.py) — stage 3: the claim fields

`FacilityFacts { procedure[], equipment[], capability[] }` — the three columns our whole trust layer scores.

The prompt defines the category boundaries: **procedure** = interventions performed; **equipment** = physical devices/infrastructure (models when available, "do NOT list bed counts here"); **capability** = level-of-care claims (trauma levels, ICU/NICU units, programs, accreditations, staffing/capacity). Facts must be self-contained declarative sentences, traceable to the source content, no generic statements.

**Implications for us:**
- Each list entry is meant to be **self-contained and source-traceable** — that's why sentence-level citation (our evidence "receipts") is feasible at all.
- The category boundaries justify cross-field corroboration: a real ICU should leave traces in *both* `capability` (the unit) and `equipment` (ventilators/monitors) — the prompt design pushes correlated evidence for real capabilities.
- Content came from websites *and images* — some claims trace to photo interpretation, a weaker evidence class.

## [`medical_specialties.py`](../starter_materials/medical_specialties.py) — stage 4: specialty classification

`MedicalSpecialties { specialties[] }` — a closed-vocabulary classifier mapping content onto a fixed camelCase specialty taxonomy (`internalMedicine`, `gynecologyAndObstetrics`, `cardiacSurgery`…), taken from levels 0–1 of a specialty hierarchy.

Notable defaults baked into the prompt: a generic "Hospital" with no specialty terms → `internalMedicine`; "Clinic" → `familyMedicine`; **"Trauma" → `criticalCareMedicine`**; generic "Oncology" → `medicalOncology`.

**Implications for us:**
- `specialties` values are **name-derived defaults** in many cases — a facility called "X General Hospital" gets `internalMedicine` even if the page said nothing about services. Treat specialties as the weakest claim class.
- When filtering by capability, don't rely on `specialties` alone — e.g. trauma lives under `criticalCareMedicine`, and maternity under `gynecologyAndObstetrics`.
- The file imports the taxonomy from the (unpublished) `fdr.config` module, so it doesn't run standalone — it's documentation, not runnable code.

## The takeaway for the trust scorer

| Field class | Produced by | Trust prior |
|---|---|---|
| `description` | scraped + summarized | highest — closest to source text |
| `procedure`, `equipment`, `capability` | free-form fact extraction | medium — self-contained but LLM-read, sometimes from images |
| structured fields (`capacity`, `numberDoctors`, …) | conservative extraction | honest but sparse — missing means *unknown*, not zero |
| `specialties` | closed-vocab classifier with name-based defaults | lowest — may reflect the facility's *name*, not its services |
| `address_country` | explicitly inferred | fine here (all India), but inferred |

Our scoring should weight corroboration accordingly — and these prompts are the citation for *why* in the demo ("we know this field is weak because here's the prompt that made it").
