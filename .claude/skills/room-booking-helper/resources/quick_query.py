#!/usr/bin/env python3
"""
快速查询脚本 - 仅查询空闲会议室，不自动预订

用法：
1. 查询指定建筑在某时间段的所有空闲会议室
  python quick_query.py --city 上海 --building D2 --date 2026-03-10 --start 12:00 --end 13:00

2. 交互式模式 - 模糊建筑查询后列出所有空闲会议室
  python quick_query.py --interactive --city 上海 --date 2026-03-10 --start 12:00 --end 13:00

3. 带容量筛选的查询（只显示容纳>=5人的会议室）
  python quick_query.py --city 上海 --building D2 --date 2026-03-10 --start 12:00 --end 13:00 --capacity 5

特点：
  - 仅查询，不预订（与 quick_book.py 完全不同）
  - 返回所有匹配的空闲会议室列表
  - 支持容量、窗户、楼层等筛选条件
  - 支持交互式建筑选择
  - 输出格式便于 Agent 读取和处理
"""

import json
import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import requests as req_lib
    USE_REQUESTS = True
except ImportError:
    import urllib.request
    import ssl
    USE_REQUESTS = False
    _ssl_ctx = ssl.create_default_context()
    _ssl_ctx.check_hostname = False
    _ssl_ctx.verify_mode = ssl.CERT_NONE

# 导入缓存管理器和其他工具函数
sys.path.insert(0, str(Path(__file__).parent))
from cache_manager import CacheManager
from quick_book import (
    load_cookie, headers, api, round_to_5_minutes,
    _parse_and_validate_time, _detect_auth_strategy,
    find_building_interactive, _find_building_with_refresh,
    match_floor_names, match_equipment, cap_range, is_training_room,
    fetch_and_cache_buildings
)

SKILL_DIR = Path(__file__).parent.parent
COOKIE_FILE = SKILL_DIR / 'cookie.json'
SSO_CONFIG_FILE = Path.home() / ".catpaw" / "sso_config.json"
SSO_SCRIPT = SKILL_DIR / 'scripts' / 'rbh_sso.py'
CACHE_FILE = SKILL_DIR / 'resources' / 'cache' / 'buildings_cache.json'
TZ = timezone(timedelta(hours=8))
CACHE_MANAGER = CacheManager()

