# CampusClaw 项目规则

- 规约是契约，代码是派生物；没有对应的 OpenSpec Requirement/Scenario 不新增业务功能。
- 先读 `openspec/specs/auth-upload/spec.md` 与最近的 `openspec/changes/archive/` 记录，再修改代码；新需求先创建 active change。
- 班级过滤和角色授权必须在服务端执行，前端隐藏按钮不算安全控制。
- 密码只能存哈希；`SECRET_KEY` 只能从服务端环境变量读取，不得写入源码或提交真实 `.env`。
- 每项实现都要有可复现的命令或测试证据；失败路径与成功路径同等重要。
