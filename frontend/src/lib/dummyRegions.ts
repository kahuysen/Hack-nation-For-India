// Dummy data shaped to the REAL API contract (RegionResult / CapabilityItem),
// so the UI already speaks the deployed schema. Swapping to live data is a
// data-source switch (see dataSource.ts) — no component changes.
//
// NOTE: the real /api/regions is district-level; this dummy is state-level to
// match our vendored state choropleth. When wired live, we either fetch a
// district GeoJSON or roll districts up to states for the map.

import type { CapabilityItem, RegionResult, Verdict } from "./api"

export const DUMMY_CAPABILITIES: CapabilityItem[] = [
  { id: "ICU", label: "ICU / Critical care", has_need_signal: true },
  { id: "NICU", label: "NICU", has_need_signal: true },
  { id: "maternity", label: "Maternity", has_need_signal: true },
  { id: "emergency", label: "Emergency care", has_need_signal: true },
  { id: "oncology", label: "Oncology", has_need_signal: true },
  { id: "trauma", label: "Trauma center", has_need_signal: false },
]

// Older state GeoJSON uses these spellings; alias to our region names.
export const STATE_ALIAS: Record<string, string> = {
  orissa: "odisha",
  uttaranchal: "uttarakhand",
}

function region(
  state: string,
  verdict: Verdict,
  coverage: number,
  need_score: number | null,
  risk_score: number,
  n_records: number,
  claiming: number,
  corroborated: number,
): RegionResult {
  return {
    capability_id: "ICU",
    state,
    district: `(${state})`, // dummy is state-grain
    lat: null,
    lon: null,
    n_records,
    n_candidates: claiming,
    claiming,
    corroborated,
    trust_weighted_supply: Math.round(coverage * claiming * 10) / 10,
    coverage,
    knowledge: Math.min(1, 0.2 + corroborated / Math.max(1, claiming)),
    mean_source_trust: 0.4 + coverage * 0.4,
    need_score,
    n_indicators: need_score == null ? 0 : 3,
    data_confidence: verdict === "data_desert" ? "data_desert" : n_records >= 100 ? "solid" : "thin",
    verdict,
    risk_score,
  }
}

// State-level rollup for one capability (dummy).
export const DUMMY_REGIONS: RegionResult[] = [
  region("Delhi", "covered", 0.82, 40, 0.18, 340, 120, 88),
  region("Maharashtra", "covered", 0.74, 45, 0.28, 520, 210, 150),
  region("Karnataka", "covered", 0.68, 50, 0.33, 300, 140, 96),
  region("Kerala", "covered", 0.79, 35, 0.2, 210, 95, 74),
  region("Andhra Pradesh", "covered", 0.66, 50, 0.34, 230, 110, 78),
  region("Haryana", "covered", 0.64, 46, 0.3, 150, 72, 51),
  region("Goa", "covered", 0.76, 38, 0.22, 40, 18, 14),
  region("Tamil Nadu", "watch", 0.55, 52, 0.44, 280, 160, 61),
  region("Gujarat", "watch", 0.5, 48, 0.46, 240, 130, 58),
  region("Telangana", "watch", 0.52, 50, 0.45, 190, 105, 49),
  region("West Bengal", "watch", 0.48, 58, 0.5, 260, 140, 55),
  region("Bihar", "medical_desert", 0.18, 86, 0.91, 90, 40, 12),
  region("Uttar Pradesh", "medical_desert", 0.24, 82, 0.85, 160, 70, 22),
  region("Madhya Pradesh", "medical_desert", 0.21, 78, 0.8, 110, 48, 15),
  region("Rajasthan", "medical_desert", 0.28, 70, 0.72, 120, 55, 19),
  region("Odisha", "medical_desert", 0.26, 74, 0.76, 85, 38, 13),
  region("Chhattisgarh", "medical_desert", 0.2, 80, 0.82, 70, 30, 9),
  region("Uttarakhand", "underserved_need_unknown", 0.23, null, 0.74, 48, 21, 7),
  region("Jharkhand", "underserved_need_unknown", 0.25, null, 0.7, 33, 11, 4),
  region("Punjab", "data_desert", 0.3, null, 0.4, 42, 14, 6),
  region("Assam", "data_desert", 0.22, null, 0.5, 28, 9, 3),
  region("Himachal Pradesh", "data_desert", 0.28, null, 0.48, 26, 8, 3),
  region("Jammu and Kashmir", "data_desert", 0.24, null, 0.52, 30, 10, 4),
]

const byState = new Map<string, RegionResult>(
  DUMMY_REGIONS.map((r) => [r.state.toLowerCase(), r]),
)

/** Look up a dummy region by GeoJSON state name (alias-aware). */
export function regionForState(stateName: string): RegionResult | undefined {
  const key = stateName.toLowerCase()
  return byState.get(STATE_ALIAS[key] ?? key)
}
