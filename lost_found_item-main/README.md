# Lost & Found Intelligence System
### DBMS Mini-Project with Database Connectivity — TAE-2 (10 Marks)

A campus Lost & Found portal where students can report lost or found items,
browse/search all reports, update or resolve cases, and get **automatic
match suggestions** between lost and found items using a similarity-scoring
"intelligence" engine.

---

## 1. Tech Stack

| Layer          | Technology                          |
|----------------|--------------------------------------|
| Application    | Python 3 + Flask (web framework)     |
| Database       | SQLite 3 (file-based, zero setup)    |
| DB Connectivity| Python's built-in `sqlite3` module   |
| Frontend       | HTML + Jinja2 templates + Bootstrap 5|

SQLite was chosen so the project runs anywhere with **no server installation
required** — perfect for a quick evaluation/demo. The same code pattern
(`sqlite3.connect`, `cursor.execute`, parameterized queries) is what you'd use
with MySQL (`mysql-connector-python`) or PostgreSQL (`psycopg2`) — only the
connection string changes. See section 6 if your instructor wants MySQL instead.

---

## 2. Database Design

Single table `items` (you can point to this as your "table design" in the report):

| Column       | Type    | Notes                                   |
|--------------|---------|------------------------------------------|
| id           | INTEGER | Primary key, autoincrement                |
| item_type    | TEXT    | 'lost' or 'found'                         |
| item_name    | TEXT    | e.g. "Black Wallet"                       |
| category     | TEXT    | Electronics, Documents, Bags, etc.        |
| description  | TEXT    | Free-text details                         |
| location     | TEXT    | Where it was lost/found                   |
| event_date   | TEXT    | Date of the event (ISO format)            |
| person_name  | TEXT    | Reporter's name                           |
| contact      | TEXT    | Email/phone                               |
| status       | TEXT    | 'open' or 'resolved'                      |
| created_at   | TEXT    | Timestamp of the report                   |

This is intentionally a single denormalized table for simplicity. If your
evaluator wants to see **normalization / multiple tables with a foreign key**,
an easy extension (mentioned in section 7) is to split `categories` and
`users` into their own tables.

---

## 3. CRUD Operations — where to find them

| Operation | Route                     | File                          |
|-----------|----------------------------|--------------------------------|
| Create    | `GET/POST /add`            | `add_item()` in `app.py`       |
| Read      | `GET /`, `GET /items`      | `dashboard()`, `view_items()`  |
| Update    | `GET/POST /edit/<id>`, `POST /resolve/<id>` | `edit_item()`, `resolve_item()` |
| Delete    | `POST /delete/<id>`        | `delete_item()`                |

All SQL uses **parameterized queries** (`?` placeholders) to prevent SQL
injection — a good point to mention during evaluation.

---

## 4. The "Intelligence" Feature

`match_score()` in `app.py` compares a lost item against a found item using:
- Name similarity (35%) — via `difflib.SequenceMatcher`
- Description similarity (25%)
- Category exact match (25%)
- Location similarity (15%)

producing a 0–100% match score. The **Smart Matches** page shows the best
match for every open lost item, and each item also has a "find matches"
button showing all ranked candidates. This demonstrates logic beyond plain
CRUD, which is good for a "mini-project" style evaluation.

---

## 5. How to Run

```bash
cd lost_found_system
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000** in your browser. The SQLite database file
(`lostfound.db`) is created automatically on first run — no manual DB setup
needed.

### Demo script for evaluation
1. Show the empty dashboard, explain the schema (`app.py` → `init_db()`).
2. **Create**: Report 2–3 "lost" items and 2–3 "found" items (use similar
   names/descriptions for at least one pair so a match appears).
3. **Read**: Go to "All Items", filter by type/status.
4. **Update**: Edit an item's description, or click the ✓ to mark it resolved.
5. **Delete**: Remove a test item.
6. **Intelligence**: Open "Smart Matches" to show the auto-suggested match,
   then click into a single item's match list.

---

## 6. Switching to MySQL / Oracle / MongoDB instead of SQLite

The assignment allows any DBMS. If you'd rather demonstrate MySQL:
1. `pip install mysql-connector-python`
2. Replace `sqlite3.connect(DB_PATH)` with:
   ```python
   import mysql.connector
   mysql.connector.connect(host="localhost", user="root", password="...", database="lostfound")
   ```
3. Adjust `CREATE TABLE` syntax slightly (`AUTO_INCREMENT` instead of
   `AUTOINCREMENT`, `ENUM` instead of `CHECK`).
4. Everything else (routes, templates, matching logic) stays identical —
   this is a good talking point: the **application layer is decoupled from
   the database layer**.

---

## 7. Possible Extensions (for extra polish / viva questions)

- Split into `users`, `categories`, `items` tables with foreign keys to show
  normalization (3NF) and JOIN queries.
- Add login/authentication so only the reporter or an admin can edit/delete.
- Add image upload for items.
- Add email notification when a match is found (using `smtplib`).
- Add full-text search using SQLite's `FTS5` extension.

## 8. Common Viva Questions to Prepare

- What is the difference between `DELETE` and `DROP`? (used `DELETE FROM items`)
- Why use parameterized queries (`?`) instead of string formatting? (SQL injection)
- Explain the CRUD mapping to HTTP methods (GET vs POST).
- Walk through the ER diagram / schema and primary key choice.
- Explain the similarity/matching algorithm's time complexity (O(n) per
  lost item against all open found items).
