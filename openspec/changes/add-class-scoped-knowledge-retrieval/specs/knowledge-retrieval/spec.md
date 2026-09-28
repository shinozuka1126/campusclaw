## Purpose

让已登录的教师和学生在所属班级范围内检索知识库，并能从每个命中片段追溯到原始材料和正文位置。

## ADDED Requirements

### Requirement: 班级限定的知识库检索

系统 MUST 提供需要登录的 `GET /api/knowledge/search` 检索接口；查询必须使用服务端会话中的 `class_id` 过滤知识片段，不能使用客户端提供的班级值。

#### Scenario: A 班用户检索本班内容

- **WHEN** 已登录的 A 班用户以 `q=项目` 请求检索接口
- **THEN** 返回 HTTP 200
- **AND** 每个结果的 `class_id` 均为当前会话班级
- **AND** 命中片段来自 A 班材料正文

#### Scenario: A 班用户检索 B 班内容

- **WHEN** 已登录的 A 班用户查询只存在于 B 班材料的词语，或附带 `class_id=B`
- **THEN** 返回 HTTP 200 的空结果或仅包含 A 班命中
- **AND** 响应不包含 B 班标题、正文、文件路径、片段标识或来源链接

#### Scenario: 未登录检索

- **WHEN** 未登录请求 `/api/knowledge/search`
- **THEN** 返回 HTTP 401
- **AND** 响应不包含任何知识库内容

### Requirement: 查询参数和稳定结果

系统 MUST 去除查询首尾空白，拒绝空查询和超过 200 个字符的查询；`limit` MUST 默认为 10 且只允许 1 到 20 的整数。合法无命中 MUST 返回 HTTP 200 和空结果，结果顺序 MUST 稳定。

#### Scenario: 非法查询被拒绝

- **WHEN** 调用者提交空白 `q`、超长 `q` 或非整数/越界 `limit`
- **THEN** 返回 HTTP 400
- **AND** 响应不包含 SQL、文件路径或其他内部错误细节

#### Scenario: 合法查询没有命中

- **WHEN** 已登录用户提交合法但不存在的查询词
- **THEN** 返回 HTTP 200
- **AND** `results` 为空数组
- **AND** 响应不泄露其他班级是否存在匹配

### Requirement: 知识片段和索引一致性

系统 MUST 将每条 `knowledge_entry` 切分为带顺序和字符区间的 `knowledge_chunks`；新材料上传成功后必须在同一事务中写入片段，历史条目初始化回填必须幂等。索引失败 MUST 回滚材料、知识条目和片段写入，并清理孤立文件。

#### Scenario: 上传内容立即可检索

- **WHEN** 教师上传合法 UTF-8 `.txt` 或 `.md` 材料并提交成功
- **THEN** 当前班级立刻可以用正文中的连续片段检索到结果
- **AND** 结果的 `chunk_index`、`start_offset` 和 `end_offset` 对应原始正文

#### Scenario: 非法上传不产生检索数据

- **WHEN** 上传空文件、不支持扩展名或非 UTF-8 文件
- **THEN** 上传返回 HTTP 400
- **AND** materials、knowledge_entries、knowledge_chunks 和文件目录均无对应新增记录

### Requirement: 内容溯源

每个检索命中 MUST 返回 `chunk_id`、`material_id`、材料标题、片段序号、命中片段、原文字符区间、材料详情 URL 和下载 URL。来源详情和下载操作 MUST 继续执行当前用户的班级授权检查。

#### Scenario: 命中可回到材料

- **WHEN** 当前班级用户获得一个检索结果
- **THEN** 结果包含非空材料标识、标题、片段内容和来源 URL
- **AND** 请求该来源 URL 可查看同一班级材料
- **AND** 下载 URL 返回同一材料文件

#### Scenario: 跨班来源不可访问

- **WHEN** A 班用户拿已知的 B 班材料或片段标识请求来源详情或下载
- **THEN** 返回 HTTP 404
- **AND** 响应不泄露 B 班材料的标题、正文或路径

### Requirement: 检索数据持久化

系统 MUST 将知识片段和检索索引随现有 SQLite `data` 挂载持久化；应用重启或 Compose `down` 后再 `up`（不删除 `data`）时，已有班级过滤、检索命中和来源字段保持一致。

#### Scenario: 重启后检索仍可用

- **WHEN** 已上传材料可被检索，随后执行不删除 `data` 的 Compose 重启
- **THEN** 同一班级再次检索得到相同材料和片段来源
- **AND** 其他班级仍不能命中该材料

### Requirement: 检索故障不泄露内部信息

检索索引异常 MUST 返回通用 HTTP 500 JSON 错误，不能把 SQL、绝对文件路径、其他班级正文或向量服务凭据写入响应。

#### Scenario: 索引异常

- **WHEN** 检索后端发生数据库或索引异常
- **THEN** 返回 HTTP 500 和稳定的通用错误标识
- **AND** 响应不包含异常堆栈、文件路径或知识正文
