from pathlib import Path

import pytest

from app import create_app


@pytest.fixture()
def app(tmp_path: Path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "DATABASE": str(tmp_path / "app.db"),
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
    })
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, username, password):
    return client.post("/login", data={"username": username, "password": password}, follow_redirects=False)
