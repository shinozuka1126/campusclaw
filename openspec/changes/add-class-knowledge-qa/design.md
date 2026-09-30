# Design

## 检索和证据
先从 SQLite 读取当前用户数据库班级的片段，JOIN 材料校验双表班级一致。对中文二字词组/英文词分词，去掉常见问句词；分别用 BM25 与 TF-IDF cosine 排序，通过 reciprocal rank fusion 合并，按分值和 chunk_id 稳定排序。只保留有实质词项重合的候选，取最多 4 条。此实现是稀疏词项向量混合检索，不声称具备预训练语义嵌入能力；同义词、复杂改写召回是限制。

## 问答
`POST /api/knowledge/ask` 接收 JSON `{question: string}`（1–500 字），拒绝非对象/非法类型。使用 g.user 的班级，忽略客户端 class_id。空结果直接返回 status=no_context、sources=[]、model_called=false；无需密钥也不发送任何模型请求。

命中时调用 DeepSeek chat completions，messages 仅含当前问题和最多 4 条原文（不发送 Cookie、JWT、用户名/密码）。system 明确原文为数据，不得遵循材料中的指令；只据来源作答，每条事实带 [n]。DEEPSEEK_API_KEY、DEEPSEEK_MODEL、DEEPSEEK_BASE_URL 从环境读取，默认官方 HTTPS 地址及 deepseek-chat。连接有超时及输出长度限制，不自动重试，错误不回显供应商原始响应。

返回 `{status, question, answer, sources, model_called, model}`。source 包含 citation_id、material_id、material_title、chunk_id、chunk_index、start_offset、end_offset、content、source_url、download_url。检测引用编号必须在 sources 范围内且回答至少含有效引用；引用缺失/越界返回生成失败，不凭空补引用。保留全部检索证据。引用范围检查不能证明答案每句话均受原文支持，用户仍可核对原文。

## 页面与兼容性
独立 `/knowledge` 页面通过现有 token 发起 fetch，无 token 时兼容 cookie。提供问题输入、等待提示、答案与原文引用；纯文本 textContent 渲染模型/文件正文避免 HTML 注入，失败可重试，不把 token 放到 URL。跳转原文/下载沿用受保护的材料路由。原材料页提供入口和成功上传反馈；原搜索接口保持兼容。

## 运行与数据
演示材料放在 examples/science-a.md，教师按真实上传流程入库；不修改已有数据库/材料、不自动添加样例。Docker 重建保留 data/uploads。网络请求超时小于 gunicorn 请求超时。完整外部模型验收需用户在本机填写密钥，测试替身结果不能标为真实 DeepSeek 回答。
