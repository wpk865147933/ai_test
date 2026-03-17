# 会议室预订 API 详细参考

## API 端点列表

| 功能 | 端点 | 方法 |
|------|------|------|
| 获取城市/大厦/楼层 | `/room/front/app/room/cityBuilding` | POST |
| 获取筛选条件 | `/room/front/pc/room/moreInfo` | POST |
| 查询可用会议室 | `/meeting/api/pc/room/appointment/v2/find-rooms` | POST |
| 查询会议室预订 | `/meeting/api/pc/room/appointment/findRoomAppointmentsV2` | POST |
| 提交预订 | `/api/v2/xm/schedules` | POST |
| **查询员工信息** | **/api/v2/xm/meeting/dataset/account** | **POST** |
| **创建空闲监测任务** | **/room/front/appointment-room/insertV2** | **POST** |

基础 URL：`https://calendar.sankuai.com`

---

## API 1: 获取城市、大厦和楼层列表

**端点**: `POST /room/front/app/room/cityBuilding`

**请求头**：
```
Accept: application/json, text/plain, */*
Content-Type: application/json
Content-Length: 0
M-UserContext: eyJsb2NhbGUiOiJ6aCIsInRpbWVab25lIjoiQXNpYS9TaGFuZ2hhaSJ9
```

**请求体**：无（或空 JSON `{}` ）

**响应示例**：

```json
{
    "code": 200,
    "message": "success",
    "data": [
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
                }
            ]
        }
    ]
}
```

**关键字段说明**：
- `cityId`: 城市唯一标识
- `building.buildingId`: 大厦 ID（在 API 3 中使用）
- `floors[].floorId`: 楼层 ID（在 API 3 中使用）

---

## API 2: 获取筛选条件列表

**端点**: `POST /room/front/pc/room/moreInfo`

**请求参数**：无

**响应示例**：

```json
{
  "code": 200,
  "message": "success",
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

**容量匹配逻辑**：
- 1-6 人 → 选择 `capacityMin: 1, capacityMax: 6`
- 7-14 人 → 选择 `capacityMin: 7, capacityMax: 14`
- 15-21 人 → 选择 `capacityMin: 15, capacityMax: 21`
- 22-40 人 → 选择 `capacityMin: 22, capacityMax: 40`
- 41-60 人 → 选择 `capacityMin: 41, capacityMax: 60`
- 60+ 人 → 选择 `capacityMin: 61, capacityMax: 1000`

---

## API 3: 查询可用会议室

**端点**: `POST /meeting/api/pc/room/appointment/v2/find-rooms`

**请求头**：
```
Content-Type: application/json
```

**请求体**（完整格式）：

```json
{
  "date": 1773504000000,
  "buildingId": "669",
  "floorIds": [1654, 1744],
  "equipIds": [7],
  "capacity": [
    {
      "capacityMin": 1,
      "capacityMax": 6,
      "name": "1-6人"
    },
    {
      "capacityMin": 15,
      "capacityMax": 21,
      "name": "15-21人"
    }
  ],
  "window": "EXIST",
  "startTime": "12:00",
  "endTime": "16:00"
}
```

**参数说明**：

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `date` | number | 是 | 日期零点的毫秒时间戳 | `1773504000000` |
| `buildingId` | string | 是 | 大厦 ID（从 API 1 获取） | `"669"` 或 `"843"` |
| `floorIds` | array | 否 | 楼层 ID 数组，支持多选，空表示不限 | `[]` 或 `[1654, 1744]` |
| `equipIds` | array | 否 | 设备 ID 数组，支持多选 | `[7]` (Zoom) 或 `[7, 8]` (多设备) |
| `capacity` | array | 否 | 容量范围对象数组，支持多个范围同时筛选 | `[{"capacityMin":1,"capacityMax":6,"name":"1-6人"}]` 或多个 |
| `window` | string | 否 | 窗户属性过滤 | `"EXIST"`(有窗) 或 `"NONE"`(无窗) |
| `startTime` | string | 是 | 开始时间（24小时制） | `"12:00"` |
| `endTime` | string | 是 | 结束时间（24小时制） | `"16:00"` |

**响应示例**：

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 11516,
      "name": "濮阳厅",
      "email": "room-blx-2f-d-puyangting@meituan.com",
      "capacity": 13,
      "disabled": 0,
      "floorId": 2001,
      "floorName": "2层",
      "buildingId": 843,
      "buildingName": "北京/保利广场西座",
      "equips": [
        {
          "equipId": 7,
          "equipName": "Zoom"
        }
      ],
      "memo": "该会议室已上线Zoom占位检测无人后自动释放功能，请预订后及时前往会议室使用。",
      "bookCardMemo": "该会议室已上线Zoom占位检测无人后自动释放功能，请预订后及时前往会议室使用。",
      "roomName": "濮阳厅",
      "roomMap": "https://s3plus.meituan.net/.../濮阳厅_1764839462880.png",
      "price": null,
      "pointX": 0.641860465116279,
      "pointY": 0.19590490680870065,
      "window": "NOT_EXIST",
      "roomLocationUrl": "https://123.sankuai.com/huiyi/map/dx?id=11516"
    },
    {
      "id": 11608,
      "name": "淮河厅",
      "capacity": 5,
      "floorId": 2003,
      "floorName": "4层",
      "window": "EXIST"
    }
  ]
}
```

