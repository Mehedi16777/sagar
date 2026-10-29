"""Deterministic rule engine. Pure functions: no DB, no AI. The agent may only call these."""
SHIP_WINDOW_HOURS = 3.5  # arrival ~10:30 to boarding ~14:00 (return ships sail 3-6 pm)

def access_check(rules, dest, month):
    """rules: dicts with dest, kind, months, text, active. Returns (blocks, warns, day_only)."""
    blocks, warns, day_only = [], [], False
    for r in rules:
        if r["dest"] != dest or not r.get("active", True): continue
        k, m = r["kind"], r.get("months") or []
        if k == "closed_months" and month in m: blocks.append(r["text"])
        elif k == "day_only_months" and month in m: day_only = True; warns.append(r["text"])
        elif k == "warn" or (k == "warn_months" and month in m): warns.append(r["text"])
    return blocks, warns, day_only

def blocked_reason(item, advisories):
    """item: {id,dest,needs_verification,verified}. Returns '' when allowed."""
    for a in advisories:
        if a["active"] and a["dest"] == item["dest"] and (a["blocks_all"] or item["id"] in a.get("blocks", [])):
            return f"Active advisory: {a['title']} ({a['date']})"
    if item.get("needs_verification") and not item.get("verified"):
        return "Operator authorization / rule not verified by administrator"
    return ""

def check_rental(r, decl, advisories):
    """Licence documents are never verified here; only the traveller's declaration is recorded."""
    out = []
    if r["licence"] and not decl.get("lic"): out.append("Licence declaration required (shop checks the document at hand-over)")
    if r["helmet"] and not decl.get("hel"): out.append("Helmet condition must be accepted")
    if decl.get("age", 0) < r["min_age"]: out.append(f"Minimum age is {r['min_age']}")
    b = blocked_reason(r, advisories)
    if b: out.append(b)
    return out

def estimate_route(distance_km, speed_kmh, breaks, mileage, fuel_price):
    hours = distance_km / speed_kmh + breaks * 10 / 60
    fuel = distance_km / mileage * fuel_price if mileage else 0.0
    return {"distance_km": distance_km, "hours": round(hours, 2), "breaks": breaks, "fuel_cost": round(fuel), "estimate": True}

def rental_charge(rates, plan, hours, surge_pct=0.0):
    if plan not in rates: raise ValueError("Plan not offered by this shop")
    return rates[plan] * (hours if plan == "h" else 1) * (1 + surge_pct / 100)

def check_package(items, pax, cap, advisories):
    """items: dicts with id,dest,name,price,start,end,needs_verification,verified -> (conflicts, total)."""
    conflicts, ok = [], []
    for i in items:
        b = blocked_reason(i, advisories)
        conflicts.append((i["name"], b)) if b else ok.append(i)
    by = {}
    for i in ok: by.setdefault(i["dest"], []).append(i)
    for lst in by.values():
        lst.sort(key=lambda x: x["start"])
        for a, b in zip(lst, lst[1:]):
            if b["start"] < a["end"]: conflicts.append((b["name"], f"Time overlap with {a['name']}"))
    total = sum(i["price"] * pax for i in ok)
    if total > cap: conflicts.append(("Budget", f"Package total {total:.0f} exceeds cap {cap:.0f}"))
    return conflicts, total
