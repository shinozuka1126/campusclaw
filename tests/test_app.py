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


def test_knowledge_search_returns_provenance_and_enforces_class_scope(client):
    assert login(client, "student_a1", "StudentA1!2026").status_code == 302
    response = client.get("/api/knowledge/search?q=预置&limit=5")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total"] == 1
    result = payload["results"][0]
    assert result["material_title"] == "A 班欢迎材料"
    assert result["material_id"] == 1
    assert result["snippet"]
    assert result["start_offset"] < result["end_offset"]
    assert result["source_url"].endswith("/api/materials/1")
    assert result["download_url"].endswith("/materials/1/download")

    cross_class = client.get("/api/knowledge/search?q=B%20%E7%8F%AD&class_id=2")
    assert cross_class.status_code == 200
    assert cross_class.get_json()["results"] == []
    assert "B 班" not in cross_class.get_data(as_text=True)


def test_knowledge_search_requires_valid_query(client):
    assert client.get("/api/knowledge/search?q=预置").status_code == 401
    assert login(client, "student_a1", "StudentA1!2026").status_code == 302
    assert client.get("/api/knowledge/search?q=").status_code == 400
    assert client.get("/api/knowledge/search?q=预置&limit=21").status_code == 400
    assert client.get("/api/knowledge/search?q=不存在的词").get_json()["results"] == []


def test_teacher_upload_writes_material_and_knowledge_entry(client, app):
    assert login(client, "teacher_a", "TeacherA!2026").status_code == 302
    response = client.post("/api/materials/upload", data={"file": (io.BytesIO("新课内容".encode()), "new-lesson.md")})
    assert response.status_code == 201
    with sqlite3.connect(app.config["DATABASE"]) as db:
        row = db.execute("SELECT m.title, m.class_id, k.body_text FROM materials m JOIN knowledge_entries k ON k.material_id=m.id WHERE m.title='new-lesson'").fetchone()
    assert row == ("new-lesson", 1, "新课内容")
    assert client.get("/api/materials").get_json()["materials"][0]["title"] == "new-lesson"
    result = client.get("/api/knowledge/search?q=新课内容").get_json()["results"]
    assert result[0]["material_title"] == "new-lesson"
    assert result[0]["start_offset"] == 0
    assert result[0]["end_offset"] == len("新课内容")


def test_knowledge_chunks_are_idempotently_backfilled(app):
    import sqlite3

    with sqlite3.connect(app.config["DATABASE"]) as db:
        first = db.execute("SELECT COUNT(*) FROM knowledge_chunks").fetchone()[0]
    from app import create_app

    create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "DATABASE": app.config["DATABASE"],
            "UPLOAD_FOLDER": app.config["UPLOAD_FOLDER"],
        }
    )
    with sqlite3.connect(app.config["DATABASE"]) as db:
        second = db.execute("SELECT COUNT(*) FROM knowledge_chunks").fetchone()[0]
    assert first == second


def test_invalid_upload_leaves_no_db_row_or_file(client, app):
    assert login(client, "teacher_a", "TeacherA!2026").status_code == 302
    response = client.post("/api/materials/upload", data={"file": (io.BytesIO(b"bad"), "bad.exe")})
    assert response.status_code == 400
    with sqlite3.connect(app.config["DATABASE"]) as db:
        assert db.execute("SELECT COUNT(*) FROM materials WHERE title='bad'").fetchone()[0] == 0


def issue_token(client, username="student_a1", password="StudentA1!2026"):
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["token_type"] == "Bearer"
    assert payload["access_token"].count(".") == 2
    return payload["access_token"]


