# 会议室预订 Skill - 本地缓存优化

## 概述

本目录包含会议室预订 Skill 的优化模块，主要功能是通过本地缓存减少 API 调用次数。缓存功能已集成到 `quick_book.py` 中，自动管理建筑列表数据。

## 文件说明

### cache_manager.py
缓存管理核心模块，由 `quick_book.py` 自动调用，提供以下功能：

- **检查缓存有效性**：`is_buildings_cache_valid()`, `is_conditions_cache_valid()`
- **获取缓存数据**：`get_buildings_cache()`, `get_conditions_cache()`
- **保存缓存数据**：`save_buildings_cache()`, `save_conditions_cache()`
- **清除缓存**：`clear_buildings_cache()`, `clear_conditions_cache()`, `clear_all_cache()`
- **查看缓存状态**：`get_cache_status()`

**缓存配置**：
- 缓存路径：`resources/cache/`
- 建筑缓存文件：`buildings_cache.json` (~788KB)
- 条件缓存文件：`conditions_cache.json`（预留）
- 缓存过期时间：7 天

### quick_book.py
一体化快速会议室预订脚本，**已集成缓存功能**：

- **第一次运行**：自动从 API 获取城市、建筑、楼层数据并缓存
- **后续运行**：优先使用本地缓存，加快预订速度（~1.5s vs 无缓存）
- 当缓存过期时自动刷新
- **支持参数**：
  - `--city`：城市名称（如 "上海"）
  - `--building`：建筑名称（如 "D2"）
  - `--date`：日期（格式：YYYY-MM-DD）
  - `--start`：开始时间（格式：HH:MM）
  - `--end`：结束时间（格式：HH:MM）
  - `--capacity`：容纳人数（默认 5 人）
  - `--floors`：楼层筛选（可选，不指定则查询所有楼层）
  - `--window`：窗户筛选（EXIST/NONE）
  - `--equips`：设备筛选（如 Zoom 投影 等）
  - `--mis`：MIS 账号
  - `--attendees`：参会人账号列表
  - `--interactive`：启用交互式模式

## 缓存工作流

```
快速预订请求
    ↓
quick_book.py 启动
    ↓
CacheManager.get_buildings_cache()
    ↓
缓存有效？
    ├─ 是 → 使用缓存数据（~立即）
    └─ 否 → API 获取 → CacheManager.save_buildings_cache() → 使用新数据
    ↓
继续预订流程
```

## 使用示例

### 快速预订（使用缓存）

```bash
# 第一次运行（会自动缓存）
python quick_book.py --city 上海 --building D2 --date 2026-03-15 --start 12:00 --end 13:00 --capacity 5

# 后续运行（使用缓存，更快）
python quick_book.py --city 上海 --building D2 --date 2026-03-16 --start 14:00 --end 15:00 --capacity 8
```

### 交互式预订

```bash
# 支持模糊城市和建筑搜索，自动从列表选择
python quick_book.py --interactive --city 上海 --date 2026-03-15 --start 12:00 --end 13:00
```

### 指定楼层和设备

```bash
# 限制楼层和设备
python quick_book.py --city 上海 --building D2 --date 2026-03-15 --start 12:00 --end 13:00 \
  --floors 4层 5层 --equips Zoom --capacity 8
```

## 性能对比

| 操作 | 无缓存 | 有缓存 | 提升 |
|------|--------|--------|------|
| 获取建筑列表 | ~1.5s | ~立即 | 1.5s |
| 第一次完整预订 | ~5-8s | ~5-8s | - |
| 后续预订 | ~5-8s | ~3-4s | 40% |
| 缓存文件大小 | - | ~788KB | - |

## 缓存更新策略

### 自动过期
- 缓存有效期：**7 天**
- 超过 7 天自动判定为过期
- 下次使用时会自动从 API 重新获取并更新缓存

### 手动清除（如需要）

如果要手动清除所有缓存，可以删除缓存文件：

```bash
# 删除缓存文件
rm -f /Users/wangjun/.catpaw/skills/room-booking-helper/resources/cache/*.json

# 或者在 Python 中清除
python3 -c "from cache_manager import CacheManager; c = CacheManager(); c.clear_all_cache(); print('✅ 缓存已清除')"
```

## 缓存数据结构

### buildings_cache.json（已缓存，~788KB）

存储城市、建筑、楼层的完整层级关系，从 API 1 (`/room/front/app/room/cityBuilding`) 的响应转换而来：

