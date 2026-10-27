# AI 工作台规约

## ADDED Requirements

### Requirement: 多 AI 应用与提示词模板
系统 MUST 提供至少三个可选择的 AI 应用 profile，并允许使用绑定的提示词模板。发送模型前 MUST 记录并展示实际渲染后的 messages、模型参数和模板版本。

#### Scenario: 模板随请求发送
- **WHEN** 用户选择应用和模板提问
- **THEN** system/user messages 包含该模板渲染内容，trace 包含 template_id、version 和 messages

### Requirement: 班级限定知识库绑定
系统 MUST 按服务端用户班级检索知识库，最多发送四条命中切片，不得发送整个知识库；无命中 MUST 不调用模型。

#### Scenario: 知识上下文可验证
- **WHEN** 用户在绑定知识库的应用中提问
- **THEN** trace 包含命中的 chunk/source，且模型 messages 只包含这些内容

### Requirement: Skill 管理与受控执行
系统 MUST 提供内置 Skill 和教师上传 Skill。绑定 Skill 时 MUST 将完整 instructions 加入模型上下文，并记录长度和哈希。Skill action MUST 使用白名单，未知动作或代码执行请求必须拒绝。

#### Scenario: 上传 Skill
- **WHEN** 教师上传声明式 Skill
- **THEN** Skill 可在工作台选择，不能执行任意代码

### Requirement: 外部工具与 MCP
系统 MUST 支持注册工具并将已绑定工具 schema 传给模型；MCP 工具调用必须校验名称、参数和超时，trace 记录 schema、参数、结果和状态。未配置工具时返回明确错误。

#### Scenario: 工具调用可追溯
- **WHEN** 模型返回已注册工具调用
- **THEN** 服务端执行 allowlisted 工具并将结果作为 tool message 回填，trace 可查看完整业务参数

### Requirement: AI 请求审计与脱敏
每次 AI 请求 MUST 生成 request_id 和 trace，包含模型请求、绑定上下文、工具调用和返回内容；不得保存 Token、Cookie、密码或 API Key。

#### Scenario: 查看调用详情
- **WHEN** 已登录用户查看自己班级的请求详情
- **THEN** 返回脱敏 trace；跨班或未登录返回 401/404
