// Dummy region data for the Medical Desert Planner visualization.
// One entry per Indian state with a fabricated status + trust-weighted metrics,
// standing in for GET /api/regions until the real API is wired.

export type RegionStatus =
  | "served" // 🟢 trusted supply meets need
  | "claimed-unverified" // 🟠 claims present, weak corroboration
  | "data-desert" // 🟡 too few records to judge
  | "medical-desert" // 🔴 high need, low trusted supply

export type Region = {
  region: string
  lat: number
  lng: number
  status: RegionStatus
  coverage: number // 0..1 trust-weighted supply
  health_need: number | null // 0..1 NFHS need
  priority_score: number // 0..1 ranking signal
  facilities: number
  claiming: number
  corroborated: number
}

// status → color (globe marker + legend)
export const STATUS_COLOR: Record<RegionStatus, string> = {
  served: "#16a34a", // green
  "claimed-unverified": "#f59e0b", // amber
  "data-desert": "#eab308", // yellow
  "medical-desert": "#dc2626", // red
}

export const STATUS_LABEL: Record<RegionStatus, string> = {
  served: "Served",
  "claimed-unverified": "Claimed, unverified",
  "data-desert": "Data desert (unknown)",
  "medical-desert": "Medical desert (real gap)",
}

// Dummy state-level rollup for a single capability (e.g. "ICU").
export const DUMMY_REGIONS: Region[] = [
  { region: "Delhi", lat: 28.61, lng: 77.21, status: "served", coverage: 0.82, health_need: 0.4, priority_score: 0.18, facilities: 340, claiming: 120, corroborated: 88 },
  { region: "Maharashtra", lat: 19.75, lng: 75.71, status: "served", coverage: 0.74, health_need: 0.45, priority_score: 0.28, facilities: 520, claiming: 210, corroborated: 150 },
  { region: "Karnataka", lat: 15.32, lng: 75.71, status: "served", coverage: 0.68, health_need: 0.5, priority_score: 0.33, facilities: 300, claiming: 140, corroborated: 96 },
  { region: "Kerala", lat: 10.53, lng: 76.21, status: "served", coverage: 0.79, health_need: 0.35, priority_score: 0.2, facilities: 210, claiming: 95, corroborated: 74 },
  { region: "Tamil Nadu", lat: 11.13, lng: 78.66, status: "claimed-unverified", coverage: 0.55, health_need: 0.52, priority_score: 0.44, facilities: 280, claiming: 160, corroborated: 61 },
  { region: "Gujarat", lat: 22.66, lng: 71.85, status: "claimed-unverified", coverage: 0.5, health_need: 0.48, priority_score: 0.46, facilities: 240, claiming: 130, corroborated: 58 },
  { region: "Telangana", lat: 17.9, lng: 79.3, status: "claimed-unverified", coverage: 0.52, health_need: 0.5, priority_score: 0.45, facilities: 190, claiming: 105, corroborated: 49 },
  { region: "Punjab", lat: 31.15, lng: 75.34, status: "data-desert", coverage: 0.3, health_need: null, priority_score: 0.4, facilities: 42, claiming: 14, corroborated: 6 },
  { region: "Assam", lat: 26.2, lng: 92.94, status: "data-desert", coverage: 0.22, health_need: null, priority_score: 0.5, facilities: 28, claiming: 9, corroborated: 3 },
  { region: "Jharkhand", lat: 23.61, lng: 85.28, status: "data-desert", coverage: 0.25, health_need: null, priority_score: 0.55, facilities: 33, claiming: 11, corroborated: 4 },
  { region: "Bihar", lat: 25.79, lng: 85.3, status: "medical-desert", coverage: 0.18, health_need: 0.86, priority_score: 0.91, facilities: 90, claiming: 40, corroborated: 12 },
  { region: "Uttar Pradesh", lat: 26.85, lng: 80.91, status: "medical-desert", coverage: 0.24, health_need: 0.82, priority_score: 0.85, facilities: 160, claiming: 70, corroborated: 22 },
  { region: "Madhya Pradesh", lat: 23.47, lng: 77.95, status: "medical-desert", coverage: 0.21, health_need: 0.78, priority_score: 0.8, facilities: 110, claiming: 48, corroborated: 15 },
  { region: "Rajasthan", lat: 26.57, lng: 73.84, status: "medical-desert", coverage: 0.28, health_need: 0.7, priority_score: 0.72, facilities: 120, claiming: 55, corroborated: 19 },
  { region: "Odisha", lat: 20.52, lng: 84.93, status: "medical-desert", coverage: 0.26, health_need: 0.74, priority_score: 0.76, facilities: 85, claiming: 38, corroborated: 13 },
  { region: "West Bengal", lat: 22.99, lng: 87.75, status: "claimed-unverified", coverage: 0.48, health_need: 0.58, priority_score: 0.5, facilities: 260, claiming: 140, corroborated: 55 },
  { region: "Andhra Pradesh", lat: 15.91, lng: 79.74, status: "served", coverage: 0.66, health_need: 0.5, priority_score: 0.34, facilities: 230, claiming: 110, corroborated: 78 },
  { region: "Chhattisgarh", lat: 21.28, lng: 81.87, status: "medical-desert", coverage: 0.2, health_need: 0.8, priority_score: 0.82, facilities: 70, claiming: 30, corroborated: 9 },
  { region: "Haryana", lat: 29.06, lng: 76.09, status: "served", coverage: 0.64, health_need: 0.46, priority_score: 0.3, facilities: 150, claiming: 72, corroborated: 51 },
  { region: "Himachal Pradesh", lat: 31.1, lng: 77.17, status: "data-desert", coverage: 0.28, health_need: null, priority_score: 0.48, facilities: 26, claiming: 8, corroborated: 3 },
  { region: "Uttarakhand", lat: 30.07, lng: 79.09, status: "medical-desert", coverage: 0.23, health_need: 0.72, priority_score: 0.74, facilities: 48, claiming: 21, corroborated: 7 },
  { region: "Goa", lat: 15.3, lng: 74.12, status: "served", coverage: 0.76, health_need: 0.38, priority_score: 0.22, facilities: 40, claiming: 18, corroborated: 14 },
  { region: "Jammu and Kashmir", lat: 33.78, lng: 76.58, status: "data-desert", coverage: 0.24, health_need: null, priority_score: 0.52, facilities: 30, claiming: 10, corroborated: 4 },
]

// Alias geojson state names (older dataset) → our region names.
export const STATE_ALIAS: Record<string, string> = {
  orissa: "odisha",
  uttaranchal: "uttarakhand",
}

// Neutral fill for states with no rollup in view.
export const NO_DATA_COLOR = "#475569" // slate

const byName = new Map<string, Region>(
  DUMMY_REGIONS.map((r) => [r.region.toLowerCase(), r]),
)

export function regionForState(stateName: string): Region | undefined {
  const key = stateName.toLowerCase()
  return byName.get(STATE_ALIAS[key] ?? key)
}
