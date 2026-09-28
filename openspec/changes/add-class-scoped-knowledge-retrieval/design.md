## Context

当前应用使用 Flask + SQLite。`materials` 保存材料元数据，`knowledge_entries` 保存每份材料的完整 UTF-8 正文；上一课的路由已按会话中的 `class_id` 保护材料列表、详情和下载。数据量和部署规模仍是课程级单体应用，新增外部向量数据库会引入额外服务、凭据、持久化和网络依赖。

## Goals / Non-Goals

Goals：登录用户可以检索本班知识库；结果稳定、可分页限制；每个结果能回到原始材料和正文字符区间；上传后立即可检索；历史种子数据可回填；`down` 后 `up`（不删除 `data/`）仍可检索。

Non-goals：语义生成、跨班搜索、向量相似度排序、异步任务队列和生产级分布式索引。

## Index Choice and Replacement Point

本期采用 SQLite `knowledge_chunks` 普通表和参数化 `LIKE` 子串匹配，并在 `class_id`、`material_id`、`knowledge_entry_id` 上建立索引。这样中文连续片段不依赖 SQLite FTS5 的分词行为，也无需新增镜像或服务。结果按匹配优先级、材料创建时间、片段序号和 ID 稳定排序。

检索服务使用内部后端接口。以后引入向量数据库时，向量记录必须携带 `class_id`、`material_id`、`chunk_id`，但服务端仍需在可信数据库中执行班级授权过滤或复查；向量库返回的 metadata 不得单独决定是否可以读取内容。

## Chunk and Provenance Model

新增 `knowledge_chunks`：

- `id`：片段标识；
- `knowledge_entry_id`、`material_id`、`class_id`：全部为服务端关联字段；
- `chunk_index`：同一知识条目内的稳定顺序；
- `content`：片段原文；
- `start_offset`、`end_offset`：相对于 `knowledge_entries.body_text` 的半开区间；
- `content_hash`、`created_at`：用于重建检测和审计。

切分器按 UTF-8 解码后的 Python 字符索引切分，优先在段落边界断开，必要时按固定最大字符数断开，不丢失或改写原文。历史条目回填必须幂等；上传事务在材料、知识条目和片段任一环节失败时全部回滚并删除落盘文件。

## Search Contract

提供 `GET /api/knowledge/search?q=<text>&limit=<n>`：

- 必须登录；未登录 API 返回 401，页面入口重定向到登录页；
- `q` 去除首尾空白，不能为空且最多 200 个字符；
- `limit` 默认为 10，允许 1 到 20，非法值返回 400；
- 查询使用 `WHERE knowledge_chunks.class_id = session.class_id` 与匹配条件的同一条 SQL；请求中的 `class_id` 或其他班级筛选参数被忽略；
- 结果最多返回 `limit` 条，合法但无命中返回 200 和空数组；
- 每个结果包含 `chunk_id`、`material_id`、`material_title`、`chunk_index`、`snippet`、`start_offset`、`end_offset`、`source_url`、`download_url` 和 `created_at`；不得返回不属于当前班级的标题、正文、路径或来源字段。

可选的 `/knowledge/search` HTML 页面复用同一服务函数，不能另行实现一套未过滤的查询。

## Authorization and Failure Handling

检索先执行登录检查，再从服务端会话读取 `class_id`。即使调用者知道其他班级的材料 ID、标题或片段 ID，也只能得到当前班级的结果；材料详情和下载链接继续经过上一课的 404 隔离检查。空查询、超长查询和非法 limit 返回不泄露数据库路径的 400；索引异常返回通用 500，详细错误只写服务端日志。

## Persistence and Operations

`knowledge_chunks` 与 SQLite 数据库一起落在现有 `./data:/app/data` 挂载中。应用初始化执行一次幂等回填；不删除数据的 Compose 重启后，检索结果和来源区间保持一致。健康检查仍无需登录。