def quick_query(city, building, date_str, start_time, end_time, capacity=None, 
                window=None, floors=None, equips=None, interactive=False):
    """
    快速查询空闲会议室。
    返回 (success, message, rooms_list)
    
    rooms_list 结构：
    [
        {
            "id": 11486,
            "name": "富春厅",
            "building": "上海/互联D2",
            "floor": "2层",
            "capacity": 20,
            "window": "有窗",
            "equipment": ["Zoom", "投影仪"],
            "roomMap": "https://..."
        },
        ...
    ]
    """
    # 1. 加载 Cookie
    cookie, default_mis = load_cookie()
    if not cookie:
        strategy = _detect_auth_strategy()
        hints = {
            "catpaw_exchange": "sso_config.json 换票失败，CatPaw Desk token 可能已过期，请重新登录 CatPaw Desk",
            "ciba": "请运行 CIBA 认证：python3 ~/.catpaw/skills/room-booking-helper/scripts/rbh_sso.py ciba-login <misId>",
            "browser": "请手动获取 cookie 后运行：python3 ~/.catpaw/skills/room-booking-helper/scripts/rbh_sso.py save-cookie <cookie_str>",
        }
        return False, f"❌ 未找到有效登录态。{hints.get(strategy, '请重新认证')}", []
    
    hdrs = headers(cookie)

    # 2. 定位建筑
    if interactive and not building:
        bid, bname, all_fids, err = find_building_interactive(city, hdrs)
    else:
        bid, bname, all_fids, err = _find_building_with_refresh(city, building or "", hdrs)
    
    if err:
        return False, err, []
    print(f"📍 建筑: {bname}")
    
    # 3. 匹配楼层
    if floors:
        fids, err = match_floor_names(floors, city, building or "")
        if err:
            return False, err, []
        print(f"🏢 楼层: {', '.join(floors)}")
    else:
        fids = []
        print(f"🏢 楼层: 所有")

    # 4. 时间计算与验证
    start_dt, end_dt, start_ts, end_ts, date_ts, err = _parse_and_validate_time(date_str, start_time, end_time)
    if err:
        return False, err, []
    
    print(f"📅 日期: {date_str}")
    print(f"⏰ 时间: {start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}")
    
    # 5. 日期窗口检查
    today = datetime.now(TZ).date()
    target_date = start_dt.date()
    days_ahead = (target_date - today).days
    
    if days_ahead > 30:
        return False, f"⚠️ 预订日期过远（第{days_ahead}天），最多可查询未来30天", []
    
    # 6. 设备筛选
    equip_ids = []
    if equips:
        equip_ids, err = match_equipment(equips, hdrs)
        if err:
            return False, err, []
        print(f"🔧 设备: {', '.join(equips)}")
    
    # 7. 查询会议室
    print("\n🔍 查询中...")
    try:
        _find_rooms_resp = api(
            'https://calendar.sankuai.com/meeting/api/pc/room/appointment/v2/find-rooms',
            hdrs, {
                "date": date_ts,
                "buildingId": str(bid),
                "floorIds": fids,
                "capacity": [cap_range(capacity)] if capacity else [],
                "startTime": start_time,
                "endTime": end_time,
                "equipmentIds": equip_ids if equip_ids else []
            }
        )
    except Exception as e:
        if "AUTH_EXPIRED" in str(e):
            return False, "❌ 认证已过期，请重新运行 SSO 登录", []
        return False, f"❌ 查询失败: {str(e)}", []
    
    rooms = _find_rooms_resp.get('data', [])
    if not rooms:
        return False, "⚠️ 没有找到匹配的会议室", []
    
    print(f"✅ 找到 {len(rooms)} 个候选会议室")
    
    # 8. 查询预订情况并过滤已下线/已占用的会议室
    rmap = {r['id']: r for r in rooms}
    try:
        appt = api(
            'https://calendar.sankuai.com/meeting/api/pc/room/appointment/findRoomAppointmentsV2',
            hdrs, {"date": date_ts, "roomIds": list(rmap.keys())}
        )
    except Exception as e:
        return False, f"❌ 查询预订情况失败: {str(e)}", []
    
    free_rooms = []
    offline_count = 0
    for ra in appt.get('data', []):
        rid = ra['roomId']
        apts = ra.get('appointmentVOS') or []
        # roomSubscribe 有值表示全天已被人预约（长期预订/已下线），直接跳过
        if ra.get('roomSubscribe'):
            offline_count += 1
            continue
        # appointmentVOS 有值表示部分时段已被预约，检查是否与目标时段重叠
        # 重叠条件：appt_start < target_end AND appt_end > target_start
        if any(a['startTime'] < end_ts and a['endTime'] > start_ts for a in apts):
            continue
        free_rooms.append(rmap[rid])
    
    rooms = free_rooms
    if not rooms:
        return False, f"⚠️ 没有找到空闲的会议室（已下线: {offline_count}）", []
    
    print(f"✅ 过滤已下线/占用后: {len(rooms)} 个可用\n")
    
    # 9. 容量二次筛选（如果指定了容量）
    if capacity:
        filtered_rooms = [r for r in rooms if r.get('capacity', 0) >= capacity]
        if not filtered_rooms:
            return False, f"⚠️ 没有找到容量 >= {capacity} 人的会议室", []
        rooms = filtered_rooms
        print(f"📊 按容量筛选后: {len(rooms)} 个\n")
    
    # 10. 窗户筛选
    if window:
        window_value = 1 if window.upper() in ('EXIST', '有窗') else 0
        filtered_rooms = [r for r in rooms if r.get('window', 0) == window_value]
        if not filtered_rooms:
            return False, f"⚠️ 没有找到{window}的会议室", []
        rooms = filtered_rooms
        print(f"🪟 按窗户筛选后: {len(rooms)} 个\n")
    
    # 11. 格式化输出
    result_rooms = []
    for i, r in enumerate(rooms, 1):
        room_info = {
            "index": i,
            "id": r.get('id'),
            "name": r.get('name', ''),
            "building": bname,
            "floor": r.get('floorName', ''),
            "capacity": r.get('capacity', 0),
            "window": "有窗" if r.get('window') else "无窗",
            "equipment": r.get('equipmentName', []) if isinstance(r.get('equipmentName'), list) else [],
            "roomMap": r.get('roomMap', ''),
            "roomLocationUrl": r.get('roomLocationUrl', '')
        }
        result_rooms.append(room_info)
        
        # 打印可读的列表
        equips_str = "、".join(room_info["equipment"]) if room_info["equipment"] else "无"
        print(f"{i}️⃣  【{room_info['name']}】")
        print(f"   📍 位置: {room_info['floor']}")
        print(f"   👥 容量: {room_info['capacity']} 人")
        print(f"   🪟 窗户: {room_info['window']}")
        print(f"   🔧 设备: {equips_str}")
        if room_info.get('roomMap'):
            print(f"   🗺️  地图: ![地图]({room_info['roomMap']})")
        print()
    
    return True, f"✅ 成功查询到 {len(result_rooms)} 个可用会议室", result_rooms

def main():
    parser = argparse.ArgumentParser(description='快速查询会议室脚本（仅查询，不预订）')
    parser.add_argument('--city', required=True, help='城市（支持模糊匹配）')
    parser.add_argument('--building', help='建筑（支持模糊匹配）。不指定时使用 --interactive 交互选择')
    parser.add_argument('--date', required=True, help='日期 (YYYY-MM-DD)')
    parser.add_argument('--start', required=True, help='开始时间 (HH:MM)')
    parser.add_argument('--end', required=True, help='结束时间 (HH:MM)')
    parser.add_argument('--capacity', type=int, help='最少容纳人数（可选，默认无筛选）')
    parser.add_argument('--floors', nargs='+', help='楼层列表（可选，如 2层 3层）')
    parser.add_argument('--window', choices=['EXIST', 'NONE', '有窗', '无窗'], help='窗户（可选）')
    parser.add_argument('--equips', nargs='+', help='设备关键词（可选，如 Zoom 投影）')
    parser.add_argument('--interactive', action='store_true', help='交互式模式（模糊建筑查询）')
    
    args = parser.parse_args()
    
    # 检查必要参数
    if not args.interactive and not args.building:
        print("❌ 错误: 需要指定 --building 或使用 --interactive 模式")
        sys.exit(1)
    
    # 执行查询
    success, msg, rooms = quick_query(
        city=args.city,
        building=args.building,
        date_str=args.date,
        start_time=args.start,
        end_time=args.end,
        capacity=args.capacity,
        window=args.window,
        floors=args.floors,
        equips=args.equips,
        interactive=args.interactive
    )
    
    print(msg)
    
    # 输出 JSON 格式的结果（便于后续处理）
    if success:
        print("\n📋 JSON 格式结果:")
        print(json.dumps(rooms, ensure_ascii=False, indent=2))
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
