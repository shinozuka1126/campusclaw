# AI 工作台与可验证工具链

## Why

阶段性验收要求个人项目具备多个 AI 应用、提示词模板、知识库检索、内置和可上传 Skill，以及外部工具/MCP 接入，并能说明每次请求实际发送给模型的内容。现有项目只有固定的知识库问答接口，无法查看模板、Skill、工具和模型请求之间的关系。

## What Changes

- 增加班级范围的 AI 应用配置、提示词模板和 AI 工作台。
- 复用已有知识库检索，为绑定知识库的请求只发送命中的片段。
- 增加内置 Skill 与教师上传的声明式 Skill，并用白名单动作执行。
- 增加外部工具/MCP 注册、工具 schema 传递、工具调用校验和调用记录。
- 保存脱敏的 AI trace，展示模板、知识库、Skill、工具、模型参数和返回结果。

## Impact

沿用已有 Token/Cookie 认证和服务端班级隔离。默认使用 DeepSeek；测试使用本地替身，不依赖真实 API Key 或外部 MCP 服务。不会执行上传 Skill 中的 Python、Shell 或 JavaScript，不会把 Authorization、Cookie、密码或 API Key 写入审计记录。
