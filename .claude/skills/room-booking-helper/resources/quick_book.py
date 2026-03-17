#!/usr/bin/env python3
"""
一体化快速会议室预订脚本

用法（两种模式）：

1. 快速模式（所有参数都指定）:
  python quick_book.py --city 上海 --building D2 --date 2026-03-10 --start 12:00 --end 13:00 [--capacity 5] [--floors 2层 3层] [--window EXIST] [--equips Zoom] [--mis wangjun137]

2. 交互式模式（自动帮您选择建筑和设备）:
  python quick_book.py --interactive --city 上海 --date 2026-03-10 --start 12:00 --end 13:00

特点:
  - 单次执行完成全流程（查建筑→查楼层→查房间→查预订→预订，一气呵成）
  - 优先使用本地缓存定位建筑
  - 支持多楼层筛选（可选，默认查询所有楼层）
  - 楼层名称模糊匹配（"11"可匹配"11层"）
  - 支持高级筛选：窗户、设备类型（Zoom、投影、腾讯会议等）
  - 交互式模式：模糊建筑查询，支持从列表中选择
  - 设备智能匹配：支持设备关键词模糊查询
  - 批量尝试预订，遇到成功立即返回
  - 自动处理已下线会议室
  - 全部失败时自动创建监测任务
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

# 导入缓存管理器
sys.path.insert(0, str(Path(__file__).parent))
from cache_manager import CacheManager

SKILL_DIR = Path(__file__).parent.parent
COOKIE_FILE = SKILL_DIR / 'cookie.json'
SSO_CONFIG_FILE = Path.home() / ".catpaw" / "sso_config.json"
SSO_SCRIPT = SKILL_DIR / 'scripts' / 'rbh_sso.py'
CACHE_FILE = SKILL_DIR / 'resources' / 'cache' / 'buildings_cache.json'
TZ = timezone(timedelta(hours=8))
CACHE_MANAGER = CacheManager()

# ── helpers ────────────────────────────────────────────────

def round_to_5_minutes(dt):
    """将时间四舍五入到最近的5分钟倍数"""
    minute = dt.minute
    remainder = minute % 5
    if remainder < 3:
        new_minute = minute - remainder
    else:
        new_minute = minute + (5 - remainder)
    if new_minute >= 60:
        from datetime import timedelta
        dt = (dt.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
    else:
        dt = dt.replace(minute=new_minute, second=0)
    return dt

def is_training_room(room_name):
    """判断是否为培训会议室"""
    return "培训" in room_name

def get_booking_window(room_name):
    """获取预订窗口天数（普通会议室8天，培训会议室30天）"""
    return 30 if is_training_room(room_name) else 8

def _parse_and_validate_time(date_str, start_time, end_time):
    """
    解析并验证时间参数。
    返回 (start_dt, end_dt, start_ts, end_ts, date_ts, err_msg)
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=TZ)
    except ValueError:
        return None, None, None, None, None, f"日期格式错误，应为 YYYY-MM-DD: {date_str}"
    
    date_ts = int(dt.timestamp() * 1000)
    
    try:
        sh, sm = map(int, start_time.split(':'))
        eh, em = map(int, end_time.split(':'))
    except ValueError:
        return None, None, None, None, None, f"时间格式错误，应为 HH:MM: {start_time}, {end_time}"
    
    from datetime import timedelta
    # 特例：用户输入 24:00 表示当天结束，等价于次日 00:00，系统允许此时间戳
    end_is_midnight = (eh == 24 and em == 0)

    # 时间精度：四舍五入到5分钟倍数
    start_dt = dt.replace(hour=sh, minute=sm, second=0)
    if end_is_midnight:
        # 直接构造次日 00:00，不做 round（已经是整点）
        end_dt = (dt + timedelta(days=1)).replace(hour=0, minute=0, second=0)
    else:
        end_dt = dt.replace(hour=eh, minute=em, second=0)
        end_dt_rounded = round_to_5_minutes(end_dt)
        # 若进位后恰好落在次日 00:00，视为 24:00 特例，允许通过
        next_midnight = (dt + timedelta(days=1)).replace(hour=0, minute=0, second=0)
        if end_dt_rounded == next_midnight:
            end_is_midnight = True
            end_dt = next_midnight
        else:
            end_dt = end_dt_rounded
    start_dt = round_to_5_minutes(start_dt)

    # 跨天检查：结束时间恰好为次日 00:00（24:00 特例）允许通过；其余跨天一律拦截
    if start_dt.date() != end_dt.date() and not end_is_midnight:
        return None, None, None, None, None, "不支持跨天预订，请调整时间"
    
    # 时长检查：5-240分钟
    duration_minutes = (end_dt - start_dt).total_seconds() / 60
    if duration_minutes < 5 or duration_minutes > 240:
        return None, None, None, None, None, f"时长必须在5-240分钟之间，当前: {duration_minutes}分钟"
    
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(end_dt.timestamp() * 1000)
    
    return start_dt, end_dt, start_ts, end_ts, date_ts, None

