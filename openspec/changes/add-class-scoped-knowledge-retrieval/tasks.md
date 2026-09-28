## 1. 规约与数据模型

- [x] 1.1 在 `knowledge-retrieval` capability 中确认 API、参数、班级过滤和来源字段 — verify: strict change validation passes
- [x] 1.2 新增 `knowledge_chunks` 表、外键、唯一顺序约束和 class/material indexes — verify: fresh and existing databases expose the schema
- [x] 1.3 编写幂等历史条目回填和固定字符区间切分器 — verify: repeated app initialization test keeps chunk count stable

## 2. 检索与溯源服务

- [x] 2.1 实现 `GET /api/knowledge/search` 的登录、参数校验、稳定排序和 limit — verify: search validation tests pass
- [x] 2.2 在同一数据库查询中加入 session `class_id`，忽略客户端班级参数 — verify: A/B isolation test passes
- [x] 2.3 返回 chunk/material/source/download/offset 字段，并复用材料详情与下载授权 — verify: provenance assertions pass
- [x] 2.4 将上传写入与片段索引纳入同一事务，处理索引失败清理 — verify: upload search and invalid upload tests pass

## 3. 页面与持久化

- [x] 3.1 在材料页面增加本班检索入口和来源展示 — verify: materials template uses the authenticated search service and source URLs
- [ ] 3.2 保持 chunks 与 SQLite data volume 一起持久化 — verify: run down/up without deleting data in Docker Desktop and confirm search remains available
- [x] 3.3 记录 API、错误路径、跨班拒绝和重启验证证据 — verify: evidence document contains reproducible commands and outputs

## 4. 测试与收尾

- [x] 4.1 增加未登录、A/B 隔离、参数校验、来源字段和非法上传测试 — verify: `12 passed`
- [x] 4.2 增加历史回填与片段 offset 测试 — verify: repeated initialization and offset assertions pass
- [x] 4.3 更新 README、requirements/Compose 说明（如实现需要） — verify: README includes search endpoint and persistence check
- [x] 4.4 执行 `openspec validate add-class-scoped-knowledge-retrieval --strict` — verify: command reports the change is valid
