import { useEffect, useMemo, useState } from "react"
import { Globe } from "@/components/Globe"
import { FacilityPanel } from "@/components/FacilityPanel"
import {
  FACILITY_TYPE_COLOR,
  FACILITY_TYPE_LABEL,
  FACILITY_TYPE_ORDER,
  VERDICT_COLOR,
  VERDICT_LABEL,
  VERDICT_ORDER,
  type CapabilityItem,
  type FacilityLocation,
  type RegionResult,
} from "@/lib/api"
import {
  fetchCapabilities,
  fetchFacilityLocations,
  fetchRegions,
  USE_API,
} from "@/lib/dataSource"

type Tab = "coverage" | "facilities"

function App() {
  const [tab, setTab] = useState<Tab>("coverage")
  const [capabilities, setCapabilities] = useState<CapabilityItem[]>([])
  const [capability, setCapability] = useState<string>("")
  const [regions, setRegions] = useState<RegionResult[]>([])
  const [facilities, setFacilities] = useState<FacilityLocation[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [panelOpen, setPanelOpen] = useState(false)
  const [selectedState, setSelectedState] = useState("")
  const [districtFilter, setDistrictFilter] = useState("")

  // Load the capability catalog once.
  useEffect(() => {
    fetchCapabilities()
      .then((caps) => {
        setCapabilities(caps)
        if (caps[0]) setCapability(caps[0].id)
      })
      .catch((e) => console.error("capabilities load failed", e))
  }, [])

  // Load regions whenever the capability changes.
  useEffect(() => {
    if (!capability) return
    let cancelled = false
    setLoading(true)
    fetchRegions(capability)
      .then((r) => !cancelled && setRegions(r))
      .catch((e) => console.error("regions load failed", e))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [capability])

  // Load facility locations once, the first time the tab opens (~1 MB live).
  useEffect(() => {
    if (tab !== "facilities" || facilities !== null) return
    let cancelled = false
    setLoading(true)
    fetchFacilityLocations()
      .then((f) => !cancelled && setFacilities(f))
      .catch((e) => console.error("facility locations load failed", e))
      // Unconditional: setting `facilities` re-runs this effect, whose cleanup
      // flips `cancelled` before this finally fires — gating would strand the
      // header in "loading…".
      .finally(() => setLoading(false))
    return () => {
      cancelled = true
    }
  }, [tab, facilities])

  const activeLabel =
    capabilities.find((c) => c.id === capability)?.label ?? capability

  // Distinct states present in the current rollup, for the panel's filter.
  const states = useMemo(
    () => Array.from(new Set(regions.map((r) => r.state))).sort(),
    [regions],
  )

  const openStatePanel = (state: string) => {
    setSelectedState(state)
    setDistrictFilter("")
    setPanelOpen(true)
  }

  const typeCounts = new Map<string, number>()
  for (const f of facilities ?? []) {
    typeCounts.set(f.facility_type, (typeCounts.get(f.facility_type) ?? 0) + 1)
  }

  const tabClass = (t: Tab) =>
    `rounded-md px-3 py-1.5 text-sm transition-colors ${
      tab === t
        ? "bg-slate-800 text-slate-100"
        : "text-slate-400 hover:text-slate-200"
    }`

  return (
    <div className="flex min-h-svh flex-col bg-slate-950 text-slate-100">
      <header className="flex items-center justify-between border-b border-white/10 px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Medical Desert Planner</h1>
          <p className="text-sm text-slate-400">
            Trust-weighted healthcare coverage across India ·{" "}
            <span className={USE_API ? "text-emerald-400" : "text-amber-400"}>
              {USE_API ? "live API" : "dummy data"}
            </span>
            {loading && <span className="ml-2 text-slate-500">loading…</span>}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <nav className="flex gap-1 rounded-lg border border-white/10 bg-slate-900 p-1">
            <button className={tabClass("coverage")} onClick={() => setTab("coverage")}>
              Coverage
            </button>
            <button className={tabClass("facilities")} onClick={() => setTab("facilities")}>
              Facilities
            </button>
          </nav>
          {tab === "coverage" && (
            <>
              <label className="flex items-center gap-2 text-sm">
                <span className="text-slate-400">Capability</span>
                <select
                  value={capability}
                  onChange={(e) => setCapability(e.target.value)}
                  className="rounded-md border border-white/15 bg-slate-900 px-3 py-1.5 text-sm text-slate-100 outline-none focus:border-blue-400"
                >
                  {capabilities.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </label>
              <button
                onClick={() => setPanelOpen((o) => !o)}
                className="rounded-md border border-white/15 bg-slate-900 px-3 py-1.5 text-sm text-slate-100 hover:border-blue-400 hover:bg-slate-800"
              >
                Receipts
              </button>
            </>
          )}
        </div>
      </header>

      <main className="relative flex-1 overflow-hidden bg-slate-950">
        {tab === "coverage" ? (
          <>
            <Globe capability={activeLabel} regions={regions} onSelectState={openStatePanel} />

            {/* Legend — verdict taxonomy; data desert set apart from real gaps */}
            <div className="pointer-events-none absolute bottom-6 left-6 rounded-lg border border-white/10 bg-slate-900/70 p-4 backdrop-blur">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                Region verdict
              </p>
              <ul className="space-y-1.5">
                {VERDICT_ORDER.map((v) => (
                  <li key={v} className="flex items-center gap-2 text-sm">
                    <span
                      className="inline-block h-3 w-3 rounded-full"
                      style={{ backgroundColor: VERDICT_COLOR[v] }}
                    />
                    <span className="text-slate-200">{VERDICT_LABEL[v]}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-3 max-w-[16rem] text-xs text-slate-400">
                Hover a state for its evidence. A <b>data desert</b> means too few
                records to judge — not a proven gap.
              </p>
            </div>

            <FacilityPanel
              open={panelOpen}
              capability={capability}
              capabilityLabel={activeLabel}
              state={selectedState}
              district={districtFilter}
              states={states}
              onStateChange={setSelectedState}
              onDistrictChange={setDistrictFilter}
              onClose={() => setPanelOpen(false)}
            />
          </>
        ) : (
          <>
            <Globe capability={activeLabel} regions={regions} facilities={facilities ?? []} />

            {/* Legend — facility types with live counts */}
            <div className="pointer-events-none absolute bottom-6 left-6 rounded-lg border border-white/10 bg-slate-900/70 p-4 backdrop-blur">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                Facility type
              </p>
              <ul className="space-y-1.5">
                {FACILITY_TYPE_ORDER.filter((t) => (typeCounts.get(t) ?? 0) > 0).map((t) => (
                  <li key={t} className="flex items-center gap-2 text-sm">
                    <span
                      className="inline-block h-3 w-3 rounded-full"
                      style={{ backgroundColor: FACILITY_TYPE_COLOR[t] }}
                    />
                    <span className="text-slate-200">{FACILITY_TYPE_LABEL[t]}</span>
                    <span className="text-slate-500">{typeCounts.get(t)}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-3 max-w-[16rem] text-xs text-slate-400">
                {facilities === null
                  ? "Loading facility locations…"
                  : facilities.length === 0
                    ? "No facility locations yet — run the materialization pipeline."
                    : `${facilities.length.toLocaleString()} geolocated facilities. Hover a dot for details.`}
              </p>
            </div>
          </>
        )}
      </main>
    </div>
  )
}

export default App