```json
{
  "cached_at": 1773570264396,
  "data": {
    "cityList": [
      {
        "cityId": 3531,
        "cityName": "北京市",
        "buildings": [
          {
            "buildingId": 843,
            "buildingName": "北京/保利广场西座",
            "floors": [
              {
                "floorId": 2001,
                "floorName": "2层"
              },
              {
                "floorId": 2002,
                "floorName": "3层"
              }
            ]
          }
        ]
      },
      {
        "cityId": 3532,
        "cityName": "上海市",
        "buildings": [
          {
            "buildingId": 335,
            "buildingName": "上海/互联D2栋",
            "floors": [...]
          }
        ]
      }
    ]
  }
}
```

**数据转换说明**：
- API 1 返回的原始格式使用 `code`/`parentCode`/`type`/`children` 字段
- 缓存时被优化为更清晰的结构：`cityId`/`cityName`/`buildings`/`floors`
- 提高了查询效率和代码可读性

### conditions_cache.json（预留，暂未使用）

将来用于缓存设备、容量、窗户等筛选条件，从 API 2 (`/room/front/pc/room/moreInfo`) 的响应保存：

```json
{
  "cached_at": 1773570264396,
  "data": {
    "equips": [
      {"id": 7, "name": "Zoom"},
      {"id": 9, "name": "腾讯会议"},
      {"id": 8, "name": "无线投屏"},
      {"id": 2, "name": "投影"},
      {"id": 3, "name": "电视"}
    ],
    "capacity": [
      {"capacityMin": 1, "capacityMax": 6, "name": "1-6人"},
      {"capacityMin": 7, "capacityMax": 14, "name": "7-14人"},
      {"capacityMin": 15, "capacityMax": 21, "name": "15-21人"},
      {"capacityMin": 22, "capacityMax": 40, "name": "22-40人"},
      {"capacityMin": 41, "capacityMax": 60, "name": "41-60人"},
      {"capacityMin": 61, "capacityMax": 1000, "name": "61人及以上"}
    ],
    "window": [
      {"code": "EXIST", "name": "有窗"}
    ]
  }
}
```

## 工作原理

1. **初始化阶段**：`quick_book.py` 启动时，初始化 `CACHE_MANAGER` 实例
2. **查询建筑**：在查询建筑前，调用 `CACHE_MANAGER.get_buildings_cache()`
   - 如果缓存有效，立即返回
   - 如果缓存不存在或过期，自动调用 `fetch_and_cache_buildings()` 从 API 获取
3. **保存缓存**：获取到 API 响应后，自动调用 `CACHE_MANAGER.save_buildings_cache()` 保存
4. **后续请求**：再次查询时直接使用缓存，无需 API 调用

## 注意事项

1. **缓存文件权限**
   - 缓存文件位置：`resources/cache/`
   - 需要读写权限

2. **首次使用**
   - 首次运行 `quick_book.py` 会自动创建缓存目录和文件
   - 无需手动初始化

3. **离线使用**
   - 如果缓存有效，即使网络不稳定也能快速定位建筑
   - 但实际预订查询和提交仍需要网络连接

4. **跨机器使用**
   - 不建议跨机器共享缓存文件
   - 每台机器独立维护自己的缓存

5. **缓存与 API 一致性**
   - 缓存有 7 天的有效期
   - 超过 7 天后会自动重新从 API 获取

## 常见问题

### Q: 为什么有时候缓存失效？
A: 缓存有 7 天的有效期。如果超过 7 天或手动删除了缓存文件，下次运行时会自动从 API 重新获取。

### Q: 缓存占用多少空间？
A: 建筑缓存约 788KB，条件缓存（预留）通常 <100KB。

### Q: 能否手动禁用缓存？
A: 缓存是自动管理的。如果需要临时禁用，可以手动删除缓存文件，下次运行会重新创建。

### Q: buildings_cache.json 的结构和 API 1 返回的格式不一样吗？
A: 是的。缓存采用了优化后的结构，更清晰地表示了层级关系。
- API 1 使用嵌套的 `children` 数组
- 缓存使用专门的 `buildings`/`floors` 字段
- 这样可以更方便地进行查询和匹配

### Q: quick_book.py 什么时候会更新缓存？
A: 在以下情况会自动更新缓存：
1. 首次运行时，自动从 API 获取并缓存
2. 缓存过期（7 天后）自动重新获取
3. 建筑查询失败时自动刷新缓存重试

### Q: 什么时候会使用 conditions_cache？
A: 当前版本预留了 `conditions_cache.json` 文件位置，但暂未实际使用。
后续如果需要支持更多筛选条件（如设备、窗户等的缓存），将启用此缓存以提升性能。

