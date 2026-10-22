export const pct = (x: number, d = 1) => `${(x * 100).toFixed(d)}%`;
export const num = (x: number) => x.toLocaleString("en-US");
export const money = (x: number) => x.toLocaleString("en-US", { style: "currency", currency: "USD" });
export const prob = (p: number) => (p < 0.001 ? "<0.1%" : pct(p, p < 0.1 ? 2 : 1));
export const when = (iso: string) => new Date(iso + (iso.endsWith("Z") ? "" : "Z")).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
