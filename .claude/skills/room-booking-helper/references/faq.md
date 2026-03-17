# 常见问题 (FAQ)

## Cookie 和认证

### Q: 如何配置 Cookie？

**CatPaw Desk 环境（全自动，无需操作）**：

`quick_book.py` 会自动检测 `~/.catpaw/sso_config.json`，调换票接口获取 `calendar.sankuai.com` 专属 token，无需任何手动操作。

**Sandbox 环境（CIBA 大象授权）**：
```bash
python3 ~/.catpaw/skills/room-booking-helper/scripts/rbh_sso.py ciba-login wangjun137
```
在大象中点击授权后，cookie 自动保存到 `cookie.json`。

**手动方式（兜底）**：
1. 打开 https://calendar.sankuai.com 并完成 SSO 登录
2. 按 **F12** 打开开发者工具，复制 Network 标签中任意请求的 Cookie 头
3. 运行：`python3 ~/.catpaw/skills/room-booking-helper/scripts/rbh_sso.py save-cookie "<cookie_str>"`

### Q: Cookie 过期了怎么办？

Cookie 有效期约 2-4 小时。过期后：

1. **CatPaw Desk 环境**：自动从 sso_config.json 重新换票，无需手动操作
2. **Sandbox 环境**：重新运行 `ciba-login` 命令
3. **本地环保**：如果提示 401 错误，按照上面"手动保存"流程重新获取

## 预订功能

### Q: quick_book.py 什么时候会自动创建监测任务？

**自动触发情况**：
- 找不到任何空闲会议室时
- 所有空闲会议室都已下线时
- 所有预订尝试都失败时

系统会自动调用监测接口，您无需手动操作。

### Q: 为什么预订失败了？

常见失败原因：

1. **认证过期** - Cookie 已过期
   - **解决方案**：重新获取 Cookie（见上文）

2. **时间范围超过预订窗口** - 预订日期超过 8 天（普通）或 30 天（培训）
   - **解决方案**：调整预订日期

3. **容量不匹配** - 所有空闲房间容量都不符合要求
   - **解决方案**：调整人数需求或增加备选容量范围

4. **建筑或楼层不存在** - 建筑名称输入错误或已下线
   - **解决方案**：检查建筑名称是否正确

5. **单间会议室预订超限** - 同一账号每天在同一间会议室最多预订 3 次
   - **解决方案**：选择不同的会议室或日期

6. **用户权限问题** - MIS 账号无效或权限不足
   - **解决方案**：验证 MIS 账号是否正确

更多详情见 **[📖 reference.md](../reference.md)** 中的错误码说明。

### Q: 如何指定参会人？

只需提供参会人的 MIS 账号，脚本会自动通过接口转换为 empId：

```bash
python3 quick_book.py \
  --city 上海 --building D2 --date 2026-03-10 --start 12:00 --end 13:00 \
  --attendees wb_zhuxinglong wangjun137
```

参会人字段接受 MIS 账号列表（如 `wb_zhuxinglong`、`wangjun137`），脚本会自动调用员工信息查询接口（API 6）将每个 MIS 转换为对应的 empId，无需手动处理。

### Q: 支持取消或修改预订吗？

目前 quick_book.py 只支持新建预订。如需取消或修改，请使用完整 Agent 流程。

## 高级功能

### Q: 如何使用高级筛选（设备、窗户等）？

目前 Quick Book 支持的筛选参数有限。对于高级需求（如指定投影仪、Zoom 设备等），请使用完整 Agent 流程。

### Q: 可以预订周期性会议室吗？

Quick Book 只支持单日期预订。

### Q: 可以跨天预订吗？

 Quick Book 只支持同日期的预订。

## 性能和优化

### Q: 预订速度慢吗？

**首次预订**：会从 API 获取并缓存建筑列表，速度可能稍慢（1-2 秒）
**后续预订**：直接使用本地缓存，速度快 40%（几百毫秒）

缓存在 7 天后自动失效并重新获取。

### Q: 如何清除缓存？

```bash
# 查看缓存状态
python3 ~/.catpaw/skills/room-booking-helper/resources/cache_manager.py

# 手动清除缓存
python3 -c "from cache_manager import CacheManager; c = CacheManager(); c.clear_all_cache(); print('✅ 缓存已清除')"

# 或直接删除缓存文件
rm -f ~/.catpaw/skills/room-booking-helper/resources/cache/*.json
```

缓存已自动集成到 `quick_book.py` 中，无需手动管理。仅在需要重置时使用上述命令。

## 技术细节

### Q: 时间精度是多少？

系统会自动将时间四舍五入到 5 分钟倍数。例如：
- `12:02` → `12:00`
- `12:03` → `12:05`
- `12:07` → `12:05`
- `12:08` → `12:10`

### Q: 查询时间范围有限制吗？

API 仅支持查询 **7 天内** 的会议室数据。超过 7 天的请求会返回错误。

### Q: 支持哪些时长的预订？

单次预订时长限制为：**5 分钟 ~ 240 分钟（4 小时）**

超出范围会拒绝预订。

### Q: 预订窗口是多久？

- **普通会议室**：每日 9:30 开放未来 8 个自然日内的预订权限
- **培训会议室**：每日 9:30 开放未来 30 个自然日内的预订权限

区分方式：会议室名称中包含"培训"二字的为培训会议室。

## 故障排除

### Q: 脚本运行出错，如何查看详细日志？

虽然目前没有完整的日志输出，但可以查看 Python 的标准错误输出：

```bash
python3 quick_book.py --city 上海 --building D2 --date 2026-03-10 --start 12:00 --end 13:00 2>&1 | cat
```

关键的错误信息会输出到控制台。

### Q: 某个建筑匹配失败，提示"未找到建筑"

可能的原因：
1. 建筑名称有多个匹配项（如"D"可能匹配 D1、D2、D3）
2. 建筑已下线或名称改变
3. 城市名称错误

**解决方案**：
- 使用完整 Agent 流程，交互式选择建筑
- 或使用更唯一的建筑名称（如"互联D2"而非"D2"）

### Q: API 返回 401 或 30002 错误

这表示认证已过期。请重新获取 Cookie：

**CatPaw Desk 环境**：通常会自动重试，不需要手动操作

**Sandbox 环境**：
```bash
python3 ~/.catpaw/skills/room-booking-helper/scripts/rbh_sso.py ciba-login <misId>
```

### Q: 某些功能不支持，下一步是什么？

参考 **[📖 references/boundaries.md](boundaries.md)** 了解 Quick Book vs Agent 的功能差异，根据您的需求选择合适的方式。