def test_api_login_issues_bearer_token(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "teacher_a", "password": "TeacherA!2026"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["token_type"] == "Bearer"
    assert payload["expires_in"] > 0
    assert payload["access_token"].count(".") == 2
    assert response.headers["Cache-Control"] == "no-store"


def test_bearer_token_can_access_api_without_cookie(app, client):
    token = issue_token(client)
    bearer_client = app.test_client()
    response = bearer_client.get(
        "/api/materials", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    titles = {row["title"] for row in response.get_json()["materials"]}
    assert "A 班欢迎材料" in titles
    assert "B 班欢迎材料" not in titles


def test_invalid_bearer_token_returns_401_even_with_cookie(client):
    assert login(client, "student_a1", "StudentA1!2026").status_code == 302
    response = client.get(
        "/api/materials", headers={"Authorization": "Bearer tampered"}
    )
    assert response.status_code == 401
    assert "A 班欢迎材料" not in response.get_data(as_text=True)


def test_bearer_token_cannot_cross_class(app, client):
    token = issue_token(client)
    bearer_client = app.test_client()
    response = bearer_client.get(
        "/api/knowledge/search?q=B%20%E7%8F%AD&class_id=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.get_json()["results"] == []
    assert "B 班" not in response.get_data(as_text=True)


def test_expired_bearer_token_is_rejected(app, client):
    app.config["TOKEN_TTL"] = 0
    token = issue_token(client)
    response = app.test_client().get(
        "/api/materials", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


def test_materials_page_contains_bearer_fetch_for_browser_evidence(client):
    assert login(client, "student_a1", "StudentA1!2026").status_code == 302
    response = client.get("/materials")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "/api/materials" in body
    assert "Authorization" in body
    assert "campusclaw_access_token" in body


def test_knowledge_page_and_retrieve_are_protected_and_class_scoped(client):
    assert client.get("/knowledge").status_code == 302
    assert login(client, "student_a1", "StudentA1!2026").status_code == 302
    page = client.get("/knowledge")
    assert page.status_code == 200
    assert "知识检索" in page.get_data(as_text=True)
    response = client.get("/api/knowledge/retrieve?q=B%20班&limit=4")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total"] <= 4
    assert all(source["material_title"].startswith("A 班") for source in payload["sources"])
    assert "B 班欢迎材料" not in response.get_data(as_text=True)


def test_hybrid_retrieve_matches_science_question_with_provenance(client):
    assert login(client, "teacher_a", "TeacherA!2026").status_code == 302
    uploaded = client.post(
        "/api/materials/upload",
        data={"file": (io.BytesIO("磁铁能吸引铁钉，不能吸引木块。".encode()), "science.md")},
    )
    assert uploaded.status_code == 201
    response = client.get("/api/knowledge/retrieve?q=磁铁能吸木块吗？&limit=4")
    assert response.status_code == 200
    sources = response.get_json()["sources"]
    assert sources and sources[0]["material_title"] == "science"
    assert "木块" in sources[0]["content"]
    assert sources[0]["start_offset"] == 0


def test_knowledge_ask_no_context_does_not_call_model(client, app, monkeypatch):
    assert login(client, "student_a1", "StudentA1!2026").status_code == 302
    called = False

    def fail_if_called(_question, _sources):
        nonlocal called
        called = True
        raise AssertionError("model must not be called without context")

    monkeypatch.setattr("app.qa._call_deepseek", fail_if_called)
    response = client.post("/api/knowledge/ask", json={"question": "量子曲速引擎的颜色？"})
    assert response.status_code == 200
    assert response.get_json()["status"] == "no_context"
    assert response.get_json()["model_called"] is False
    assert called is False


def test_knowledge_ask_requires_config_when_context_exists(client, app):
    assert login(client, "student_a1", "StudentA1!2026").status_code == 302
    app.config["DEEPSEEK_API_KEY"] = ""
    response = client.post("/api/knowledge/ask", json={"question": "预置教学材料"})
    assert response.status_code == 503
    assert "密钥" not in response.get_data(as_text=True)
    assert response.headers["Cache-Control"] == "no-store"


def test_knowledge_ask_provider_failure_is_generic(client, app, monkeypatch):
    assert login(client, "student_a1", "StudentA1!2026").status_code == 302
    app.config["DEEPSEEK_API_KEY"] = "test-only-key"
    monkeypatch.setattr("app.qa._call_deepseek", lambda *_args: (_ for _ in ()).throw(TimeoutError()))
    response = client.post("/api/knowledge/ask", json={"question": "预置教学材料"})
    assert response.status_code == 503
    assert "TimeoutError" not in response.get_data(as_text=True)
    assert "test-only-key" not in response.get_data(as_text=True)


def test_knowledge_ask_returns_cited_sources_with_mocked_deepseek(client, app, monkeypatch):
    assert login(client, "student_a1", "StudentA1!2026").status_code == 302
    app.config["DEEPSEEK_API_KEY"] = "test-only-key"
    monkeypatch.setattr("app.qa._call_deepseek", lambda _question, _sources: "这是本班材料的内容。[1]")
    response = client.post("/api/knowledge/ask", json={"question": "预置教学材料"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "answered"
    assert payload["model_called"] is True
    assert payload["sources"][0]["citation_id"] == 1
    assert payload["sources"][0]["material_title"] == "A 班欢迎材料"
    assert payload["sources"][0]["content"]


@pytest.mark.parametrize("answer", ["没有引用的回答", "越界引用[9]"])
def test_knowledge_ask_rejects_invalid_model_citations(client, app, monkeypatch, answer):
    assert login(client, "student_a1", "StudentA1!2026").status_code == 302
    app.config["DEEPSEEK_API_KEY"] = "test-only-key"
    monkeypatch.setattr("app.qa._call_deepseek", lambda _question, _sources: answer)
    response = client.post("/api/knowledge/ask", json={"question": "预置教学材料"})
    assert response.status_code == 502
    assert "回答" not in response.get_data(as_text=True) or "引用无效" in response.get_data(as_text=True)


def test_knowledge_ask_rejects_invalid_questions_without_model(client, app, monkeypatch):
    assert login(client, "student_a1", "StudentA1!2026").status_code == 302
    monkeypatch.setattr("app.qa._call_deepseek", lambda *_args: (_ for _ in ()).throw(AssertionError("not called")))
    assert client.post("/api/knowledge/ask", json={"question": ""}).status_code == 400
    assert client.post("/api/knowledge/ask", json={"question": "x" * 501}).status_code == 400