**关键字段说明**：
- `id`: 会议室 ID（在 API 4、API 5 中使用）
- `name`: 会议室名称
- `capacity`: 会议室容量
- `equips`: 会议室设备列表
- `memo`: 会议室备注说明
- `window`: 是否有窗户 (`EXIST` / `NOT_EXIST`)
- `roomLocationUrl`: 会议室位置地图的跳转链接
- `roomMap`: 会议室位置的图片

---

## API 4: 查询会议室预订情况

**端点**: `POST /meeting/api/pc/room/appointment/findRoomAppointmentsV2`

**请求头**：
```
Content-Type: application/json
```

**请求体**：

```json
{
  "date": 1772553600000,
  "roomIds": [11525, 11516, 11591]
}
```

**参数说明**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `date` | number | 是 | 日期零点的毫秒时间戳 |
| `roomIds` | array | 是 | 会议室 ID 数组（从 API 3 获取） |

**响应示例**：

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "roomId": 11516,
      "appKey": "meeting",
      "entryList": null,
      "appointmentVOS": [
        {
          "id": "54986818",
          "scheduleId": "2028812952760832035",
          "title": "郝妍的会议",
          "isOrganizer": 0,
          "startTime": 1772593200000,
          "endTime": 1772596800000,
          "isRecur": false
        },
        {
          "id": "55222216",
          "scheduleId": "2029090334139371533",
          "title": "徐坤鹏的会议",
          "isOrganizer": 0,
          "startTime": 1772608500000,
          "endTime": 1772611200000,
          "isRecur": false
        }
      ]
    },
    {
            "roomId": 9505,
            "appKey": "meeting",
            "entryList": null,
            "appointmentVOS": [],
            "roomSubscribe": {
                "id": 12625,
                "subscribeUserId": "2565539",
                "subscribeMis": "zhuchao14",
                "subscribeName": "朱超",
                "roomId": 9505,
                "roomName": "石家庄厅",
                "onlyRoomName": "石家庄厅",
                "startTime": 1755446400000,
                "endTime": 1774972799000,
                "subscribeTopic": "临时工位 zhuchao14 2025年08月18日-2026年03月31日",
                "memo": null,
                "disabled": 0,
                "createTime": 1754635781000,
                "updateTime": 1768285176000,
                "subscribeEmail": null,
                "subscribeXmUId": null,
                "orgFullName": null,
                "icon": null,
                "bgCode": null,
                "bgName": null
            }
        }
  ]
}
```

**字段说明**：
- `roomId`: 会议室 ID
- `appointmentVOS[].title`: 预订的会议标题
- `appointmentVOS[].startTime`: 开始时间（毫秒时间戳）
- `appointmentVOS[].endTime`: 结束时间（毫秒时间戳）
- 空数组 `[]` 表示该会议室当天无预订

**空闲时段判断**：
1. **先检查 roomSubscribe**：有值表示已下线（长期预订/全天被人预约），直接排除
2. **再检查 appointmentVOS**：
   - 如果为空数组 → 空闲
   - 如果有值 → 遍历每条预约，检查是否与目标时段重叠
   - 重叠条件：`appt['startTime'] < target_end AND appt['endTime'] > target_start`
3. 无重叠 = 空闲

---

## API 5: 提交预订

**端点**: `POST /api/v2/xm/schedules`

**请求头**：
```
Content-Type: application/json
Cookie: [浏览器当前cookie]
```

**请求体（完整格式）**：

```json
{
  "title": "会议主题",
  "startTime": 1772848800000,
  "endTime": 1772852400000,
  "isAllDay": 0,
  "location": "",
  "attendees": ["6485487"],
  "noticeType": 0,
  "noticeRule": "P0Y0M0DT0H10M0S",
  "recurrencePattern": {
    "type": "NONE",
    "showType": "NONE"
  },
  "deadline": 0,
  "memo": "",
  "organizer": "6485487",
  "room": {
    "id": 11486,
    "name": "富春厅",
    "email": "room-blx-2f-a-fuchunting@meituan.com",
    "capacity": 13,
    "disabled": 0,
    "floorId": 2001,
    "floorName": "2层",
    "buildingId": 843,
    "buildingName": "北京/保利广场西座"
  },
  "appKey": "meeting",
  "bookType": 11
}
```

**参数说明**：

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `title` | string | 是 | 会议标题 | "周会" |
| `startTime` | number | 是 | 开始时间（毫秒时间戳） | `1772848800000` |
| `endTime` | number | 是 | 结束时间（毫秒时间戳） | `1772852400000` |
| `isAllDay` | number | 是 | 是否全天 | `0` (不全天) |
| `organizer` | string | 是 | 组织者 ID（数字 ID） | `"6485487"` |
| `attendees` | array | 是 | 参与人员 ID 列表 | `["6485487"]` |
| `room.id` | number | 是 | 会议室 ID | `11486` |
| `room.name` | string | 是 | 会议室名称 | `"富春厅"` |
| `room.email` | string | 是 | 会议室邮箱 | `"room-blx-2f-a-fuchunting@meituan.com"` |
| `room.capacity` | number | 是 | 会议室容量 | `13` |
| `room.floorId` | number | 是 | 楼层 ID | `2001` |
| `room.floorName` | string | 是 | 楼层名称 | `"2层"` |
| `room.buildingId` | number | 是 | 大厦 ID | `843` |
| `room.buildingName` | string | 是 | 大厦名称 | `"北京/保利广场西座"` |
| `appKey` | string | 是 | 应用标识 | `"meeting"` |
| `bookType` | number | 是 | 预订类型 | `11` |
| `noticeType` | number | 否 | 通知类型 | `0` |
| `recurrencePattern` | object | 否 | 循环模式 | `{"type":"NONE","showType":"NONE"}` |
| `deadline` | number | 否 | 截止时间 | `0` |
| `memo` | string | 否 | 备忘录 | `""` |
| `location` | string | 否 | 位置描述 | `""` |

**成功响应**：

```json
{
  "code": 200,
  "message": "成功",
  "redirectUrl": "/schedules/2028812952760832035",
  "data": null
}
```

**常见失败响应**：

1. **时间参数不合法**：

```json
{
  "data": {
    "message": "时间参数不合法"
  },
  "rescode": 1
}
```

2. **过去时间不可预订**：

```json
{
  "data": {
    "message": "过去时间不可预订会议室"
  },
  "rescode": 1
}
```

3. **会议室已被预订**：

```json
{
  "data": {
    "message": "会议室已被预订，请重新选择！"
  },
  "rescode": 1
}
```

4. **权限不匹配**：

```json
{
  "data": {
    "errorCode": "PERMISSION_REJECT",
    "message": "权限不匹配，拒绝操作"
  },
  "rescode": 1
}
```

5. **未登录**：

```json
{
  "data": {
    "message": "未登录"
  },
  "rescode": 1
}
```

---

## API 6: 查询员工信息（MIS 转 empId）

**端点**: `POST /api/v2/xm/meeting/dataset/account`

**功能**：将员工 MIS 账号转换为 empId。用于在提交预订时获取参会人的 empId（组织者和参会人均需要此 ID）。

**请求头**：
```
Content-Type: application/json
Cookie: [浏览器当前cookie]
```

**请求体**：

```json
{
  "filter": "wb_zhuxinglong"
}
```

**参数说明**：

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `filter` | string | 是 | 员工 MIS 账号（单个） | `"wb_zhuxinglong"` 或 `"wangjun137"` |

**成功响应示例**：

```json
{
  "data": [
    {
      "email": null,
      "name": "朱形龙",
      "enName": "",
      "empId": "7409759",
      "avatar": "https://s3plus-img.meituan.net/v1/mss_491cda809310478f898d7e10a9bb68ec/profile2/095a74b4-a6a9-4c6c-9819-e3a6082fde0b",
      "deptName": null,
      "deptId": null,
      "mis": "wb_zhuxinglong",
      "phone": null,
      "admin": null,
      "tenantId": null,
      "equal": 0,
      "frequentContact": 0,
      "sameDepartment": 0,
      "statusOfDxUuid": false,
      "dxUserId": "2398376820",
      "group": false
    }
  ],
  "code": 200,
  "message": "success"
}
```

**关键字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `empId` | string | **重要**：员工的数字 ID，用于预订接口的 `organizer` 和 `attendees` 字段 |
| `name` | string | 员工中文名称 |
| `mis` | string | 员工 MIS 账号（与查询参数对应） |
| `dxUserId` | string | 大象用户 ID |
| `email` | string | 公司邮箱（可能为空） |

**使用流程**：

1. **查询单个员工**：

```json
   {"filter": "wb_zhuxinglong"}
