from .models import *

def L(id, dest, kind, name, price, unit, provider, est=False, s=None, e=None, nv=False, v=True):
    return Listing(id=id, dest=dest, kind=kind, name=name, price=price, unit=unit, provider=provider, is_estimate=est, start=s, end=e, needs_verification=nv, verified=v)

def seed(db):
    if db.query(Listing).first(): return
    db.add_all([
        L("h1", "cxb", "Hotel", "Sea View Guest House", 2500, "night", "Sea View Guest House"),
        L("h2", "sm", "Hotel", "Island Cottage Resort", 3000, "night", "Island Cottage Resort"),
        L("h3", "saj", "Hotel", "Hilltop Cottage (Konglak)", 2200, "night", "Hilltop Cottage"),
        L("h4", "ban", "Hotel", "Jhum-house Homestay", 1500, "night", "Community Homestay"),
        L("ship", "sm", "Ship", "Ship ticket Cox's Bazar <-> Saint Martin (info only)", 1800, "person", "Ship operator", est=True),
        L("e1", "cxb", "Exp", "Parasailing", 2500, "person", "Verified Water Sports Co.", s=9, e=10, nv=True, v=True),
        L("e2", "cxb", "Exp", "Jet ski ride (life jacket)", 1500, "person", "Verified Water Sports Co.", s=10, e=10.5, nv=True, v=True),
        L("e3", "cxb", "Exp", "Speedboat ride", 1000, "person", "Bay Speedboat", s=10.5, e=11, nv=True, v=False),
        L("e9", "cxb", "Exp", "Marine Drive bike ride (half day)", 900, "person", "Kalatoli Rent-a-Bike", s=9, e=13),
        L("e7", "cxb", "Exp", "Himchari-Inani sunset tour", 800, "person", "Coastal Tours", s=16, e=18),
        L("e4", "sm", "Exp", "Tide-aware Chhera Dwip visit", 500, "person", "Island Guide Co.", s=11, e=12.5),
        L("e5", "saj", "Exp", "Convoy seat Dighinala -> Sajek", 400, "person", "Convoy Transport", s=8, e=9),
        L("e6", "ban", "Exp", "Boga Lake trek (guide + permission)", 3500, "person", "Ruma Local Guides", s=7, e=17),
        L("e10", "ban", "Exp", "Sunrise & cloud-viewing tour", 1200, "person", "Nilgiri Tours", s=5, e=9),
        Rental(id="r1", dest="sm", name="Island cycle", provider="Jetty Cycle Point", rates={"h": 80, "d": 400}, deposit=500, licence=False, helmet=False, min_age=0, mileage=0, route_id="smc"),
        Rental(id="r2", dest="cxb", name="Bike / scooter", provider="Kalatoli Rent-a-Bike", rates={"h": 300, "half": 900, "d": 1500}, deposit=3000, licence=True, helmet=True, min_age=18, mileage=40, route_id="cxb"),
        Rental(id="r3", dest="saj", name="Sajek hill bike", provider="Dighinala Bike Hub", rates={"d": 1200}, deposit=2000, licence=True, helmet=True, min_age=18, mileage=40, route_id="saj", needs_verification=True, verified=False),
        Route(id="smc", dest="sm", name="Jetty -> village lanes -> coconut groves (loop)", distance_km=11, speed_kmh=10, breaks=2, terrain="road"),
        Route(id="cxb", dest="cxb", name="Kalatoli -> Himchari -> Inani, Marine Drive (one way)", distance_km=32, speed_kmh=30, breaks=3, terrain="paved"),
        Route(id="saj", dest="saj", name="Sajek fixed hill route", distance_km=14, speed_kmh=18, breaks=2, terrain="hill"),
        Rule(dest="sm", kind="closed_months", months=list(range(2, 11)), text="Island closed to tourists Feb-Oct (2025-26 pattern)", source="[4] BSS", effective="2025-26", last_verified="2026-10-20"),
        Rule(dest="sm", kind="day_only_months", months=[11], text="November is day-visit only", source="[4] BSS", effective="2025-26", last_verified="2026-10-20"),
        Rule(dest="sm", kind="warn", text="Travel pass (QR) from the official channel; return ship 3-6 pm; no riding on beaches; plastic ban", source="[2][3]", effective="2025-26", last_verified="2026-10-20"),
        Rule(dest="cxb", kind="warn", text="Beach is an Ecologically Critical Area: no vehicles on the shore", source="[11] Prothom Alo", effective="2026", last_verified="2026-10-20"),
        Rule(dest="saj", kind="warn", text="Entry/exit only on convoy timetable via Dighinala", source="[7] BSS", effective="2026", last_verified="2026-10-20"),
        Rule(dest="ban", kind="warn", text="Treks need a registered local guide and permission", source="[9] Financial Express", effective="2026", last_verified="2026-10-20"),
        Rule(dest="ban", kind="warn_months", months=[6, 7, 8, 9], text="Monsoon season: tourist spots may close", source="[5] bdnews24", effective="2026", last_verified="2026-10-20"),
        Advisory(id="a1", dest="saj", title="Road blockade / landslide caution", source="District admin notice (demo)", date="2026-10-16", active=False, blocks_all=True),
        Advisory(id="a2", dest="ban", title="Ruma-Thanchi-Rowangchhari security restriction", source="Local admin notice (demo)", date="2026-10-20", active=True, blocks_all=False, blocks=["e6"]),
        Setting(key="fuel_price", value=120), Setting(key="surge_pct", value=0),
        Doc(en="Saint Martin needs an official ticket that generates a mandatory travel pass with a QR code. This platform does not issue it.", bn="সেন্ট মার্টিনে যেতে সরকারি টিকিট থেকে QR কোডসহ ভ্রমণ পাস লাগে। এই প্ল্যাটফর্ম পাস দেয় না।", source="[3] Dhaka Tribune", last_verified="2026-10-20"),
        Doc(en="Return sailings from Saint Martin fall in a 3-6 pm window, so day plans must end before boarding.", bn="সেন্ট মার্টিন থেকে ফেরার জাহাজ বিকেল ৩–৬টার মধ্যে; দিনের পরিকল্পনা আগে শেষ করতে হবে।", source="[3] Dhaka Tribune", last_verified="2026-10-20"),
        Doc(en="For 2025-26: November day-visit only, overnight stays in December-January, island closed from 1 February.", bn="২০২৫–২৬: নভেম্বরে শুধু দিনের ভ্রমণ, ডিসেম্বর–জানুয়ারিতে রাত্রিযাপন, ১ ফেব্রুয়ারি থেকে বন্ধ।", source="[4] BSS", last_verified="2026-10-20"),
        Doc(en="Riding on the Cox's Bazar shore is banned (Ecologically Critical Area). Use the paved Marine Drive instead.", bn="কক্সবাজার সৈকতে বাইক চালানো নিষিদ্ধ। পাকা মেরিন ড্রাইভ ব্যবহার করুন।", source="[11] Prothom Alo", last_verified="2026-10-20"),
        Doc(en="Sajek is reached via Dighinala on fixed convoy timetables and has closed during landslide risk and blockades.", bn="সাজেকে দিঘিনালা হয়ে নির্দিষ্ট কনভয় সময়ে যেতে হয়; ভূমিধস ও অবরোধে বন্ধ হয়েছে।", source="[7] BSS", last_verified="2026-10-20"),
        Doc(en="Treks such as Boga Lake, Keokradong and Tajingdong require a registered local guide and permission.", bn="বগা লেক, কেওক্রাডং, তাজিংডং ট্রেকে নিবন্ধিত স্থানীয় গাইড ও অনুমতি লাগে।", source="[9] Financial Express", last_verified="2026-10-20"),
        Doc(en="Jet-ski rides require life jackets; only administrator-verified operators are listed.", bn="জেট স্কিতে লাইফ জ্যাকেট বাধ্যতামূলক; শুধু যাচাইকৃত অপারেটর তালিকাভুক্ত।", source="[12] The Daily Star", last_verified="2026-10-20"),
        Doc(en="Ask permission before photographing people and respect community-run homestays and guides.", bn="মানুষের ছবি তোলার আগে অনুমতি নিন এবং স্থানীয় সম্প্রদায়কে সম্মান করুন।", source="Project knowledge base", last_verified="2026-10-20"),
    ])
    db.commit()
