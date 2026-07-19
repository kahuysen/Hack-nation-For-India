import { useEffect, useMemo, useRef, useState } from "react"
import * as THREE from "three"
import { cellToLatLng, polygonToCells } from "h3-js"
import GlobeGL, { type GlobeMethods } from "react-globe.gl"

const WATER_COLOR = 0x2563eb // blue ocean (globe sphere)
const LAND_COLOR = "#ffffff" // white land fill
const BORDER_COLOR = "#000000" // black country borders

// Dummy "activity" hotspots over India — [lat, lng, intensity].
const HOTSPOTS: [number, number, number][] = [
  [28.6139, 77.209, 0.9], // Delhi
  [19.076, 72.8777, 0.85], // Mumbai
  [12.9716, 77.5946, 0.8], // Bengaluru
  [22.5726, 88.3639, 0.7], // Kolkata
  [13.0827, 80.2707, 0.65], // Chennai
  [17.385, 78.4867, 0.6], // Hyderabad
  [26.9124, 75.7873, 0.5], // Jaipur
]
const HOTSPOT_SIGMA = 2.6 // degrees

// Heatmap color ramp: blue → cyan → green → orange → red.
const HEAT_STOPS: [number, [number, number, number]][] = [
  [0.0, [37, 99, 235]],
  [0.3, [6, 182, 212]],
  [0.55, [132, 204, 22]],
  [0.78, [245, 158, 11]],
  [1.0, [220, 38, 38]],
]

// Smooth dummy weight in [0, 1] from the hotspots — resolution-independent.
function weightAt(lat: number, lng: number): number {
  let w = 0.08
  for (const [hlat, hlng, intensity] of HOTSPOTS) {
    const d2 = (lat - hlat) ** 2 + (lng - hlng) ** 2
    w += intensity * Math.exp(-d2 / (2 * HOTSPOT_SIGMA ** 2))
  }
  return Math.min(1, w)
}

function heatColor(t: number, alpha = 0.92): string {
  const x = Math.max(0, Math.min(1, t))
  for (let i = 1; i < HEAT_STOPS.length; i++) {
    const [t1, c1] = HEAT_STOPS[i]
    if (x <= t1) {
      const [t0, c0] = HEAT_STOPS[i - 1]
      const f = (x - t0) / (t1 - t0)
      const r = Math.round(c0[0] + (c1[0] - c0[0]) * f)
      const g = Math.round(c0[1] + (c1[1] - c0[1]) * f)
      const b = Math.round(c0[2] + (c1[2] - c0[2]) * f)
      return `rgba(${r}, ${g}, ${b}, ${alpha})`
    }
  }
  const [, last] = HEAT_STOPS[HEAT_STOPS.length - 1]
  return `rgba(${last[0]}, ${last[1]}, ${last[2]}, ${alpha})`
}

// Zoom → H3 resolution. Closer camera (smaller altitude) → finer hexagons.
function altitudeToResolution(altitude: number): number {
  if (altitude > 3.2) return 2
  if (altitude > 2.4) return 3
  if (altitude > 1.6) return 4
  return 5
}

// One weighted point per H3 cell covering India, so every cell renders (full coverage).
function buildHeatPoints(indiaFeature: GeoFeature | null, resolution: number) {
  if (!indiaFeature) return []
  const geom = indiaFeature.geometry
  const polygons =
    geom.type === "Polygon"
      ? [geom.coordinates as number[][][]]
      : (geom.coordinates as number[][][][])

  const cells = new Set<string>()
  for (const polygon of polygons) {
    // isGeoJson=true → coordinates are [lng, lat], clipped to the polygon.
    for (const cell of polygonToCells(polygon, resolution, true)) cells.add(cell)
  }

  return Array.from(cells, (cell) => {
    const [lat, lng] = cellToLatLng(cell)
    return { lat, lng, weight: weightAt(lat, lng) }
  })
}

type GeoFeature = {
  properties: { ADMIN?: string }
  geometry: { type: "Polygon" | "MultiPolygon"; coordinates: unknown }
}
type HeatPoint = { lat: number; lng: number; weight: number }
// Aggregated hexbin passed to the accessors by react-globe.gl.
type HexBin = { points: HeatPoint[]; sumWeight: number }

// Mean weight of a hexbin — stable across resolution (1 point per cell → the cell's weight).
const binIntensity = (bin: HexBin) =>
  bin.points.length ? bin.sumWeight / bin.points.length : 0

export function Globe() {
  const globeRef = useRef<GlobeMethods | undefined>(undefined)
  const containerRef = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ width: 0, height: 0 })
  const [countries, setCountries] = useState<GeoFeature[]>([])
  const [resolution, setResolution] = useState(() => altitudeToResolution(2))

  const globeMaterial = useMemo(
    () => new THREE.MeshPhongMaterial({ color: WATER_COLOR }),
    [],
  )

  const india = useMemo(
    () => countries.find((f) => f.properties.ADMIN === "India") ?? null,
    [countries],
  )

  // Rebuild the hex grid whenever India loads or the zoom resolution changes.
  const heatPoints = useMemo(
    () => buildHeatPoints(india, resolution),
    [india, resolution],
  )

  // Load precise country boundaries (Natural Earth 110m, vendored in /public).
  useEffect(() => {
    fetch("/countries.geojson")
      .then((res) => res.json())
      .then((geo) => setCountries(geo.features))
      .catch((err) => console.error("Failed to load country outlines", err))
  }, [])

  // Keep the globe sized to its container.
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

  // Point the camera at India on mount. No auto-rotation — the user drives it.
  useEffect(() => {
    const globe = globeRef.current
    if (!globe) return
    globe.controls().autoRotate = false
    globe.pointOfView({ lat: 22, lng: 79, altitude: 2 }, 0)
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
          showAtmosphere={false}
          polygonsData={countries}
          polygonCapColor={() => LAND_COLOR}
          polygonSideColor={() => LAND_COLOR}
          polygonStrokeColor={() => BORDER_COLOR}
          polygonAltitude={0.006}
          polygonsTransitionDuration={0}
          hexBinPointsData={heatPoints}
          hexBinPointLat={(d: object) => (d as HeatPoint).lat}
          hexBinPointLng={(d: object) => (d as HeatPoint).lng}
          hexBinPointWeight={(d: object) => (d as HeatPoint).weight}
          hexBinResolution={resolution}
          hexBinMerge={false}
          hexMargin={0.08}
          hexAltitude={(d: object) => 0.02 + binIntensity(d as HexBin) * 0.16}
          hexTopColor={(d: object) => heatColor(binIntensity(d as HexBin))}
          hexSideColor={(d: object) => heatColor(binIntensity(d as HexBin), 0.6)}
          hexLabel={(d: object) =>
            `Intensity: ${Math.round(binIntensity(d as HexBin) * 100)}%`
          }
          onZoom={(pov: { altitude: number }) =>
            setResolution(altitudeToResolution(pov.altitude))
          }
        />
      )}
    </div>
  )
}