```

获取 `empId: "7409759"`

2. **在预订请求中使用**：

```json
   {
     "organizer": "7409759",
     "attendees": ["7409759", "6485487"]  // empId 列表
   }
```

**常见错误响应**：

1. **员工不存在**：

```json
   {
     "data": [],
     "code": 200,
     "message": "success"
   }
```

→ 解决：检查 MIS 账号是否正确

2. **权限不足**：

```json
   {
     "code": 401,
     "message": "未登录"
   }
```

→ 解决：重新登录获取有效的 Cookie

**Python 调用示例**：

```python
import json
import urllib.request

headers = {
    'Content-Type': 'application/json',
    'Cookie': 'your_cookie_here'
}

# 查询单个员工
data = {"filter": "wb_zhuxinglong"}

req = urllib.request.Request(
    'https://calendar.sankuai.com/api/v2/xm/meeting/dataset/account',
    data=json.dumps(data).encode('utf-8'),
    headers=headers,
    method='POST'
)

with urllib.request.urlopen(req) as response:
    result = json.loads(response.read().decode('utf-8'))
    emp_id = result['data'][0]['empId']  # 获取 empId
    print(f"员工 {result['data'][0]['name']} 的 empId: {emp_id}")
```

**快速查询多个员工（批量）**：

```python
mis_list = ["wb_zhuxinglong", "wangjun137"]
emp_ids = []

