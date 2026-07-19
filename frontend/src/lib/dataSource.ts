// Data source switch: live API (when explicitly enabled) vs. dummy data.
//
// The deployed API is behind Databricks SSO, so live calls only succeed
// same-origin inside the Databricks App. Enable with VITE_USE_API=true at build
// time; otherwise (local dev) we serve dummy data shaped to the real contract.

import { api, type CapabilityItem, type FacilityEvidence, type RegionResult } from "./api"
import { DUMMY_CAPABILITIES, DUMMY_REGIONS } from "./dummyRegions"

// Live by default in any production build — Databricks serves the built dist
// same-origin with the API, so a prod build should never fall back to dummy.
// Dummy only in `vite dev`, unless a local dev opts into a running backend
// with VITE_USE_API=true.
const USE_API =
  import.meta.env.VITE_USE_API === "true" || import.meta.env.PROD

export async function fetchCapabilities(): Promise<CapabilityItem[]> {
  if (!USE_API) return DUMMY_CAPABILITIES
  const { capabilities } = await api.getCapabilities()
  return capabilities
}

export async function fetchRegions(capability: string): Promise<RegionResult[]> {
  if (!USE_API) return DUMMY_REGIONS.map((r) => ({ ...r, capability_id: capability }))
  return api.getRegions(capability)
}

export async function fetchFacilities(
  capability: string,
  opts: { state?: string; district?: string } = {},
): Promise<FacilityEvidence[]> {
  if (!USE_API) return [] // dummy facility receipts land in a later step
  return api.getFacilities(capability, opts)
}

export { USE_API }
