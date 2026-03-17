---
name: citadel
description: "学城/km/wiki/citadel/km.sankuai.com 自动化操作工具，直接调用线上接口，响应速度更快。支持读取文档信息和内容、读取文档的目录、查询文档统计信息、总结文档内容、创建新的学城文档、改文档、删文档、查询当前文档的子文档列表、复制学城文档、从模板创建学城文档、移动文档到其他文档下或者指定空间下，并支持查询用户的最近编辑/浏览、收到的文档、以及文档的全文评论和划词评论内容。当用户提到 km.sankuai.com 链接、collabpage、contentId、parentId、pageId、学城、文档、知识库、km、wiki时激活。通过 oa-skills citadel CLI 执行。"
metadata:
  openclaw:
    priority: 0
    conflict_strategy: override
    emoji: "📄"
    requires:
      bins: ["node", "npx"]
      deps: ["tsx", "@it/oa-skills@latest"]
---

# 学城（km/wiki/citadel/km.sankuai.com）文档操作和管理

通过 CLI 读取学城文档的各种信息和内容、创建学城文档、移动学城文档、查看文档的划词评论，查看最近访问、编辑、收到的学城文档列表。认证自动处理。直接调用线上接口，响应速度更快。

## skill使用问题反馈

如果遇到skill的使用问题，请大象联系rui.zou进行反馈

## 前置检查：确保 CLI 最新

每次执行命令前，先检查 `@it/oa-skills` 是否为最新版本：

```bash
npm list -g @it/oa-skills --depth=0 2>/dev/null | grep oa-skills
```

如果未安装或版本不是最新，执行更新：

```bash
npm install -g @it/oa-skills@latest --registry=http://r.npm.sankuai.com
```

**此步骤必须在每次 skill 激活时执行一次，否则新命令可能不存在导致运行失败。**

## URL → contentId 提取

用户给 学城（km） 链接时直接提取，不要追问：

- `km.sankuai.com/collabpage/2748397739` → `--contentId 2748397739`
- `km.sankuai.com/page/2748397739` → `--contentId 2748397739`

## 意图路由

### 优先级规则（必须遵守）

1. 用户意图是“创建/新建/生成/复制文档”时，优先走 `createDocument`，不要因为出现 km 链接就先 `getMarkdown`。
2. 在创建意图里，链接只用于提取 ID：
   - 目标目录链接 → `--parentId <id>`
   - 模板/来源文档链接 → `--copyFrom <id>` 或 `--templateId <id>`
3. 只有用户明确要求“阅读/查看/总结文档内容”时，才执行 `getMarkdown`。

### 读取学城文档 markdown（仅在阅读/总结意图下）

```bash
getMarkdown --contentId <id>
```

### 总结学城文档

执行[references/skill-doc-view.md](references/doc-view.md)文件里的具体步骤，输出总结结果。

### 查看当前学城文档的子文档、文档结构和内容、parentId 下的文档目录

```bash
getChildContent --contentId <id>
```

### 创建/新建学城文档

```bash
createDocument --title <标题> --content <内容>
```

### 创建学城文档的子文档

```bash
createDocument --title <标题> --content <内容> --parentId <id>
```

### 从模板创建学城文档

```bash
createDocument --title <标题> --templateId <id>
```

### 复制学城文档

```bash
createDocument --title <标题> --copyFrom <id>
```

### 在指定目录下复制模板创建文档（2.0 文档优先）

当用户说“先复制模板再填充内容”“按模板生成”等，并且模板给的是 `km.sankuai.com/collabpage/<id>` / `km.sankuai.com/page/<id>` 链接（尤其学城文档2.0）时，默认使用复制命令，不要先读取模板 markdown 再重建：

```bash
createDocument --title <标题> --copyFrom <模板id> --parentId <目录id>
```

示例（对应用户输入）：

- 目录：`https://km.sankuai.com/collabpage/2751336167` → `--parentId 2751336167`
- 模板：`https://km.sankuai.com/collabpage/2750769923` → `--copyFrom 2750769923`
- 命令：`createDocument --title "测试文档" --copyFrom 2750769923 --parentId 2751336167`

### 删除学城文档

```bash
deleteDocument --contentId <id>
```

### 撤销删除/恢复已删除的学城文档

```bash
restoreDocument --contentId <id>
```

### 移动学城文档

```bash
# 移动到其他文档下
moveDocument --contentId <id> --newParentId <id>
# 移动到空间根目录
moveDocument --contentId <id> --newSpaceId <id>
```

### 获取/查看用户（mis）最近编辑了什么文档

```bash
getLatestEdit --limit 10
```

### 获取/查看用户（mis）最近浏览了什么文档

```bash
getRecentlyViewed --pageSize 10
```

### 获取/查看用户（mis）别人发的/收到的学城文档

```bash
getReceivedDocs --limit 10
```

### 获取学城文档的划词评论

