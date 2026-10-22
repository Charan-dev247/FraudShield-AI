import type { Impact } from "../lib/api";

const label = (f: string) => (f === "Amount" ? "Amount" : f === "Time" ? "Time of day" : f);

/** Diverging bars: right (red) pushed the score up vs a typical transaction, left (green) pulled it down. */
export default function ImpactBars({ items }: { items: Impact[] }) {
  const max = Math.max(...items.map((i) => Math.abs(i.impact)), 1e-9);
  return (
    <div>
      <ul className="space-y-1.5">
        {items.map((i) => {
          const w = (Math.abs(i.impact) / max) * 50;
          const up = i.impact > 0;
          return (
            <li key={i.feature} className="grid grid-cols-[4.5rem_1fr_4.5rem] items-center gap-2 text-sm">
              <span className="font-medium">{label(i.feature)}</span>
              <div className="relative h-4">
                <div className="absolute inset-y-0 left-1/2 w-px bg-fog-line" />
                <div className={`absolute inset-y-0.5 rounded-sm ${up ? "bg-alarm" : "bg-safe"}`}
                  style={up ? { left: "50%", width: `${w}%` } : { right: "50%", width: `${w}%` }} />
              </div>
              <span className={`text-right text-xs tabular-nums ${up ? "text-alarm" : "text-safe"}`}>
                {up ? "+" : ""}{(i.impact * 100).toFixed(2)} pts
              </span>
            </li>
          );
        })}
      </ul>
      <p className="mt-3 text-xs text-ink-muted">
        How much the fraud probability changes when that one input is replaced with a typical (median) value.
        V1–V28 are anonymised PCA components, so they have no plain-language meaning.
      </p>
    </div>
  );
}
