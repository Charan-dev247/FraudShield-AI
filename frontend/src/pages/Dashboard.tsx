import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Link } from "react-router-dom";
import { Card, Empty, ErrorBox, Spinner, Stat } from "../components/ui";
import { STATUSES, type Metrics } from "../lib/api";
import { num, pct } from "../lib/format";
import { useApi } from "../lib/useApi";

export default function Dashboard() {
  const { data: m, error, loading, reload } = useApi<Metrics>("/api/v1/metrics");
  if (loading) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!m) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      {m.total === 0 ? (
        <Empty title="No transactions scored yet">
          <Link className="text-tide underline" to="/check">Score a transaction</Link>, upload a CSV, or run
          <code className="mx-1 rounded bg-fog px-1">python -m scripts.seed_demo</code> to load synthetic demo data.
        </Empty>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Stat label="Transactions scored" value={num(m.total)} />
            <Stat label="Flagged for review" value={num(m.flagged)} tone="alarm" hint={`${pct(m.flagged_rate, 2)} of all scored`} />
            <Stat label="Still pending" value={num(m.by_status.Pending)} hint={`${num(m.by_status.Escalated)} escalated`} />
            <Stat label="Alert precision (reviewed)"
              value={m.review_quality.alert_precision === null ? "–" : pct(m.review_quality.alert_precision, 0)}
              hint={m.review_quality.reviewed_alerts ? `${m.review_quality.reviewed_alerts} reviewed alerts` : "Review flagged cases to measure this"} />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card title="Score distribution">
              <div className="h-64">
                <ResponsiveContainer>
                  <BarChart data={m.score_histogram} margin={{ left: -10 }}>
                    <CartesianGrid vertical={false} stroke="#D3DCE0" />
                    <XAxis dataKey="bucket" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="count" name="Transactions" fill="#0B5D6B" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <p className="mt-2 text-xs text-ink-muted">Fraud probability buckets. Most traffic should sit at the far left.</p>
            </Card>

            <Card title="Last 14 days">
              <div className="h-64">
                <ResponsiveContainer>
                  <LineChart data={m.daily} margin={{ left: -10 }}>
                    <CartesianGrid vertical={false} stroke="#D3DCE0" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(d: string) => d.slice(5)} />
                    <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                    <Tooltip />
                    <Line dataKey="total" name="Scored" stroke="#0B5D6B" dot={false} strokeWidth={2} />
                    <Line dataKey="flagged" name="Flagged" stroke="#D9422B" dot={false} strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>

          <Card title="Review queue" aside={<Link to="/investigations" className="text-sm text-tide underline">Open investigations</Link>}>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              {STATUSES.map((s) => (
                <div key={s}><div className="text-2xl font-semibold tabular-nums">{num(m.by_status[s])}</div><div className="text-sm text-ink-muted">{s}</div></div>
              ))}
            </div>
            {m.review_quality.fraud_found_in_unflagged > 0 && (
              <p className="mt-4 text-sm text-alarm">
                {m.review_quality.fraud_found_in_unflagged} confirmed fraud case(s) were below the alert threshold, so the model missed them.
              </p>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
