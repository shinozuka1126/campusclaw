# CampusClaw 迭代 2：班级限定知识库检索与内容溯源

## 价值

为中小学教研团队提供按班级隔离的教学材料管理和可核验检索底座。

## 场景

教师登录后上传本班 `.txt` / `.md` 材料，系统解析、切分后写入知识库；本班教师和学生可以检索本班内容并追溯到原始材料。

## 不做

本迭代不做生成式检索问答、对话助手、作业提交与批改、注册/找回密码、SSO、多租户和生产高可用。

## 快速启动

```powershell
Copy-Item .env.example .env
# 编辑 .env，至少设置一个随机 SECRET_KEY
docker compose up --build
```

浏览器访问 <http://localhost:8080/login>，健康检查访问 <http://localhost:8080/health>。

登录后，材料页的检索框只搜索当前用户所属班级。API 调用示例：

```powershell
curl.exe -b cookies.txt "http://localhost:8080/api/knowledge/search?q=项目&limit=10"
```

每个命中包含 `material_id`、`material_title`、`chunk_id`、正文字符区间、片段、材料详情 URL 和下载 URL。服务端从会话读取班级，忽略请求中的 `class_id`；本期使用 SQLite 片段索引，不需要单独启动向量数据库。

## Bearer token 演示

除兼容 HTML 页面的 signed-cookie session 外，项目提供短期的 HS256 Bearer token，用于 API 客户端和浏览器 Network 面板演示：

```powershell
$login = curl.exe -sS -X POST http://localhost:8080/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{"username":"student_a1","password":"StudentA1!2026"}' | ConvertFrom-Json
$token = $login.access_token
curl.exe -i http://localhost:8080/api/materials -H "Authorization: Bearer $token"
```

`/api/auth/login` 返回 `access_token`、`token_type=Bearer` 和 `expires_in`。服务端验证签名和有效期后，按 token 的 `sub` 回查用户表，再从数据库取得角色和班级；不会信任 token 或 URL 中的 `class_id`。登录页面会把 token 暂存到当前浏览器会话，材料页随后以 `Authorization: Bearer <token>` 请求 `/api/materials`，因此可在 DevTools 的 Network → Fetch/XHR → `materials` → Headers 中看到该请求头。token 不放入 URL，响应设置 `Cache-Control: no-store`。

预置账号：

| 账号 | 密码 | 角色 | 班级 |
| --- | --- | --- | --- |
| `teacher_a` | `TeacherA!2026` | 教师 | A |
| `student_a1` | `StudentA1!2026` | 学生 | A |
| `student_b1` | `StudentB1!2026` | 学生 | B |

教师可上传/查看/下载本班材料，学生可查看/下载但不可上传。跨班访问固定返回 `404`，响应不包含对方班级的标题、正文或路径。

## 本地开发

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:SECRET_KEY = 'local-development-only-change-me'
python -m app
```

初始化数据库：

```powershell
python scripts/init_db.py
```

## 验证

```powershell
pytest -q
```

OpenSpec 规约校验（归档前已执行，安装 `@fission-ai/openspec` 后可在归档前的 change 目录执行）：

```powershell
openspec validate add-auth-rbac-class-knowledge --strict
```

第四课活动 change 为 `add-class-scoped-knowledge-retrieval`，描述和实现任务在 `openspec/changes/add-class-scoped-knowledge-retrieval/`；上一课四件套已归档在 `openspec/changes/archive/2026-09-23-add-auth-rbac-class-knowledge/`。验收证据见 `evidence/verification.md`。
