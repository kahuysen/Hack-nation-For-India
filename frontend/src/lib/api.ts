// Typed client for the Medical Desert Planner API (v2.0.0).
// Contract mirrors api/openapi.json. The deployed app sits behind Databricks
// SSO, so live calls only work same-origin (inside the Databricks App) — locally
// we fall back to dummy data (see dataSource.ts).

export type Verdict =
  | "covered"
  | "watch"
  | "medical_desert"
  | "underserved_need_unknown"
  | "data_desert"

export type CapabilityItem = {
  id: string
  label: string
  has_need_signal: boolean
}

export type RegionResult = {
  capability_id: string
  state: string
  district: string
  lat: number | null
  lon: number | null
  n_records: number
  n_candidates: number
  claiming: number
  corroborated: number
  trust_weighted_supply: number
  coverage: number // 0..1
  knowledge: number // 0..1
  mean_source_trust: number
  need_score: number | null // 0..100
  n_indicators: number
  data_confidence: string
  verdict: Verdict
  risk_score: number
}

export type FacilityLocation = {
  facility_id: string
  name: string
  facility_type: string
  state: string
  district: string
  latitude: number
  longitude: number
}

export type EvidenceItem = { field: string; snippet: string }

export type FacilityEvidence = {
  capability_id: string
  facility_id: string
  name: string
  state: string
  district: string
  pin: string | null
  is_candidate: number
  claiming: number
  n_corroborating: number
  tier: string
  trust_weight: number
  knowledge: number
  source_trust: number
  data_confidence: string
  evidence: EvidenceItem[]
  description: string | null
  latitude: number | null
  longitude: number | null
  source_urls: string | null
}

// --- verdict presentation (single source of truth for map + legend) --------- #
export const VERDICT_COLOR: Record<Verdict, string> = {
  medical_desert: "#dc2626", // red — real gap
  underserved_need_unknown: "#f97316", // orange — low supply, need unknown
  watch: "#eab308", // yellow — thin gap
  covered: "#16a34a", // green — served
  data_desert: "#64748b", // slate — too few records (NOT a medical gap)
}

export const VERDICT_LABEL: Record<Verdict, string> = {
  medical_desert: "Medical desert (real gap)",
  underserved_need_unknown: "Underserved · need unknown",
  watch: "Watch (thin gap)",
  covered: "Served",
  data_desert: "Data desert (too few records)",
}

// Legend order: worst → best, with data desert set apart as "unknown".
export const VERDICT_ORDER: Verdict[] = [
  "medical_desert",
  "underserved_need_unknown",
  "watch",
  "covered",
  "data_desert",
]

// --- facility type presentation (single source of truth for points + legend) - #
export const FACILITY_TYPE_COLOR: Record<string, string> = {
  hospital: "#38bdf8", // sky
  clinic: "#34d399", // emerald
  dentist: "#fbbf24", // amber
  doctor: "#f472b6", // pink
  pharmacy: "#a78bfa", // violet
  nursing_home: "#fb923c", // orange
  unknown: "#94a3b8", // slate
}

export const FACILITY_TYPE_LABEL: Record<string, string> = {
  hospital: "Hospital",
  clinic: "Clinic",
  dentist: "Dentist",
  doctor: "Doctor",
  pharmacy: "Pharmacy",
  nursing_home: "Nursing home",
  unknown: "Unknown type",
}

// Legend order: most common first, unknown last.
export const FACILITY_TYPE_ORDER = [
  "hospital", "clinic", "dentist", "doctor", "pharmacy", "nursing_home", "unknown",
]

export const facilityTypeColor = (type: string): string =>
  FACILITY_TYPE_COLOR[type] ?? FACILITY_TYPE_COLOR.unknown

// --- HTTP client ------------------------------------------------------------ #
// Same-origin by default (Databricks App); override for a local proxy/mock.
const BASE = import.meta.env.VITE_API_BASE ?? ""

async function get<T>(path: string, params: Record<string, string | number | boolean | undefined>): Promise<T> {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null) qs.set(k, String(v))
  }
  const url = `${BASE}${path}${qs.toString() ? `?${qs}` : ""}`
  const res = await fetch(url, { credentials: "include" }) // SSO cookie when same-origin
  if (!res.ok) throw new Error(`${path} → ${res.status}`)
  return res.json() as Promise<T>
}

export const api = {
  getCapabilities: () =>
    get<{ capabilities: CapabilityItem[] }>("/api/capabilities", {}),

  getRegions: (capability: string, opts: { state?: string; verdict?: Verdict; limit?: number } = {}) =>
    get<RegionResult[]>("/api/regions", {
      capability,
      state: opts.state,
      verdict: opts.verdict,
      limit: opts.limit ?? 706, // full national picture (API caps limit at 706 districts)
    }),

  getFacilityLocations: () =>
    get<FacilityLocation[]>("/api/facility-locations", {}),

  getFacilities: (capability: string, opts: { state?: string; district?: string; limit?: number } = {}) =>
    get<FacilityEvidence[]>("/api/facilities", {
      capability,
      state: opts.state,
      district: opts.district,
      limit: opts.limit ?? 100,
    }),
}
