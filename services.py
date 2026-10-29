"""Glue between DB and pure rules. Single place that prices items, so the agent and the booking API agree."""
from .models import *
from . import rules as R

def d(o): return {c.name: getattr(o, c.name) for c in o.__table__.columns}
def setting(db, k, default=0.0):
    s = db.get(Setting, k); return s.value if s else default
def advisories(db): return [d(a) for a in db.query(Advisory).all()]
def rule_list(db): return [d(r) for r in db.query(Rule).all()]
def audit(db, actor, action): db.add(Audit(actor=actor, action=action)); db.commit()

def build_line(db, spec, pax=1, decl=None):
    """spec: {type: listing|rental, id, qty | plan,hours}. Returns (line, reasons). Prices are computed here, never by the AI."""
    adv = advisories(db)
    if spec["type"] == "listing":
        l = db.get(Listing, spec["id"])
        if not l: return None, ["Unknown item"]
        qty = spec.get("qty", pax)
        why = R.blocked_reason(d(l), adv)
        line = {"spec": spec, "id": l.id, "dest": l.dest, "name": l.name, "provider": l.provider, "kind": l.kind, "amount": l.price * qty,
                "verified": not l.is_estimate, "note": f"{qty} x {l.price:.0f}/{l.unit}"}
        return line, ([why] if why else [])
    r = db.get(Rental, spec["id"])
    if not r: return None, ["Unknown rental"]
    rt = db.get(Route, r.route_id)
    why = R.check_rental(d(r), decl, adv) if decl is not None else ([R.blocked_reason(d(r), adv)] if R.blocked_reason(d(r), adv) else [])
    try: amt = R.rental_charge(r.rates, spec["plan"], spec.get("hours", 1), setting(db, "surge_pct") if r.dest == "cxb" else 0)
    except ValueError as e: return None, [str(e)]
    est = R.estimate_route(rt.distance_km, rt.speed_kmh, rt.breaks, r.mileage, setting(db, "fuel_price"))
    line = {"spec": spec, "id": r.id, "dest": r.dest, "name": f"{r.name} ({spec['plan']})", "provider": r.provider, "kind": "Rental", "amount": amt,
            "verified": True, "note": f"deposit {r.deposit:.0f} · route {est['distance_km']} km ~{est['hours']} h (estimate)", "route": est}
    return line, why

def audit_rows(db, n=30): return [{"ts": str(a.ts), "actor": a.actor, "action": a.action} for a in db.query(Audit).order_by(Audit.id.desc()).limit(n)]
