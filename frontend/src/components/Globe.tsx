import { useEffect, useMemo, useRef, useState } from "react"
import * as THREE from "three"
import GlobeGL, { type GlobeMethods } from "react-globe.gl"
import {
  STATUS_COLOR,
  STATUS_LABEL,
  NO_DATA_COLOR,
  regionForState,
} from "@/lib/dummyRegions"

const WATER_COLOR = 0x0b1f3a // deep blue ocean
const LAND_COLOR = "#dbe2ea" // pale land fill (rest of world)
const BORDER_COLOR = "#334155" // slate borders

type Feature = {
  properties: { ADMIN?: string; state?: string }
  geometry: { type: string; coordinates: unknown }
}
// Tag which layer a feature belongs to.
type TaggedFeature = Feature & { __kind: "country" | "state" }

const isState = (f: object): f is TaggedFeature =>
  (f as TaggedFeature).__kind === "state"

function stateColor(f: TaggedFeature): string {
  const r = regionForState(f.properties.state ?? "")
  return r ? STATUS_COLOR[r.status] : NO_DATA_COLOR
}

export function Globe({ capability }: { capability: string }) {
  const globeRef = useRef<GlobeMethods | undefined>(undefined)
  const containerRef = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ width: 0, height: 0 })
  const [countries, setCountries] = useState<Feature[]>([])
  const [states, setStates] = useState<Feature[]>([])

  const globeMaterial = useMemo(
    () => new THREE.MeshPhongMaterial({ color: WATER_COLOR }),
    [],
  )

  // World land (minus India, which the state layer fills) + India states.
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
          polygonCapColor={(f: object) =>
            isState(f as TaggedFeature)
              ? stateColor(f as TaggedFeature)
              : LAND_COLOR
          }
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
                  <div style="color:${NO_DATA_COLOR}">No rollup for ${capability}</div>
                </div>`
            const need = r.health_need == null ? "unknown" : `${Math.round(r.health_need * 100)}%`
            return `
              <div style="font:12px/1.4 system-ui;color:#fff;background:rgba(15,23,42,.92);
                          padding:8px 10px;border-radius:8px;border:1px solid rgba(255,255,255,.15);max-width:230px">
                <div style="font-weight:600;font-size:13px">${r.region}</div>
                <div style="color:${STATUS_COLOR[r.status]};font-weight:600;margin:2px 0 4px">
                  ${STATUS_LABEL[r.status]}
                </div>
                <div>Capability: <b>${capability}</b></div>
                <div>Coverage: ${Math.round(r.coverage * 100)}% · Need: ${need}</div>
                <div>Priority: ${Math.round(r.priority_score * 100)}%</div>
                <div>${r.corroborated}/${r.claiming} claims corroborated · ${r.facilities} records</div>
              </div>`
          }}
        />
      )}
    </div>
  )
}
