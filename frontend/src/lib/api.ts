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

// --- district → state rollup ------------------------------------------------ #
// The API returns district-level rows (up to 706); the map is state-level. We
// AGGREGATE every district of a state into one synthetic row and RECOMPUTE the
// verdict, instead of surfacing a single worst-risk district (which let a thin
// sub-district paint the whole state grey/orange and show a misleading record
// count). Thresholds mirror data_eng/district_rollup.py — keep them in sync.
const COVERAGE_OK = 0.35 // mean facility_trust at/above this = covered (keep in sync with district_rollup.py)
const NEED_HI = 50 // NFHS need at/above this = high need
const MIN_SOLID = 10 // >= records = "solid"
const MIN_THIN = 3 // >= records = "thin"; below = data desert

function stateVerdict(nRecords: number, coverage: number, need: number | null): Verdict {
  if (nRecords < MIN_THIN) return "data_desert"
  if (coverage >= COVERAGE_OK) return "covered"
  if (need == null) return "underserved_need_unknown"
  if (need >= NEED_HI) return "medical_desert"
  return "watch"
}

const round = (x: number, p: number) => {
  const f = 10 ** p
  return Math.round(x * f) / f
}

/**
 * Roll district rows up to one synthetic RegionResult per state.
 * Keyed by lowercased state name, matching how the map looks states up.
 */
export function aggregateRegionsByState(regions: RegionResult[]): Map<string, RegionResult> {
  const groups = new Map<string, RegionResult[]>()
  for (const r of regions) {
    const key = r.state.toLowerCase()
    const g = groups.get(key)
    if (g) g.push(r)
    else groups.set(key, [r])
  }

  const out = new Map<string, RegionResult>()
  for (const [key, rows] of groups) {
    const sum = (f: (r: RegionResult) => number) => rows.reduce((a, r) => a + f(r), 0)

    const nRecords = sum((r) => r.n_records)
    const nCandidates = sum((r) => r.n_candidates)
    const trustSupply = sum((r) => r.trust_weighted_supply)

    // coverage = mean facility_trust over candidates → reconstruct from the sums.
    const coverage = nCandidates > 0 ? trustSupply / nCandidates : 0
    // knowledge / source trust are per-record means → weight by record count.
    const knowledge = nRecords > 0 ? sum((r) => r.knowledge * r.n_records) / nRecords : 0
    const meanSourceTrust =
      nRecords > 0 ? sum((r) => r.mean_source_trust * r.n_records) / nRecords : 0
    // need is a demand signal independent of facility density: average the
    // districts that actually carry an NFHS need score (null if none do).
    const needRows = rows.filter((r) => r.need_score != null)
    const need = needRows.length
      ? needRows.reduce((a, r) => a + (r.need_score as number), 0) / needRows.length
      : null

    // record-weighted centroid over districts that have coordinates.
    const geoRows = rows.filter((r) => r.lat != null && r.lon != null && r.n_records > 0)
    const geoWeight = geoRows.reduce((a, r) => a + r.n_records, 0)
    const lat = geoWeight ? geoRows.reduce((a, r) => a + (r.lat as number) * r.n_records, 0) / geoWeight : null
    const lon = geoWeight ? geoRows.reduce((a, r) => a + (r.lon as number) * r.n_records, 0) / geoWeight : null

    const dataConfidence =
      nRecords >= MIN_SOLID ? "solid" : nRecords >= MIN_THIN ? "thin" : "data_desert"
    const verdict = stateVerdict(nRecords, coverage, need)
    const riskScore = ((need ?? NEED_HI) / 100) * (1 - coverage) * knowledge

    out.set(key, {
      capability_id: rows[0].capability_id,
      state: rows[0].state,
      district: `${rows.length} district${rows.length === 1 ? "" : "s"}`,
      lat,
      lon,
      n_records: nRecords,
      n_candidates: nCandidates,
      claiming: sum((r) => r.claiming),
      corroborated: sum((r) => r.corroborated),
      trust_weighted_supply: round(trustSupply, 3),
      coverage: round(coverage, 3),
      knowledge: round(knowledge, 3),
      mean_source_trust: round(meanSourceTrust, 3),
      need_score: need == null ? null : round(need, 2),
      n_indicators: Math.max(0, ...rows.map((r) => r.n_indicators)),
      data_confidence: dataConfidence,
      verdict,
      risk_score: round(riskScore, 4),
    })
  }
  return out
}

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

  getFacilities: (capability: string, opts: { state?: string; district?: string; limit?: number } = {}) =>
    get<FacilityEvidence[]>("/api/facilities", {
      capability,
      state: opts.state,
      district: opts.district,
      limit: opts.limit ?? 100,
    }),
}