def _classify_rooms_by_type(rooms):
    """
    将会议室列表按类型分组。
    返回 (training_rooms, normal_rooms)
    """
    training_rooms = []
    normal_rooms = []
    for room in rooms:
        if is_training_room(room.get('name', '')):
            training_rooms.append(room)
        else:
            normal_rooms.append(room)
    return training_rooms, normal_rooms

def _get_attendee_ids(hdrs, mis_id, attendees=None):
    """
    获取组织者和参会人的empId列表。
    返回 (organizer_eid, attendee_ids, err_msg)
    """
    # 获取组织者 empId
    acct = api('https://calendar.sankuai.com/api/v2/xm/meeting/dataset/account', hdrs, {"filter": mis_id})
    eid = None
    for u in acct.get('data', []):
        if u.get('mis') == mis_id:
            eid = str(u['empId'])
            break
    if not eid and acct.get('data'):
        eid = str(acct['data'][0]['empId'])
    if not eid:
        return None, None, f"未找到 {mis_id} 的 empId"
    
    # 获取参会人 empId 列表
    attendee_ids = [eid]  # 始终包含组织者自己
    attendee_names = []
    
    if attendees:
        for att_mis in attendees:
            att_resp = api('https://calendar.sankuai.com/api/v2/xm/meeting/dataset/account', hdrs, {"filter": att_mis})
            if att_resp.get('code') == 200 and att_resp.get('data'):
                att_id = str(att_resp['data'][0]['empId'])
                att_name = att_resp['data'][0]['name']
                if att_id not in attendee_ids:
                    attendee_ids.append(att_id)
                    attendee_names.append(att_name)
        if attendee_names:
            print(f"✅ 参会人: {', '.join(attendee_names)}")
    
    return eid, attendee_ids, None

def _detect_auth_strategy():
    """
    选择认证策略，优先级：
    1. catpaw_exchange：~/.catpaw/sso_config.json 存在 → CatPaw Desk 换票方案
    2. ciba：sso_config.json 不存在 + IDENTIFIER/sandbox.json 存在 → CIBA 大象授权
    3. browser：都没有 → 浏览器 fetch 降级（尝试读取 cookie.json）
    """
    if SSO_CONFIG_FILE.exists():
        return "catpaw_exchange"
    if os.environ.get("IDENTIFIER") or Path("/root/.openclaw/config/sandbox.json").exists():
        return "ciba"
    return "browser"


def _load_ssoid_from_config():
    """
    从 ~/.catpaw/sso_config.json 读取 CatPaw Desk 的 ssoid，
    再调换票接口换取 calendar.sankuai.com 专属 token。
    返回 cookie 字符串，或 None（文件不存在/换票失败）。
    """
    if not SSO_CONFIG_FILE.exists():
        return None
    try:
        with open(SSO_CONFIG_FILE) as f:
            data = json.load(f)
        catpaw_ssoid = data.get("ssoid", "")
        if not catpaw_ssoid:
            return None
    except Exception:
        return None

    # 用 CatPaw Desk 的 ssoid 换取 calendar.sankuai.com 的 cookie（按 domain 换票）
    try:
        result = subprocess.run(
            [
                "curl", "--noproxy", "*", "-s", "-X", "POST",
                "https://supabase.sankuai.com/api/sandbox/sso/exchange-token",
                "-H", "Content-Type: application/json",
                "-d", json.dumps({"accessToken": catpaw_ssoid, "domain": "calendar.sankuai.com"}),
            ],
            capture_output=True, text=True, timeout=30
        )
        exchange_result = json.loads(result.stdout)
        if exchange_result.get("code") == 0:
            cookie_list = exchange_result.get("data", [])
            if isinstance(cookie_list, list) and cookie_list:
                cookie_str = "; ".join(
                    f"{c['name']}={c['value']}"
                    for c in cookie_list
                    if c.get('name') and c.get('value')
                )
                if cookie_str:
                    return cookie_str
    except Exception:
        pass
    return None


def _merge_cookie(base_cookie, new_pairs):
    """
    将 new_pairs（dict，如 {"37facae47f_ssoid": "AT_xxx"}）注入到 base_cookie 字符串中。
    若 base_cookie 中已有同名 key，则替换；否则追加。
    """
    if not base_cookie:
        return "; ".join(f"{k}={v}" for k, v in new_pairs.items())
    # 解析 base_cookie 为 dict
    parts = {}
    for part in base_cookie.split(";"):
        part = part.strip()
        if "=" in part:
            k, _, v = part.partition("=")
            parts[k.strip()] = v.strip()
    # 注入新 pairs
    parts.update(new_pairs)
    return "; ".join(f"{k}={v}" for k, v in parts.items())


