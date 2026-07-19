import { useEffect, useState } from "react"
import { Globe } from "@/components/Globe"
import { VERDICT_COLOR, VERDICT_LABEL, VERDICT_ORDER, type CapabilityItem, type RegionResult } from "@/lib/api"
import { fetchCapabilities, fetchRegions, USE_API } from "@/lib/dataSource"

function App() {
  const [capabilities, setCapabilities] = useState<CapabilityItem[]>([])
  const [capability, setCapability] = useState<string>("")
  const [regions, setRegions] = useState<RegionResult[]>([])
  const [loading, setLoading] = useState(false)

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
      </header>

      <main className="relative flex-1 overflow-hidden bg-slate-950">
        <Globe capability={activeLabel} regions={regions} />

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
      </main>
    </div>
  )
}

export default App
