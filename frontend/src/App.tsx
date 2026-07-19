import { useEffect, useMemo, useState } from "react"
import { GlobeStage } from "@/components/GlobeStage"
import { FacilityPanel } from "@/components/FacilityPanel"
import {
  VERDICT_COLOR,
  VERDICT_LABEL,
  VERDICT_ORDER,
  type CapabilityItem,
  type RegionResult,
} from "@/lib/api"
import { fetchCapabilities, fetchRegions, USE_API } from "@/lib/dataSource"
import { canonicalStateOptions } from "@/lib/states"

function App() {
  const [capabilities, setCapabilities] = useState<CapabilityItem[]>([])
  const [capability, setCapability] = useState<string>("")
  const [regions, setRegions] = useState<RegionResult[]>([])
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

  const activeLabel =
    capabilities.find((c) => c.id === capability)?.label ?? capability

  // Distinct states present in the current rollup, for the panel's filter.
  const states = useMemo(
    () => canonicalStateOptions(regions.map((r) => r.state)),
    [regions],
  )

  const openStatePanel = (state: string) => {
    setSelectedState(state)
    setDistrictFilter("")
    setPanelOpen(true)
  }

  return (
    <div className="flex min-h-svh flex-col bg-neutral-950 text-neutral-100">
      <header className="flex items-center justify-between border-b border-white/10 px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Medical Desert Planner</h1>
          <p className="text-sm text-neutral-400">
            Trust-weighted healthcare coverage across India ·{" "}
            <span className={USE_API ? "text-neutral-100" : "text-neutral-500"}>
              {USE_API ? "live API" : "dummy data"}
            </span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm">
            <span className="text-neutral-400">Capability</span>
            <select
              value={capability}
              onChange={(e) => setCapability(e.target.value)}
              className="rounded-md border border-white/15 bg-neutral-900 px-3 py-1.5 text-sm text-neutral-100 outline-none focus:border-neutral-400"
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
            className="rounded-md border border-white/15 bg-neutral-900 px-3 py-1.5 text-sm text-neutral-100 hover:border-neutral-400 hover:bg-neutral-800"
          >
            Receipts
          </button>
        </div>
      </header>

      <main className="relative flex-1 overflow-hidden bg-neutral-950">
        <GlobeStage
          loading={loading}
          capability={activeLabel}
          regions={regions}
          onSelectState={openStatePanel}
        />

        {/* Legend — verdict taxonomy; data desert set apart from real gaps */}
        <div className="pointer-events-none absolute bottom-6 left-6 rounded-lg border border-white/10 bg-neutral-900/70 p-4 backdrop-blur">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-400">
            Region verdict
          </p>
          <ul className="space-y-1.5">
            {VERDICT_ORDER.map((v) => (
              <li key={v} className="flex items-center gap-2 text-sm">
                <span
                  className="inline-block h-3 w-3 rounded-full"
                  style={{ backgroundColor: VERDICT_COLOR[v] }}
                />
                <span className="text-neutral-200">{VERDICT_LABEL[v]}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 max-w-[16rem] text-xs text-neutral-400">
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
      </main>
    </div>
  )
}

export default App
