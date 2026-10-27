import io
import json
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


def test_teacher_can_upload_chinese_named_gb18030_txt(client, app):
    assert login(client, "teacher_a", "TeacherA!2026").status_code == 302
    content = "磁铁能吸引铁钉，不能吸引木块。".encode("gb18030")
    response = client.post(
        "/api/materials/upload",
        data={"file": (io.BytesIO(content), "小学科学资料.txt")},
    )
    assert response.status_code == 201
    with sqlite3.connect(app.config["DATABASE"]) as db:
        row = db.execute(
            "SELECT title FROM materials WHERE id=?", (response.get_json()["material_id"],)
        ).fetchone()
    assert row == ("小学科学资料",)
    assert client.get("/api/knowledge/search?q=木块").get_json()["total"] == 1


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


def test_ai_workbench_seeds_multiple_apps_templates_skills_and_tools(client):
    assert login(client, "student_a1", "StudentA1!2026").status_code == 302
    page = client.get("/ai")
    assert page.status_code == 200
    apps = client.get("/api/ai/apps").get_json()["apps"]
    assert {item["app_key"] for item in apps} >= {"chat", "knowledge_qa", "summarizer"}
    templates = client.get("/api/ai/apps/knowledge_qa/templates").get_json()["templates"]
    assert templates and "{context}" in templates[0]["user_prompt"]
    skills = client.get("/api/ai/skills").get_json()["skills"]
    assert any(item["action"] == "summarize_material" for item in skills)
    tools = client.get("/api/ai/tools").get_json()["tools"]
    assert any(item["name"] == "knowledge_search" for item in tools)


