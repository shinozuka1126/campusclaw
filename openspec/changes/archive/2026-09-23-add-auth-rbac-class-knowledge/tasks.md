## 1. 仓库与文档

- [x] 1.1 README、AGENTS.md、requirements.txt 与应用骨架 — verify: 文件存在且 `python -c "import app"` 通过

## 2. 数据模型与种子

- [x] 2.1 创建八类数据表 — verify: `python scripts/init_db.py` 后 SQLite schema 含 classes/users/materials/knowledge_entries
- [x] 2.2 种子 A/B 班、教师 A、学生 A1/B1 与双班材料 — verify: 测试查询可区分 A/B 标题
- [x] 2.3 参数化数据库查询并按 class_id 列表 — verify: `pytest -q` 隔离用例通过

## 3. 登录、会话与密码

- [x] 3.1 `/login` 与会话字段 — verify: 正确账号登录后 session 含 role/class_id
- [x] 3.2 `login_required` 与登出 — verify: 未登录 `/materials` 返回 302，API 返回 401
- [x] 3.3 哈希校验与错误密码失败 — verify: `pytest -q` 错误密码用例通过

## 4. 班级隔离

- [x] 4.1 列表使用 session.class_id — verify: A 班列表不含 B 班样本
- [x] 4.2 按 ID 校验班级 — verify: A 班请求 B 班 ID 返回 404 且不泄露内容
- [x] 4.3 忽略客户端 class_id — verify: 路由不从 query/body 取班级

## 5. 角色权限与上传入库

- [x] 5.1 学生上传 403 且无新增 — verify: `pytest -q` 学生上传用例通过
- [x] 5.2 教师上传落盘、解析并事务写两表 — verify: 测试查询两表关联记录
- [x] 5.3 上传后本班列表可见且本班学生可下载 — verify: API 列表含新标题，下载端点返回正文
- [x] 5.4 非法扩展名/空文件 400 且无脏数据 — verify: 测试失败路径通过

## 6. Docker Compose 与 GET /health

- [x] 6.1 Dockerfile、Compose、env.example 与 volume — verify: YAML 与 Dockerfile 存在
- [x] 6.2 `/health` 无需登录 — verify: `pytest -q` health 用例通过
- [x] 6.3 启动时自动 init_db — verify: Docker CMD 先执行 `scripts/init_db.py`
- [x] 6.4 data/uploads 持久化 — verify: Compose volume 配置存在
- [x] 6.5 README 提供从零启动步骤 — verify: README 含 `.env`、Compose、login、health

## 7. 规约与收尾

- [x] 7.1 `openspec validate add-auth-rbac-class-knowledge --strict` — verify: 本变更四件套结构完整
- [x] 7.2 记录跨班拒绝、学生 403、上传可查三条验收证据 — verify: `evidence/verification.md`
