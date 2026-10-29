"""Trip orchestrator. LangGraph state machine with bounded revision loop and an approval gate.
The agent only *plans*; every price, rule and availability value comes from services/rules (AI-02).
It never books: it returns a plan that the traveller must approve through POST /bookings/approve."""
import os, re
from typing import TypedDict
from . import rules as R
from .models import Listing, Rental
from .services import *

class State(TypedDict, total=False):
    req: dict; prefs: set; log: list; lines: list; revisions: int; need_input: bool

def llm_parse(text):
    """Optional: structured extraction with an LLM (Bangla/English). Falls back to regex when no key."""
    if not (os.getenv("ANTHROPIC_API_KEY") and text.strip()): return set()
    try:
        from langchain_anthropic import ChatAnthropic
        from pydantic import BaseModel
        class X(BaseModel):
            prefs: list[str]  # subset of cycle, bike, water, hill
        out = ChatAnthropic(model=os.getenv("LLM_MODEL", "claude-sonnet-4-6")).with_structured_output(X).invoke(
            "Extract travel preferences (cycle, bike, water, hill) from this Bangla/English request. Do not invent anything:\n" + text)
        return {p for p in out.prefs if p in {"cycle", "bike", "water", "hill"}}
    except Exception:
        return set()

def regex_parse(t):
    t = t.lower(); p = set()
    if re.search(r"cycl|সাইকেল", t): p.add("cycle")
    if re.search(r"bike|scooter|বাইক", t): p.add("bike")
    if re.search(r"water|parasail|jet|speedboat|ওয়াটার", t): p.add("water")
    if re.search(r"trek|hill|sunrise|ট্রেক|পাহাড়", t): p.add("hill")
    return p

def make_nodes(db):
    def log(s, tool, msg): s["log"].append({"tool": tool, "msg": msg})

    def parse(s):
        r = s["req"]; s["log"] = []; s["lines"] = []; s["revisions"] = 0
        s["prefs"] = set(r.get("prefs", [])) | regex_parse(r.get("text", "")) | llm_parse(r.get("text", ""))
        log(s, "parse_request", f"{r['dests']} · {r['days']} day(s) · {r['pax']} pax · budget {r['budget']} · month {r['month']}")
        s["need_input"] = not r["dests"]
        if s["need_input"]: log(s, "ask_user", "Missing essential information: choose at least one destination.")
        if re.search(r"shore|beach.*(bike|ride)|(bike|ride).*beach|বিচে|সৈকতে", r.get("text", "").lower()):
            log(s, "policy_check", "DECLINED: riding on the beach shore is prohibited. Alternative: Marine Drive ride Kalatoli -> Himchari -> Inani.")
        return s

    def plan(s):
        r, rules, adv = s["req"], rule_list(db), advisories(db)
        nights = r["days"] - 1
        per = (nights // len(r["dests"]) or (1 if nights > 0 else 0)) if r["dests"] else 0
        for dest in r["dests"]:
            blocks, warns, day_only = R.access_check(rules, dest, r["month"])
            for b in blocks: log(s, f"rule_engine·{dest}", "BLOCKED: " + b)
            if blocks: log(s, "plan_revision", f"Dropped {dest}. Try another month or destination."); continue
            for w in warns: log(s, f"rule_engine·{dest}", w)
            for a in adv:
                if a["active"] and a["dest"] == dest: log(s, "advisory_checker", f"ACTIVE: {a['title']} ({a['date']})")
            n = 0 if day_only else per
            def put(spec):
                line, why = build_line(db, spec, r["pax"])
                if why: log(s, "rule_check", f"BLOCKED {line['name'] if line else spec['id']}: {why[0]}"); return False
                s["lines"].append(line); return True
            if n:
                hs = sorted(db.query(Listing).filter_by(dest=dest, kind="Hotel"), key=lambda h: h.price)
                if not any(put({"type": "listing", "id": h.id, "qty": n}) for h in hs[:1]): log(s, "hotel_search", "No stay available")
            if dest == "sm": put({"type": "listing", "id": "ship"})
            P = s["prefs"]
            if "cycle" in P and dest == "sm" and put({"type": "rental", "id": "r1", "plan": "d"}):
                rt = s["lines"][-1]["route"]
                if not n: log(s, "time_budget_planner", ("Fits" if rt["hours"] <= R.SHIP_WINDOW_HOURS else "Does NOT fit") + f" the return-ship window ({rt['hours']} h route vs {R.SHIP_WINDOW_HOURS} h available)")
            if "bike" in P and dest == "cxb": put({"type": "rental", "id": "r2", "plan": "half"})
            if "bike" in P and dest == "saj": put({"type": "rental", "id": "r3", "plan": "d"})
            if "water" in P and dest == "cxb":
                for i in ("e3", "e1"): put({"type": "listing", "id": i})
            if "hill" in P and dest == "saj": put({"type": "listing", "id": "e5"})
            if "hill" in P and dest == "ban" and not put({"type": "listing", "id": "e6"}):
                put({"type": "listing", "id": "e10"}); log(s, "plan_revision", "Replaced trek with a sunrise & cloud-viewing tour.")
        return s

    def cost(s):
        t = sum(l["amount"] for l in s["lines"]); log(s, "budget_calculator", f"Estimated total {t:.0f} vs budget {s['req']['budget']}"); return s

    def revise(s):  # bounded: removes the priciest optional item per pass
        opt = [l for l in s["lines"] if l["kind"] not in ("Hotel", "Ship")]
        o = max(opt, key=lambda l: l["amount"]); s["lines"].remove(o); s["revisions"] += 1
        log(s, "plan_revision", f"Over budget -> removed optional item: {o['name']}"); return s

    def gate(s):
        if sum(l["amount"] for l in s["lines"]) > s["req"]["budget"]: log(s, "ask_user", "Still over budget. Raise the budget or shorten the trip.")
        log(s, "approval_gate", "Plan ready. Nothing is booked until the traveller approves."); return s

    def over(s):
        opt = [l for l in s["lines"] if l["kind"] not in ("Hotel", "Ship")]
        return bool(opt) and s["revisions"] < 6 and sum(l["amount"] for l in s["lines"]) > s["req"]["budget"]
    return parse, plan, cost, revise, gate, over

def run_plan(db, req):
    parse, plan, cost, revise, gate, over = make_nodes(db)
    s: State = {"req": req}
    try:
        from langgraph.graph import StateGraph, END
        g = StateGraph(State)
        for n, f in (("parse", parse), ("plan", plan), ("cost", cost), ("revise", revise), ("gate", gate)): g.add_node(n, f)
        g.set_entry_point("parse")
        g.add_conditional_edges("parse", lambda st: "gate" if st["need_input"] else "plan")
        g.add_edge("plan", "cost")
        g.add_conditional_edges("cost", lambda st: "revise" if over(st) else "gate")
        g.add_conditional_edges("revise", lambda st: "revise" if over(st) else "gate")
        g.add_edge("gate", END)
        out = g.compile().invoke(s)
    except ImportError:  # same nodes, no LangGraph installed
        s = parse(s)
        if not s["need_input"]:
            s = cost(plan(s))
            while over(s): s = revise(s)
        out = gate(s)
    audit(db, "agent", f"plan: {len(out['lines'])} items")
    return {"log": out["log"], "lines": out["lines"], "total": sum(l["amount"] for l in out["lines"])}
