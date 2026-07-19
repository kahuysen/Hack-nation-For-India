import { useState } from "react"
import { Globe } from "@/components/Globe"
import { STATUS_COLOR, STATUS_LABEL, type RegionStatus } from "@/lib/dummyRegions"

const CAPABILITIES = ["ICU", "NICU", "Emergency care", "Maternity", "Oncology", "Trauma center"]

const LEGEND_ORDER: RegionStatus[] = [
  "medical-desert",
  "claimed-unverified",
  "data-desert",
  "served",
]

function App() {
  const [capability, setCapability] = useState(CAPABILITIES[0])

  return (
    <div className="flex min-h-svh flex-col bg-slate-950 text-slate-100">
      <header className="flex items-center justify-between border-b border-white/10 px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Medical Desert Planner</h1>
          <p className="text-sm text-slate-400">
            Trust-weighted healthcare coverage across India ·{" "}
            <span className="text-amber-400">dummy data</span>
          </p>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <span className="text-slate-400">Capability</span>
          <select
            value={capability}
            onChange={(e) => setCapability(e.target.value)}
            className="rounded-md border border-white/15 bg-slate-900 px-3 py-1.5 text-sm text-slate-100 outline-none focus:border-blue-400"
          >
            {CAPABILITIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
      </header>

      <main className="relative flex-1 overflow-hidden bg-slate-950">
        <Globe capability={capability} />

        {/* Legend — the honest data-desert vs medical-desert distinction */}
        <div className="pointer-events-none absolute bottom-6 left-6 rounded-lg border border-white/10 bg-slate-900/70 p-4 backdrop-blur">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Region status
          </p>
          <ul className="space-y-1.5">
            {LEGEND_ORDER.map((s) => (
              <li key={s} className="flex items-center gap-2 text-sm">
                <span
                  className="inline-block h-3 w-3 rounded-full"
                  style={{ backgroundColor: STATUS_COLOR[s] }}
                />
                <span className="text-slate-200">{STATUS_LABEL[s]}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 max-w-[15rem] text-xs text-slate-400">
            Hover a region for its evidence. Grey = no rollup for this capability.
          </p>
        </div>
      </main>
    </div>
  )
}

export default App
