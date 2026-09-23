# CampusClaw 迭代 1：认证、授权与知识库入库

## 价值

为中小学教研团队提供按班级隔离的教学材料管理底座。

## 场景

教师登录后上传本班 `.txt` / `.md` 材料，系统解析后写入知识库；学生只能查看本班材料。

## 不做

本迭代不做检索问答、对话助手、作业提交与批改、注册/找回密码、SSO、多租户和生产高可用。

## 快速启动

```powershell
Copy-Item .env.example .env
# 编辑 .env，至少设置一个随机 SECRET_KEY
docker compose up --build
```

浏览器访问 <http://localhost:8080/login>，健康检查访问 <http://localhost:8080/health>。

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

当前活动 change 已归档，因此 `openspec list` 为空；实现范围与四件套已归档在 `openspec/changes/archive/2026-09-23-add-auth-rbac-class-knowledge/`，当前基线在 `openspec/specs/auth-upload/spec.md`。验收证据见 `evidence/verification.md`。
