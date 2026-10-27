## 1. Implementation
- [x] 1.1 增加 AI 应用、提示词模板、Skill、工具和 trace 数据结构及内置种子
- [x] 1.2 实现多应用请求、模板渲染和班级限定知识库上下文
- [x] 1.3 实现内置/上传 Skill、白名单动作和执行记录
- [x] 1.4 实现工具注册、内置工具和最小 MCP JSON-RPC 适配
- [x] 1.5 实现工作台、管理入口和 trace 详情页
- [x] 1.6 更新 README、环境配置和作业验证报告

## 2. Verification
- [x] 2.1 测试五项作业验收点、班级隔离、未命中不调用模型和脱敏
- [x] 2.2 运行完整测试、编译检查和 OpenSpec strict 校验（OpenSpec CLI 当前环境不可用，见验证记录）
- [x] 2.3 使用替身 provider/MCP 生成可复现 trace；真实外部密钥验证单独标明
