import "./globals.css";
import Link from "next/link";
export const metadata = { title: "Sagar–Pahar AI Travel Agent" };
export default function Root({ children }: { children: React.ReactNode }) {
  return (<html lang="bn"><body>
    <header><h1>🌊 সাগর–পাহাড় · Sagar–Pahar AI Travel Agent</h1><small>Cox’s Bazar · Saint Martin · Sajek · Bandarban</small></header>
    <div className="demo">⚠️ DEMO: seeded data, estimated prices, simulated payments. Rules come from news reports; verify with official notices.</div>
    <nav><Link href="/">🧭 Plan</Link><Link href="/rides">🚲 Rides</Link><Link href="/ask">💬 Ask</Link><Link href="/console">⚙️ Console</Link></nav>
    <main>{children}</main></body></html>);
}
