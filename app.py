"""Tripsite Flask app: routes + small helpers.

Single trip (NZ 2027), two users, no passwords. A name-picker cookie stamps
authorship and feed events. Every write appends one human-readable event row.
"""

from datetime import date, datetime

from flask import (Flask, abort, g, redirect, render_template, request,
                   url_for)

import db

app = Flask(__name__)

ENERGY_LABELS = {"rest": "Rest", "light": "Light", "full": "Full"}
COST_CATEGORIES = ["transport", "accommodation", "food", "activities", "other"]
IDEA_STATUSES = ["idea", "agreed", "booked", "rejected"]
ACCOM_STATUSES = ["tbd", "shortlisted", "booked"]


# --- request lifecycle ----------------------------------------------------

@app.before_request
def load_person():
    """Attach the current trip and person; bounce to /whoami if unidentified."""
    g.conn = db.connect()
    g.trip = g.conn.execute("SELECT * FROM trip ORDER BY id LIMIT 1").fetchone()
    g.person = None
    pid = request.cookies.get("person_id")
    if pid:
        g.person = g.conn.execute(
            "SELECT * FROM person WHERE id = ?", (pid,)).fetchone()
    # Endpoints reachable without a chosen identity
    if request.endpoint in ("whoami", "static") or request.path.startswith("/static"):
        return
    if g.person is None:
        return redirect(url_for("whoami"))


@app.teardown_request
def close_conn(exc):
    conn = g.pop("conn", None)
    if conn is not None:
        conn.close()


# --- helpers --------------------------------------------------------------

def to_eur(amount, currency):
    """Convert a cost line to EUR using the trip's single editable rate."""
    if currency == "EUR":
        return amount
    return amount * g.trip["fx_nzd_eur"]


def eur(x):
    return f"€{x:,.0f}"


def leg_for_date(iso):
    """The leg you sleep at on a given date (start <= date < end)."""
    return g.conn.execute(
        "SELECT * FROM leg WHERE start_date <= ? AND end_date > ? ORDER BY seq",
        (iso, iso)).fetchone()


def nights(leg):
    return (date.fromisoformat(leg["end_date"])
            - date.fromisoformat(leg["start_date"])).days


def event(summary):
    """Log a feed event authored by the current person. Caller commits."""
    db.log_event(g.conn, g.trip["id"], g.person["id"] if g.person else None,
                 summary)


def person_name():
    return g.person["name"] if g.person else "Someone"


app.jinja_env.filters["eur"] = eur


@app.context_processor
def inject_globals():
    open_tasks = g.conn.execute(
        "SELECT COUNT(*) AS n FROM task WHERE done = 0").fetchone()["n"] \
        if g.get("trip") else 0
    return {"trip": g.get("trip"), "me": g.get("person"),
            "open_task_count": open_tasks,
            "energy_labels": ENERGY_LABELS}


# --- whoami ---------------------------------------------------------------

@app.route("/whoami", methods=["GET", "POST"])
def whoami():
    if request.method == "POST":
        pid = request.form.get("person_id")
        row = g.conn.execute("SELECT * FROM person WHERE id = ?", (pid,)).fetchone()
        if row:
            resp = redirect(url_for("home"))
            resp.set_cookie("person_id", str(row["id"]),
                            max_age=60 * 60 * 24 * 365)
            return resp
    people = g.conn.execute("SELECT * FROM person ORDER BY id").fetchall()
    return render_template("whoami.html", people=people)


# --- home -----------------------------------------------------------------