for mis in mis_list:
    data = {"filter": mis}
    # 发送请求...
    result = json.loads(response.read().decode('utf-8'))
    if result['data']:
        emp_ids.append(result['data'][0]['empId'])

print(f"参会人 empId: {emp_ids}")
```

**quick_book.py 中的自动转换流程**：

当用户指定 `--attendees mis1 mis2` 时，脚本会：
1. 自动调用此接口查询每个 MIS 的 empId
2. 将 empId 列表传递给预订接口的 `attendees` 字段
3. 用户无需关心 MIS 和 empId 的转换细节

---

## 时间戳转换

### JavaScript 示例：

```js
// 获取日期的零点时间戳（毫秒）
function getDateTimeStamp(dateStr) {
  return new Date(dateStr + ' 00:00:00').getTime();
}

// 获取具体时间的时间戳
function getTimeStamp(dateStr, timeStr) {
  return new Date(dateStr + ' ' + timeStr).getTime();
}
```

### 常用日期时间戳：
- 2026-02-18 00:00:00 → `1772553600000`
- 2026-02-18 10:00:00 → `1772619300000`
- 2026-02-18 11:00:00 → `1772622900000`

---

## API 7: 创建空闲会议室监测任务

**端点**: `POST /room/front/appointment-room/insertV2`

**功能**：当没有找到符合条件的空闲会议室时，为用户自动创建监测预约任务。系统会在指定的时间段内持续监测该建筑的会议室状态，如果有符合条件的空闲会议室出现，会自动向用户发送通知。

**请求头**：
```
Accept: application/json, text/plain, */*
Content-Type: application/json
X-Requested-With: XMLHttpRequest
M-UserContext: eyJsb2NhbGUiOiJ6aCIsInRpbWVab25lIjoiQXNpYS9TaGFuZ2hhaSJ9
Referer: https://calendar.sankuai.com/rooms
tz: Asia/Shanghai
la: zh
sec-ch-ua-platform: macOS
sec-ch-ua: "Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"
sec-ch-ua-mobile: ?0
Cookie: [用户的Cookie]
```

**请求体参数**：

```json
{
  "buildingId": 843,
  "planStartTimestamp": 1772688600000,
  "planEndTimestamp": 1772692200000,
  "floorIds": [2003, 2004],
  "headCount": 5
}
```

| 参数 | 类型 | 说明 | 必填 |
|------|------|------|------|
| `buildingId` | number | 建筑ID | 是 |
| `planStartTimestamp` | number | 开始时间的毫秒时间戳 | 是 |
| `planEndTimestamp` | number | 结束时间的毫秒时间戳 | 是 |
| `floorIds` | array | 楼层ID列表（支持空数组表示不限楼层） | 否 |
| `headCount` | number | 人数需求 | 是 |

**成功响应示例**：

```json
{
  "code": 200,
  "message": "success",
  "data": "添加成功，在 03-05 13:30 (GMT+08:00) 前会为你持续监测。"
}
```

**失败响应示例**：

```json
{
  "code": 400,
  "message": "参数错误",
  "data": null
}
```

**响应说明**：
- `code: 200`：监测任务创建成功
- `data` 字段包含监测的过期时间说明
- 用户会在监测期限前收到通知（如果有符合条件的空闲会议室）

**使用场景**：
1. 用户查询会议室时，发现指定时间段所有房间都已被预订
2. 系统自动调用此接口，为用户创建监测任务
3. 用户无需任何额外操作，系统后台持续监测
4. 有空闲会议室出现时，系统自动通知用户

**Python 调用示例**：

```python
import json
import urllib.request

headers = {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
    'M-UserContext': 'eyJsb2NhbGUiOiJ6aCIsInRpbWVab25lIjoiQXNpYS9TaGFuZ2hhaSJ9',
    'Cookie': 'your_cookie_here'
}

data = {
    "buildingId": 843,
    "planStartTimestamp": 1772688600000,
    "planEndTimestamp": 1772692200000,
    "floorIds": [2003, 2004],
    "headCount": 5
}

req = urllib.request.Request(
    'https://calendar.sankuai.com/room/front/appointment-room/insertV2',
    data=json.dumps(data).encode('utf-8'),
    headers=headers,
    method='POST'
)

with urllib.request.urlopen(req) as response:
    result = json.loads(response.read().decode('utf-8'))
    print(result)
```

---

## 错误排查

| 错误信息 | 可能原因 | 解决方案 |
|----------|---------|---------|
| `code: 401` | Cookie 过期或未登录 | 重新登录获取新 Cookie |
| `code: 4001` | 该时间段已被预订 | 选择其他时间或会议室 |
| `code: 403` | 权限不足 | 检查账户权限或联系管理员 |
| `code: 500` | 服务器错误 | 稍后重试 |
| `code: 10001` | 请求参数错误 | 检查参数格式和时间戳 |
| 监测创建失败 | buildingId 或时间戳格式错误 | 验证参数是否正确（使用毫秒级时间戳） |

---

## 建筑数据结构说明（重要！）

### 数据层级

```
data
└── cityList (数组)
    └── cityId + cityName (城市)
        └── buildings (数组)
            ├── buildingId (建筑ID，全局唯一)
            ├── buildingName (建筑名称，格式："城市/建筑名")
            └── floors (楼层数组)
                ├── floorId (楼层ID)
                └── floorName (楼层名称)
```

### 关键注意事项 ⚠️

#### 1. buildingId 是全局唯一的
- 每个建筑ID在整个系统中唯一标识一个建筑
- 不同城市的建筑绝不会有相同的ID
- 例如：
  - `buildingId = 335` → `上海/互联D2栋` (上海市)
  - `buildingId = 843` → `北京/保利广场西座` (北京市)

#### 2. 必须通过城市上下文确认建筑
- 不能仅凭建筑名称中的关键词（如"D2"）进行匹配
- 必须先确定城市，再在该城市的 `buildings` 中查找
- 查找流程：

```python
  # 正确做法
  city_list = data.get('data', {}).get('cityList', [])
  for city in city_list:
      if '上海' in city['cityName']:  # 1. 先定位城市
          for building in city['buildings']:
              if 'D2' in building['buildingName']:  # 2. 再匹配建筑名
                  building_id = building['buildingId']
                  # 找到正确的建筑
```

#### 3. 查询后必须验证返回的建筑名称
- 在调用会议室查询接口后，检查返回的 `room.buildingName`
- 确认实际地点与用户需求一致
- 如果不一致，说明使用了错误的 buildingId

#### 4. 缓存数据结构
- 缓存的 JSON 结构应保持与 API 返回一致
- 缓存文件应包含完整的城市→建筑→楼层层级关系
- 示例缓存结构：

```json
  {
    "timestamp": 1709567890000,
    "data": {
      "cityList": [
        {
          "cityId": 3532,
          "cityName": "上海市",
          "buildings": [...]
        }
      ]
    }
  }
```

---

## 会议室预订情况分析（重要！）

### 通过预订记录识别下线会议室和时段冲突

**判断逻辑**：
- `roomSubscribe` 有值 → 全天已被预约（长期预订/已下线），无法预订
- `appointmentVOS` 有值 → 部分时段已被预约，需要检查时间是否与目标时段重叠

**判断规则**：
1. **先检查 roomSubscribe**：有值表示已下线（长期预订/全天被人预约），直接排除
2. **再检查 appointmentVOS**：遍历每条预约记录，判断时间段是否与目标时段重叠
   - 重叠条件：`appt['startTime'] < target_end AND appt['endTime'] > target_start`
   - 有重叠 = 时段冲突，无法预订
   - 无重叠 = 空闲

```python
free_rooms = []
offline_rooms = []
busy_rooms = []

for room in rooms_data:
    room_id = room.get('roomId') or room.get('id')
    appointment_vos = room.get('appointmentVOS', []) or []
    room_subscribe = room.get('roomSubscribe')  # 全天预约情况
    
    # 第一步：检查是否已下线（roomSubscribe 有值表示全天已被人预约）
    if room_subscribe:
        offline_rooms.append(room_id)
        continue
    
    # 第二步：检查 appointmentVOS 是否有时间重叠
    has_conflict = False
    for appt in appointment_vos:
        # 判断时间段是否重叠：appt_start < target_end AND appt_end > target_start
        if appt['startTime'] < target_end and appt['endTime'] > target_start:
            has_conflict = True
            break
    
    if has_conflict:
        busy_rooms.append(room_id)
    else:
        free_rooms.append(room_id)

print(f'空闲: {len(free_rooms)}, 已预订: {len(busy_rooms)}, 已下线: {len(offline_rooms)}')
```

---

## 会议室下线处理（两层防护）

下线会议室的识别采用**两层防护**机制：

### 第一层（预订记录预判）
在查询预订情况时，检查 `roomSubscribe` 字段是否为空，提前过滤掉已下线的会议室，避免发起无效请求。

### 第二层（预订响应兜底）
即使通过了第一层过滤，提交预订时仍可能遇到下线错误（如会议室刚刚下线、预订记录尚未更新等边缘情况），此时需要自动重试下一个：

```python
# 遍历空闲会议室（已排除预判为下线的），逐个尝试预订
for selected in free_rooms:
    resp = requests.post(book_url, headers=HEADERS, json=build_booking_body(selected))
    result = resp.json()
    
    if result.get('message') == '成功':
        print(f'✅ 预订成功: {selected["name"]}')
        break
    
    err_msg = result.get('data', {}).get('message', '')
    if '已下线' in err_msg:
        print(f'⚠️ {selected["name"]} 已下线，尝试下一个...')
        continue  # 跳过下线的会议室，尝试下一个
    else:
        print(f'❌ 预订失败: {err_msg}')
        break  # 其他错误直接停止
else:
    # 所有空闲会议室都下线或预订失败
    print('所有空闲会议室均不可用，自动创建空闲监测任务...')
    add_room_monitor(...)  # 触发监测
```

**下线会议室的错误响应**：

```json
{
  "data": {
    "message": "会议室已下线! 当前不支持预订及抢订!"
  },
  "rescode": 1
}
```

**关键规则**：
- **优先通过预订记录预判**：
  1. `roomSubscribe` 有值 → 标记为已下线（长期预订）
  2. `appointmentVOS` 有值 → 检查时间是否重叠，有重叠则标记为已占用
- 遇到「会议室已下线」错误时，**不要停止**，继续尝试下一个空闲会议室
- 只有当所有空闲会议室都尝试失败后，才触发空闲监测
- 下线的会议室仍会出现在查询结果中，这是 API 的已知行为

---

## 请求头完整说明

### 标准请求头（所有接口通用）

```python
headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json, text/plain, */*',
    'X-Requested-With': 'XMLHttpRequest',
    'X-Request-Source': 'OpenClaw-Agent',  # AI 请求标识
    'M-UserContext': 'eyJsb2NhbGUiOiJ6aCIsInRpbWVab25lIjoiQXNpYS9TaGFuZ2hhaSJ9',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Cookie': cookie_string
}
```

### 空闲监测接口特殊请求头

监测接口需要额外的请求头：

```python
headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json, text/plain, */*',
    'X-Requested-With': 'XMLHttpRequest',
    'M-UserContext': 'eyJsb2NhbGUiOiJ6aCIsInRpbWVab25lIjoiQXNpYS9TaGFuZ2hhaSJ9',
    'Referer': 'https://calendar.sankuai.com/rooms',   # ← 必须
    'tz': 'Asia/Shanghai',                              # ← 必须
    'la': 'zh',                                         # ← 必须
    'User-Agent': 'Mozilla/5.0 ...',
    'Cookie': cookie_string   # ← 必须使用 cookie.json 中的 cookie
}
```

---

## 预订完整流程检查清单

### 信息收集阶段
- [ ] 城市名称获取
- [ ] 建筑名称获取（支持模糊匹配）
- [ ] 日期是否在有效范围内（7 天内）
- [ ] 时间是否在未来
- [ ] 时长是否在 5-240 分钟范围内
- [ ] 人数信息获取

### API 调用阶段
- [ ] 建筑列表查询（检查缓存）
- [ ] 会议室列表查询（验证返回的建筑名称是否正确）
- [ ] 预订情况查询（识别下线会议室）
- [ ] 员工信息查询（获取 empId）

### 预订阶段
- [ ] 遍历空闲会议室列表
- [ ] 逐个尝试预订
- [ ] 遇到下线错误时继续尝试下一个
- [ ] 其他致命错误时停止
- [ ] 全部失败时创建监测任务

### 成功/失败处理
- [ ] 成功：展示会议室名称、时间、地点、容量（不展示 schedule_id）
- [ ] 失败：显示失败原因并建议用户修改查询条件或等待监测通知