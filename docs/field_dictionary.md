# 字段字典 · 数据导入与编码指南

## 导入数据时的字段映射

### CSV/XLSX 导入列名对照

| 中文列名 | 英文列名 | 类型 | 说明 |
|---------|---------|------|------|
| 平台 | platform | douyin/kuaishou | 如可从URL解析，可不填 |
| 视频ID | platform_video_id | 数字/字符串 | 从URL提取的纯数字或字母ID |
| 视频链接 | video_url | URL | 完整链接 |
| 短链接 | short_url | URL | v.douyin.com 短链 |
| 标题 | video_title | 文本 | |
| 描述 | video_description | 文本 | |
| 标签 | hashtags | 逗号分隔 | 如 "AI数字人, 带货" |
| 发布时间 | publish_time | 日期 | 如 2024-01-15 |
| 时长秒 | duration_seconds | 整数 | |
| 封面URL | cover_url | URL | |
| 作者名 | author_name_public | 文本 | 公开显示的昵称 |
| 作者ID | author_id_raw | 字符串 | 平台原始ID（将自动哈希化） |
| 作者粉丝数 | follower_count | 整数 | |
| 点赞数 | like_count | 整数 | 不可见时留空 |
| 评论数 | comment_count | 整数 | 不可见时留空 |
| 分享数 | share_count | 整数 | 不可见时留空 |
| 收藏数 | favorite_count | 整数 | 不可见时留空 |
| 播放数 | view_count | 整数 | 不可见时留空 |
| 搜索关键词 | collection_keyword | 文本 | 搜索时使用的关键词 |
| 搜索排名 | search_result_rank | 整数 | 在搜索结果中的位置 |
| 搜索排序 | search_sort_mode | comprehensive/hot/latest | |

## 编码字段参考

### AI角色出现 (ai_character_present)
判断视频中是否出现AI生成的虚拟角色（数字人、AI萌娃、AI孙女/孙子等）。

- `true`: 视频中出现明显的AI生成/合成人物
- `false`: 视频中为真实人物或未出现人物

### AI身份披露 (ai_identity_disclosed)
判断视频是否明确告知观众画面中的人物是AI生成的。

- `true`: 在视频字幕、描述、标签或口播中明确说明使用了AI/数字人
- `false`: 未披露AI身份

### 亲属称谓出现 (kinship_address_present)
判断视频中是否使用了面向老年观众的亲属称谓。

- `true`: 使用了如"爷爷"、"奶奶"、"外婆"等称呼
- `false`: 未使用

### 亲属称谓文本 (kinship_address_text)
记录视频中出现的具体亲属称谓词语，多个用逗号分隔。

### 孙辈角色扮演 (grandchild_role_enactment)
判断AI角色是否扮演孙辈（孙女/孙子）角色。

- `true`: 明确以孙子/孙女身份出现
- `false`: 不是

### 关怀语言出现 (care_language_present)
判断视频中是否有表达关心/关怀老年观众的语言。

- `true`: 有
- `false`: 无

### 礼物语言出现 (gift_language_present)
判断是否提及送礼物给老年观众。

### 情感诉求 (emotional_appeal)
- `nostalgia`: 怀旧情感
- `warmth`: 温暖/亲情
- `fear`: 恐惧/健康担忧
- `humor`: 幽默
- `none`: 无明显情感诉求

### 理性诉求 (rational_appeal)
- `price`: 价格强调
- `efficacy`: 功效说明
- `quality`: 质量强调
- `comparison`: 对比
- `none`: 无明显理性诉求

### 产品类别 (product_category)
推广产品的分类，如：保健品、日用品、医疗器械、食品等。

### 健康声称出现 (health_claim_present)
判断是否宣称产品有健康功效。

### 购买指引出现 (purchase_instruction_present)
判断是否提供购买方式或引导下单。

## 重要规则

1. **不可见≠不存在**: 某字段不可见时保存为null，绝对不要填0
2. **不要猜测**: 无法确定的字段留空
3. **编码证据**: publisher_type_evidence 和 coding_notes 字段用于记录编码依据
4. **年龄推断**: 不得根据头像或昵称推断评论者年龄，仅记录 self_disclosed_age
