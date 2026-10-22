import { pct, prob } from "../lib/format";

/**
 * The signature element: a probability ruler on a square-root scale (so the low end,
 * where fraud scores live, isn't squashed) with the alert threshold marked.
 */
export default function ScoreRuler({ p, threshold }: { p: number; threshold: number }) {
  const pos = (x: number) => `${Math.sqrt(Math.min(Math.max(x, 0), 1)) * 100}%`;
  const half = threshold * 0.5;
  const flagged = p >= threshold;
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className={`text-4xl font-semibold tabular-nums ${flagged ? "text-alarm" : "text-ink"}`}>{prob(p)}</span>
        <span className="text-sm text-ink-muted">fraud probability</span>
      </div>
      <div className="relative mt-4 h-3 rounded-full" style={{
        background: `linear-gradient(to right, #DDEFE6 0 ${pos(half)}, #F8EBCB ${pos(half)} ${pos(threshold)}, #FBE4DF ${pos(threshold)} 100%)`,
      }}>
        <div className="absolute -top-1 h-5 w-0.5 bg-ink" style={{ left: pos(threshold) }} />
        <div className={`absolute -top-1.5 h-6 w-3 -translate-x-1/2 rounded-sm border-2 border-white ${flagged ? "bg-alarm" : "bg-tide"}`} style={{ left: pos(p) }} />
      </div>
      <div className="relative mt-2 h-4 text-xs text-ink-muted">
        <span className="absolute left-0">0%</span>
        <span className="absolute -translate-x-1/2" style={{ left: pos(threshold) }}>alert at {pct(threshold, 1)}</span>
        <span className="absolute right-0">100%</span>
      </div>
    </div>
  );
}
