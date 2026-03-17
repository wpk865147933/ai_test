# 缓存管理指南

## 概述

建筑和条件列表数据相对稳定，系统自动缓存以提升性能。

## 缓存效果

- ✅ **首次预订**：从 API 获取并自动缓存（速度稍慢）
- ✅ **后续预订**：直接使用缓存（**速度快 40%**）
- ✅ **自动过期**：7 天后自动失效，下次重新获取

## 缓存位置和文件

```
~/.catpaw/skills/room-booking-helper/resources/cache/
├── buildings_cache.json    # 城市、建筑、楼层列表（~120KB）
└── conditions_cache.json   # 设备、容量、窗户等条件（~1KB）
```

### buildings_cache.json 结构

```json
{
  "timestamp": 1710604800000,  // 缓存创建时间戳
  "data": [
    {
      "code": 3531,
      "name": "北京市",
      "type": "city",
      "children": [
        {
          "code": 843,
          "name": "北京/保利广场西座",
          "type": "building",
          "children": [
            {
              "code": 2001,
              "name": "2层",
              "type": "floor"
            }
          ]
        }
      ]
    }
  ]
}
```

### conditions_cache.json 结构

```json
{
  "timestamp": 1710604800000,
  "capacity_ranges": [
    {"min": 1, "max": 6, "name": "1-6人"},
    {"min": 7, "max": 14, "name": "7-14人"}
  ],
  "window_options": [
    {"key": "EXIST", "name": "有窗"},
    {"key": "NONE", "name": "无窗"}
  ]
}
```

## 缓存管理命令

### 查看缓存状态

```bash
python3 ~/.catpaw/skills/room-booking-helper/resources/cache_manager.py
```

输出示例：
```
✅ 缓存状态
├─ buildings_cache.json: 存在，3天前更新
├─ conditions_cache.json: 存在，3天前更新
└─ 总大小: 121.5 KB
```

### 手动清除所有缓存

```bash
python3 -c "from cache_manager import CacheManager; c = CacheManager(); c.clear_all_cache(); print('✅ 缓存已清除')"
```

或直接删除缓存文件：

```bash
rm -f ~/.catpaw/skills/room-booking-helper/resources/cache/*.json
```

### 清除特定缓存

```bash
# 只清除建筑缓存
rm -f ~/.catpaw/skills/room-booking-helper/resources/cache/buildings_cache.json

# 只清除条件缓存
rm -f ~/.catpaw/skills/room-booking-helper/resources/cache/conditions_cache.json
```

## 缓存失效场景

### 自动失效

- **过期时间**：7 天
- **触发时机**：执行 `quick_book.py` 时检查，若超过 7 天自动重新获取

### 手动失效

需要立即更新缓存的情况：

1. **新增建筑** - 系统添加了新的办公楼或楼层
   - **解决方案**：清除 `buildings_cache.json`

2. **设备或容量范围变更** - API 定义的条件有更新
   - **解决方案**：清除 `conditions_cache.json`

3. **缓存文件损坏** - 缓存数据异常导致预订失败
   - **解决方案**：清除所有缓存并重试

4. **测试环境重置** - 开发或测试期间重置数据
   - **解决方案**：清除所有缓存

## 缓存失败处理

### 当前行为

如果预订时使用的建筑或条件缓存已过期：

1. API 返回"建筑不存在"或"条件不符"错误
2. Quick Book 终止并提示用户
3. 用户需要手动清除缓存并重试

### 改进方案（待实现）

建议添加"自动清除缓存重试"的逻辑：

```python
# 伪代码
try:
    result = quick_book(...)
except BuildingNotFoundError:
    # 缓存可能已过期
    cache_manager.clear_cache('buildings')
    result = quick_book(...)  # 重试
```

## 缓存工作流程

```
调用 quick_book.py
    ↓
检查缓存是否存在且未过期？
    ├─ 是 → 使用缓存
    │   ↓
    │   预订操作...
    │
    └─ 否 → 调用 API 获取
        ↓
        保存到缓存文件
        ↓
        使用新数据进行预订操作...
```

## 性能数据

| 场景 | 响应时间 | 说明 |
|------|---------|------|
| 首次预订（API获取） | 1-2 秒 | 包括建筑列表 HTTP 请求 |
| 使用缓存的预订 | 200-500 ms | 直接使用本地缓存 |
| 缓存查询模糊匹配 | < 10 ms | 纯 CPU 操作 |
| 预订和查询总耗时 | 2-5 秒 | 含网络请求 |

## 最佳实践

### ✅ 建议做法

1. **正常使用时** - 让系统自动管理缓存，无需手动干预
2. **定期检查** - 每周运行一次 `cache_manager.py` 检查状态
3. **重大更新后** - 如果发现建筑信息错误，立即清除缓存
4. **测试或调试** - 使用 `--update-cache` 参数强制刷新（待实现）

### ❌ 避免做法

1. 不要频繁手动清除缓存（影响性能）
2. 不要修改缓存文件内容（可能导致数据不一致）
3. 不要在缓存目录添加其他文件（可能被意外删除）

## 故障排除

### 问题：缓存文件损坏导致预订失败

**现象**：
```
Error: JSON decode error in cache file
```

**解决方案**：
```bash
rm -f ~/.catpaw/skills/room-booking-helper/resources/cache/*.json
python3 quick_book.py --city 上海 --building D2 ...
```

### 问题：新增的建筑一直显示"不存在"

**原因**：缓存还未过期，包含的是旧数据

**解决方案**：
```bash
python3 -c "from cache_manager import CacheManager; c = CacheManager(); c.clear_cache('buildings'); print('✅ 建筑缓存已清除')"
```

### 问题：缓存文件过大

**现象**：`buildings_cache.json` 超过 200KB

**原因**：通常不是问题，只是包含了很多城市和建筑数据

**解决方案**：可选择删除，系统会自动重新获取

## 高级配置（待实现）

### 计划功能

1. **`--update-cache` 参数** - 强制刷新缓存而不检查过期时间
   ```bash
   python3 quick_book.py --update-cache --city 上海 ...
   ```

2. **增量缓存更新** - 只更新变化部分，而非全量重新获取
   
3. **缓存版本机制** - 服务端告知客户端缓存是否最新

4. **智能过期策略** - 根据实际使用频率动态调整缓存时间

5. **缓存统计** - 记录缓存命中率和性能指标
