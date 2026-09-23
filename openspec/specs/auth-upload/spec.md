# auth-upload Specification

## Purpose
让教师与学生以各自角色登录 CampusClaw，以班级作为数据边界隔离教学材料；教师上传的内容解析后写入知识库，本班成员通过列表查看；越权上传、跨班访问与未登录访问在服务端被拒绝。

## Requirements

### Requirement: 用户登录

系统 MUST 提供教师和学生账号密码登录；登录成功建立服务端会话，未登录访问受保护页面重定向登录页，API 返回 401 且不得泄露业务数据。

#### Scenario: 教师与学生登录成功

- **WHEN** 使用预置账号和正确密码登录
- **THEN** 登录成功并建立会话
- **AND** 会话记录用户标识、角色与所属班级

#### Scenario: 错误密码登录失败

- **WHEN** 存在的用户名使用错误密码登录
- **THEN** 登录失败且不建立有效会话

### Requirement: 角色权限

教师可上传、查看、下载本班材料；学生只读并可下载本班材料；学生调用上传接口 MUST 返回 403。

#### Scenario: 学生上传被拒绝

- **WHEN** student 会话向上传接口提交文件
- **THEN** 返回 HTTP 403
- **AND** materials、knowledge_entries 与 uploads 均无新增

#### Scenario: 教师上传被允许

- **WHEN** teacher 会话提交合法 `.txt` 或 `.md`
- **THEN** 返回 HTTP 201 并包含新材料标识

### Requirement: 班级隔离

所有材料和知识库查询 MUST 在服务端按会话班级过滤；前端隐藏按钮不是安全控制。

#### Scenario: 跨班按 ID 访问被拒绝

- **WHEN** A 班用户请求 B 班材料 ID
- **THEN** 返回 404
- **AND** 响应不含 B 班标题、正文或文件路径

#### Scenario: 列表不得泄露其他班

- **WHEN** A 班用户请求材料列表
- **THEN** 每条记录均归属 A 班
- **AND** 不出现 B 班预置材料

### Requirement: 材料上传与知识库入库

教师上传后系统 MUST 落盘、解析文本并在同一事务写入材料和知识库记录；刷新列表可见。

#### Scenario: 上传后知识库与列表可查

- **WHEN** 教师 A 上传合法 UTF-8 Markdown
- **THEN** materials 和 knowledge_entries 各新增关联记录
- **AND** 教师 A 刷新列表可见新标题

#### Scenario: 上传失败无脏数据

- **WHEN** 上传空文件、不支持格式或解析失败
- **THEN** 返回 400
- **AND** 不留下数据库记录或孤立文件

### Requirement: 预置核心数据

系统 MUST 建立 classes、users、lectures、assignments、assistants、skills、materials、knowledge_entries 表并预置 A/B 班、教师 A、学生 A1/B1 及双班材料。

#### Scenario: 首次初始化满足双班与用户

- **WHEN** 首次执行初始化脚本
- **THEN** A/B 班及三名预置用户存在
- **AND** 用户密码字段为哈希而非明文

### Requirement: 密码哈希与会话密钥

密码 MUST 使用单向哈希存储；`SECRET_KEY` MUST 仅从服务端环境变量读取。

#### Scenario: 缺少密钥时启动失败

- **WHEN** 未提供 `SECRET_KEY`
- **THEN** 应用启动失败，不得静默使用不安全默认值

### Requirement: Docker Compose 部署与健康检查

系统 MUST 以 Docker Compose 启动，提供无需登录的 `GET /health`，并用 volume 持久化数据库和上传目录。

#### Scenario: Compose 启动后健康

- **WHEN** 按 README 配置 `.env` 并执行 `docker compose up --build`
- **THEN** 登录页可访问且 `/health` 返回 200 JSON `status: ok`

#### Scenario: 重建后数据仍在

- **WHEN** down 后 up 且不删除 `data`/`uploads`
- **THEN** 预置与已上传记录仍可查询
