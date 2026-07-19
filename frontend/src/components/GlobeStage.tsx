import { useCallback, useEffect, useRef, useState } from "react"
import type { GlobeMethods } from "react-globe.gl"
import { Globe } from "@/components/Globe"
import type { RegionResult } from "@/lib/api"

const SLIDE_MS = 600 // slide transition duration each way
const MIN_HIDDEN_MS = 650 // floor so the down-and-up gesture always completes
const ZOOM_MS = 450 // camera zoom transition duration each way
const BASE_ALTITUDE = 1.6 // must match Globe's initial pointOfView altitude
const ZOOM_EPSILON = 0.05 // altitudes within this of base count as "not zoomed in"

// Wraps the globe and slides it out the bottom of the viewport while data is
// loading, then eases it back up once real regions land — so the grey region
// re-paint mid-fetch is never seen.
//
// The plain CSS slide only looks right when the globe reads as a sphere in
// space. When the user has zoomed in far enough to fill the frame, sliding the
// canvas just moves a flat rectangle. So if we detect a zoomed-in camera, we
// first ease the camera back to base zoom (an honest 3D move), run the slide,
// then restore the user's zoom on the way back.
export function GlobeStage({
  loading,
  capability,
  regions,
  onSelectState,
}: {
  loading: boolean
  capability: string
  regions: RegionResult[]
  onSelectState?: (state: string) => void
}) {
  // Globe starts off-screen and rises when the first data arrives; every
  // subsequent capability switch drops it away and brings it back.
  const [hidden, setHidden] = useState(true)
  const globeApi = useRef<GlobeMethods | undefined>(undefined)
  const hideStart = useRef<number | null>(null)
  const savedAltitude = useRef<number | null>(null) // set when we zoomed out for the slide
  const gen = useRef(0) // bumped per capability change; stale timers self-cancel

  const handleReady = useCallback((g: GlobeMethods) => {
    globeApi.current = g
  }, [])

  // Hide choreography: optionally normalize zoom, then drop the globe. Keyed off
  // the capability change (not `loading`): with fast dummy data the fetch can
  // resolve before `loading` ever commits as true, but the capability always
  // changes.
  useEffect(() => {
    if (!capability) return // nothing selected yet; stay off-screen
    const myGen = ++gen.current
    const api = globeApi.current
    const pov = api?.pointOfView()
    const zoomedIn = !!pov && pov.altitude < BASE_ALTITUDE - ZOOM_EPSILON

    const dropGlobe = () => {
      if (myGen !== gen.current) return // superseded by a newer switch
      hideStart.current = performance.now()
      setHidden(true)
    }

    if (api && pov && zoomedIn) {
      // Ease back to base zoom first so the slide reads as a sphere in space;
      // remember where to return to on reveal.
      savedAltitude.current = pov.altitude
      api.pointOfView({ lat: pov.lat, lng: pov.lng, altitude: BASE_ALTITUDE }, ZOOM_MS)
      setTimeout(dropGlobe, ZOOM_MS)
    } else {
      savedAltitude.current = null
      dropGlobe()
    }
  }, [capability])

  // Reveal once data has landed and the globe is fully hidden, never before the
  // min-hidden floor. Restores the user's zoom after the slide completes.
  useEffect(() => {
    if (!capability || loading || !hidden || hideStart.current == null) return
    const myGen = gen.current
    const elapsed = performance.now() - hideStart.current
    const wait = Math.max(0, MIN_HIDDEN_MS - elapsed)

    const timer = setTimeout(() => {
      if (myGen !== gen.current) return
      setHidden(false) // slide back up
      const target = savedAltitude.current
      savedAltitude.current = null
      if (target == null) return
      // After the slide settles, zoom back to where the user was.
      setTimeout(() => {
        if (myGen !== gen.current) return
        const api = globeApi.current
        const pov = api?.pointOfView()
        if (api && pov) api.pointOfView({ lat: pov.lat, lng: pov.lng, altitude: target }, ZOOM_MS)
      }, SLIDE_MS)
    }, wait)

    return () => clearTimeout(timer)
  }, [capability, loading, hidden])

  return (
    <div
      className="absolute inset-0"
      style={{
        // While off-screen/animating we apply a transform (and its will-change
        // hint); at rest we drop both to `none`/`auto`. This matters because a
        // non-none transform or will-change:transform creates a stacking
        // context that would trap the globe's hover preview (.float-tooltip-kap)
        // beneath the sibling verdict legend. At rest there's no context, so the
        // preview escapes into the page layer and its z-index (see index.css)
        // can lift it in front of the legend.
        transform: hidden ? "translateY(110%)" : undefined,
        willChange: hidden ? "transform" : undefined,
        // Expo-out both ways: launch fast, decelerate. Going down this clears
        // the globe off-screen immediately (so a slow production fetch never
        // shows through the top); the decel tail happens off-screen. Coming
        // back up it reads as a settle into place.
        transition: `transform ${SLIDE_MS}ms cubic-bezier(0.16, 1, 0.3, 1)`,
      }}
    >
      <Globe
        capability={capability}
        regions={regions}
        onSelectState={onSelectState}
        onReady={handleReady}
      />
    </div>
  )
}
