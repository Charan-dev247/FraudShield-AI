import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend } from "recharts";
import { Card, ErrorBox, Spinner, Stat } from "../components/ui";
import type { ModelInfo, Monitoring } from "../lib/api";
import { num, pct } from "../lib/format";
import { useApi } from "../lib/useApi";

const COLORS = ["#0B5D6B", "#D9422B", "#B7790A"];
const nice = (n: string) => n.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
const ci = (x: [number, number]) => `${pct(x[0], 0)}–${pct(x[1], 0)}`;

export default function Models() {
  const info = useApi<ModelInfo>("/api/v1/models");
  const mon = useApi<Monitoring>("/api/v1/monitoring");
  if (info.loading) return <Spinner />;
  if (info.error) return <ErrorBox message={info.error} onRetry={info.reload} />;
  const m = info.data;
  if (!m) return null;
  const best = m.comparison.find((c) => c.name === m.model_name)!;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Model and monitoring</h1>
        <p className="mt-1 text-sm text-ink-muted">{m.model_version} · trained {new Date(m.trained_at).toLocaleDateString()} · {m.split_strategy}</p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="PR-AUC (test)" value={pct(best.test.average_precision ?? 0, 1)} hint={`95% CI ${ci(best.test_ci_95.average_precision)}`} />
        <Stat label="Precision at alert threshold" value={pct(best.test.precision, 0)} hint={`95% CI ${ci(best.test_ci_95.precision)}`} />
        <Stat label="Recall at alert threshold" value={pct(best.test.recall, 0)} hint={`95% CI ${ci(best.test_ci_95.recall)}`} />
        <Stat label="Single-row latency (p95)" value={`${best.latency_ms.p95.toFixed(0)} ms`} />
      </div>

      <Card title="Model comparison (held-out test period)">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-ink-muted"><tr>
              {["Model", "Val PR-AUC", "Test PR-AUC", "ROC-AUC", "Precision", "Recall", "F1", "False alarms", "Missed fraud", "p50 ms"].map((h) => <th key={h} className="pb-2 pr-4 font-medium">{h}</th>)}
            </tr></thead>
            <tbody>{m.comparison.map((c) => (
              <tr key={c.name} className={`border-t border-fog-line ${c.name === m.model_name ? "bg-tide-wash font-medium" : ""}`}>
                <td className="py-2 pr-4">{nice(c.name)}{c.name === m.model_name && " (deployed)"}</td>
                <td className="pr-4 tabular-nums">{pct(c.validation.average_precision ?? 0)}</td>
                <td className="pr-4 tabular-nums">{pct(c.test.average_precision ?? 0)}</td>
                <td className="pr-4 tabular-nums">{pct(c.test.roc_auc ?? 0)}</td>
                <td className="pr-4 tabular-nums">{pct(c.test.precision, 0)}</td>
                <td className="pr-4 tabular-nums">{pct(c.test.recall, 0)}</td>
                <td className="pr-4 tabular-nums">{c.test.f1.toFixed(2)}</td>
                <td className="pr-4 tabular-nums">{c.test.fp}</td>
                <td className="pr-4 tabular-nums">{c.test.fn}</td>
                <td className="tabular-nums">{c.latency_ms.p50.toFixed(1)}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-ink-muted">
          Chosen by validation PR-AUC ({m.selection_metric}); each model's alert threshold: {m.threshold_rule}. Test set: {num(m.splits.test.rows)} transactions,
          only {m.splits.test.fraud} fraud, so intervals are wide. Treat small differences between models as noise.
        </p>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Precision–recall curves (test)">
          <div className="h-72">
            <ResponsiveContainer>
              <LineChart margin={{ left: -10 }}>
                <CartesianGrid stroke="#D3DCE0" />
                <XAxis type="number" dataKey="recall" domain={[0, 1]} tick={{ fontSize: 11 }} label={{ value: "Recall", position: "insideBottom", offset: -2, fontSize: 11 }} />
                <YAxis type="number" domain={[0, 1]} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => v.toFixed(2)} />
                <Legend />
                {m.comparison.map((c, i) => <Line key={c.name} data={c.pr_curve} dataKey="precision" name={nice(c.name)} stroke={COLORS[i % 3]} dot={false} strokeWidth={2} isAnimationActive={false} />)}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="What the model relies on (permutation importance)">
          <div className="h-72">
            <ResponsiveContainer>
              <BarChart data={m.feature_importance.slice(0, 10)} layout="vertical" margin={{ left: 10 }}>
                <CartesianGrid horizontal={false} stroke="#D3DCE0" />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="feature" tick={{ fontSize: 12 }} width={48} />
                <Tooltip formatter={(v: number) => v.toFixed(4)} />
                <Bar dataKey="importance" name="PR-AUC drop when shuffled" fill="#0B5D6B" radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Simulator info={m} />
      <MonitoringCard mon={mon} />
      <p className="text-xs text-ink-muted">{m.dataset_note}</p>
    </div>
  );
}

function Simulator({ info }: { info: ModelInfo }) {
  const table = info.threshold_table;
  const nearest = (t: number) => table.reduce((a, b) => (Math.abs(b.threshold - t) < Math.abs(a.threshold - t) ? b : a));
  const [thr, setThr] = useState(Math.min(0.99, Math.max(0.01, Number(info.threshold.toFixed(2)))));
  const [costFn, setCostFn] = useState(500);
  const [costFp, setCostFp] = useState(10);
  const row = nearest(thr);
  const cost = row.fn * costFn + row.fp * costFp;
  const best = table.reduce((a, b) => (b.fn * costFn + b.fp * costFp < a.fn * costFn + a.fp * costFp ? b : a));

  return (
    <Card title="Threshold simulator (test set)">
      <label className="block text-sm font-medium">Alert threshold: {pct(row.threshold, 0)}
        <input type="range" min={0.01} max={0.99} step={0.01} value={thr} onChange={(e) => setThr(Number(e.target.value))} className="mt-2 w-full !border-0 !p-0" aria-label="Alert threshold" />
      </label>
      <p className="mt-1 text-xs text-ink-muted">Deployed threshold: {pct(info.threshold, 1)}. Anything scoring at or above the threshold is sent to an analyst.</p>
      <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-5">
        <Stat label="Precision" value={pct(row.precision, 0)} />
        <Stat label="Recall" value={pct(row.recall, 0)} />
        <Stat label="False alarms" value={num(row.fp)} />
        <Stat label="Missed fraud" value={num(row.fn)} tone={row.fn ? "alarm" : "safe"} />
        <Stat label="Alerts raised" value={num(row.tp + row.fp)} />
      </div>
      <div className="mt-5 flex flex-wrap items-end gap-4 text-sm">
        <label>Cost of a missed fraud ($)<input className="mt-1 block w-28" type="number" min={0} value={costFn} onChange={(e) => setCostFn(Math.max(0, Number(e.target.value)))} /></label>
        <label>Cost of a false alarm ($)<input className="mt-1 block w-28" type="number" min={0} value={costFp} onChange={(e) => setCostFp(Math.max(0, Number(e.target.value)))} /></label>
        <div>Total cost here: <strong className="tabular-nums">${num(cost)}</strong>
          <div className="text-xs text-ink-muted">Cheapest threshold for these costs: {pct(best.threshold, 0)} (${num(best.fn * costFn + best.fp * costFp)})</div></div>
      </div>
    </Card>
  );
}

function MonitoringCard({ mon }: { mon: ReturnType<typeof useApi<Monitoring>> }) {
  const d = mon.data;
  return (
    <Card title="Live monitoring" aside={d && <span className={`text-xs font-medium ${d.drift_status === "warning" ? "text-alarm" : "text-ink-muted"}`}>Drift: {d.drift_status}</span>}>
      {mon.loading && <Spinner />}
      {mon.error && <ErrorBox message={mon.error} onRetry={mon.reload} />}
      {d && (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Stat label="Scored, last 24 h" value={num(d.volume_24h)} hint={`${num(d.volume_7d)} in 7 days`} />
            <Stat label="Latency avg / p95" value={`${d.latency_ms.avg.toFixed(1)} / ${d.latency_ms.p95.toFixed(1)} ms`} />
            <Stat label="API errors (since restart)" value={d.api_errors_since_restart} tone={d.api_errors_since_restart ? "alarm" : undefined} />
            <Stat label="Mean score (recent)" value={pct(d.score_mean, 2)} />
          </div>
          {d.drift.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold">Largest input shifts vs training</h3>
              <div className="mt-2 h-48">
                <ResponsiveContainer>
                  <BarChart data={d.drift} margin={{ left: -10 }}>
                    <CartesianGrid vertical={false} stroke="#D3DCE0" />
                    <XAxis dataKey="feature" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v: number) => `${v.toFixed(2)} SD`} />
                    <Bar dataKey="shift_std" name="Shift (training SD)" fill="#B7790A" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <p className="mt-1 text-xs text-ink-muted">{d.drift_note}</p>
            </div>
          )}
          {d.drift.length === 0 && <p className="text-sm text-ink-muted">Drift is shown once 100+ transactions have been scored. {d.sample_size} so far.</p>}
          <p className="text-xs text-ink-muted">Live precision and recall need verified labels. Reviewed alert precision appears on the Dashboard as analysts close cases.</p>
        </div>
      )}
    </Card>
  );
}
