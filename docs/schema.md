# 数据库 Schema 设计文档

## 概述

抖音-快手AI数字人短视频内容分析数据管理工具使用关系型数据库（开发阶段SQLite，正式阶段可切换PostgreSQL）。所有用户ID、评论者ID均经过SHA-256哈希化处理。

## ER 关系图

```
users ─────1:N────> audit_logs
  │
  └──────1:N────> coding_records
  │
  └──────1:N────> search_sessions (created_by)

authors ────1:N────> videos

videos ─────1:N────> metric_snapshots
  │
  ├──────1:N────> comments
  │
  ├──────1:N────> coding_records
  │
  ├──────1:N────> media_files
  │
  ├──────1:N────> transcripts
  │
  ├──────1:N────> keyframes
  │
  └──────M:N────> search_sessions (via session_videos)
```

## 表清单

| 表名 | 用途 | 核心唯一约束 |
|------|------|------------|
| `users` | 系统用户（编码者） | `username` UNIQUE |
| `authors` | 发布者信息 | (platform, author_id_hash) |
| `videos` | 视频核心实体 | (platform, platform_video_id) UNIQUE |
| `metric_snapshots` | 互动指标时间序列 | 无（允许同一视频多次采集） |
| `comments` | 评论数据 | 无（comment_id_hash可能重复） |
| `coding_records` | 编码记录 | 无 |
| `media_files` | 媒体文件档案 | 无 |
| `transcripts` | 语音转录 | 无 |
| `keyframes` | 关键帧 | 无 |
| `audit_logs` | 修改审计日志 | 无 |
| `search_sessions` | 检索任务 | 无 |
| `session_videos` | 检索任务-视频关联 | (session_id, video_id) PK |

## 关键字段说明

### verification_status
- `unverified`: 待人工复核
- `verified`: 已复核通过
- `needs_review`: 需要再次审核
- `flagged`: 已标记（有问题）

### unavailable_reason
- `deleted_by_author`: 作者自行删除
- `removed_by_platform`: 平台下架
- `private_or_permission_changed`: 权限变更为私密
- `link_invalid`: 链接失效
- `region_or_login_restricted`: 地区或登录限制
- `unknown`: 未知原因

### collection_method
- `official_api`: 平台官方API
- `researcher_browser`: 研究者浏览器提取
- `manual_import`: 手工导入
- `licensed_provider`: 授权第三方数据服务

### publisher_type_coded
- `individual_creator`: 个人创作者
- `merchant_or_brand`: 商家/品牌
- `health_professional`: 健康专业人士
- `media_or_institution`: 媒体/机构
- `virtual_influencer_account`: 虚拟网红账号
- `unclear`: 无法判断

### metric_visibility（JSON，每个指标一个状态）
- `visible`: 公开可见
- `unavailable_not_displayed`: 页面未显示
- `unavailable_not_authorized`: 需要授权
- `unavailable_platform_restricted`: 平台限制
- `unavailable_parse_failed`: 解析失败