- **检查缓存有效性**：`is_buildings_cache_valid()`, `is_conditions_cache_valid()`
- **获取缓存数据**：`get_buildings_cache()`, `get_conditions_cache()`
- **保存缓存数据**：`save_buildings_cache()`, `save_conditions_cache()`
- **清除缓存**：`clear_buildings_cache()`, `clear_conditions_cache()`, `clear_all_cache()`
- **查看缓存状态**：`get_cache_status()`

**缓存配置**：
- 缓存路径：`resources/cache/`
- 建筑缓存文件：`buildings_cache.json` (788KB)
- 条件缓存文件：`conditions_cache.json`
- 缓存过期时间：7 天

### booking_optimized.py
优化版预订脚本，集成了缓存功能：

- **第一次运行**：从 API 获取城市、建筑、楼层数据并缓存（减少 API 调用）
- **后续运行**：直接从本地缓存读取（加快预订速度）
- **支持参数**：
  - `city_name`：城市名称（如 "上海"）
  - `building_name`：建筑名称（如 "D2"）
  - `date_str`：日期（如 "2026-03-05" 或 "明天"）
  - `start_time`：开始时间（如 "19:00"）
  - `end_time`：结束时间（如 "20:00"）
  - `capacity`：容量（默认 5 人）

### manage_cache.py
缓存管理命令行工具：

```bash
# 查看缓存状态
python manage_cache.py status

# 清除建筑缓存
python manage_cache.py clear-buildings

# 清除条件缓存
python manage_cache.py clear-conditions

# 清除所有缓存
python manage_cache.py clear-all
```

## 使用示例

### Python 脚本中使用

```python
from cache_manager import CacheManager

cache = CacheManager()

# 检查建筑缓存是否有效
if cache.is_buildings_cache_valid():
    data = cache.get_buildings_cache()
    print("使用缓存的建筑数据")
else:
    # 从 API 获取数据
    data = fetch_from_api()
    # 保存到缓存
    cache.save_buildings_cache(data)
```

### 命令行使用

```bash
# 查看缓存状态
python resources/manage_cache.py status

# 第一次预订（会缓存数据）
python resources/booking_optimized.py

# 第二次预订（使用缓存，更快）
python resources/booking_optimized.py

# 清除缓存
python resources/manage_cache.py clear-all
```

## 性能对比

| 操作 | 无缓存 | 有缓存 | 提升 |
|------|--------|--------|------|
| 获取建筑列表 | ~1.5s | 立即 | 1.5s |
| 第一次完整预订 | ~5-8s | ~5-8s | - |
| 后续预订 | ~5-8s | ~3-4s | 40% |
| 缓存文件大小 | - | 788KB | - |

## 缓存更新策略

### 自动过期
- 缓存有效期：7 天
- 超过 7 天自动判定为过期，下次使用时会重新从 API 获取

### 手动清除
```bash
python resources/manage_cache.py clear-all
```

### 按需更新
如果需要手动更新缓存，可以：
1. 清除旧缓存：`python resources/manage_cache.py clear-buildings`
2. 再次运行预订脚本会自动重新缓存

## 缓存数据结构

### buildings_cache.json（已缓存，文件大小 ~788KB）

存储城市、建筑、楼层的完整层级关系，从 API 1 (`/room/front/app/room/cityBuilding`) 的响应转换而来：

```json
{
  "cached_at": 1773570264396,
  "data": {
    "cityList": [
      {
        "cityId": 3531,
        "cityName": "北京市",
        "buildings": [
          {
            "buildingId": 843,
            "buildingName": "北京/保利广场西座",
            "floors": [
              {
                "floorId": 2001,
                "floorName": "2层"
              },
              {
                "floorId": 2002,
                "floorName": "3层"
              },
              {
                "floorId": 2003,
                "floorName": "4层"
              }
            ]
          },
          {
            "buildingId": 884,
            "buildingName": "北京/保利会议仓专区",
            "floors": [...]
          }
        ]
      },
      {
        "cityId": 3532,
        "cityName": "上海市",
        "buildings": [
          {
            "buildingId": 335,
            "buildingName": "上海/互联D2栋",
            "floors": [...]
          }
        ]
      }
    ]
  }
}
```

**数据转换说明**：
- API 1 返回的原始格式使用 `code`/`parentCode`/`type`/`children` 字段，缓存时被重新映射
- 转换规则：
  - `code` → `cityId` / `buildingId` / `floorId`（根据层级）
  - `name` → `cityName` / `buildingName` / `floorName`（根据层级）
  - `children` 数组 → `buildings` / `floors` 数组（根据层级）
- 楼层对象不包含 `children` 字段（最末层级）

