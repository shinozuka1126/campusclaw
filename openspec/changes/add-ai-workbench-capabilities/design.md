# Design

## 工作台与模板

AI 应用是带有 key、名称、用途、模型参数和默认模板的 profile。内置 chat、knowledge_qa、summarizer 三个 profile；应用和模板均按用户班级读取。请求选择应用和可选模板后，服务端渲染 system/user messages，trace 保存模板版本和渲染结果。

## 知识库上下文

knowledge_qa 和显式绑定知识库的应用先调用已有 hybrid_search_knowledge(g.user.class_id, question, 4)。发送给模型的上下文只包括命中的切片，trace 保存 chunk id、来源、字符数和未发送的候选数量。查询始终使用服务端班级，客户端不能扩大范围；无命中直接返回 no_context，不调用模型。

## Skill

Skill 使用声明式 JSON/Markdown 数据保存 name、version、instructions、action、allowed_tools。内置 Skill 提供 summarize_material 与 quiz_from_sources；教师可以上传 `.json`、`.md` 或 `.txt` Skill。上传内容只作为不可信提示和白名单声明，未知 action 返回 422，禁止 eval、exec、shell 或动态导入。绑定 Skill 时完整 instructions 放入模型 system/context，trace 保存内容长度和哈希。

## 外部工具与 MCP

工具注册包含 name、description、JSON schema、kind、endpoint、timeout 和 class_id。内置 knowledge_search 使用本地检索；MCP 工具使用最小 JSON-RPC adapter，支持 initialize、tools/list、tools/call。请求前将已绑定工具的 schema 放入模型 tools；模型 tool call 只能调用已注册工具并通过 schema 基础校验，结果以 tool message 回填。未配置或失败返回通用 503，不展示密钥和上游原文。

## Trace

每次请求生成 request_id，保存 provider、model、temperature、max_tokens、messages、tools、template、knowledge policy、skill 摘要、tool calls、响应和状态。字段截断并脱敏，禁止 Authorization、Cookie、密码、API Key。用户只能查看自己班级的 trace；教师可查看本班记录。
