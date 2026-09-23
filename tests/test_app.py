import io
import sqlite3
import pytest

from conftest import login


def test_secret_key_is_required(tmp_path):
    from app import create_app
    with pytest.raises(RuntimeError):
        create_app({"DATABASE": str(tmp_path / "app.db")})


def test_health_is_public(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_protected_page_redirects_without_leaking_data(client):
    response = client.get("/materials")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert "A 班欢迎材料" not in response.get_data(as_text=True)


def test_wrong_password_does_not_create_session(client):
    response = login(client, "teacher_a", "wrong")
    assert response.status_code == 200
    with client.session_transaction() as session:
        assert "user_id" not in session


def test_student_sees_only_own_class_and_upload_is_forbidden(client):
    assert login(client, "student_a1", "StudentA1!2026").status_code == 302
    response = client.get("/api/materials")
    assert response.status_code == 200
    titles = {row["title"] for row in response.json["materials"]}
    assert "A 班欢迎材料" in titles
    assert "B 班欢迎材料" not in titles
    upload = client.post("/api/materials/upload", data={"file": (io.BytesIO(b"x"), "student.md")})
    assert upload.status_code == 403


def test_cross_class_material_is_not_found(client, app):
    assert login(client, "teacher_a", "TeacherA!2026").status_code == 302
    with sqlite3.connect(app.config["DATABASE"]) as db:
        b_id = db.execute("SELECT id FROM materials WHERE title='B 班欢迎材料'").fetchone()[0]
    response = client.get(f"/api/materials/{b_id}")
    assert response.status_code == 404
    assert "B 班" not in response.get_data(as_text=True)


def test_student_can_download_own_class_material(client):
    assert login(client, "student_a1", "StudentA1!2026").status_code == 302
    response = client.get("/materials/1/download")
    assert response.status_code == 200
    assert "A 班" in response.get_data(as_text=True)


def test_teacher_upload_writes_material_and_knowledge_entry(client, app):
    assert login(client, "teacher_a", "TeacherA!2026").status_code == 302
    response = client.post("/api/materials/upload", data={"file": (io.BytesIO("新课内容".encode()), "new-lesson.md")})
    assert response.status_code == 201
    with sqlite3.connect(app.config["DATABASE"]) as db:
        row = db.execute("SELECT m.title, m.class_id, k.body_text FROM materials m JOIN knowledge_entries k ON k.material_id=m.id WHERE m.title='new-lesson'").fetchone()
    assert row == ("new-lesson", 1, "新课内容")
    assert client.get("/api/materials").get_json()["materials"][0]["title"] == "new-lesson"


def test_invalid_upload_leaves_no_db_row_or_file(client, app):
    assert login(client, "teacher_a", "TeacherA!2026").status_code == 302
    response = client.post("/api/materials/upload", data={"file": (io.BytesIO(b"bad"), "bad.exe")})
    assert response.status_code == 400
    with sqlite3.connect(app.config["DATABASE"]) as db:
        assert db.execute("SELECT COUNT(*) FROM materials WHERE title='bad'").fetchone()[0] == 0

