"use client";
import { useEffect, useState } from "react";
import { api, taka } from "../../lib/api";

export default function Rides() {
  const [rentals, setRentals] = useState<any[]>([]); const [q, setQ] = useState({ id: "r2", plan: "half", hours: 3, lic: false, hel: false, age: 20 });
  const [res, setRes] = useState<any>(null); const [err, setErr] = useState("");
  useEffect(() => { api("/rentals").then(setRentals).catch(e => setErr(e.message)); }, []);
  const r = rentals.find(x => x.id === q.id);
  const check = async () => { setErr(""); try { setRes(await api("/rentals/check", { body: q })); } catch (e: any) { setErr(e.message); } };
  if (!r) return <div className="card">{err || "Loading… (is the backend running on :8000?)"}</div>;
  return (<>
    <section className="card"><h2>Ride & rental planner</h2>
      <div className="grid"><label>Rental<select value={q.id} onChange={e => { const n = rentals.find(x => x.id === e.target.value); setQ({ ...q, id: n.id, plan: Object.keys(n.rates)[0] }); setRes(null); }}>{rentals.map(x => <option key={x.id} value={x.id}>{x.name} — {x.provider}</option>)}</select></label>
        <label>Plan<select value={q.plan} onChange={e => setQ({ ...q, plan: e.target.value })}>{Object.entries(r.rates).map(([k, v]: any) => <option key={k} value={k}>{k} · {taka(v)}</option>)}</select></label>
        <label>Hours (hourly plan)<input type="number" value={q.hours} onChange={e => setQ({ ...q, hours: +e.target.value })} /></label>
        <label>Rider age<input type="number" value={q.age} onChange={e => setQ({ ...q, age: +e.target.value })} /></label></div>
      <p className="mut">{r.licence ? "Licence required" : "No licence needed"} · {r.helmet ? "helmet required" : "no helmet rule"} · min age {r.min_age || "none"} · deposit {taka(r.deposit)} · {r.route.name}</p>
      <label><input type="checkbox" checked={q.lic} onChange={e => setQ({ ...q, lic: e.target.checked })} />I declare I hold a valid driving licence (the shop checks the document)</label>
      <label><input type="checkbox" checked={q.hel} onChange={e => setQ({ ...q, hel: e.target.checked })} />I accept the helmet condition</label>
      <button onClick={check}>Check conditions & estimate</button></section>
    {err && <div className="card bad">{err}</div>}
    {res && <section className="card"><h2>{res.ok ? "✅ Conditions passed" : "⛔ Blocked"}</h2>{res.reasons.map((x: string) => <div key={x} className="step bad">{x}</div>)}
      {res.line && <p>Charge <b>{taka(res.line.amount)}</b> · {res.line.route.distance_km} km · {res.line.route.hours} h · {res.line.route.breaks} breaks{res.line.route.fuel_cost ? ` · fuel ≈ ${taka(res.line.route.fuel_cost)}` : ""} <i>(ESTIMATE)</i></p>}</section>}
  </>);
}
