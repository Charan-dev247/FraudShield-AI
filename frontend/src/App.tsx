import { NavLink, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Check from "./pages/Check";
import Investigations from "./pages/Investigations";
import Models from "./pages/Models";

const NAV = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/check", label: "Check a transaction" },
  { to: "/investigations", label: "Investigations" },
  { to: "/models", label: "Model & monitoring" },
];

export default function App() {
  return (
    <div className="flex min-h-full flex-col md:flex-row">
      <aside className="shrink-0 bg-ink px-4 py-5 text-white md:w-60 md:py-8">
        <div className="px-2">
          <div className="text-lg font-semibold">FraudShield AI</div>
          <div className="mt-0.5 text-xs text-white/60">Fraud scoring and case review</div>
        </div>
        <nav className="mt-4 flex gap-1 overflow-x-auto md:mt-8 md:flex-col">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end}
              className={({ isActive }) => `whitespace-nowrap rounded-md px-3 py-2 text-sm ${isActive ? "bg-white/15 font-medium" : "text-white/75 hover:bg-white/10"}`}>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <p className="mt-8 hidden px-2 text-xs leading-relaxed text-white/50 md:block">
          Portfolio demo on a public research dataset (anonymised features). Not a production banking system.
        </p>
      </aside>
      <main className="min-w-0 flex-1 px-4 py-6 md:px-10 md:py-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/check" element={<Check />} />
          <Route path="/investigations" element={<Investigations />} />
          <Route path="/models" element={<Models />} />
          <Route path="*" element={<p>Page not found.</p>} />
        </Routes>
      </main>
    </div>
  );
}
