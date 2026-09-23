# 迭代 1 设计与发布记录

## 决策 1：Flask + SQLite

本迭代选择 Flask + SQLite，是因为需求规模是单实例课堂演示，Python 标准库能直接管理 SQLite，减少部署依赖；后续需要多实例时再单独提出迁移变更。

## 决策 2：服务端 signed-cookie session

登录后的会话由 Flask 签名 cookie 携带 `user_id`、`role`、`class_id`。这样每个请求都能统一做身份、角色和班级校验；本迭代不引入 JWT 刷新、OAuth 或 SSO 的额外边界。

## 决策 3：单库按 class_id 隔离

两班共用一个 SQLite 文件，但所有材料列表、详情、下载和上传写入都由服务端使用会话班级过滤。这样跨班越权有明确的 404 失败路径，也能用一组双班种子数据复现验收。

## 发布记录

- 版本：`v0.1.0-auth-upload`
- 规约：`openspec/specs/auth-upload/spec.md`
- 归档 change：`openspec/changes/archive/2026-09-23-add-auth-rbac-class-knowledge/`
- 验收：`pytest -q` 通过 9 项；严格 OpenSpec 校验通过；活动 change 已归零。
