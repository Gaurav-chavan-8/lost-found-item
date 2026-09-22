"""
Lost & Found Intelligence System
---------------------------------
A DBMS mini-project demonstrating full database connectivity (SQLite) with
CRUD operations (Create, Read, Update, Delete) plus a simple "intelligence"
layer that auto-suggests matches between reported LOST items and reported
FOUND items using a similarity score (name + description + category + location).

Tech stack: Python 3, Flask, SQLite3 (via sqlite3 stdlib), Jinja2, Bootstrap 5 (CDN)

Run:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000 in your browser.
"""

import sqlite3
import os
from datetime import datetime, date
from difflib import SequenceMatcher

from flask import Flask, render_template, request, redirect, url_for, flash, g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "lostfound.db")

app = Flask(__name__)
app.secret_key = "tae2-lost-and-found-secret-key"  # only for flash messages, fine for a mini-project


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_db():
    """Open a new database connection if there isn't one for the current app context."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create tables if they do not already exist. Called once at startup."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            item_type     TEXT    NOT NULL CHECK (item_type IN ('lost', 'found')),
            item_name     TEXT    NOT NULL,
            category      TEXT    NOT NULL,
            description   TEXT    NOT NULL,
            location      TEXT    NOT NULL,
            event_date    TEXT    NOT NULL,
            person_name   TEXT    NOT NULL,
            contact       TEXT    NOT NULL,
            status        TEXT    NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
            created_at    TEXT    NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


CATEGORIES = [
    "Electronics", "Documents / ID Cards", "Bags", "Wallets / Purses",
    "Keys", "Jewellery", "Books / Stationery", "Clothing", "Accessories", "Other",
]


# ---------------------------------------------------------------------------
# Matching "intelligence" engine
# ---------------------------------------------------------------------------
def text_similarity(a, b):
    a = (a or "").strip().lower()
    b = (b or "").strip().lower()
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def match_score(item_a, item_b):
    """Return a 0-100 similarity score between a lost item and a found item."""
    name_sim = text_similarity(item_a["item_name"], item_b["item_name"])
    desc_sim = text_similarity(item_a["description"], item_b["description"])
    loc_sim = text_similarity(item_a["location"], item_b["location"])
    category_match = 1.0 if item_a["category"] == item_b["category"] else 0.0

    score = (name_sim * 0.35) + (desc_sim * 0.25) + (category_match * 0.25) + (loc_sim * 0.15)
    return round(score * 100, 1)


def find_matches_for(item, threshold=30.0, limit=5):
    """Given an item row, find candidate matches from the opposite list (open only)."""
    db = get_db()
    opposite_type = "found" if item["item_type"] == "lost" else "lost"
    candidates = db.execute(
        "SELECT * FROM items WHERE item_type = ? AND status = 'open' AND id != ?",
        (opposite_type, item["id"]),
    ).fetchall()

    scored = []
    for c in candidates:
        s = match_score(item, c)
        if s >= threshold:
            scored.append((s, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:limit]


# ---------------------------------------------------------------------------
# Routes: Dashboard (READ - aggregate)
# ---------------------------------------------------------------------------
@app.route("/")
def dashboard():
    db = get_db()
    total_lost = db.execute("SELECT COUNT(*) c FROM items WHERE item_type='lost'").fetchone()["c"]
    total_found = db.execute("SELECT COUNT(*) c FROM items WHERE item_type='found'").fetchone()["c"]
    total_resolved = db.execute("SELECT COUNT(*) c FROM items WHERE status='resolved'").fetchone()["c"]
    total_open = db.execute("SELECT COUNT(*) c FROM items WHERE status='open'").fetchone()["c"]
    recent = db.execute("SELECT * FROM items ORDER BY id DESC LIMIT 6").fetchall()
    return render_template(
        "index.html",
        total_lost=total_lost,
        total_found=total_found,
        total_resolved=total_resolved,
        total_open=total_open,
        recent=recent,
    )


# ---------------------------------------------------------------------------
# Routes: View / Read all (with filters)
# ---------------------------------------------------------------------------
@app.route("/items")
def view_items():
    db = get_db()
    item_type = request.args.get("type", "all")
    status = request.args.get("status", "all")
    query = "SELECT * FROM items WHERE 1=1"
    params = []
    if item_type in ("lost", "found"):
        query += " AND item_type = ?"
        params.append(item_type)
    if status in ("open", "resolved"):
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY id DESC"
    items = db.execute(query, params).fetchall()
    return render_template("view_items.html", items=items, item_type=item_type, status=status)


# ---------------------------------------------------------------------------
# Routes: Create (Insert)
# ---------------------------------------------------------------------------
@app.route("/add", methods=["GET", "POST"])
def add_item():
    default_type = request.args.get("type", "lost")
    if request.method == "POST":
        form = request.form
        db = get_db()
        db.execute(
            """INSERT INTO items
               (item_type, item_name, category, description, location, event_date,
                person_name, contact, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)""",
            (
                form["item_type"],
                form["item_name"].strip(),
                form["category"],
                form["description"].strip(),
                form["location"].strip(),
                form["event_date"],
                form["person_name"].strip(),
                form["contact"].strip(),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        db.commit()
        flash(f"{form['item_type'].capitalize()} item reported successfully!", "success")
        return redirect(url_for("view_items"))

    return render_template("add_item.html", categories=CATEGORIES, default_type=default_type, today=date.today().isoformat())


# ---------------------------------------------------------------------------
# Routes: Update (Edit)
# ---------------------------------------------------------------------------
@app.route("/edit/<int:item_id>", methods=["GET", "POST"])
def edit_item(item_id):
    db = get_db()
    item = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if item is None:
        flash("Item not found.", "danger")
        return redirect(url_for("view_items"))

    if request.method == "POST":
        form = request.form
        db.execute(
            """UPDATE items SET item_name=?, category=?, description=?, location=?,
               event_date=?, person_name=?, contact=?, status=? WHERE id=?""",
            (
                form["item_name"].strip(),
                form["category"],
                form["description"].strip(),
                form["location"].strip(),
                form["event_date"],
                form["person_name"].strip(),
                form["contact"].strip(),
                form["status"],
                item_id,
            ),
        )
        db.commit()
        flash("Item updated successfully!", "success")
        return redirect(url_for("view_items"))

    return render_template("edit_item.html", item=item, categories=CATEGORIES)


# ---------------------------------------------------------------------------
# Routes: Quick status update (extra Update operation)
# ---------------------------------------------------------------------------
@app.route("/resolve/<int:item_id>", methods=["POST"])
def resolve_item(item_id):
    db = get_db()
    db.execute("UPDATE items SET status='resolved' WHERE id=?", (item_id,))
    db.commit()
    flash("Item marked as resolved.", "success")
    return redirect(request.referrer or url_for("view_items"))


# ---------------------------------------------------------------------------
# Routes: Delete
# ---------------------------------------------------------------------------
@app.route("/delete/<int:item_id>", methods=["POST"])
def delete_item(item_id):
    db = get_db()
    db.execute("DELETE FROM items WHERE id = ?", (item_id,))
    db.commit()
    flash("Item deleted.", "info")
    return redirect(request.referrer or url_for("view_items"))


# ---------------------------------------------------------------------------
# Routes: Intelligence / Matching
# ---------------------------------------------------------------------------
@app.route("/matches")
def matches_overview():
    """Show best current match for every open lost item (the 'intelligence' feature)."""
    db = get_db()
    lost_items = db.execute("SELECT * FROM items WHERE item_type='lost' AND status='open'").fetchall()
    results = []
    for li in lost_items:
        best = find_matches_for(li, threshold=30.0, limit=1)
        results.append((li, best[0] if best else None))
    return render_template("matches.html", results=results)


@app.route("/matches/<int:item_id>")
def matches_for_item(item_id):
    db = get_db()
    item = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if item is None:
        flash("Item not found.", "danger")
        return redirect(url_for("view_items"))
    candidates = find_matches_for(item, threshold=15.0, limit=10)
    return render_template("matches.html", single_item=item, candidates=candidates, results=None)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