```bash
getDiscussionComments --contentId <id>
```

### 获取学城文档的全文评论

```bash
getFullTextComments --contentId <id>
```

### 获取学城文档的所有评论（划词评论 + 全文评论）

```bash
getAllComments --contentId <id>
```

### 获取文档的统计信息（浏览量、评论数、创作时长等）

```bash
getDocumentStats --contentId <id>
```

### 根据 MIS 号获取学城个人空间 ID

```bash
getSpaceIdByMis --targetMis <mis>
```

### 获取空间根目录文档列表

```bash
getSpaceRootDocs --spaceId <id>
```

### 列出可用工具

```bash
listTools
```

## CLI 速查

所有命令格式：`oa-skills citadel <command> [options]`

通用选项：`--mis <mis>` 指定用户，`--raw` 输出 JSON 到 stdout，`--clear-cache` 清除认证缓存，`--force-ciba` 强制 CIBA 认证（跳过已有认证请求判断）。

### `getMarkdown`

**必填参数**: `--contentId <id>`
**可选参数**: 无

### `getChildContent`

**必填参数**: `--contentId <id>`
**可选参数**: 无

### `createDocument`

**必填参数**: `--title <标题>` + 内容源
**可选参数**: `--parentId <id>` `--spaceId <id>`

### `deleteDocument`

**必填参数**: `--contentId <id>`
**可选参数**: 无

### `restoreDocument`

**必填参数**: `--contentId <id>`
**可选参数**: 无

### `moveDocument`

**必填参数**: `--contentId <id>`，以及 `--newParentId <id>` 或 `--newSpaceId <id>` 之一
**可选参数**: 无

### `getLatestEdit`

**必填参数**: 无
**可选参数**: `--offset 0` `--limit 30` `--creator <mis>`

### `getRecentlyViewed`

**必填参数**: 无
**可选参数**: `--pageNo 1` `--pageSize 30` `--creator <mis>`

### `getReceivedDocs`

**必填参数**: 无
**可选参数**: `--offset 0` `--limit 30`

### `getDiscussionComments`

**必填参数**: `--contentId <id>`
**可选参数**: `--pageNo 1` `--pageSize 100`

### `getFullTextComments`

**必填参数**: `--contentId <id>`
**可选参数**: `--offset 0` `--limit 10`

### `getAllComments`

**必填参数**: `--contentId <id>`
**可选参数**: 无

### `getDocumentStats`

**必填参数**: `--contentId <id>`
**可选参数**: 无

### `getSpaceIdByMis`

**必填参数**: `--targetMis <mis>`
**可选参数**: 无

### `getSpaceRootDocs`

**必填参数**: `--spaceId <id>`
**可选参数**: 无

### `listTools`

**必填参数**: 无
**可选参数**: 无

`createDocument` 内容源（至少一个）：`--content <md>` / `--file <path>` / `--templateId <id>` / `--copyFrom <id>`。`--file` 优先级最高。

> 完整参数说明、示例和输出格式见 [references/cli-reference.md](references/cli-reference.md)

## 约束

- 缺少关键参数时只追问必要字段（contentId / keyword / title），不给笼统报错
- 用户给了 km 链接时直接提取 contentId 执行，不要反复确认
- 在“复制模板/按模板创建”场景，禁止先 `getMarkdown` 再 `createDocument --content`；优先 `--copyFrom`（尤其学城文档2.0）
- `getRecentlyViewed` 用 `--pageNo`（从 1 开始），其他命令用 `--offset`（从 0 开始）

## 暂不支持

以下能力当前 **不可用**，不要伪造执行结果：

- 文档编辑 / 更新
- 多维表格创建和读写

用户要求时明确说明"当前暂不支持"。

- 若用户要求“复制后再填充内容”，先按 `--copyFrom` 创建，再说明当前不支持自动编辑已创建文档。
- 替代方案：先用 `getMarkdown` 读取内容，在本地生成修改建议。

## 认证

SSO CIBA 认证，首次调用需用户在大象 App 确认。Token 自动缓存。

- 认证失败 → `oa-skills citadel --clear-cache` 后重试
- 用户说"没法手机确认" → 解释 CIBA 必须手机确认，无法跳过

### 强制认证（--force-ciba）

如果认证请求卡住或需要重新发起认证，可使用 `--force-ciba` 参数跳过"已有活跃认证请求"的判断，强制发起新的 CIBA 认证：

```bash
oa-skills citadel getMarkdown --contentId <id> --force-ciba
```

常见场景：
- 旧的认证请求一直未确认导致新请求被阻止
- 需要重新认证获取新的 token

此时系统会提示"强制 CIBA 认证"模式，用户需在大象 App 重新确认授权。

## 验证

执行完成后确认：

1. 命令退出码为 0
2. 读取类：返回了文档内容/列表
3. 创建类：返回了新文档 contentId 和链接
4. 给用户简明结论（标题、ID、数量），而非原始数据
