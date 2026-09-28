# 第 3、4 课验收证据

在仓库根执行 `pytest -q`，第四课实现后应得到 12 个通过用例，除上一课用例外，还覆盖：

1. 未登录访问受保护页面返回 302，响应不泄露材料；
2. 错误密码不建立会话；
3. A 班学生只能看到 A 班材料；
4. 学生上传返回 403；
5. A 班教师访问 B 班材料返回 404，响应不含 B 班内容；
6. 教师上传后 `materials` 与 `knowledge_entries` 同时新增，列表可见；
7. 非法扩展名返回 400 且无数据库脏行。
8. 本班学生可以下载本班材料，下载接口仍经过会话班级校验。
9. 缺少 `SECRET_KEY` 时应用启动失败；
10. A 班搜索返回材料标题、片段区间和详情/下载来源，附带 B 班筛选仍无 B 班泄露；
11. 未登录、空查询和非法 limit 被拒绝，合法无命中返回空数组；
12. 上传正文立即可检索，历史片段回填重复执行不重复建索引。

第四课 API 验收：

```powershell
curl.exe -i -b cookies.txt "http://localhost:8080/api/knowledge/search?q=项目&limit=10"
curl.exe -i -b cookies.txt "http://localhost:8080/api/knowledge/search?q=B%20班&class_id=2"
```

第二条调用必须只返回当前班级内容。结果中的 `source_url` 和 `download_url` 仍由材料路由执行班级授权。

Compose 验收命令：

```powershell
Copy-Item .env.example .env
docker compose up --build -d
curl.exe -fsS http://localhost:8080/health
docker compose down
docker compose up -d
```

`data/` 和 `uploads/` 通过 volume 持久化；`GET /health` 不需要登录。

规约流程证据：`openspec validate add-auth-rbac-class-knowledge --strict` 已返回 `Change ... is valid`；第四课执行 `openspec validate add-class-scoped-knowledge-retrieval --strict` 返回 `Change 'add-class-scoped-knowledge-retrieval' is valid`。

SQLite 的 `knowledge_chunks` 与既有 `data/` volume 一起持久化；容器重启验收命令仍为 `docker compose down` 后 `docker compose up -d`，不要使用 `down -v`。当前本地 Python 测试结果为 `12 passed`；Compose 场景需在 Docker Desktop 环境按上述命令复核。
