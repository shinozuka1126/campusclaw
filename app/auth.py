from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
from functools import wraps

from flask import Blueprint, current_app, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from .db import get_db

bp = Blueprint("auth", __name__)


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue_access_token(user, *, secret_key: str, ttl: int) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user["id"]),
        "username": user["username"],
        "role": user["role"],
        "class_id": user["class_id"],
        "iat": now,
        "exp": now + ttl,
    }
    encoded_header = _b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_b64encode(signature)}"


def decode_access_token(token: str, *, secret_key: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("invalid token format")
    encoded_header, encoded_payload, encoded_signature = parts
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual = _b64decode(encoded_signature)
    if not hmac.compare_digest(expected, actual):
        raise ValueError("invalid token signature")
    header = json.loads(_b64decode(encoded_header))
    payload = json.loads(_b64decode(encoded_payload))
    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise ValueError("invalid token claims")
    if header.get("alg") != "HS256" or header.get("typ") != "JWT":
        raise ValueError("unsupported token header")
    if not isinstance(payload.get("sub"), str):
        raise ValueError("missing token subject")
    try:
        int(payload["sub"])
    except (TypeError, ValueError):
        raise ValueError("invalid token subject")
    if int(payload.get("exp", 0)) <= int(time.time()):
        raise ValueError("expired token")
    return payload


def _bearer_payload() -> dict | None:
    authorization = request.headers.get("Authorization")
    if authorization is None:
        return None
    if not authorization.startswith("Bearer "):
        raise ValueError("invalid authorization scheme")
    token = authorization[7:].strip()
    if not token:
        raise ValueError("missing bearer token")
    return decode_access_token(token, secret_key=current_app.config["SECRET_KEY"])


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            if request.path.startswith("/api/") or request.is_json or g.auth_error:
                return jsonify(error="unauthorized"), 401
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped_view


@bp.before_app_request
def load_logged_in_user():
    g.auth_error = False
    g.user = None
    try:
        token_payload = _bearer_payload()
    except (TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError, binascii.Error, OverflowError):
        g.auth_error = request.headers.get("Authorization") is not None
        return
    if token_payload is not None:
        user_id = token_payload["sub"]
    else:
        user_id = session.get("user_id")
    if user_id is not None:
        g.user = get_db().execute(
            "SELECT id, username, role, class_id FROM users WHERE id=?", (user_id,)
        ).fetchone()
        if g.user is None and token_payload is not None:
            g.auth_error = True


@bp.post("/api/auth/login")
def api_login():
    data = request.get_json(silent=True) or request.form
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    user = get_db().execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify(error="invalid credentials"), 401
    token_ttl = int(current_app.config.get("TOKEN_TTL", 3600))
    token = issue_access_token(user, secret_key=current_app.config["SECRET_KEY"], ttl=token_ttl)
    session.clear()
    session.update(user_id=user["id"], role=user["role"], class_id=user["class_id"])
    response = jsonify(
        access_token=token,
        token_type="Bearer",
        expires_in=token_ttl,
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("用户名或密码错误。")
        else:
            session.clear()
            session.update(user_id=user["id"], role=user["role"], class_id=user["class_id"])
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("materials.list_materials"))
    return render_template("login.html")


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