def load_cookie():
    """
    加载 cookie 字符串，自动选择认证策略：
    - catpaw_exchange：从 sso_config.json 换票获取新 ssoid，注入到 cookie.json 的完整 cookie 中
    - ciba：从 cookie.json 读取（Sandbox/CIBA 流程写入）
    - browser：尝试读取 cookie.json（手动保存或旧版 sso-login.sh 写入）
    返回 (cookie_str, mis_id)，cookie_str 为 None 时表示需要重新认证。
    """
    strategy = _detect_auth_strategy()

    # 先读取 cookie.json 里的基础 cookie（如果存在）
    base_cookie = ""
    base_mis = ""
    if COOKIE_FILE.exists():
        try:
            with open(COOKIE_FILE) as f:
                d = json.load(f)
            base_cookie = d.get("cookie", "")
            base_mis = d.get("mis", "")
        except Exception:
            pass

    if strategy == "catpaw_exchange":
        # 换票获取新 ssoid，注入到基础 cookie 中
        new_cookie_str = _load_ssoid_from_config()
        if new_cookie_str:
            # new_cookie_str 格式：name=value（如 37facae47f_ssoid=AT_xxx）
            new_pairs = {}
            for part in new_cookie_str.split(";"):
                part = part.strip()
                if "=" in part:
                    k, _, v = part.partition("=")
                    new_pairs[k.strip()] = v.strip()
            merged = _merge_cookie(base_cookie, new_pairs)
            return merged, base_mis
        # 换票失败，降级到直接使用 cookie.json
        if base_cookie:
            return base_cookie, base_mis
        return None, ""

    if strategy == "ciba":
        if base_cookie:
            return base_cookie, base_mis
        return None, ""

    # browser 策略：直接使用 cookie.json
    if base_cookie:
        return base_cookie, base_mis
    return None, ""

