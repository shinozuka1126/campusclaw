"""SQLite connection, schema and seed data."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import current_app, g
from werkzeug.security import generate_password_hash


SCHEMA = """
CREATE TABLE IF NOT EXISTS classes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('teacher', 'student')),
  class_id INTEGER NOT NULL REFERENCES classes(id)
);
CREATE TABLE IF NOT EXISTS lectures (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  class_id INTEGER REFERENCES classes(id)
);
CREATE TABLE IF NOT EXISTS assignments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  class_id INTEGER REFERENCES classes(id)
);
CREATE TABLE IF NOT EXISTS assistants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  class_id INTEGER REFERENCES classes(id)
);
CREATE TABLE IF NOT EXISTS skills (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  class_id INTEGER REFERENCES classes(id)
);
CREATE TABLE IF NOT EXISTS materials (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  class_id INTEGER NOT NULL REFERENCES classes(id),
  file_path TEXT NOT NULL,
  uploaded_by INTEGER NOT NULL REFERENCES users(id),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS knowledge_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  material_id INTEGER NOT NULL UNIQUE REFERENCES materials(id),
  class_id INTEGER NOT NULL REFERENCES classes(id),
  body_text TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        db_path = Path(current_app.config["DATABASE"])
        db_path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(seed: bool = True) -> None:
    db = get_db()
    db.executescript(SCHEMA)
    if seed:
        _seed(db)
    db.commit()


def _seed(db: sqlite3.Connection) -> None:
    existing = db.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
    if existing:
        return
    db.executemany("INSERT INTO classes(name) VALUES (?)", [("A",), ("B",)])
    class_ids = {row["name"]: row["id"] for row in db.execute("SELECT id, name FROM classes")}
    users = [
        ("teacher_a", "TeacherA!2026", "teacher", class_ids["A"]),
        ("student_a1", "StudentA1!2026", "student", class_ids["A"]),
        ("student_b1", "StudentB1!2026", "student", class_ids["B"]),
    ]
    db.executemany(
        "INSERT INTO users(username, password_hash, role, class_id) VALUES (?, ?, ?, ?)",
        [(u, generate_password_hash(p), r, c) for u, p, r, c in users],
    )
    teacher_id = db.execute("SELECT id FROM users WHERE username='teacher_a'").fetchone()["id"]
    db.executemany("INSERT INTO lectures(title, class_id) VALUES (?, ?)", [("A 班示例讲义", class_ids["A"]), ("B 班示例讲义", class_ids["B"])])
    db.executemany("INSERT INTO assignments(title, class_id) VALUES (?, ?)", [("A 班占位作业", class_ids["A"]), ("B 班占位作业", class_ids["B"])])
    db.executemany("INSERT INTO assistants(name, class_id) VALUES (?, ?)", [("A 班占位助手", class_ids["A"]), ("B 班占位助手", class_ids["B"])])
    db.executemany("INSERT INTO skills(name, class_id) VALUES (?, ?)", [("A 班解题引导", class_ids["A"]), ("B 班解题引导", class_ids["B"])])
    for class_name, title, body in [
        ("A", "A 班欢迎材料", "这是 A 班的预置教学材料。"),
        ("B", "B 班欢迎材料", "这是 B 班的预置教学材料。"),
    ]:
        class_id = class_ids[class_name]
        seed_path = Path("seed") / f"{class_name.lower()}-welcome.md"
        seed_file = Path(current_app.config["UPLOAD_FOLDER"]) / seed_path
        seed_file.parent.mkdir(parents=True, exist_ok=True)
        seed_file.write_text(body, encoding="utf-8")
        cur = db.execute(
            "INSERT INTO materials(title, class_id, file_path, uploaded_by) VALUES (?, ?, ?, ?)",
            (title, class_id, str(seed_path), teacher_id),
        )
        db.execute(
            "INSERT INTO knowledge_entries(material_id, class_id, body_text) VALUES (?, ?, ?)",
            (cur.lastrowid, class_id, body),
        )


def list_materials(class_id: int):
    return get_db().execute(
        "SELECT m.id, m.title, m.class_id, m.created_at, u.username AS uploaded_by "
        "FROM materials m JOIN users u ON u.id=m.uploaded_by "
        "WHERE m.class_id=? ORDER BY m.id DESC",
        (class_id,),
    ).fetchall()


def get_material(material_id: int):
    return get_db().execute(
        "SELECT m.*, k.body_text FROM materials m "
        "LEFT JOIN knowledge_entries k ON k.material_id=m.id WHERE m.id=?",
        (material_id,),
    ).fetchone()
