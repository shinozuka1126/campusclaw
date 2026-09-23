## Context

第 2 课已完成 change 四件套，本课按同一规约实施 CampusClaw 最小可运行栈。实现选用 Flask + SQLite，与规约保持一致。

## Goals / Non-Goals

Goals：登录可用；会话含 `user_id`、`role`、`class_id`；服务端强制授权和班级过滤；教师上传链路为落盘 → 解析 → 双表入库 → 列表可见；`docker compose up` 可启动；`GET /health` 无需登录。

Non-goals：沿用 proposal 中的检索问答、对话、作业、注册、SSO 与生产 HA 非目标。

## Session and Passwords

使用 Flask signed-cookie session，设置 HttpOnly、SameSite=Lax。`SECRET_KEY` 只从环境变量读取，缺失时应用启动失败。用户表只有 `password_hash`，用 Werkzeug 的单向哈希和校验函数，禁止明文密码。

## Server-side Class Isolation

所有列表查询固定 `WHERE class_id = session.class_id`。按 ID 访问先取记录，再比较班级；跨班固定返回 404，响应不泄露标题、正文、文件路径。上传记录的 `class_id` 只取自会话，不接受客户端覆盖。

## Upload Data Flow

教师提交 multipart 文件后检查角色、扩展名和 UTF-8 内容，保存到 `uploads/<class>/`；解析失败、空文件或不支持扩展名时返回 400 并清理文件。成功时在一个事务内写 `materials` 和 `knowledge_entries` 两表。

材料下载也经过同一会话班级校验，文件目录不作为静态资源暴露；学生可下载本班材料，跨班或不存在的 ID 统一返回 404。

## Data Model

`classes`、`users`、`lectures`、`assignments`、`assistants`、`skills`、`materials`、`knowledge_entries`。初始化脚本建立双班、用户、占位实体和双班材料样本。

## Compose and Health

Compose 的 app 服务构建 Dockerfile，挂载 `./data:/app/data`、`./uploads:/app/uploads`，从 `.env` 注入 `SECRET_KEY`，使用 `curl /health` healthcheck。容器启动先执行 `scripts/init_db.py`，再由 gunicorn 监听 `0.0.0.0:8080`。
