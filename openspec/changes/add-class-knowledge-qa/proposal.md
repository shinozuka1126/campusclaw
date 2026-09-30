# 基于本班知识库的 AI 问答

## Why
0930 课堂任务要求：在当前班级内混合检索，取前 4 条切片生成简短回答，使用 [1]、[2] 引用并展示原文。未命中不调用模型，明确告知资料中没有。

## What Changes
- 新增 `/knowledge` 双页签界面与 `POST /api/knowledge/ask`、`GET /api/knowledge/retrieve`。
- 本地 BM25 关键词排序和 TF-IDF 词项向量余弦排序融合；保留原精确子串检索接口。
- 服务端调用 DeepSeek，根据最多 4 条本班片段回答，引用由服务器绑定到已有材料。
- 新增课堂演示 Markdown 材料、配置说明、失败路径和验收测试。

## Impact
沿用 SQLite 持久化切片、Cookie/Bearer 认证和服务端班级隔离。模型密钥只在服务端；不引入额外向量数据库、嵌入模型或多轮历史存储。