def test_ai_chat_records_rendered_prompt_and_class_scoped_sources(client, app, monkeypatch):
    assert login(client, "student_a1", "StudentA1!2026").status_code == 302
    captured = {}

    def fake_provider(messages, app_cfg, tools):
        captured["messages"] = messages
        captured["app"] = app_cfg
        captured["tools"] = tools
        return {"choices": [{"message": {"content": "材料说明了本班内容。[1]"}}]}

    monkeypatch.setattr("app.ai._provider", fake_provider)
    response = client.post(
        "/api/ai/chat",
        json={"app_key": "knowledge_qa", "question": "预置教学材料"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "answered"
    assert payload["request_id"]
    assert captured["app"]["app_key"] == "knowledge_qa"
    joined = json.dumps(captured["messages"], ensure_ascii=False)
    assert "预置教学材料" in joined
    assert "A 班欢迎材料" in joined
    assert "B 班欢迎材料" not in joined
    trace = client.get(f"/api/ai/traces/{payload['request_id']}")
    assert trace.status_code == 200
    trace_payload = trace.get_json()["trace"]
    assert trace_payload["status"] == "answered"
    assert trace_payload["request"]["knowledge_policy"] == "top_k"
    assert trace_payload["request"]["matched_chunk_ids"]
    assert trace_payload["request"]["template"]["version"] == 1
    assert "预置教学材料" in json.dumps(trace_payload["request"]["model_calls"][0]["messages"], ensure_ascii=False)
    assert "Authorization" not in trace.get_data(as_text=True)
    assert "api_key" not in trace.get_data(as_text=True).lower()


def test_ai_no_context_does_not_call_provider_and_trace_is_visible(client, monkeypatch):
    assert login(client, "student_a1", "StudentA1!2026").status_code == 302
    monkeypatch.setattr("app.ai._provider", lambda *_args: (_ for _ in ()).throw(AssertionError("must not call provider")))
    response = client.post("/api/ai/chat", json={"app_key": "knowledge_qa", "question": "外星基地的温度是多少"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "no_context"
    assert payload["model_called"] is False
    trace = client.get(f"/api/ai/traces/{payload['request_id']}")
    assert trace.status_code == 200
    assert trace.get_json()["trace"]["status"] == "no_context"


def test_ai_skill_is_included_and_arbitrary_code_is_rejected(client, monkeypatch):
    assert login(client, "teacher_a", "TeacherA!2026").status_code == 302
    upload = client.post(
        "/api/ai/skills/upload",
        data={"file": (io.BytesIO(b'{"name":"safe","instructions":"Use short bullets","action":"summarize_material"}'), "safe.json")},
    )
    assert upload.status_code == 201
    skill_id = upload.get_json()["skill_id"]
    captured = {}
    def fake_provider(messages, _app, _tools):
        captured["messages"] = messages
        return {"choices": [{"message": {"content": "ok"}}]}
    monkeypatch.setattr("app.ai._provider", fake_provider)
    response = client.post("/api/ai/chat", json={"app_key": "chat", "skill_id": skill_id, "question": "你好"})
    assert response.status_code == 200
    assert "Use short bullets" in json.dumps(captured["messages"])
    rejected = client.post("/api/ai/skills/upload", data={"file": (io.BytesIO(b'{"instructions":"run subprocess", "action":"none"}'), "bad.json")})
    assert rejected.status_code == 422


def test_ai_tool_schema_is_sent_and_tool_call_is_audited(client, monkeypatch):
    assert login(client, "student_a1", "StudentA1!2026").status_code == 302
    calls = []

    def fake_provider(messages, _app_cfg, tools):
        calls.append((messages, tools))
        if len(calls) == 1:
            return {"choices": [{"message": {"content": "", "tool_calls": [{"id": "call-1", "function": {"name": "knowledge_search", "arguments": json.dumps({"query": "预置"})}}]}}]}
        return {"choices": [{"message": {"content": "工具返回了本班材料。[1]"}}]}

    monkeypatch.setattr("app.ai._provider", fake_provider)
    tool_id = client.get("/api/ai/tools").get_json()["tools"][0]["id"]
    response = client.post("/api/ai/chat", json={"app_key": "chat", "tool_ids": [tool_id], "question": "查找预置材料"})
    assert response.status_code == 200
    assert len(calls) == 2
    assert calls[0][1][0]["function"]["name"] == "knowledge_search"
    request_id = response.get_json()["request_id"]
    trace = client.get(f"/api/ai/traces/{request_id}").get_json()["trace"]
    assert trace["request"]["tool_calls"][0]["name"] == "knowledge_search"
    assert trace["request"]["tool_calls"][0]["arguments"]["query"] == "预置"
    assert len(trace["request"]["model_calls"]) == 2
    assert any(message["role"] == "tool" for message in trace["request"]["model_calls"][1]["messages"])


def test_ai_tool_arguments_are_validated_and_audited(client, monkeypatch):
    assert login(client, "student_a1", "StudentA1!2026").status_code == 302

    def fake_provider(_messages, _app_cfg, _tools):
        return {"choices": [{"message": {"content": "", "tool_calls": [{"id": "call-invalid", "function": {"name": "knowledge_search", "arguments": json.dumps({"limit": "four"})}}]}}]}

    monkeypatch.setattr("app.ai._provider", fake_provider)
    tool_id = client.get("/api/ai/tools").get_json()["tools"][0]["id"]
    response = client.post("/api/ai/chat", json={"app_key": "chat", "tool_ids": [tool_id], "question": "查找材料"})
    assert response.status_code == 503


def test_ai_teacher_can_create_template_and_register_mcp_tool(client):
    assert login(client, "teacher_a", "TeacherA!2026").status_code == 302
    template = client.post(
        "/api/ai/templates",
        json={"app_key": "chat", "name": "课堂模板", "system_prompt": "请简短回答", "user_prompt": "问题：{question}"},
    )
    assert template.status_code == 201
    tool = client.post(
        "/api/ai/tools",
        json={"name": "class_calendar", "description": "读取课堂日程", "schema": {"type": "object"}, "kind": "mcp", "endpoint": "http://mcp.invalid/rpc"},
    )
    assert tool.status_code == 201
    assert any(item["name"] == "class_calendar" for item in client.get("/api/ai/tools").get_json()["tools"])


def test_ai_mcp_adapter_performs_handshake_and_audits_call(client, monkeypatch):
    assert login(client, "teacher_a", "TeacherA!2026").status_code == 302
    created = client.post(
        "/api/ai/tools",
        json={"name": "class_calendar", "description": "读取课堂日程", "schema": {"type": "object", "properties": {"week": {"type": "integer"}}, "required": ["week"]}, "endpoint": "http://mcp.test/rpc"},
    )
    assert created.status_code == 201
    requests = []

    class FakeResponse:
        def __init__(self, body, headers=None):
            self._body = body
            self.headers = headers or {}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return self._body

    def fake_urlopen(req, timeout):
        body = json.loads(req.data.decode("utf-8"))
        requests.append((body, dict(req.headers), timeout))
        method = body["method"]
        if method == "initialize":
            return FakeResponse(b'{"jsonrpc":"2.0","id":"1","result":{"protocolVersion":"2025-06-18"}}', {"Mcp-Session-Id": "session-1"})
        if method == "notifications/initialized":
            return FakeResponse(b"")
        if method == "tools/list":
            return FakeResponse(b'{"jsonrpc":"2.0","id":"2","result":{"tools":[{"name":"class_calendar"}]}}')
        assert method == "tools/call"
        return FakeResponse('{"jsonrpc":"2.0","id":"3","result":{"content":[{"type":"text","text":"周一有课"}]}}'.encode("utf-8"))

    monkeypatch.setattr("app.ai.urllib.request.urlopen", fake_urlopen)
    provider_calls = []

    def fake_provider(messages, _app_cfg, _tools):
        provider_calls.append(messages)
        if len(provider_calls) == 1:
            return {"choices": [{"message": {"content": "", "tool_calls": [{"id": "call-1", "function": {"name": "class_calendar", "arguments": json.dumps({"week": 1})}}]}}]}
        return {"choices": [{"message": {"content": "本周一有课。[1]"}}]}

    monkeypatch.setattr("app.ai._provider", fake_provider)
    response = client.post("/api/ai/chat", json={"app_key": "chat", "tool_ids": [created.get_json()["tool_id"]], "question": "查本周课表"})
    assert response.status_code == 200
    assert [item[0]["method"] for item in requests] == ["initialize", "notifications/initialized", "tools/list", "tools/call"]
    assert requests[-1][0]["params"] == {"name": "class_calendar", "arguments": {"week": 1}}
    assert requests[-1][1].get("Mcp-session-id") == "session-1"
    trace = client.get(f"/api/ai/traces/{response.get_json()['request_id']}").get_json()["trace"]
    assert trace["request"]["tool_calls"][0]["result"]["content"][0]["text"] == "周一有课"


def test_ai_student_cannot_upload_skill_or_register_tool(client):
    assert login(client, "student_a1", "StudentA1!2026").status_code == 302
    assert client.post("/api/ai/skills/upload", data={"file": (io.BytesIO(b"instructions"), "x.md")}).status_code == 403
    assert client.post("/api/ai/tools", json={"name": "x", "description": "x", "schema": {}, "endpoint": "http://x"}).status_code == 403

