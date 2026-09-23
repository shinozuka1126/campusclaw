# 第 3 课验收证据

在仓库根执行 `pytest -q`，应得到 9 个通过用例，覆盖：

1. 未登录访问受保护页面返回 302，响应不泄露材料；
2. 错误密码不建立会话；
3. A 班学生只能看到 A 班材料；
4. 学生上传返回 403；
5. A 班教师访问 B 班材料返回 404，响应不含 B 班内容；
6. 教师上传后 `materials` 与 `knowledge_entries` 同时新增，列表可见；
7. 非法扩展名返回 400 且无数据库脏行。
8. 本班学生可以下载本班材料，下载接口仍经过会话班级校验。
9. 缺少 `SECRET_KEY` 时应用启动失败。

Compose 验收命令：

```powershell
Copy-Item .env.example .env
docker compose up --build -d
curl.exe -fsS http://localhost:8080/health
docker compose down
docker compose up -d
```

`data/` 和 `uploads/` 通过 volume 持久化；`GET /health` 不需要登录。

规约流程证据：`openspec validate add-auth-rbac-class-knowledge --strict` 已返回 `Change ... is valid`；随后执行 Archive，`openspec list` 显示 `No active changes found`，`openspec list --specs` 显示 `auth-upload requirements 7`。

当前工作环境没有 Docker Desktop，因此 `docker compose up --build` 与容器重建场景未能在本机执行；Dockerfile、Compose healthcheck、volume 与 README 启动路径已完成静态核对。
