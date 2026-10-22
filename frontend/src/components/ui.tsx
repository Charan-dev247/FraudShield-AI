import type { ReactNode } from "react";
import type { Risk, Status } from "../lib/api";

export function Card({ title, aside, children, className = "" }: { title?: string; aside?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-lg border border-fog-line bg-white ${className}`}>
      {(title || aside) && (
        <header className="flex items-center justify-between gap-3 border-b border-fog-line px-5 py-3">
          <h2 className="text-sm font-semibold">{title}</h2>
          {aside}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function Stat({ label, value, hint, tone }: { label: string; value: ReactNode; hint?: string; tone?: "alarm" | "safe" }) {
  const color = tone === "alarm" ? "text-alarm" : tone === "safe" ? "text-safe" : "text-ink";
  return (
    <div className="rounded-lg border border-fog-line bg-white px-5 py-4">
      <div className="text-sm text-ink-muted">{label}</div>
      <div className={`mt-1 text-3xl font-semibold tabular-nums ${color}`}>{value}</div>
      {hint && <div className="mt-1 text-xs text-ink-muted">{hint}</div>}
    </div>
  );
}

const RISK: Record<Risk, string> = { High: "bg-alarm-wash text-alarm", Medium: "bg-amber-wash text-amber", Low: "bg-safe-wash text-safe" };
export const RiskBadge = ({ risk }: { risk: Risk }) => (
  <span className={`inline-block rounded px-2 py-0.5 text-xs font-semibold ${RISK[risk]}`}>{risk}</span>
);

const STATUS: Record<Status, string> = {
  Pending: "bg-fog text-ink-soft", "Confirmed Fraud": "bg-alarm-wash text-alarm",
  Legitimate: "bg-safe-wash text-safe", Escalated: "bg-amber-wash text-amber",
};
export const StatusBadge = ({ status }: { status: Status }) => (
  <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${STATUS[status]}`}>{status}</span>
);

export const Spinner = ({ label = "Loading" }: { label?: string }) => (
  <div role="status" className="flex items-center gap-2 py-10 text-sm text-ink-muted">
    <span className="h-4 w-4 animate-spin rounded-full border-2 border-fog-line border-t-tide" />{label}…
  </div>
);

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-lg border border-alarm/30 bg-alarm-wash px-4 py-3 text-sm text-alarm">
      <p className="font-medium">Something went wrong</p>
      <p className="mt-0.5 text-ink-soft">{message}</p>
      {onRetry && <button onClick={onRetry} className="mt-2 rounded bg-white px-3 py-1 text-xs font-medium text-ink shadow-sm">Try again</button>}
    </div>
  );
}

export const Empty = ({ title, children }: { title: string; children?: ReactNode }) => (
  <div className="rounded-lg border border-dashed border-fog-line px-6 py-10 text-center">
    <p className="font-medium">{title}</p>
    {children && <div className="mx-auto mt-1 max-w-md text-sm text-ink-muted">{children}</div>}
  </div>
);

export function Button({ variant = "primary", className = "", ...p }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" }) {
  const v = variant === "primary" ? "bg-tide text-white hover:bg-tide-dark" : variant === "danger" ? "bg-alarm text-white hover:opacity-90" : "border border-fog-line bg-white hover:bg-fog";
  return <button {...p} className={`rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${v} ${className}`} />;
}
