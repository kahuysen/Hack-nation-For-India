import { useEffect, useState } from "react"
import { type FacilityEvidence } from "@/lib/api"
import { fetchFacilities } from "@/lib/dataSource"
import { FacilityCard } from "./FacilityCard"

type Props = {
  open: boolean
  capability: string
  capabilityLabel: string
  state: string
  district: string
  states: string[]
  onStateChange: (state: string) => void
  onDistrictChange: (district: string) => void
  onClose: () => void
}

export function FacilityPanel({
  open,
  capability,
  capabilityLabel,
  state,
  district,
  states,
  onStateChange,
  onDistrictChange,
  onClose,
}: Props) {
  const [facilities, setFacilities] = useState<FacilityEvidence[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Close on Escape while open.
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose()
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [open, onClose])

  // Fetch whenever the query changes (only while open, and once a state is chosen).
  useEffect(() => {
    if (!open || !capability || !state) {
      setFacilities([])
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchFacilities(capability, { state, district: district || undefined })
      .then((f) => !cancelled && setFacilities(f))
      .catch((e) => {
        if (!cancelled) {
          console.error("facilities load failed", e)
          setError("Could not load facilities. Try again.")
        }
      })
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [open, capability, state, district])

  // Districts available for the current state, from the loaded facilities.
  const districts = Array.from(new Set(facilities.map((f) => f.district))).sort()

  return (
    <aside
      className={`absolute inset-y-0 right-0 z-20 flex w-[380px] max-w-[90vw] flex-col border-l border-white/10 bg-neutral-950/95 shadow-2xl backdrop-blur transition-transform duration-200 ${
        open ? "translate-x-0" : "pointer-events-none translate-x-full"
      }`}
      aria-hidden={!open}
    >
      <header className="flex items-start justify-between gap-2 border-b border-white/10 px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-neutral-100">Facility receipts</h2>
          <p className="text-xs text-neutral-400">
            Evidence behind <span className="text-neutral-200">{capabilityLabel}</span> coverage
          </p>
        </div>
        <button
          onClick={onClose}
          aria-label="Close panel"
          className="rounded-md p-1 text-neutral-400 hover:bg-white/10 hover:text-neutral-100"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6 6 18M6 6l12 12" strokeLinecap="round" />
          </svg>
        </button>
      </header>

      <div className="flex gap-2 border-b border-white/10 px-4 py-3">
        <label className="flex-1 text-xs">
          <span className="mb-1 block text-neutral-500">State</span>
          <select
            value={state}
            onChange={(e) => {
              onStateChange(e.target.value)
              onDistrictChange("")
            }}
            className="w-full rounded-md border border-white/15 bg-neutral-900 px-2 py-1.5 text-sm text-neutral-100 outline-none focus:border-neutral-400"
          >
            <option value="">Select a state…</option>
            {states.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="flex-1 text-xs">
          <span className="mb-1 block text-neutral-500">District</span>
          <select
            value={district}
            onChange={(e) => onDistrictChange(e.target.value)}
            disabled={!state || districts.length === 0}
            className="w-full rounded-md border border-white/15 bg-neutral-900 px-2 py-1.5 text-sm text-neutral-100 outline-none focus:border-neutral-400 disabled:opacity-50"
          >
            <option value="">All districts</option>
            {districts.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {!state && (
          <p className="mt-8 text-center text-sm text-neutral-500">
            Pick a state above, or click one on the map, to see the facilities behind its verdict.
          </p>
        )}
        {state && loading && <p className="mt-8 text-center text-sm text-neutral-500">Loading facilities…</p>}
        {state && !loading && error && <p className="mt-8 text-center text-sm text-neutral-300">{error}</p>}
        {state && !loading && !error && facilities.length === 0 && (
          <p className="mt-8 text-center text-sm text-neutral-500">
            No facility evidence for {state}
            {district ? ` · ${district}` : ""} under {capabilityLabel}.
          </p>
        )}
        {state &&
          !loading &&
          !error &&
          facilities.map((f) => <FacilityCard key={f.facility_id} f={f} />)}
      </div>
    </aside>
  )
}
