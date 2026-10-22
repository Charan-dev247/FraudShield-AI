import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import ImpactBars from "../components/ImpactBars";
import ScoreRuler from "../components/ScoreRuler";
import { Button, Card, ErrorBox, RiskBadge, Spinner } from "../components/ui";
import { api, type BatchResult, type Prediction, type Sample } from "../lib/api";
import { pct, prob } from "../lib/format";
import { useApi } from "../lib/useApi";

const V = Array.from({ length: 28 }, (_, i) => `V${i + 1}`);
const COLUMNS = ["Time", ...V, "Amount"];
const blank = () => Object.fromEntries(COLUMNS.map((c) => [c, "0"])) as Record<string, string>;

export default function Check() {
  const { data: samples } = useApi<Sample[]>("/api/v1/samples");
  const [form, setForm] = useState<Record<string, string>>(blank());
  const [result, setResult] = useState<Prediction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [paste, setPaste] = useState("");

  const invalid = useMemo(() => COLUMNS.filter((c) => form[c].trim() === "" || Number.isNaN(Number(form[c]))), [form]);
  const negative = Number(form.Amount) < 0 || Number(form.Time) < 0;

  const load = (values: Record<string, number>) =>
    setForm(Object.fromEntries(COLUMNS.map((c) => [c, String(values[c] ?? 0)])));

  const applyPaste = () => {
    try {
      const obj = JSON.parse(paste);
      const miss = COLUMNS.filter((c) => typeof obj[c] !== "number");
      if (miss.length) throw new Error(`Missing numeric fields: ${miss.slice(0, 5).join(", ")}${miss.length > 5 ? "…" : ""}`);
      load(obj); setError(null);
    } catch (e) { setError((e as Error).message); }
  };

  const submit = async () => {
    setBusy(true); setError(null);
    try {
      const body = Object.fromEntries(COLUMNS.map((c) => [c, Number(form[c])]));
      setResult(await api.post<Prediction>("/api/v1/predict", body));
    } catch (e) { setError((e as Error).message); setResult(null); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Check a transaction</h1>
      <div className="grid gap-6 xl:grid-cols-[1fr_26rem]">
        <Card title="Transaction inputs">
          <p className="mb-3 text-sm text-ink-muted">
            This dataset has no merchant or location fields. Inputs are the original anonymised columns: Time, V1–V28 and Amount.
          </p>
          {!!samples?.length && (
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <span className="text-sm text-ink-muted">Load a synthetic sample:</span>
              {samples.map((s) => <Button key={s.name} variant="ghost" className="!py-1 !text-xs" onClick={() => load(s.values)}>{s.name}</Button>)}
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            {["Time", "Amount"].map((c) => (
              <label key={c} className="text-sm">
                <span className="mb-1 block font-medium">{c === "Time" ? "Time (seconds since first transaction)" : "Amount"}</span>
                <input className="w-full" inputMode="decimal" value={form[c]} onChange={(e) => setForm({ ...form, [c]: e.target.value })} />
              </label>
            ))}
          </div>
          <details className="mt-4">
            <summary className="cursor-pointer text-sm font-medium">PCA components V1–V28</summary>
            <div className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-4 lg:grid-cols-7">
              {V.map((c) => (
                <label key={c} className="text-xs text-ink-muted">{c}
                  <input aria-label={c} className="mt-0.5 w-full !px-2 !py-1 text-ink" value={form[c]} onChange={(e) => setForm({ ...form, [c]: e.target.value })} />
                </label>
              ))}
            </div>
            <div className="mt-4">
              <label className="text-sm font-medium" htmlFor="paste">Or paste one transaction as JSON</label>
              <textarea id="paste" rows={3} className="mt-1 w-full font-mono text-xs" value={paste} onChange={(e) => setPaste(e.target.value)} placeholder='{"Time": 0, "V1": -1.36, ..., "Amount": 149.62}' />
              <Button variant="ghost" className="mt-1 !py-1 !text-xs" onClick={applyPaste} disabled={!paste.trim()}>Fill form from JSON</Button>
            </div>
          </details>
          <div className="mt-5 flex items-center gap-3">
            <Button onClick={submit} disabled={busy || invalid.length > 0 || negative}>{busy ? "Scoring…" : "Score transaction"}</Button>
            {invalid.length > 0 && <span className="text-sm text-alarm">Enter a number for: {invalid.slice(0, 4).join(", ")}{invalid.length > 4 ? "…" : ""}</span>}
            {negative && <span className="text-sm text-alarm">Time and Amount cannot be negative.</span>}
          </div>
        </Card>

        <Card title="Result">
          {error && <ErrorBox message={error} />}
          {busy && <Spinner label="Scoring" />}
          {!busy && !result && !error && <p className="text-sm text-ink-muted">Score a transaction to see its fraud probability and what drove it.</p>}
          {result && !busy && (
            <div className="space-y-5">
              <ScoreRuler p={result.probability} threshold={result.threshold} />
              <div className="flex flex-wrap items-center gap-3 text-sm">
                <RiskBadge risk={result.risk_level} />
                <span>{result.flagged ? "Flagged for review" : "Below the alert threshold"}</span>
                <Link className="text-tide underline" to={`/investigations?id=${result.id}`}>Open case #{result.id}</Link>
              </div>
              <div className="text-xs text-ink-muted">Model {result.model_version} · {result.latency_ms.toFixed(1)} ms</div>
              <ImpactBars items={result.explanation} />
            </div>
          )}
        </Card>
      </div>
      <BatchUpload />
    </div>
  );
}

function BatchUpload() {
  const [res, setRes] = useState<BatchResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onFile = async (f: File | undefined) => {
    if (!f) return;
    setBusy(true); setErr(null); setRes(null);
    try { setRes(await api.upload<BatchResult>("/api/v1/predict/batch", f)); }
    catch (e) { setErr((e as Error).message); }
    finally { setBusy(false); }
  };

  return (
    <Card title="Score a CSV">
      <p className="text-sm text-ink-muted">Columns required: Time, V1–V28, Amount (an optional Class column is ignored). Up to 5 MB and 5,000 rows.</p>
      <input type="file" accept=".csv" className="mt-3 block text-sm" aria-label="CSV file" onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = ""; }} />
      {busy && <Spinner label="Scoring file" />}
      {err && <div className="mt-3"><ErrorBox message={err} /></div>}
      {res && (
        <div className="mt-4">
          <p className="text-sm"><strong>{res.rows.toLocaleString()}</strong> rows scored, <strong className="text-alarm">{res.flagged}</strong> flagged ({pct(res.flagged_rate, 2)}).{" "}
            <Link className="text-tide underline" to="/investigations">Review them</Link></p>
          <table className="mt-3 w-full text-left text-sm">
            <thead className="text-ink-muted"><tr><th className="py-1 font-medium">Case</th><th className="font-medium">Probability</th><th className="font-medium">Risk</th></tr></thead>
            <tbody>{res.top.slice(0, 8).map((t) => (
              <tr key={t.id} className="border-t border-fog-line"><td className="py-1.5">#{t.id}</td><td className="tabular-nums">{prob(t.probability)}</td><td><RiskBadge risk={t.risk_level} /></td></tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
