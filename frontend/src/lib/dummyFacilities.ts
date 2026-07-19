// Dummy facility evidence shaped to the REAL API contract (FacilityEvidence),
// so the receipts panel renders in `vite dev` and offline demos. The live path
// (VITE_USE_API / prod build) hits /api/facilities instead — see dataSource.ts.

import type { FacilityEvidence } from "./api"

function facility(
  name: string,
  state: string,
  district: string,
  tier: string,
  trust_weight: number,
  knowledge: number,
  source_trust: number,
  n_corroborating: number,
  claiming: number,
  data_confidence: string,
  evidence: { field: string; snippet: string }[],
  description: string | null,
  source_urls: string | null,
): FacilityEvidence {
  return {
    capability_id: "ICU",
    facility_id: `${state}-${district}-${name}`.toLowerCase().replace(/\s+/g, "-"),
    name,
    state,
    district,
    pin: null,
    is_candidate: 1,
    claiming,
    n_corroborating,
    tier,
    trust_weight,
    knowledge,
    source_trust,
    data_confidence,
    evidence,
    description,
    latitude: null,
    longitude: null,
    source_urls,
  }
}

// A handful of states with contrasting trust profiles for the demo.
export const DUMMY_FACILITIES: FacilityEvidence[] = [
  facility(
    "Patna Medical College Hospital", "Bihar", "Patna", "government", 0.82, 0.7, 0.78, 3, 4, "solid",
    [
      { field: "services", snippet: "24x7 intensive care unit with 30 ICU beds and ventilator support." },
      { field: "accreditation", snippet: "Listed as a state tertiary referral centre for critical care." },
    ],
    "Tertiary government teaching hospital; primary ICU referral centre for central Bihar.",
    "https://pmch.gov.in https://data.gov.in/facility/pmch",
  ),
  facility(
    "Sahyog Nursing Home", "Bihar", "Gaya", "private", 0.34, 0.4, 0.36, 1, 3, "thin",
    [{ field: "listing", snippet: "Directory entry mentions 'ICU facility' without bed count or staffing detail." }],
    null,
    null,
  ),
  facility(
    "KEM Hospital", "Maharashtra", "Mumbai", "government", 0.9, 0.86, 0.88, 5, 6, "solid",
    [
      { field: "services", snippet: "Multi-disciplinary ICU, NICU and cardiac ICU across 120+ critical-care beds." },
      { field: "corroboration", snippet: "Confirmed by state health directory and two independent hospital indexes." },
    ],
    "Major public tertiary hospital and medical college in Mumbai.",
    "https://www.kem.edu",
  ),
  facility(
    "Lifeline Multispeciality", "Maharashtra", "Nagpur", "private", 0.61, 0.6, 0.58, 2, 3, "solid",
    [{ field: "services", snippet: "Private multispecialty with a 12-bed ICU and 24x7 emergency intake." }],
    "Private multispecialty hospital serving eastern Maharashtra.",
    "https://example-lifeline.in",
  ),
  facility(
    "Government Rajaji Hospital", "Tamil Nadu", "Madurai", "government", 0.79, 0.74, 0.8, 4, 5, "solid",
    [
      { field: "services", snippet: "Government tertiary hospital with dedicated medical and surgical ICUs." },
      { field: "accreditation", snippet: "State-designated tertiary referral centre for southern Tamil Nadu." },
    ],
    "One of the largest government hospitals in southern Tamil Nadu.",
    "https://www.mmc.tn.gov.in",
  ),
]

/** Dummy stand-in for /api/facilities: filter by state/district. */
export function dummyFacilities(state?: string, district?: string): FacilityEvidence[] {
  return DUMMY_FACILITIES.filter(
    (f) =>
      (!state || f.state.toLowerCase() === state.toLowerCase()) &&
      (!district || f.district.toLowerCase() === district.toLowerCase()),
  ).sort((a, b) => b.trust_weight - a.trust_weight)
}
