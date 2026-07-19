import { useEffect, useMemo, useRef, useState } from "react"
import * as THREE from "three"
import GlobeGL, { type GlobeMethods } from "react-globe.gl"
import {
  FACILITY_TYPE_LABEL,
  VERDICT_COLOR,
  VERDICT_LABEL,
  facilityTypeColor,
  type FacilityLocation,
  type RegionResult,
} from "@/lib/api"
import { STATE_ALIAS } from "@/lib/dummyRegions"

const WATER_COLOR = 0x0b1f3a // deep blue ocean
const LAND_COLOR = "#dbe2ea" // pale land fill (rest of world)
const BORDER_COLOR = "#334155" // slate borders
const NO_ROLLUP_COLOR = "#3f4a5a" // muted — state absent from the response
const NEUTRAL_STATE_COLOR = "#1e293b" // dark neutral fill under facility points

type Feature = {
  properties: { ADMIN?: string; state?: string }
  geometry: { type: string; coordinates: unknown }
}
type TaggedFeature = Feature & { __kind: "country" | "state" }

const isState = (f: object): f is TaggedFeature =>
  (f as TaggedFeature).__kind === "state"

// With `facilities` set, the globe renders one dot per facility over a neutral
// India instead of the verdict choropleth (regions are then ignored).
export function Globe({
  capability,
  regions,
  facilities,
}: {
  capability: string
  regions: RegionResult[]
  facilities?: FacilityLocation[]
}) {
  const pointsMode = facilities !== undefined
  const globeRef = useRef<GlobeMethods | undefined>(undefined)
  const containerRef = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ width: 0, height: 0 })
  const [countries, setCountries] = useState<Feature[]>([])
  const [states, setStates] = useState<Feature[]>([])

  const globeMaterial = useMemo(
    () => new THREE.MeshPhongMaterial({ color: WATER_COLOR }),
    [],
  )

  // Lookup region by GeoJSON state name (alias-aware).
  const byState = useMemo(() => {
    // The API returns district-level rows (up to 706); the map is state-level.
    // Surface each state's WORST (highest-risk) district so real deserts are
    // never hidden behind a better-off district in the same state.
    const m = new Map<string, RegionResult>()
    for (const r of regions) {
      const key = r.state.toLowerCase()
      const cur = m.get(key)
      if (!cur || r.risk_score > cur.risk_score) m.set(key, r)
    }
    return m
  }, [regions])
  const regionForState = (name: string): RegionResult | undefined => {
    const key = name.toLowerCase()
    return byState.get(STATE_ALIAS[key] ?? key)
  }

  const polygons = useMemo<TaggedFeature[]>(() => {
    const world = countries
      .filter((f) => f.properties.ADMIN !== "India")
      .map((f) => ({ ...f, __kind: "country" as const }))
    const ind = states.map((f) => ({ ...f, __kind: "state" as const }))
    return [...world, ...ind]
  }, [countries, states])

  useEffect(() => {
    fetch("/countries.geojson")
      .then((r) => r.json())
      .then((geo) => setCountries(geo.features))
      .catch((e) => console.error("countries load failed", e))
    fetch("/india-states.geojson")
      .then((r) => r.json())
      .then((geo) => setStates(geo.features))
      .catch((e) => console.error("states load failed", e))
  }, [])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect
      setSize({ width, height })
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    const globe = globeRef.current
    if (!globe) return
    globe.controls().autoRotate = false
    globe.pointOfView({ lat: 22, lng: 80, altitude: 1.6 }, 0)
  }, [size.width])

  return (
    <div ref={containerRef} className="absolute inset-0">
      {size.width > 0 && (
        <GlobeGL
          ref={globeRef}
          width={size.width}
          height={size.height}
          backgroundColor="rgba(0,0,0,0)"
          globeMaterial={globeMaterial}
          showAtmosphere={true}
          atmosphereColor="#3b82f6"
          atmosphereAltitude={0.18}
          polygonsData={polygons}
          polygonCapColor={(f: object) => {
            const tf = f as TaggedFeature
            if (!isState(tf)) return LAND_COLOR
            if (pointsMode) return NEUTRAL_STATE_COLOR
            const r = regionForState(tf.properties.state ?? "")
            return r ? VERDICT_COLOR[r.verdict] : NO_ROLLUP_COLOR
          }}
          polygonSideColor={(f: object) =>
            isState(f as TaggedFeature) ? "rgba(0,0,0,0.35)" : "rgba(0,0,0,0.15)"
          }
          polygonStrokeColor={() => BORDER_COLOR}
          polygonAltitude={(f: object) =>
            isState(f as TaggedFeature) ? 0.016 : 0.006
          }
          polygonsTransitionDuration={0}
          pointsData={facilities ?? []}
          pointLat={(p: object) => (p as FacilityLocation).latitude}
          pointLng={(p: object) => (p as FacilityLocation).longitude}
          pointColor={(p: object) => facilityTypeColor((p as FacilityLocation).facility_type)}
          pointAltitude={0.02}
          pointRadius={0.12}
          pointResolution={6} // ~10k dots live; cheaper cylinders keep hover usable
          pointsMerge={false}
          pointsTransitionDuration={0}
          pointLabel={(p: object) => {
            const fac = p as FacilityLocation
            const typeLabel = FACILITY_TYPE_LABEL[fac.facility_type] ?? fac.facility_type
            return `
              <div style="font:12px/1.4 system-ui;color:#fff;background:rgba(15,23,42,.92);
                          padding:8px 10px;border-radius:8px;border:1px solid rgba(255,255,255,.15);max-width:240px">
                <div style="font-weight:600;font-size:13px">${fac.name}</div>
                <div style="color:${facilityTypeColor(fac.facility_type)};font-weight:600;margin:2px 0 4px">
                  ${typeLabel}
                </div>
                <div>${fac.district} · ${fac.state}</div>
              </div>`
          }}
          polygonLabel={(f: object) => {
            const tf = f as TaggedFeature
            if (!isState(tf) || pointsMode) return ""
            const name = tf.properties.state ?? ""
            const r = regionForState(name)
            if (!r)
              return `
                <div style="font:12px/1.4 system-ui;color:#fff;background:rgba(15,23,42,.92);
                            padding:8px 10px;border-radius:8px;border:1px solid rgba(255,255,255,.15)">
                  <div style="font-weight:600">${name}</div>
                  <div style="color:#94a3b8">No rollup for ${capability}</div>
                </div>`
            const need = r.need_score == null ? "unknown" : `${Math.round(r.need_score)}/100`
            return `
              <div style="font:12px/1.4 system-ui;color:#fff;background:rgba(15,23,42,.92);
                          padding:8px 10px;border-radius:8px;border:1px solid rgba(255,255,255,.15);max-width:240px">
                <div style="font-weight:600;font-size:13px">${r.state}</div>
                <div style="color:${VERDICT_COLOR[r.verdict]};font-weight:600;margin:2px 0 4px">
                  ${VERDICT_LABEL[r.verdict]}
                </div>
                <div>Capability: <b>${capability}</b></div>
                <div>Coverage: ${Math.round(r.coverage * 100)}% · Need: ${need}</div>
                <div>Knowledge: ${Math.round(r.knowledge * 100)}% · Risk: ${r.risk_score.toFixed(2)}</div>
                <div>${r.corroborated}/${r.claiming} claims corroborated · ${r.n_records} records</div>
              </div>`
          }}
        />
      )}
    </div>
  )
}