@app.route("/")
def home():
    conn, trip = g.conn, g.trip
    events = conn.execute(
        "SELECT e.*, p.name AS person FROM event e "
        "LEFT JOIN person p ON p.id = e.person_id "
        "ORDER BY e.id DESC LIMIT 20").fetchall()

    legs = conn.execute("SELECT * FROM leg ORDER BY seq").fetchall()
    total_nights = sum(nights(l) for l in legs)
    booked_nights = sum(nights(l) for l in legs
                        if l["accommodation_status"] == "booked")

    costs = conn.execute("SELECT amount, currency, kind FROM cost").fetchall()
    booked_eur = sum(to_eur(c["amount"], c["currency"])
                     for c in costs if c["kind"] == "booked")
    est_eur = sum(to_eur(c["amount"], c["currency"]) for c in costs)

    countdown = (date.fromisoformat(trip["start_date"]) - date.today()).days
    open_tasks = conn.execute(
        "SELECT COUNT(*) AS n FROM task WHERE done = 0").fetchone()["n"]

    return render_template(
        "home.html", events=events, countdown=countdown,
        total_nights=total_nights, booked_nights=booked_nights,
        booked_eur=booked_eur, est_eur=est_eur, open_tasks=open_tasks)


# --- days -----------------------------------------------------------------

@app.route("/days")
def days():
    conn = g.conn
    rows = conn.execute("SELECT * FROM day ORDER BY date").fetchall()
    groups = []          # list of (leg_or_None, [day_rows])
    for d in rows:
        leg = leg_for_date(d["date"])
        key = leg["id"] if leg else None
        if not groups or groups[-1][2] != key:
            groups.append([leg, [], key])
        groups[-1][1].append(d)
    # pinned ideas per date
    pinned = {}
    for i in conn.execute(
            "SELECT * FROM idea WHERE pinned_date IS NOT NULL").fetchall():
        pinned.setdefault(i["pinned_date"], []).append(i)
    return render_template("days.html", groups=groups, pinned=pinned,
                           fmt_date=fmt_date, weekday=weekday)


@app.route("/days/<d>", methods=["GET", "POST"])
def day_detail(d):
    conn = g.conn
    day = conn.execute("SELECT * FROM day WHERE date = ?", (d,)).fetchone()
    if day is None:
        abort(404)
    if request.method == "POST":
        action = request.form.get("action")
        if action == "note":
            note = request.form.get("note", "").strip()
            conn.execute("UPDATE day SET note = ? WHERE date = ?", (note, d))
            event(f"{person_name()} edited the note for {fmt_date(d)}")
        elif action == "energy":
            energy = request.form.get("energy") or None
            if energy not in (None, "rest", "light", "full"):
                abort(400)
            conn.execute("UPDATE day SET energy = ? WHERE date = ?", (energy, d))
            label = ENERGY_LABELS.get(energy, "unset")
            event(f"{person_name()} marked {fmt_date(d)} as {label}")
        conn.commit()
        return redirect(url_for("day_detail", d=d))

    leg = leg_for_date(d)
    pinned = conn.execute(
        "SELECT * FROM idea WHERE pinned_date = ? ORDER BY title", (d,)).fetchall()
    # ideas that could be pinned here: unpinned, prefer this leg's ideas first
    candidates = conn.execute(
        "SELECT * FROM idea WHERE (pinned_date IS NULL OR pinned_date != ?) "
        "AND status != 'rejected' ORDER BY "
        "CASE WHEN leg_id = ? THEN 0 ELSE 1 END, title",
        (d, leg["id"] if leg else -1)).fetchall()
    return render_template("day_detail.html", day=day, leg=leg, pinned=pinned,
                           candidates=candidates, fmt_date=fmt_date,
                           weekday=weekday)


@app.route("/days/<d>/pin", methods=["POST"])
def pin_idea(d):
    conn = g.conn
    idea_id = request.form.get("idea_id")
    idea = conn.execute("SELECT * FROM idea WHERE id = ?", (idea_id,)).fetchone()
    if idea:
        conn.execute("UPDATE idea SET pinned_date = ? WHERE id = ?", (d, idea_id))
        event(f"{person_name()} pinned '{idea['title']}' to {fmt_date(d)}")
        conn.commit()
    return redirect(url_for("day_detail", d=d))


