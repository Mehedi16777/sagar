import os, hashlib, hmac, secrets, datetime as dt
import jwt
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from . import rules as R, rag
from .agent import run_plan
from .models import *
from .seed import seed
from .services import *

SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
app = FastAPI(title="Sagar-Pahar AI Travel Agent API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def boot():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
        if not db.query(User).filter_by(email="admin@sagarpahar.test").first():
            db.add(User(email="admin@sagarpahar.test", name="Admin", pw_hash=hash_pw("admin123"), role="admin"))
            db.add(User(email="shop@sagarpahar.test", name="Kalatoli Shop", pw_hash=hash_pw("shop123"), role="provider", provider_name="Kalatoli Rent-a-Bike"))
            db.commit()

def get_db():
    with SessionLocal() as db: yield db

def hash_pw(p, salt=None):
    salt = salt or secrets.token_hex(8)
    return salt + "$" + hashlib.pbkdf2_hmac("sha256", p.encode(), salt.encode(), 120_000).hex()
def verify_pw(p, h): return hmac.compare_digest(hash_pw(p, h.split("$")[0]), h)

def user(authorization: str = Header(None), db=Depends(get_db)):
    try: uid = jwt.decode((authorization or "").removeprefix("Bearer "), SECRET, algorithms=["HS256"])["sub"]
    except Exception: raise HTTPException(401, "Login required")
    return db.get(User, int(uid))
def role(*roles):
    def dep(u=Depends(user)):
        if u.role not in roles: raise HTTPException(403, "Not allowed for your role")
        return u
    return dep

class Auth(BaseModel): email: str; password: str = Field(min_length=6); name: str = "Traveller"; role: str = "tourist"
@app.post("/auth/register")
def register(a: Auth, db=Depends(get_db)):
    if db.query(User).filter_by(email=a.email).first(): raise HTTPException(409, "Email already registered")
    u = User(email=a.email, name=a.name, pw_hash=hash_pw(a.password), role="tourist"); db.add(u); db.commit()  # admin/provider accounts are created by admin
    return {"ok": True}
@app.post("/auth/login")
def login(a: Auth, db=Depends(get_db)):
    u = db.query(User).filter_by(email=a.email).first()
    if not u or not verify_pw(a.password, u.pw_hash): raise HTTPException(401, "Wrong email or password")
    tok = jwt.encode({"sub": str(u.id), "exp": dt.datetime.utcnow() + dt.timedelta(hours=12)}, SECRET, algorithm="HS256")
    return {"token": tok, "role": u.role, "name": u.name}

@app.get("/listings")
def listings(dest: str | None = None, db=Depends(get_db)):
    q = db.query(Listing); q = q.filter_by(dest=dest) if dest else q
    return [d(x) for x in q]
@app.get("/rentals")
def rentals(db=Depends(get_db)): return [{**d(r), "route": d(db.get(Route, r.route_id))} for r in db.query(Rental)]
@app.get("/rules")
def rules_(db=Depends(get_db)): return rule_list(db)
@app.get("/advisories")
def advs(db=Depends(get_db)): return advisories(db)

class Plan(BaseModel):
    dests: list[str]; month: int = Field(ge=1, le=12); days: int = Field(ge=1, le=14); pax: int = Field(ge=1, le=30)
    budget: float = Field(gt=0); prefs: list[str] = []; text: str = ""
@app.post("/agent/plan")
def plan(p: Plan, db=Depends(get_db)): return run_plan(db, p.model_dump())

class RentalCheck(BaseModel): id: str; plan: str; hours: int = 1; lic: bool = False; hel: bool = False; age: int = 0
@app.post("/rentals/check")
def rental_check(c: RentalCheck, db=Depends(get_db)):
    line, why = build_line(db, {"type": "rental", "id": c.id, "plan": c.plan, "hours": c.hours}, decl={"lic": c.lic, "hel": c.hel, "age": c.age})
    r = db.get(Rental, c.id)
    if line and r.dest == "sm" and line["route"]["hours"] > R.SHIP_WINDOW_HOURS: why.append("Route does not fit the return-ship window")
    if line and c.plan == "h" and line["route"]["hours"] > c.hours: why.append("Route needs longer than the rented hours")
    return {"ok": not why, "reasons": why, "line": line}

class Pkg(BaseModel): ids: list[str]; pax: int = 1; cap: float = 1e9
@app.post("/packages/validate")
def pkg(p: Pkg, db=Depends(get_db)):
    items = [{**d(x), "price": x.price} for x in (db.get(Listing, i) for i in p.ids) if x and x.start is not None]
    c, t = R.check_package(items, p.pax, p.cap, advisories(db))
    return {"ok": not c and bool(items), "conflicts": [{"item": a, "reason": b} for a, b in c], "total": t}

class Item(BaseModel): type: str; id: str; qty: int | None = None; plan: str | None = None; hours: int = 1
class Approve(BaseModel):
    items: list[Item]; pax: int = 1; approved: bool = False; lic: bool = False; hel: bool = False; age: int = 0
@app.post("/bookings/approve")
def approve(a: Approve, idempotency_key: str = Header(...), u=Depends(user), db=Depends(get_db)):
    if not a.approved: raise HTTPException(400, "Explicit traveller approval is required")  # approval gate (FR-12)
    dup = db.query(Booking).filter_by(idem_key=idempotency_key, user_id=u.id).all()
    if dup: return {"duplicate": True, "bookings": [d(b) for b in dup]}
    lines = []
    for it in a.items:  # re-check rules and advisories and recompute prices server-side (AI-03)
        spec = {k: v for k, v in it.model_dump().items() if v is not None}
        line, why = build_line(db, spec, a.pax, decl={"lic": a.lic, "hel": a.hel, "age": a.age} if it.type == "rental" else None)
        if why or not line: raise HTTPException(422, f"{it.id}: {'; '.join(why)}")
        lines.append(line)
    groups = {}
    for l in lines: groups.setdefault(l["provider"], []).append(l)
    out = [Booking(user_id=u.id, provider=p, items=[l["name"] for l in ls], amount=sum(l["amount"] for l in ls), idem_key=idempotency_key) for p, ls in groups.items()]
    db.add_all(out); db.commit(); audit(db, u.email, f"approved {len(out)} requests")
    return {"duplicate": False, "bookings": [d(b) for b in out]}

@app.get("/bookings")
def my_bookings(u=Depends(user), db=Depends(get_db)):
    q = db.query(Booking)
    q = q.filter_by(user_id=u.id) if u.role == "tourist" else q.filter_by(provider=u.provider_name) if u.role == "provider" else q
    rows = [d(b) for b in q.order_by(Booking.id.desc())]
    st = {r["status"] for r in rows if r["idem_key"]}
    return {"bookings": rows, "overall": "Awaiting providers" if "Pending" in st else "Partially confirmed" if st == {"Accepted", "Declined"} else ("Confirmed" if st == {"Accepted"} else "")}
@app.post("/bookings/{bid}/respond")
def respond(bid: int, status: str, u=Depends(role("provider", "admin")), db=Depends(get_db)):
    b = db.get(Booking, bid)
    if not b or status not in ("Accepted", "Declined"): raise HTTPException(400, "Bad request")
    if u.role == "provider" and b.provider != u.provider_name: raise HTTPException(403, "Not your booking")
    b.status = status; db.commit(); audit(db, u.email, f"booking {bid} {status}"); return d(b)
@app.post("/bookings/{bid}/pay")  # sandbox only: no real payment
def pay(bid: int, u=Depends(user), db=Depends(get_db)):
    b = db.get(Booking, bid)
    if not b or b.user_id != u.id or b.status != "Accepted": raise HTTPException(400, "Only accepted bookings can be paid (sandbox)")
    b.paid = True; db.commit(); audit(db, u.email, f"sandbox payment {bid}"); return d(b)

class AdvIn(BaseModel): active: bool
@app.put("/admin/advisories/{aid}")
def set_adv(aid: str, a: AdvIn, u=Depends(role("admin")), db=Depends(get_db)):
    x = db.get(Advisory, aid); x.active = a.active; x.date = dt.date.today().isoformat(); db.commit(); audit(db, u.email, f"advisory {aid}={a.active}"); return d(x)
class Verify(BaseModel): verified: bool
@app.put("/admin/verify/{kind}/{iid}")
def verify(kind: str, iid: str, v: Verify, u=Depends(role("admin")), db=Depends(get_db)):
    x = db.get(Listing if kind == "listing" else Rental, iid); x.verified = v.verified; db.commit(); audit(db, u.email, f"verify {kind} {iid}={v.verified}"); return d(x)
class SetIn(BaseModel): fuel_price: float; surge_pct: float
@app.put("/admin/settings")
def set_settings(s: SetIn, u=Depends(role("admin")), db=Depends(get_db)):
    for k, v in s.model_dump().items(): db.merge(Setting(key=k, value=v))
    db.commit(); audit(db, u.email, "settings updated"); return s
@app.get("/admin/audit")
def audit_log(u=Depends(role("admin")), db=Depends(get_db)): return audit_rows(db)

class Q(BaseModel): q: str
@app.post("/rag/ask")
def ask(q: Q, db=Depends(get_db)): return rag.ask(db, q.q)