### conditions_cache.json（预留，暂未使用）

将来用于缓存设备、容量、窗户等筛选条件，从 API 2 (`/room/front/pc/room/moreInfo`) 的响应保存：

```json
{
  "cached_at": 1773570264396,
  "data": {
    "equips": [
      {
        "id": 7,
        "name": "Zoom"
      },
      {
        "id": 9,
        "name": "腾讯会议"
      },
      {
        "id": 8,
        "name": "无线投屏"
      },
      {
        "id": 2,
        "name": "投影"
      },
      {
        "id": 3,
        "name": "电视"
      }
    ],
    "capacity": [
      {
        "capacityMin": 1,
        "capacityMax": 6,
        "name": "1-6人"
      },
      {
        "capacityMin": 7,
        "capacityMax": 14,
        "name": "7-14人"
      },
      {
        "capacityMin": 15,
        "capacityMax": 21,
        "name": "15-21人"
      },
      {
        "capacityMin": 22,
        "capacityMax": 40,
        "name": "22-40人"
      },
      {
        "capacityMin": 41,
        "capacityMax": 60,
        "name": "41-60人"
      },
      {
        "capacityMin": 61,
        "capacityMax": 1000,
        "name": "61人及以上"
      }
    ],
    "window": [
      {
        "code": "EXIST",
        "name": "有窗"
      }
    ]
  }
}
```

**缓存使用场景**：
- `equips`：快速查询设备列表，支持用户快速筛选
- `capacity`：快速查询容量范围，用于人数匹配
- `window`：快速查询窗户属性选项

## 注意事项

1. **Cookie 管理**
   - Cookie 过期时需要手动更新
   - 缓存不依赖 Cookie，只缓存数据内容

2. **缓存文件权限**
   - 缓存文件位置：`resources/cache/`
   - 需要读写权限

3. **首次使用**
   - 首次运行会自动创建缓存目录
   - 首次调用 API 后会自动保存缓存
   - 后续使用无需额外操作

4. **离线使用**
   - 如果缓存有效，即使网络不稳定也能快速查询建筑数据
   - 但实际预订查询和提交仍需要网络连接

5. **缓存与 API 一致性**
   - conditions_cache 需要定期更新以保持与 API 2 的一致性
   - 建议每次启动时检查 7 天过期策略

## 常见问题

### Q: 缓存数据不更新怎么办？
A: 缓存有 7 天的有效期。如果需要立即更新，使用命令清除缓存：
```bash
python resources/manage_cache.py clear-all
```

### Q: 缓存占用空间是多少？
A: 建筑缓存约 788KB，条件缓存根据实际数据大小（通常 <100KB）

### Q: 能否禁用缓存？
A: 缓存是自动管理的，但可以通过以下方式禁用：
1. 定期清除缓存：`python resources/manage_cache.py clear-all`
2. 修改 `CacheManager.CACHE_EXPIRY_DAYS = 0`（立即过期）

### Q: 缓存能否跨机器使用？
A: 不建议。缓存文件是绑定到本机的，跨机器使用可能导致问题。

### Q: buildings_cache.json 的结构和 API 1 返回的格式不一样吗？
A: 是的。缓存采用了优化后的结构：
- API 1 使用嵌套的 `children` 数组 → 缓存使用专门的 `buildings`/`floors` 字段
- 这样可以更清晰地表示层级关系，并方便代码查询

### Q: 什么时候会使用 conditions_cache？
A: 当前版本预留了 `conditions_cache.json` 文件位置，但暂未实际使用。
后续如果需要支持更多筛选条件（如设备、窗户等），将启用此缓存以提升性能。

- **检查缓存有效性**：`is_buildings_cache_valid()`, `is_conditions_cache_valid()`
- **获取缓存数据**：`get_buildings_cache()`, `get_conditions_cache()`
- **保存缓存数据**：`save_buildings_cache()`, `save_conditions_cache()`
- **清除缓存**：`clear_buildings_cache()`, `clear_conditions_cache()`, `clear_all_cache()`
- **查看缓存状态**：`get_cache_status()`

**缓存配置**：
- 缓存路径：`resources/cache/`
- 建筑缓存文件：`buildings_cache.json` (788KB)
- 条件缓存文件：`conditions_cache.json`
- 缓存过期时间：7 天

### booking_optimized.py
优化版预订脚本，集成了缓存功能：