@app.route("/days/<d>/unpin", methods=["POST"])
def unpin_idea(d):
    conn = g.conn
    idea_id = request.form.get("idea_id")
    idea = conn.execute("SELECT * FROM idea WHERE id = ?", (idea_id,)).fetchone()
    if idea:
        conn.execute("UPDATE idea SET pinned_date = NULL WHERE id = ?", (idea_id,))
        event(f"{person_name()} unpinned '{idea['title']}' from {fmt_date(d)}")
        conn.commit()
    return redirect(url_for("day_detail", d=d))


# --- legs -----------------------------------------------------------------

@app.route("/legs")
def legs():
    conn = g.conn
    rows = conn.execute("SELECT * FROM leg ORDER BY seq").fetchall()
    legs_out = [dict(l, nights=nights(l)) for l in rows]
    return render_template("legs.html", legs=legs_out, fmt_date=fmt_date)


@app.route("/legs/<int:leg_id>", methods=["GET", "POST"])
def leg_detail(leg_id):
    conn = g.conn
    leg = conn.execute("SELECT * FROM leg WHERE id = ?", (leg_id,)).fetchone()
    if leg is None:
        abort(404)
    if request.method == "POST":
        accom = request.form.get("accommodation", "").strip() or None
        status = request.form.get("accommodation_status", "tbd")
        ref = request.form.get("confirmation_ref", "").strip() or None
        notes = request.form.get("notes", "").strip() or None
        if status not in ACCOM_STATUSES:
            abort(400)
        conn.execute(
            "UPDATE leg SET accommodation = ?, accommodation_status = ?, "
            "confirmation_ref = ?, notes = ? WHERE id = ?",
            (accom, status, ref, notes, leg_id))
        event(f"{person_name()} updated {leg['name']} "
              f"(accommodation: {status})")
        conn.commit()
        return redirect(url_for("leg_detail", leg_id=leg_id))

    tasks = conn.execute(
        "SELECT * FROM task WHERE leg_id = ? ORDER BY done, id", (leg_id,)).fetchall()
    costs = conn.execute(
        "SELECT * FROM cost WHERE leg_id = ? ORDER BY id", (leg_id,)).fetchall()
    ideas = conn.execute(
        "SELECT * FROM idea WHERE leg_id = ? AND status != 'rejected' "
        "ORDER BY title", (leg_id,)).fetchall()
    costs_out = [dict(c, eur=to_eur(c["amount"], c["currency"])) for c in costs]
    return render_template(
        "leg_detail.html", leg=dict(leg, nights=nights(leg)), tasks=tasks,
        costs=costs_out, ideas=ideas, fmt_date=fmt_date,
        accom_statuses=ACCOM_STATUSES)


# --- ideas ----------------------------------------------------------------

@app.route("/ideas")
def ideas():
    conn = g.conn
    status = request.args.get("status")
    q = ("SELECT i.*, l.name AS leg_name, p.name AS author FROM idea i "
         "LEFT JOIN leg l ON l.id = i.leg_id "
         "LEFT JOIN person p ON p.id = i.author_id ")
    params = ()
    if status in IDEA_STATUSES:
        q += "WHERE i.status = ? "
        params = (status,)
    q += "ORDER BY i.status, i.title"
    rows = conn.execute(q, params).fetchall()
    return render_template("ideas.html", ideas=rows, status=status,
                           statuses=IDEA_STATUSES)


@app.route("/ideas", methods=["POST"])
def add_idea():
    conn = g.conn
    title = request.form.get("title", "").strip()
    if not title:
        return redirect(url_for("ideas"))
    location = request.form.get("location", "").strip() or None
    url = request.form.get("url", "").strip() or None
    notes = request.form.get("notes", "").strip() or None
    leg_id = request.form.get("leg_id") or None
    conn.execute(
        "INSERT INTO idea (trip_id, title, location, url, notes, status, "
        "author_id, leg_id, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (g.trip["id"], title, location, url, notes, "idea", g.person["id"],
         leg_id, db.now_iso()))
    event(f"{person_name()} added the idea '{title}'")
    conn.commit()
    return redirect(url_for("ideas"))


