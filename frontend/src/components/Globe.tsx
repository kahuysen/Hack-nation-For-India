import { useEffect, useMemo, useRef, useState } from "react"
import * as THREE from "three"
import GlobeGL, { type GlobeMethods } from "react-globe.gl"
import { aggregateRegionsByState, VERDICT_COLOR, VERDICT_LABEL, type RegionResult } from "@/lib/api"
import { STATE_ALIAS } from "@/lib/dummyRegions"

const WATER_COLOR = 0x0b1f3a // deep blue ocean
const LAND_COLOR = "#dbe2ea" // pale land fill (rest of world)
const BORDER_COLOR = "#334155" // slate borders
const NO_ROLLUP_COLOR = "#3f4a5a" // muted — state absent from the response

type Feature = {
  properties: { ADMIN?: string; state?: string }
  geometry: { type: string; coordinates: unknown }
}
type TaggedFeature = Feature & { __kind: "country" | "state" }

const isState = (f: object): f is TaggedFeature =>
  (f as TaggedFeature).__kind === "state"

export function Globe({
  capability,
  regions,
}: {
  capability: string
  regions: RegionResult[]
}) {
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
  // The API returns district-level rows (up to 706); the map is state-level, so
  // aggregate every district of a state into one synthetic row with a recomputed
  // verdict (see aggregateRegionsByState). A state is only a data desert when the
  // whole state has too few records — not when one thin sub-district does.
  const byState = useMemo(() => aggregateRegionsByState(regions), [regions])
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
          polygonLabel={(f: object) => {
            const tf = f as TaggedFeature
            if (!isState(tf)) return ""
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
