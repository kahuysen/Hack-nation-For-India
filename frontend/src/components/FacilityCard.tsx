import { type FacilityEvidence } from "@/lib/api"
import { cn } from "@/lib/utils"

// Parse the loose `source_urls` string into individual http(s) links.
function parseUrls(raw: string | null): string[] {
  if (!raw) return []
  return raw
    .split(/[\s,;]+/)
    .map((s) => s.trim())
    .filter((s) => /^https?:\/\//i.test(s))
}

function pct(v: number): string {
  return `${Math.round(Math.max(0, Math.min(1, v)) * 100)}%`
}

// A 0..1 value as a labelled bar — makes trust legible at a glance.
function Meter({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div>
      <div className="mb-0.5 flex justify-between text-[11px] text-neutral-400">
        <span>{label}</span>
        <span className="tabular-nums text-neutral-300">{pct(value)}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
        <div className={cn("h-full rounded-full", tone)} style={{ width: pct(value) }} />
      </div>
    </div>
  )
}

// Monochrome tier badges — kept distinguishable by brightness, not hue.
const TIER_STYLE: Record<string, string> = {
  government: "border-white/30 bg-white/15 text-neutral-100",
  private: "border-white/20 bg-white/10 text-neutral-300",
  trust: "border-white/10 bg-white/5 text-neutral-400",
}

export function FacilityCard({ f }: { f: FacilityEvidence }) {
  const urls = parseUrls(f.source_urls)
  const tierStyle = TIER_STYLE[f.tier?.toLowerCase()] ?? "border-white/15 bg-white/5 text-neutral-300"

  return (
    <article className="rounded-lg border border-white/10 bg-neutral-900/60 p-3.5">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-neutral-100">{f.name}</h3>
          <p className="mt-0.5 text-xs text-neutral-400">
            {f.district} · {f.state}
            {f.pin ? ` · ${f.pin}` : ""}
          </p>
        </div>
        <span
          className={cn(
            "shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide",
            tierStyle,
          )}
        >
          {f.tier || "unknown"}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2">
        <Meter label="Source trust" value={f.source_trust} tone="bg-neutral-100" />
        <Meter label="Knowledge" value={f.knowledge} tone="bg-neutral-400" />
      </div>

      <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-neutral-400">
        <span>
          <b className="text-neutral-200">{f.n_corroborating}</b> corroborating
          {f.claiming ? ` · ${f.claiming} claiming` : ""}
        </span>
        <span>
          confidence: <span className="text-neutral-200">{f.data_confidence}</span>
        </span>
        <span>
          weight: <span className="tabular-nums text-neutral-200">{f.trust_weight.toFixed(2)}</span>
        </span>
      </div>

      {f.evidence.length > 0 && (
        <div className="mt-3 border-t border-white/10 pt-2.5">
          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-neutral-500">
            Evidence
          </p>
          <ul className="space-y-1.5">
            {f.evidence.map((e, i) => (
              <li key={`${e.field}-${i}`} className="text-xs text-neutral-300">
                <span className="text-neutral-500">{e.field}:</span> {e.snippet}
              </li>
            ))}
          </ul>
        </div>
      )}

      {f.description && <p className="mt-2.5 text-xs text-neutral-400">{f.description}</p>}

      {urls.length > 0 && (
        <div className="mt-2.5 flex flex-wrap gap-2">
          {urls.map((u) => (
            <a
              key={u}
              href={u}
              target="_blank"
              rel="noreferrer"
              className="max-w-full truncate text-[11px] text-neutral-300 underline decoration-neutral-400/40 hover:text-neutral-100"
            >
              {u.replace(/^https?:\/\//i, "")}
            </a>
          ))}
        </div>
      )}
    </article>
  )
}