@app.route("/ideas/<int:idea_id>/status", methods=["POST"])
def idea_status(idea_id):
    conn = g.conn
    status = request.form.get("status")
    if status not in IDEA_STATUSES:
        abort(400)
    idea = conn.execute("SELECT * FROM idea WHERE id = ?", (idea_id,)).fetchone()
    if idea is None:
        abort(404)
    conn.execute("UPDATE idea SET status = ? WHERE id = ?", (status, idea_id))
    event(f"{person_name()} set '{idea['title']}' to {status}")
    conn.commit()
    idea = conn.execute("SELECT * FROM idea WHERE id = ?", (idea_id,)).fetchone()
    return render_template("_idea_status.html", i=idea, statuses=IDEA_STATUSES)


@app.route("/ideas/<int:idea_id>", methods=["GET", "POST"])
def idea_detail(idea_id):
    conn = g.conn
    idea = conn.execute("SELECT * FROM idea WHERE id = ?", (idea_id,)).fetchone()
    if idea is None:
        abort(404)
    if request.method == "POST":
        title = request.form.get("title", "").strip() or idea["title"]
        location = request.form.get("location", "").strip() or None
        url = request.form.get("url", "").strip() or None
        notes = request.form.get("notes", "").strip() or None
        leg_id = request.form.get("leg_id") or None
        pinned = request.form.get("pinned_date", "").strip() or None
        conn.execute(
            "UPDATE idea SET title=?, location=?, url=?, notes=?, leg_id=?, "
            "pinned_date=? WHERE id=?",
            (title, location, url, notes, leg_id, pinned, idea_id))
        event(f"{person_name()} edited the idea '{title}'")
        conn.commit()
        return redirect(url_for("idea_detail", idea_id=idea_id))

    legs_all = conn.execute("SELECT id, name FROM leg ORDER BY seq").fetchall()
    tasks = conn.execute(
        "SELECT * FROM task WHERE idea_id = ? ORDER BY done, id", (idea_id,)).fetchall()
    days_all = conn.execute("SELECT date FROM day ORDER BY date").fetchall()
    return render_template("idea_detail.html", i=idea, legs=legs_all, tasks=tasks,
                           days=days_all, statuses=IDEA_STATUSES,
                           fmt_date=fmt_date)


# --- costs ----------------------------------------------------------------

@app.route("/costs")
def costs():
    conn = g.conn
    rows = conn.execute(
        "SELECT c.*, l.name AS leg_name FROM cost c "
        "LEFT JOIN leg l ON l.id = c.leg_id ORDER BY c.category, c.id").fetchall()
    lines = [dict(c, eur=to_eur(c["amount"], c["currency"])) for c in rows]

    by_cat, by_kind = {}, {"estimated": 0.0, "booked": 0.0, "actual": 0.0}
    for c in lines:
        by_cat[c["category"]] = by_cat.get(c["category"], 0.0) + c["eur"]
        by_kind[c["kind"]] += c["eur"]
    total = sum(by_kind.values())
    legs_all = conn.execute("SELECT id, name FROM leg ORDER BY seq").fetchall()
    return render_template(
        "costs.html", lines=lines, by_cat=by_cat, by_kind=by_kind, total=total,
        categories=COST_CATEGORIES, legs=legs_all)


@app.route("/costs/add", methods=["POST"])
def add_cost():
    conn = g.conn
    label = request.form.get("label", "").strip()
    try:
        amount = float(request.form.get("amount", ""))
    except ValueError:
        return redirect(url_for("costs"))
    currency = request.form.get("currency", "NZD")
    kind = request.form.get("kind", "estimated")
    category = request.form.get("category", "other")
    leg_id = request.form.get("leg_id") or None
    if not label or currency not in ("NZD", "EUR") \
            or kind not in ("estimated", "booked", "actual") \
            or category not in COST_CATEGORIES:
        return redirect(url_for("costs"))
    conn.execute(
        "INSERT INTO cost (trip_id, label, amount, currency, kind, category, leg_id) "
        "VALUES (?,?,?,?,?,?,?)",
        (g.trip["id"], label, amount, currency, kind, category, leg_id))
    event(f"{person_name()} added cost '{label}' ({currency} {amount:,.0f})")
    conn.commit()
    return redirect(url_for("costs"))


