import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import ImpactBars from "../components/ImpactBars";
import ScoreRuler from "../components/ScoreRuler";
import { Button, Card, Empty, ErrorBox, RiskBadge, Spinner, StatusBadge } from "../components/ui";
import { STATUSES, api, type Status, type TxDetail, type TxPage } from "../lib/api";
import { money, num, prob, when } from "../lib/format";
import { useApi } from "../lib/useApi";

export default function Investigations() {
  const [sp, setSp] = useSearchParams();
  const [status, setStatus] = useState("");
  const [risk, setRisk] = useState("");
  const [flaggedOnly, setFlaggedOnly] = useState(true);
  const [sort, setSort] = useState("risk");
  const [page, setPage] = useState(1);
  const [txId, setTxId] = useState(sp.get("id") ?? "");
  const [open, setOpen] = useState<number | null>(sp.get("id") ? Number(sp.get("id")) : null);

  const qs = new URLSearchParams({ sort, page: String(page), page_size: "15" });
  if (status) qs.set("status", status);
  if (risk) qs.set("risk", risk);
  if (flaggedOnly && !txId) qs.set("flagged", "true");
  if (txId) qs.set("tx_id", txId);
  const list = useApi<TxPage>(`/api/v1/transactions?${qs}`);

  useEffect(() => { setPage(1); }, [status, risk, flaggedOnly, sort, txId]);
  const pages = list.data ? Math.max(1, Math.ceil(list.data.total / list.data.page_size)) : 1;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Investigations</h1>
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">Case ID<input className="mt-1 block w-28" inputMode="numeric" value={txId}
          onChange={(e) => { setTxId(e.target.value.replace(/\D/g, "")); setSp({}); }} placeholder="e.g. 42" /></label>
        <label className="text-sm">Status<select className="mt-1 block" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All</option>{STATUSES.map((s) => <option key={s}>{s}</option>)}</select></label>
        <label className="text-sm">Risk<select className="mt-1 block" value={risk} onChange={(e) => setRisk(e.target.value)}>
          <option value="">All</option><option>High</option><option>Medium</option><option>Low</option></select></label>
        <label className="text-sm">Sort by<select className="mt-1 block" value={sort} onChange={(e) => setSort(e.target.value)}>
          <option value="risk">Highest risk</option><option value="newest">Newest</option><option value="amount">Largest amount</option></select></label>
        <label className="flex items-center gap-2 pb-2 text-sm"><input type="checkbox" className="!p-0" checked={flaggedOnly} onChange={(e) => setFlaggedOnly(e.target.checked)} />Flagged only</label>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_28rem]">
        <Card>
          {list.loading && <Spinner />}
          {list.error && <ErrorBox message={list.error} onRetry={list.reload} />}
          {list.data && list.data.items.length === 0 && !list.loading && (
            <Empty title="No cases match these filters">Clear a filter, or untick “Flagged only” to see every scored transaction.</Empty>
          )}
          {list.data && list.data.items.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-ink-muted"><tr>
                  {["Case", "Scored", "Amount", "Probability", "Risk", "Status"].map((h) => <th key={h} className="pb-2 pr-3 font-medium">{h}</th>)}
                </tr></thead>
                <tbody>
                  {list.data.items.map((t) => (
                    <tr key={t.id} onClick={() => setOpen(t.id)} className={`cursor-pointer border-t border-fog-line hover:bg-fog/60 ${open === t.id ? "bg-tide-wash" : ""}`}>
                      <td className="py-2 pr-3"><button className="font-medium text-tide underline" onClick={() => setOpen(t.id)}>#{t.id}</button></td>
                      <td className="pr-3 text-ink-muted">{when(t.created_at)}</td>
                      <td className="pr-3 tabular-nums">{money(t.amount)}</td>
                      <td className="pr-3 tabular-nums">{prob(t.probability)}</td>
                      <td className="pr-3"><RiskBadge risk={t.risk_level} /></td>
                      <td><StatusBadge status={t.review_status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="mt-4 flex items-center justify-between text-sm">
                <span className="text-ink-muted">{num(list.data.total)} cases</span>
                <div className="flex items-center gap-2">
                  <Button variant="ghost" className="!py-1" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button>
                  <span>Page {page} of {pages}</span>
                  <Button variant="ghost" className="!py-1" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</Button>
                </div>
              </div>
            </div>
          )}
        </Card>

        {open ? <CaseDetail id={open} onChanged={list.reload} onClose={() => setOpen(null)} /> : (
          <Card><p className="text-sm text-ink-muted">Select a case to see the score, the drivers behind it, and to record a decision.</p></Card>
        )}
      </div>
    </div>
  );
}

function CaseDetail({ id, onChanged, onClose }: { id: number; onChanged: () => void; onClose: () => void }) {
  const { data: d, error, loading, reload } = useApi<TxDetail>(`/api/v1/transactions/${id}`);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<Status | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { setNote(""); setErr(null); }, [id]);

  const decide = async (status: Status) => {
    setBusy(status); setErr(null);
    try { await api.patch(`/api/v1/transactions/${id}/review`, { status, note: note.trim() || null }); setNote(""); reload(); onChanged(); }
    catch (e) { setErr((e as Error).message); }
    finally { setBusy(null); }
  };

  return (
    <Card title={`Case #${id}`} aside={<button onClick={onClose} className="text-sm text-ink-muted underline">Close</button>}>
      {loading && <Spinner />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {d && (
        <div className="space-y-5">
          <ScoreRuler p={d.probability} threshold={d.threshold} />
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <RiskBadge risk={d.risk_level} /><StatusBadge status={d.review_status} />
            <span className="text-ink-muted">{money(d.amount)} · {d.source} · {d.model_version}</span>
          </div>
          <ImpactBars items={d.explanation} />

          <div>
            <h3 className="text-sm font-semibold">Decision</h3>
            <textarea className="mt-2 w-full" rows={2} maxLength={500} placeholder="Add a note (optional)" aria-label="Review note" value={note} onChange={(e) => setNote(e.target.value)} />
            <div className="mt-2 flex flex-wrap gap-2">
              <Button variant="danger" disabled={!!busy} onClick={() => decide("Confirmed Fraud")}>Confirm fraud</Button>
              <Button disabled={!!busy} onClick={() => decide("Legitimate")}>Mark legitimate</Button>
              <Button variant="ghost" disabled={!!busy} onClick={() => decide("Escalated")}>Escalate</Button>
              <Button variant="ghost" disabled={!!busy || d.review_status === "Pending"} onClick={() => decide("Pending")}>Reset</Button>
            </div>
            {err && <div className="mt-2"><ErrorBox message={err} /></div>}
          </div>

          <div>
            <h3 className="text-sm font-semibold">History</h3>
            <ol className="mt-2 space-y-2 text-sm">
              {[...d.history].reverse().map((h, i) => (
                <li key={i} className="border-l-2 border-fog-line pl-3">
                  <div className="text-xs text-ink-muted">{when(h.created_at)} · {h.action}</div>
                  <div>{h.detail}</div>
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}
    </Card>
  );
}
