from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app

secret_key = os.environ.get("SECRET_KEY")
if not secret_key:
    raise RuntimeError("SECRET_KEY environment variable is required")

app = create_app({
    "SECRET_KEY": secret_key,
    "DATABASE": os.environ.get("DATABASE_PATH", str(Path("data") / "app.db")),
    "UPLOAD_FOLDER": os.environ.get("UPLOAD_DIR", str(Path("uploads"))),
})
print(f"initialized {app.config['DATABASE']}")
