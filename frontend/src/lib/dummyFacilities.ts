// Dummy facility locations shaped to the REAL /api/facility-locations contract
// (FacilityLocation), so the Facilities tab works offline in `vite dev`. The
// live table holds ~10k rows; this is a sparse but geographically honest stand-in:
// a few facilities scattered around real city anchors, deterministic (no RNG)
// so snapshots and manual QA stay stable.

import type { FacilityLocation } from "./api"
import { FACILITY_TYPE_ORDER } from "./api"

type CityAnchor = { city: string; state: string; lat: number; lon: number }

const CITIES: CityAnchor[] = [
  { city: "Delhi", state: "Delhi", lat: 28.61, lon: 77.21 },
  { city: "Mumbai", state: "Maharashtra", lat: 19.08, lon: 72.88 },
  { city: "Kolkata", state: "West Bengal", lat: 22.57, lon: 88.36 },
  { city: "Chennai", state: "Tamil Nadu", lat: 13.08, lon: 80.27 },
  { city: "Bengaluru", state: "Karnataka", lat: 12.97, lon: 77.59 },
  { city: "Hyderabad", state: "Telangana", lat: 17.39, lon: 78.49 },
  { city: "Ahmedabad", state: "Gujarat", lat: 23.02, lon: 72.57 },
  { city: "Pune", state: "Maharashtra", lat: 18.52, lon: 73.86 },
  { city: "Jaipur", state: "Rajasthan", lat: 26.91, lon: 75.79 },
  { city: "Lucknow", state: "Uttar Pradesh", lat: 26.85, lon: 80.95 },
  { city: "Patna", state: "Bihar", lat: 25.59, lon: 85.14 },
  { city: "Bhopal", state: "Madhya Pradesh", lat: 23.26, lon: 77.41 },
  { city: "Bhubaneswar", state: "Odisha", lat: 20.3, lon: 85.82 },
  { city: "Guwahati", state: "Assam", lat: 26.14, lon: 91.74 },
  { city: "Chandigarh", state: "Punjab", lat: 30.73, lon: 76.78 },
  { city: "Kochi", state: "Kerala", lat: 9.93, lon: 76.27 },
  { city: "Nagpur", state: "Maharashtra", lat: 21.15, lon: 79.09 },
  { city: "Ranchi", state: "Jharkhand", lat: 23.34, lon: 85.31 },
  { city: "Dehradun", state: "Uttarakhand", lat: 30.32, lon: 78.03 },
  { city: "Raipur", state: "Chhattisgarh", lat: 21.25, lon: 81.63 },
  { city: "Visakhapatnam", state: "Andhra Pradesh", lat: 17.69, lon: 83.22 },
  { city: "Srinagar", state: "Jammu and Kashmir", lat: 34.08, lon: 74.8 },
  { city: "Imphal", state: "Manipur", lat: 24.82, lon: 93.94 },
  { city: "Panaji", state: "Goa", lat: 15.49, lon: 73.83 },
]

const PER_CITY = 6

// Deterministic scatter: spread facilities on a small spiral around the anchor.
export const DUMMY_FACILITY_LOCATIONS: FacilityLocation[] = CITIES.flatMap(
  (anchor, cityIndex) =>
    Array.from({ length: PER_CITY }, (_, i): FacilityLocation => {
      const angle = (cityIndex * PER_CITY + i) * 2.4 // golden-angle-ish spread
      const radius = 0.06 + 0.05 * i
      const type = FACILITY_TYPE_ORDER[(cityIndex + i) % (FACILITY_TYPE_ORDER.length - 1)] // skip "unknown"
      return {
        facility_id: `dummy-${anchor.city.toLowerCase()}-${i}`,
        name: `${anchor.city} ${type.replace("_", " ")} ${i + 1}`,
        facility_type: type,
        state: anchor.state,
        district: anchor.city,
        latitude: anchor.lat + radius * Math.sin(angle),
        longitude: anchor.lon + radius * Math.cos(angle),
      }
    }),
)