@app.route("/costs/<int:cost_id>/delete", methods=["POST"])
def delete_cost(cost_id):
    conn = g.conn
    c = conn.execute("SELECT * FROM cost WHERE id = ?", (cost_id,)).fetchone()
    if c:
        conn.execute("DELETE FROM cost WHERE id = ?", (cost_id,))
        event(f"{person_name()} removed cost '{c['label']}'")
        conn.commit()
    return redirect(url_for("costs"))


@app.route("/costs/fx", methods=["POST"])
def set_fx():
    conn = g.conn
    try:
        fx = float(request.form.get("fx", ""))
    except ValueError:
        return redirect(url_for("costs"))
    conn.execute("UPDATE trip SET fx_nzd_eur = ? WHERE id = ?", (fx, g.trip["id"]))
    event(f"{person_name()} set the FX rate to {fx:.4f} EUR per NZD")
    conn.commit()
    return redirect(url_for("costs"))


# --- tasks ----------------------------------------------------------------

@app.route("/tasks")
def tasks():
    conn = g.conn
    rows = conn.execute(
        "SELECT t.*, l.name AS leg_name, i.title AS idea_title FROM task t "
        "LEFT JOIN leg l ON l.id = t.leg_id "
        "LEFT JOIN idea i ON i.id = t.idea_id "
        "ORDER BY t.done, t.id").fetchall()
    general = [t for t in rows if t["leg_id"] is None and t["idea_id"] is None]
    grouped = {}
    for t in rows:
        if t["leg_id"] is not None:
            grouped.setdefault(("leg", t["leg_name"]), []).append(t)
        elif t["idea_id"] is not None:
            grouped.setdefault(("idea", t["idea_title"]), []).append(t)
    return render_template("tasks.html", general=general, grouped=grouped,
                           legs=conn.execute(
                               "SELECT id, name FROM leg ORDER BY seq").fetchall())


@app.route("/tasks/add", methods=["POST"])
def add_task():
    conn = g.conn
    title = request.form.get("title", "").strip()
    if not title:
        return redirect(request.referrer or url_for("tasks"))
    leg_id = request.form.get("leg_id") or None
    idea_id = request.form.get("idea_id") or None
    conn.execute("INSERT INTO task (trip_id, title, leg_id, idea_id) VALUES (?,?,?,?)",
                 (g.trip["id"], title, leg_id, idea_id))
    event(f"{person_name()} added task '{title}'")
    conn.commit()
    return redirect(request.referrer or url_for("tasks"))


@app.route("/tasks/<int:task_id>/toggle", methods=["POST"])
def toggle_task(task_id):
    conn = g.conn
    t = conn.execute("SELECT * FROM task WHERE id = ?", (task_id,)).fetchone()
    if t is None:
        abort(404)
    done = 0 if t["done"] else 1
    conn.execute("UPDATE task SET done = ? WHERE id = ?", (done, task_id))
    verb = "completed" if done else "reopened"
    event(f"{person_name()} {verb} '{t['title']}'")
    conn.commit()
    t = conn.execute("SELECT * FROM task WHERE id = ?", (task_id,)).fetchone()
    return render_template("_task_item.html", t=t)


# --- map ------------------------------------------------------------------

@app.route("/map")
def trip_map():
    conn = g.conn
    legs = conn.execute(
        "SELECT id, seq, name, lat, lon, accommodation_status FROM leg "
        "WHERE lat IS NOT NULL ORDER BY seq").fetchall()
    ideas = conn.execute(
        "SELECT id, title, lat, lon, status FROM idea "
        "WHERE lat IS NOT NULL AND status != 'rejected'").fetchall()
    leg_data = [dict(l) for l in legs]
    idea_data = [dict(i) for i in ideas]
    return render_template("map.html", legs=leg_data, ideas=idea_data)


# --- date formatting ------------------------------------------------------

def fmt_date(iso):
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%a %-d %b")


def weekday(iso):
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%A")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