- **第一次运行**：从 API 获取城市、建筑、楼层数据并缓存（减少 API 调用）
- **后续运行**：直接从本地缓存读取（加快预订速度）
- **支持参数**：
  - `city_name`：城市名称（如 "上海"）
  - `building_name`：建筑名称（如 "D2"）
  - `date_str`：日期（如 "2026-03-05" 或 "明天"）
  - `start_time`：开始时间（如 "19:00"）
  - `end_time`：结束时间（如 "20:00"）
  - `capacity`：容量（默认 5 人）

### manage_cache.py
缓存管理命令行工具：

```bash
# 查看缓存状态
python manage_cache.py status

# 清除建筑缓存
python manage_cache.py clear-buildings

# 清除条件缓存
python manage_cache.py clear-conditions

# 清除所有缓存
python manage_cache.py clear-all
```

## 使用示例

### Python 脚本中使用

```python
from cache_manager import CacheManager

cache = CacheManager()

# 检查建筑缓存是否有效
if cache.is_buildings_cache_valid():
    data = cache.get_buildings_cache()
    print("使用缓存的建筑数据")
else:
    # 从 API 获取数据
    data = fetch_from_api()
    # 保存到缓存
    cache.save_buildings_cache(data)
```

### 命令行使用

```bash
# 查看缓存状态
python resources/manage_cache.py status

# 第一次预订（会缓存数据）
python resources/booking_optimized.py

# 第二次预订（使用缓存，更快）
python resources/booking_optimized.py

# 清除缓存
python resources/manage_cache.py clear-all
```

## 性能对比

| 操作 | 无缓存 | 有缓存 | 提升 |
|------|--------|--------|------|
| 获取建筑列表 | ~1.5s | 立即 | 1.5s |
| 第一次完整预订 | ~5-8s | ~5-8s | - |
| 后续预订 | ~5-8s | ~3-4s | 40% |
| 缓存文件大小 | - | 788KB | - |

## 缓存更新策略

### 自动过期
- 缓存有效期：7 天
- 超过 7 天自动判定为过期，下次使用时会重新从 API 获取

### 手动清除
```bash
python resources/manage_cache.py clear-all
```

### 按需更新
如果需要手动更新缓存，可以：
1. 清除旧缓存：`python resources/manage_cache.py clear-buildings`
2. 再次运行预订脚本会自动重新缓存

## 缓存数据结构

### buildings_cache.json
```json
{
  "cached_at": 1772616024301,  // 缓存时间戳 (毫秒)
  "data": 
    [
        {
            "code": 3531,
            "parentCode": null,
            "name": "北京市",
            "type": "city",
            "children": [
                {
                    "code": 843,
                    "parentCode": 3531,
                    "name": "北京/保利广场西座",
                    "type": "building",
                    "children": [
                        {
                            "code": 2001,
                            "parentCode": null,
                            "name": "2层",
                            "type": "floor",
                            "children": null
                        },
                        {
                            "code": 2002,
                            "parentCode": null,
                            "name": "3层",
                            "type": "floor",
                            "children": null
                        },
                        {
                            "code": 2003,
                            "parentCode": null,
                            "name": "4层",
                            "type": "floor",
                            "children": null
                        }
                    ]
                },
            ]
        }
        ]
}
```

### conditions_cache.json
```json
{
  "cached_at": 1772616024301,
  "data": {
    "equips": [...],      // 可用设备列表
    "capacity": [...],    // 容量范围选项
    "window": [...]       // 窗户选项
  }
}
```

## 注意事项

1. **Cookie 管理**
   - Cookie 过期时需要手动更新
   - 缓存不依赖 Cookie，只缓存数据内容

2. **缓存文件权限**
   - 缓存文件位置：`resources/cache/`
   - 需要读写权限

3. **首次使用**
   - 首次运行会自动创建缓存目录
   - 首次调用 API 后会自动保存缓存
   - 后续使用无需额外操作

4. **离线使用**
   - 如果缓存有效，即使网络不稳定也能快速查询
   - 但实际预订仍需要网络连接

## 常见问题

### Q: 缓存数据不更新怎么办？
A: 缓存有 7 天的有效期。如果需要立即更新，使用命令清除缓存：
```bash
python resources/manage_cache.py clear-all
```

### Q: 缓存占用空间是多少？
A: 建筑缓存约 788KB，条件缓存根据实际数据大小（通常 <100KB）

### Q: 能否禁用缓存？
A: 缓存是自动管理的，但可以通过以下方式禁用：
1. 定期清除缓存：`python resources/manage_cache.py clear-all`
2. 修改 `CacheManager.CACHE_EXPIRY_DAYS = 0`（立即过期）

### Q: 缓存能否跨机器使用？
A: 不建议。缓存文件是绑定到本机的，跨机器使用可能导致问题。