def headers(cookie):
    """构建标准请求头"""
    return {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/plain, */*',
        'X-Requested-With': 'XMLHttpRequest',
        'X-Request-Source': 'OpenClaw-Agent',
        'M-UserContext': 'eyJsb2NhbGUiOiJ6aCIsInRpbWVab25lIjoiQXNpYS9TaGFuZ2hhaSJ9',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Cookie': cookie
    }

def api(url, hdrs, data=None):
    """API 请求封装（仅支持POST），自动检测认证失败"""
    if USE_REQUESTS:
        r = req_lib.post(url, headers=hdrs, json=data, timeout=30)
        result = r.json()
        # 检测 SSO 登录失效
        if result.get('code') in (30002, 401) or 'ssoid' in str(result.get('data', {})):
            raise Exception("AUTH_EXPIRED")
        return result
    body = json.dumps(data).encode() if data else None
    rq = urllib.request.Request(url, data=body, headers=hdrs, method='POST')
    with urllib.request.urlopen(rq, context=_ssl_ctx, timeout=30) as rp:
        result = json.loads(rp.read().decode())
        if result.get('code') in (30002, 401) or 'ssoid' in str(result.get('data', {})):
            raise Exception("AUTH_EXPIRED")
        return result

def cap_range(n):
    """
    根据人数需求返回容量范围。
    
    关键理解：
    容量范围（如"1-6人"、"7-14人"）代表的是会议室的"品类"。
    同一品类内的会议室容量可能不同（如"1-6人"品类可能包含5人、6人的房间）。
    
    匹配策略：
    为确保预订的会议室容量 >= 所需人数 n：
    1. 优先选择包含 n 的范围（lo <= n <= hi）
    2. 如果该范围的会议室实际容量可能 < n（如求6人但范围内最大是6），
       需要向上查询下一个更大的范围来获得容量更大的会议室
    3. 特殊处理：对于范围上限 = n 的情况（如n=6，范围1-6），
       向上查询下一个范围确保获得 >= 6 的会议室
    
    实际策略：对 n 向上到下一个范围的下限（如 n=6 → 7），再查询该范围
    """
    ranges = [(1,6,"1-6人"),(7,14,"7-14人"),(15,21,"15-21人"),(22,40,"22-40人"),(41,60,"41-60人"),(61,200,"61+人")]
    
    # 在范围内查找：找第一个上限 >= n 的范围
    for lo, hi, name in ranges:
        if hi >= n:
            # 特殊处理：如果 n 等于该范围的上限（如n=6，范围1-6），
            # 为了确保容量充足，向上查询下一个范围
            if n == hi and hi < 200:  # 如果不是最后一个范围
                # 找下一个范围
                for lo_next, hi_next, name_next in ranges:
                    if lo_next > hi:
                        return {"capacityMin": lo_next, "capacityMax": hi_next, "name": name_next}
            return {"capacityMin": lo, "capacityMax": hi, "name": name}
    
    # 如果没找到，返回最后一个（最大容量）
    return {"capacityMin": 61, "capacityMax": 200, "name": "61+人"}

def match_equipment(equip_keywords, hdrs):
    """
    根据设备关键词匹配设备ID列表。
    支持模糊匹配，如 "Zoom", "投影", "腾讯会议" 等
    返回 (equip_ids, err_msg)
    """
    if not equip_keywords:
        return [], None
    
    try:
        resp = api('https://calendar.sankuai.com/room/front/pc/room/moreInfo', hdrs, {})
        equips_list = resp.get('data', {}).get('equips', [])
    except:
        return None, "获取设备列表失败"
    
    result_ids = []
    unmatched = []
    
    for kw in equip_keywords:
        kw_lower = kw.lower()
        found = False
        for eq in equips_list:
            eq_name = eq.get('name', '').lower()
            # 模糊匹配：支持 "投影" 匹配 "投影仪"、"Zoom" 匹配 "Zoom" 等
            if kw_lower in eq_name or eq_name in kw_lower:
                result_ids.append(eq['id'])
                found = True
                break
        if not found:
            unmatched.append(kw)
    
    if unmatched:
        avail = [eq['name'] for eq in equips_list]
        return None, f"未找到设备: {', '.join(unmatched)}。可用设备: {', '.join(avail)}"
    
    return result_ids, None

def find_building_interactive(city_kw, hdrs):
    """
    交互式模式：支持模糊查询建筑，若有多个匹配则让用户选择。
    返回 (bid, bname, all_fids, err)
    """
    # 优先使用缓存管理器检查缓存
    cache_data = CACHE_MANAGER.get_buildings_cache()
    if cache_data is None:
        print("📦 缓存不存在或已过期，从 API 获取建筑列表...")
        try:
            if not fetch_and_cache_buildings(hdrs):
                return None, None, None, "获取建筑列表失败"
            cache_data = CACHE_MANAGER.get_buildings_cache()
        except Exception as e:
            if "AUTH_EXPIRED" in str(e):
                return None, None, None, "❌ Cookie 已过期，请重新执行 SSO 登录"
            raise
    
    cache = {"data": cache_data}
    
    city_kw_norm = city_kw.lower().replace(' ', '')
    
    # 查找匹配的城市
    matching_cities = []
    for city in cache.get('data', {}).get('cityList', []):
        city_name = city.get('cityName', '')
        city_name_norm = city_name.lower().replace(' ', '')
        if city_kw in city_name or city_kw_norm in city_name_norm:
            matching_cities.append((city_name, city))
    
    if not matching_cities:
        return None, None, None, f"未找到城市 '{city_kw}'"
    
    if len(matching_cities) > 1:
        print(f"\n🏙️  找到多个城市匹配 '{city_kw}':")
        for i, (city_name, _) in enumerate(matching_cities, 1):
            print(f"   {i}. {city_name}")
        choice = input("请选择城市编号: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(matching_cities):
                city_name, city = matching_cities[idx]
            else:
                return None, None, None, "选择无效"
        except:
            return None, None, None, "输入错误"
    else:
        city_name, city = matching_cities[0]
    
    print(f"✅ 城市: {city_name}")
    
    # 获取该城市的所有建筑
    buildings = city.get('buildings', [])
    if not buildings:
        return None, None, None, f"城市 {city_name} 内没有可用建筑"
    
    print(f"\n🏢 该城市有 {len(buildings)} 个建筑:")
    for i, b in enumerate(buildings, 1):
        print(f"   {i}. {b['buildingName']}")
    
    choice = input("请选择建筑编号（或输入部分名称查询）: ").strip()
    
    # 尝试按编号选择
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(buildings):
            b = buildings[idx]
            fids = [fl['floorId'] for fl in b.get('floors', [])]
            return b['buildingId'], b['buildingName'], fids, None
    except ValueError:
        pass
    
    # 按名称模糊查询
    matching_buildings = []
    choice_lower = choice.lower()
    for b in buildings:
        b_name_lower = b['buildingName'].lower()
        if choice_lower in b_name_lower or b_name_lower in choice_lower:
            matching_buildings.append(b)
    
    if len(matching_buildings) == 1:
        b = matching_buildings[0]
        fids = [fl['floorId'] for fl in b.get('floors', [])]
        return b['buildingId'], b['buildingName'], fids, None
    elif len(matching_buildings) > 1:
        print(f"\n🏢 找到 {len(matching_buildings)} 个匹配的建筑:")
        for i, b in enumerate(matching_buildings, 1):
            print(f"   {i}. {b['buildingName']}")
        choice2 = input("请选择建筑编号: ").strip()
        try:
            idx = int(choice2) - 1
            if 0 <= idx < len(matching_buildings):
                b = matching_buildings[idx]
                fids = [fl['floorId'] for fl in b.get('floors', [])]
                return b['buildingId'], b['buildingName'], fids, None
        except:
            pass
        return None, None, None, "选择无效"
    else:
        return None, None, None, f"未找到建筑 '{choice}'"

# ── building lookup ────────────────────────────────────────

def _find_building_with_refresh(city_kw, bld_kw, hdrs):
    """
    从缓存查找建筑，失败时自动刷新缓存重试。
    返回 (id, fullName, floorIds, err_msg)
    """
    bid, bname, fids, err = find_building(city_kw, bld_kw)
    if err:
        if err == "no_cache":
            print("📦 缓存不存在或已过期，从 API 获取建筑列表...")
        else:
            print(f"⚠️ {err}，重新获取...")
        try:
            if not fetch_and_cache_buildings(hdrs):
                return None, None, None, "获取建筑列表失败"
        except Exception as e:
            if "AUTH_EXPIRED" in str(e):
                return None, None, None, "❌ Cookie 已过期，请重新执行 SSO 登录: bash scripts/sso-login.sh <misId>"
            raise
        bid, bname, fids, err = find_building(city_kw, bld_kw)
        if err:
            return None, None, None, err
    return bid, bname, fids, None

def find_building(city_kw, bld_kw):
    """从缓存查找建筑，返回 (id, fullName, all_floor_ids, err)"""
    cache_data = CACHE_MANAGER.get_buildings_cache()
    if cache_data is None:
        return None, None, None, "no_cache"
    cache = {"data": cache_data}
    # 模糊匹配：忽略大小写和空格
    city_kw_norm = city_kw.lower().replace(' ', '')
    bld_kw_norm = bld_kw.lower().replace(' ', '')
    for city in cache.get('data', {}).get('cityList', []):
        city_name_norm = city.get('cityName', '').lower().replace(' ', '')
        if city_kw in city.get('cityName', '') or city_kw_norm in city_name_norm:
            for b in city.get('buildings', []):
                bld_name_norm = b.get('buildingName', '').lower().replace(' ', '')
                if bld_kw in b.get('buildingName', '') or bld_kw_norm in bld_name_norm:
                    fids = [fl['floorId'] for fl in b.get('floors', [])]
                    return b['buildingId'], b['buildingName'], fids, None
            avail = [b['buildingName'] for b in city.get('buildings', [])]
            return None, None, None, f"城市{city['cityName']}内未匹配建筑'{bld_kw}'，可选: {avail}"
    return None, None, None, f"未找到城市'{city_kw}'"

def match_floor_names(floor_names, city_kw, bld_kw):
    """
    根据楼层名称匹配楼层ID。
    返回 (matched_floor_ids, err_msg)
    """
    if not floor_names:
        return None, None  # None 表示查询所有楼层
    
    cache_data = CACHE_MANAGER.get_buildings_cache()
    if cache_data is None:
        return None, "缓存文件不存在或已过期"
    
    cache = {"data": cache_data}
    
    # 查找对应的建筑
    city_kw_norm = city_kw.lower().replace(' ', '')
    bld_kw_norm = bld_kw.lower().replace(' ', '')
    
    for city in cache.get('data', {}).get('cityList', []):
        city_name_norm = city.get('cityName', '').lower().replace(' ', '')
        if city_kw in city.get('cityName', '') or city_kw_norm in city_name_norm:
            for b in city.get('buildings', []):
                bld_name_norm = b.get('buildingName', '').lower().replace(' ', '')
                if bld_kw in b.get('buildingName', '') or bld_kw_norm in bld_name_norm:
                    floors = b.get('floors', [])
                    matched_ids = []
                    unmatched = []
                    
                    # 对每个用户输入的楼层名称进行模糊匹配
                    for fname in floor_names:
                        fname_norm = fname.lower().replace(' ', '').replace('层', '')
                        matched = False
                        
                        for fl in floors:
                            fl_name = fl.get('floorName', '')
                            fl_name_norm = fl_name.lower().replace(' ', '').replace('层', '')
                            
                            # 模糊匹配：支持 "2"匹配"2层"、"11"匹配"11层" 等
                            if fname_norm in fl_name_norm or fl_name_norm in fname_norm:
                                matched_ids.append(fl['floorId'])
                                matched = True
                                break
                        
                        if not matched:
                            unmatched.append(fname)
                    
                    if unmatched:
                        avail_floors = [fl['floorName'] for fl in floors]
                        return None, f"未找到楼层: {', '.join(unmatched)}。可用楼层: {', '.join(avail_floors)}"
                    
                    return matched_ids, None
    
    return None, f"未找到建筑 {city_kw}/{bld_kw}"

def fetch_and_cache_buildings(hdrs):
    """从 API 获取建筑列表并缓存（兼容两种 API 返回格式）"""
    resp = api('https://calendar.sankuai.com/room/front/app/room/cityBuilding', hdrs, {})
    if resp.get('code') != 200:
        return False
    cache_data = {"cityList": []}
    for c in resp.get('data', []):
        co = {"cityId": c['code'], "cityName": c['name'], "buildings": []}
        for b in (c.get('children') or []):
            bo = {"buildingId": b['code'], "buildingName": b['name'], "floors": []}
            for f in (b.get('children') or []):
                bo['floors'].append({"floorId": f['code'], "floorName": f['name']})
            co['buildings'].append(bo)
        cache_data['cityList'].append(co)
    # 使用缓存管理器保存缓存
    return CACHE_MANAGER.save_buildings_cache(cache_data)

# ── main flow ──────────────────────────────────────────────

def quick_book(city, building, date_str, start_time, end_time, capacity=5, mis_id=None, attendees=None, window=None, floors=None, equips=None, interactive=False):
    """
    一体化快速预订。
    返回 (success, message, details_dict)
    
    参数:
        floors: 楼层名称列表，如 ["2层", "3层"] 或 ["11", "12"]。None表示查询所有楼层。
        equips: 设备名称列表，如 ["Zoom", "投影"]。支持模糊匹配。
        interactive: 是否启用交互式模式（模糊建筑查询 + 列表选择）。若True，则building参数可为空。
    """
    # 1. cookie
    cookie, default_mis = load_cookie()
    if not cookie:
        strategy = _detect_auth_strategy()
        hints = {
            "catpaw_exchange": "sso_config.json 换票失败，CatPaw Desk token 可能已过期，请重新登录 CatPaw Desk",
            "ciba": "请运行 CIBA 认证：python3 ~/.catpaw/skills/room-booking-helper/scripts/rbh_sso.py ciba-login <misId>",
            "browser": "请手动获取 cookie 后运行：python3 ~/.catpaw/skills/room-booking-helper/scripts/rbh_sso.py save-cookie <cookie_str>",
        }
        return False, f"未找到有效登录态，需要重新认证。{hints.get(strategy, '请重新认证')}", {}
    mis_id = mis_id or default_mis
    if not mis_id:
        return False, "❌ 未指定 MIS 账号，且 cookie.json 中也没有保存的 MIS 信息。请运行 --mis <misId> 参数或先完成 SSO 认证", {}
    hdrs = headers(cookie)

    # 2. 定位建筑（支持交互式或快速模式）
    if interactive and not building:
        # 交互式模式：支持模糊查询和列表选择
        bid, bname, all_fids, err = find_building_interactive(city, hdrs)
    else:
        # 快速模式：直接模糊匹配
        bid, bname, all_fids, err = _find_building_with_refresh(city, building or "", hdrs)
    
    if err:
        return False, err, {}
    print(f"✅ 建筑: {bname} (ID:{bid})")
    
    # 3. 匹配楼层（如果指定了楼层）
    if floors:
        fids, err = match_floor_names(floors, city, building)
        if err:
            return False, err, {}
        print(f"✅ 楼层: {', '.join(floors)} (匹配到 {len(fids)} 个)")
    else:
        fids = []  # 空列表表示查询所有楼层
        print(f"✅ 楼层: 不限（查询所有楼层）")

    # 4. 时间计算与验证
    start_dt, end_dt, start_ts, end_ts, date_ts, err = _parse_and_validate_time(date_str, start_time, end_time)
    if err:
        return False, err, {}
    
    # 5. 预订窗口预检查（在查询会议室前）
    today = datetime.now(TZ).date()
    target_date = start_dt.date()
    days_ahead = (target_date - today).days
    
    # 注：由于无法提前知道会议室类型，这里先用普通会议室的限制（8天）
    # 如果用户实际要订培训会议室（30天），在查询到会议室后会重新验证
    if days_ahead > 30:
        return False, f"预订日期过远（第{days_ahead}天），培训会议室最多可预订未来30天，请调整日期", {}
    
    # 6. 查会议室（带设备筛选）
    # 构建设备筛选参数
    equip_ids = []
    if equips:
        equip_ids, err = match_equipment(equips, hdrs)
        if err:
            return False, err, {}
        if equip_ids:
            print(f"✅ 设备: {', '.join(equips)}")
    
    # 查询接口不接受 "24:00"，当结束时间为 24:00 时用 "23:55" 替代（仅用于查询）
    query_end_time = "23:55" if end_time == "24:00" else end_time
    _find_rooms_resp = api(
        'https://calendar.sankuai.com/meeting/api/pc/room/appointment/v2/find-rooms',
        hdrs, {
            "date": date_ts,
            "buildingId": str(bid),
            "floorIds": fids,
            "capacity": [cap_range(capacity)],
            "startTime": start_time,
            "endTime": query_end_time,
            "equipmentIds": equip_ids if equip_ids else []
        }
    )
    rooms = _find_rooms_resp.get('data', [])
    # 正确处理错误响应：data 为 dict（含 errorCode）或空列表时均视为无结果
    if not isinstance(rooms, list) or not rooms:
        filter_desc = cap_range(capacity)['name']
        if equips:
            filter_desc += f", {', '.join(equips)}"
        err_detail = ""
        if isinstance(rooms, dict) and rooms.get('errorCode'):
            err_detail = f"（服务端错误 {rooms.get('errorCode')}: {rooms.get('message', '')}）"
        return False, f"无符合条件的会议室 ({filter_desc}){err_detail}", {}
    print(f"✅ 候选: {len(rooms)} 个")
    
    # 7. 窗户筛选（如果指定了窗户偏好）
    if window:
        window_value = 1 if window.upper() in ('EXIST', '有窗') else 0
        filtered_rooms = [r for r in rooms if r.get('window', 0) == window_value]
        if not filtered_rooms:
            window_desc = "有窗" if window.upper() in ('EXIST', '有窗') else "无窗"
            return False, f"⚠️ 没有找到{window_desc}的会议室", {}
        rooms = filtered_rooms
        window_desc = "有窗" if window.upper() in ('EXIST', '有窗') else "无窗"
        print(f"🪟 按窗户筛选后: {len(rooms)} 个")

    # 9. 按会议室类型分组并验证预订窗口
    training_rooms, normal_rooms = _classify_rooms_by_type(rooms)
    
    # 根据实际查询到的会议室类型验证预订窗口
    if training_rooms and not normal_rooms:
        # 全是培训会议室
        if days_ahead > 30:
            return False, f"培训会议室只能预订未来30天内的，当前为第{days_ahead}天，请调整日期", {}
    elif normal_rooms and not training_rooms:
        # 全是普通会议室
        if days_ahead > 8:
            return False, f"普通会议室只能预订未来8天内的，当前为第{days_ahead}天，请调整日期", {}
    else:
        # 混合类型：过滤掉超出窗口的会议室
        if days_ahead > 8:
            rooms = training_rooms  # 只保留培训会议室
            print(f"⚠️ 第{days_ahead}天超出普通会议室窗口(8天)，已过滤为培训会议室: {len(rooms)}个")
            if not rooms:
                return False, f"普通会议室只能预订未来8天，培训会议室可预订30天，但当前无可用培训会议室", {}
        # days_ahead <= 8 时，两种类型都可以预订

    # 10. 查预订 → 筛选空闲
    rmap = {r['id']: r for r in rooms}
    appt = api(
        'https://calendar.sankuai.com/meeting/api/pc/room/appointment/findRoomAppointmentsV2',
        hdrs, {"date": date_ts, "roomIds": list(rmap.keys())}
    )
    free, busy, offline = [], 0, 0
    for ra in appt.get('data', []):
        rid = ra['roomId']
        apts = ra.get('appointmentVOS') or []
        # roomSubscribe 有值表示全天已被人预约（长期预订/已下线），直接跳过
        if ra.get('roomSubscribe'):
            offline += 1; continue
        # appointmentVOS 有值表示部分时段已被预约，检查是否与目标时段重叠
        # 重叠条件：appt_start < target_end AND appt_end > target_start
        if any(a['startTime'] < end_ts and a['endTime'] > start_ts for a in apts):
            busy += 1; continue
        free.append(rmap[rid])
    print(f"✅ 空闲:{len(free)} 占用:{busy} 下线:{offline}")

    if not free:
        return _create_monitor(hdrs, cookie, bid, fids if fids else all_fids, start_ts, end_ts, capacity)

    # 11. 获取组织者和参会人 empId
    eid, attendee_ids, err = _get_attendee_ids(hdrs, mis_id, attendees)
    if err:
        return False, err, {}

    # 12. 批量尝试预订
    for rm in free:
        body = {
            "title": f"{mis_id}的会议",
            "startTime": start_ts, "endTime": end_ts, "isAllDay": 0,
            "location": "", "attendees": attendee_ids,
            "noticeType": 0, "noticeRule": "P0Y0M0DT0H10M0S",
            "recurrencePattern": {"type":"NONE","showType":"NONE"},
            "deadline": 0, "memo": "", "organizer": eid,
            "room": {
                "id": rm['id'], "name": rm['name'], "email": rm.get('email',''),
                "capacity": rm.get('capacity',5), "disabled": 0,
                "floorId": rm.get('floorId',0), "floorName": rm.get('floorName',''),
                "buildingId": bid, "buildingName": bname
            },
            "appKey": "meeting", "bookType": 11
        }
        try:
            r = api('https://calendar.sankuai.com/api/v2/xm/schedules', hdrs, body)
            if r.get('code') == 200 or r.get('message') == '成功':
                sid = r.get('data',{}).get('scheduleId') if isinstance(r.get('data'), dict) else r.get('data')
                return True, "预订成功", {
                    "room": rm['name'], "floor": rm.get('floorName',''),
                    "capacity": rm.get('capacity',5), "building": bname,
                    "date": date_str, "time": f"{start_time}-{end_time}",
                    "schedule_id": sid,
                    "roomLocationUrl": rm.get('roomLocationUrl', ''),
                    "roomMap": rm.get('roomMap', '')
                }
            msg = r.get('data',{}).get('message','') if isinstance(r.get('data'),dict) else r.get('message','')
            
            # 致命错误：立即中断
            if '同时预订' in str(msg):
                return False, f"同时段预订超限: {msg}", {}
            if 'AUTH_EXPIRED' in str(msg) or r.get('code') in (30002, 401):
                return False, "❌ Cookie 已过期，请重新执行 SSO 登录", {}
            
            # 会议室级别错误：继续尝试下一个
            print(f"  ⚠️ {rm['name']}: {msg}")
        except Exception as e:
            if "AUTH_EXPIRED" in str(e):
                return False, "❌ Cookie 已过期，请重新执行 SSO 登录", {}
            print(f"  ⚠️ {rm['name']}: {e}")

    return _create_monitor(hdrs, cookie, bid, fids if fids else all_fids, start_ts, end_ts, capacity)

def _create_monitor(hdrs, cookie, bid, fids, start_ts, end_ts, cap):
    """创建空闲监测任务"""
    # 监测接口需要额外的请求头
    mh = headers(cookie)
    mh.update({
        'Referer': 'https://calendar.sankuai.com/rooms',
        'tz': 'Asia/Shanghai',
        'la': 'zh'
    })
    try:
        mr = api('https://calendar.sankuai.com/room/front/appointment-room/insertV2', mh,
                 {"buildingId":bid,"planStartTimestamp":start_ts,"planEndTimestamp":end_ts,"floorIds":fids or [],"headCount":cap})
        if mr.get('code') == 200:
            return False, f"无空闲会议室，已创建监测: {mr.get('data')}", {"monitor":True}
        if mr.get('code') == 50801:
            return False, "无空闲会议室，该时段已有监测任务", {"monitor":True}
        return False, f"无空闲，监测创建失败: {mr.get('message')}", {}
    except Exception as e:
        return False, f"无空闲，监测异常: {e}", {}

# ── CLI ────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description='快速预订会议室')
    p.add_argument('--city', required=True, help='城市名称，如：上海')
    p.add_argument('--building', help='建筑名称，如：D2（在--interactive模式下可不指定）')
    p.add_argument('--date', required=True, help='日期，格式：YYYY-MM-DD')
    p.add_argument('--start', required=True, help='开始时间，格式：HH:MM')
    p.add_argument('--end', required=True, help='结束时间，格式：HH:MM')
    p.add_argument('--capacity', type=int, default=5, help='容纳人数，默认5人')
    p.add_argument('--floors', nargs='*', help='楼层名称列表，如：2层 3层 或 11 12（支持多个，不指定则查询所有楼层）')
    p.add_argument('--window', choices=['EXIST', 'NONE'], help='窗户选项: EXIST=有窗, NONE=无窗')
    p.add_argument('--equips', nargs='*', help='设备名称列表，如：Zoom 投影（支持模糊匹配）')
    p.add_argument('--mis', help='MIS账号')
    p.add_argument('--attendees', nargs='*', help='参会人MIS账号列表')
    p.add_argument('--interactive', action='store_true', help='启用交互式模式（支持模糊建筑查询和列表选择）')
    a = p.parse_args()

    # 验证参数
    if not a.interactive and not a.building:
        print("❌ 错误: 在非交互式模式下，--building 参数是必需的")
        print("   或者使用 --interactive 参数启用交互式模式")
        sys.exit(1)

    ok, msg, det = quick_book(a.city, a.building, a.date, a.start, a.end, a.capacity, a.mis, a.attendees, a.window, a.floors, a.equips, a.interactive)

    print(f"\n{'='*50}")
    if ok:
        print("✅ 预订成功！")
        for k in ['room','floor','capacity','building','date','time']:
            if det.get(k): print(f"  {k}: {det[k]}")
        # 显示位置信息
        if det.get('roomMap'):
            print(f"  🗺️ 位置地图: ![会议室地图]({det['roomMap']})")
        if det.get('roomLocationUrl'):
            print(f"  📍 位置地图: {det['roomLocationUrl']}")
       
    else:
        print(f"❌ {msg}")
    print('='*50)
    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    main()
