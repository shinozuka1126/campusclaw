"""CampusClaw Flask application factory."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, redirect, url_for

from .db import close_db, init_db


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    if test_config is None:
        secret_key = os.environ.get("SECRET_KEY")
        if not secret_key:
            raise RuntimeError("SECRET_KEY environment variable is required")
        database_path = os.environ.get("DATABASE_PATH", str(Path(app.instance_path) / "app.db"))
        upload_dir = os.environ.get("UPLOAD_DIR", str(Path(app.instance_path) / "uploads"))
        app.config.from_mapping(
            SECRET_KEY=secret_key,
            DATABASE=database_path,
            UPLOAD_FOLDER=upload_dir,
            MAX_CONTENT_LENGTH=2 * 1024 * 1024,
            TOKEN_TTL=3600,
            DEEPSEEK_API_KEY=os.environ.get("DEEPSEEK_API_KEY", ""),
            DEEPSEEK_MODEL=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
            DEEPSEEK_BASE_URL=os.environ.get(
                "DEEPSEEK_BASE_URL", "https://api.deepseek.com/chat/completions"
            ),
            DEEPSEEK_TIMEOUT=20,
        )
    else:
        app.config.from_mapping(
            SECRET_KEY=test_config.get("SECRET_KEY"),
            DATABASE=test_config.get("DATABASE", str(Path(app.instance_path) / "app.db")),
            UPLOAD_FOLDER=test_config.get("UPLOAD_FOLDER", str(Path(app.instance_path) / "uploads")),
            MAX_CONTENT_LENGTH=2 * 1024 * 1024,
            TOKEN_TTL=3600,
            DEEPSEEK_API_KEY="",
            DEEPSEEK_MODEL="deepseek-chat",
            DEEPSEEK_BASE_URL="https://api.deepseek.com/chat/completions",
            DEEPSEEK_TIMEOUT=20,
        )
        app.config.update(test_config)
        if not app.config.get("SECRET_KEY"):
            raise RuntimeError("SECRET_KEY configuration is required")

    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    app.teardown_appcontext(close_db)

    from .auth import bp as auth_bp
    from .materials import bp as materials_bp
    from .qa import bp as qa_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(materials_bp)
    app.register_blueprint(qa_bp)

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/")
    def index():
        return redirect(url_for("materials.list_materials"))

    with app.app_context():
        init_db(seed=True)

    return app


def main() -> None:
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))


if __name__ == "__main__":
    main()
