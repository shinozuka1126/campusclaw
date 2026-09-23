from __future__ import annotations

import os
import uuid
from pathlib import Path

from flask import Blueprint, current_app, flash, g, jsonify, redirect, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename

from .auth import login_required
from .db import get_db, get_material, list_materials as db_list_materials

bp = Blueprint("materials", __name__)
ALLOWED_EXTENSIONS = {"txt", "md"}


def _json_requested() -> bool:
    return request.path.startswith("/api/") or request.is_json


@bp.get("/materials")
@login_required
def list_materials():
    rows = _list_for_user()
    return render_template("materials.html", materials=rows)


@bp.get("/api/materials")
@login_required
def api_list_materials():
    rows = _list_for_user()
    return jsonify(materials=[dict(row) for row in rows])


def _list_for_user():
    return db_list_materials(g.user["class_id"])


@bp.get("/api/materials/<int:material_id>")
@login_required
def api_material(material_id: int):
    row = get_material(material_id)
    if row is None or row["class_id"] != g.user["class_id"]:
        return jsonify(error="not found"), 404
    return jsonify(dict(row))


@bp.get("/materials/<int:material_id>/download")
@bp.get("/api/materials/<int:material_id>/download")
@login_required
def download(material_id: int):
    row = get_material(material_id)
    if row is None or row["class_id"] != g.user["class_id"]:
        return (jsonify(error="not found"), 404) if _json_requested() else ("Not Found", 404)
    relative = Path(row["file_path"])
    if relative.is_absolute() or ".." in relative.parts:
        return (jsonify(error="not found"), 404) if _json_requested() else ("Not Found", 404)
    path = Path(current_app.config["UPLOAD_FOLDER"]) / relative
    if not path.is_file():
        return (jsonify(error="not found"), 404) if _json_requested() else ("Not Found", 404)
    return send_file(path, as_attachment=True, download_name=Path(row["title"]).with_suffix(".md").name)


@bp.post("/api/materials/upload")
@bp.post("/materials/upload")
@login_required
def upload():
    if g.user["role"] != "teacher":
        return (jsonify(error="forbidden"), 403) if _json_requested() else ("Forbidden", 403)
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return _upload_error("请选择一个文件。")
    safe_name = secure_filename(uploaded.filename)
    suffix = Path(safe_name).suffix.lower().lstrip(".")
    if suffix not in ALLOWED_EXTENSIONS:
        return _upload_error("仅支持 .txt 或 .md 文件。")
    body = uploaded.read()
    if not body.strip():
        return _upload_error("文件不能为空。")
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return _upload_error("文件必须使用 UTF-8 编码。")

    class_name = get_db().execute("SELECT name FROM classes WHERE id=?", (g.user["class_id"],)).fetchone()["name"]
    token = f"{uuid.uuid4().hex}_{safe_name}"
    relative_path = Path(class_name.lower()) / token
    absolute_path = Path(current_app.config["UPLOAD_FOLDER"]) / class_name.lower() / token
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    db = get_db()
    try:
        absolute_path.write_bytes(body)
        title = Path(safe_name).stem
        cur = db.execute(
            "INSERT INTO materials(title, class_id, file_path, uploaded_by) VALUES (?, ?, ?, ?)",
            (title, g.user["class_id"], str(relative_path), g.user["id"]),
        )
        db.execute(
            "INSERT INTO knowledge_entries(material_id, class_id, body_text) VALUES (?, ?, ?)",
            (cur.lastrowid, g.user["class_id"], text),
        )
        db.commit()
    except Exception:
        db.rollback()
        try:
            absolute_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    if _json_requested():
        return jsonify(material_id=cur.lastrowid, title=title), 201
    flash(f"已上传：{title}")
    return redirect(url_for("materials.list_materials"))


def _upload_error(message: str):
    if _json_requested():
        return jsonify(error=message), 400
    flash(message)
    return redirect(url_for("materials.list_materials"))
