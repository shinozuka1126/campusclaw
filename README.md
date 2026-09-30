# CampusClaw 迭代 4：班级限定知识库检索与 AI 问答

## 价值

为中小学教研团队提供按班级隔离、可核验并支持 AI 问答的教学材料底座。

## 场景

教师登录后上传本班 `.txt` / `.md` 材料，系统解析、切分后写入知识库；支持 UTF-8、UTF-8 BOM、UTF-16 和 GB18030 常见文本编码。本班教师和学生可以检索本班内容、追溯原始材料，并在知识问答页获得带 `[1]`、`[2]` 来源标记的简短回答。

## 不做

本项目不做多轮对话、作业提交与批改、注册/找回密码、SSO、多租户和生产高可用。

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

## 知识问答

教师可先在材料页上传 `examples/science-a.md`，然后打开“知识问答”。每个问题先在当前用户所属班级内做 BM25 + TF-IDF 稀疏混合检索，最多选取 4 个切片交给 DeepSeek；回答必须引用 `[1]`、`[2]` 等编号，页面同时展示切片正文、字符区间、材料详情和下载链接。没有命中时返回“本班资料中没有找到相关内容”，不会调用模型。

在本机 `.env` 中填写服务端密钥（不要提交 `.env`）：

```dotenv
DEEPSEEK_API_KEY=你的本机密钥
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com/chat/completions
```

也可以使用已登录会话直接调用接口：

```powershell
curl.exe -b cookies.txt "http://localhost:8080/api/knowledge/retrieve?q=磁铁&limit=4"
curl.exe -b cookies.txt -H "Content-Type: application/json" -d '{"question":"磁铁能吸木块吗？"}' http://localhost:8080/api/knowledge/ask
```

模型只会收到问题和当前班级的原文切片，不会收到 Cookie、Bearer token、用户名或密码。未配置密钥、上游超时、无效引用和供应商故障都会返回通用错误，不回显密钥或供应商原始响应。

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
openspec validate add-class-knowledge-qa --strict
```

第四课活动 change 为 `add-class-knowledge-qa`，描述和实现任务在 `openspec/changes/add-class-knowledge-qa/`；上一课四件套已归档在 `openspec/changes/archive/2026-09-23-add-auth-rbac-class-knowledge/`。验收证据见 `evidence/verification.md`。
